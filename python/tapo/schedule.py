"""Schedule rules for Tapo plugs.

Example: "turn the boiler on between 11:00 and 15:00 if SOC > 70% and PV generation > 2 kW".

Semantics
- A rule is *satisfied* when now is inside its window (days + start/end, windows may cross midnight)
  and all its conditions hold. Conditions use hysteresis so passing clouds don't toggle the plug.
- The engine turns a plug ON when any of its rules has been satisfied for ON_DELAY seconds and
  turns it OFF only if *the engine* turned it on and no rule is satisfied anymore (after OFF_DELAY,
  or immediately when the window has ended). Plugs switched on manually are never turned off.
- A manual on/off of the plug during an active window pauses the rules of that plug until the
  window ends (the user's decision wins).
- A plug disabled by the load-shedding manager is not switched back on by a rule.
"""
import asyncio
import re
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

import python.db as db
from python.auth.verify_token import require_admin
from python.data_store import data_store
from python.push_notifications import send_push_notification
from python.tapo.tapo_service import get_tapo_device

router = APIRouter(prefix="/tapo/rules", tags=["TP-Link Tapo schedule"])

POLL_SECONDS = 20
ON_DELAY_SECONDS = 60
OFF_DELAY_SECONDS = 180
SOC_HYSTERESIS = 3.0           # % below min_soc before an already-on plug is switched off
PV_HYSTERESIS_RATIO = 0.8      # keep on while PV >= 80% of min_pv_w
METRICS_MAX_AGE_SECONDS = 120  # Deye data older than this is treated as unknown

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Runtime state (memory only)
_engine_on: dict[str, set[int]] = {}           # ip -> ids of rules that switched it on
_satisfied_since: dict[int, float] = {}        # rule id -> monotonic time conditions became true
_unsatisfied_since: dict[int, float] = {}      # rule id -> monotonic time conditions became false
_manual_override: set[str] = set()             # ips paused until their windows end
_rule_status: dict[int, dict] = {}             # rule id -> status shown in the UI


# ---------------------------------------------------------------- helpers

def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def in_window(rule: dict, now: datetime) -> bool:
    start, end = _minutes(rule["start_time"]), _minutes(rule["end_time"])
    minute = now.hour * 60 + now.minute
    days = rule.get("days") or "0123456"
    if start <= end:
        return str(now.weekday()) in days and start <= minute < end
    # Window crosses midnight: the part after midnight belongs to the previous day's schedule.
    if minute >= start:
        return str(now.weekday()) in days
    if minute < end:
        return str((now - timedelta(days=1)).weekday()) in days
    return False


def note_manual_action(ip: str):
    """Called by the manual on/off endpoints: rules for this plug pause until their window ends."""
    if any(in_window(r, datetime.now()) for r in db.list_tapo_rules() if r["ip"] == ip and r["enabled"]):
        _manual_override.add(ip)
    _engine_on.pop(ip, None)


async def collect_metrics() -> dict:
    """SOC (BMS preferred, Deye as fallback) and PV generation (sum of Deye inverters)."""
    soc = None
    cell_info = await data_store.get_cell_info()
    capacities = [(b.get("remaining_capacity") or 0, b.get("nominal_capacity") or 0) for b in cell_info.values()]
    total_nominal = sum(c for _, c in capacities)
    if total_nominal:
        soc = sum(r for r, _ in capacities) / total_nominal * 100

    pv = None
    deye_soc = []
    now_utc = datetime.utcnow()
    for device in await asyncio.to_thread(db.get_all_deye_devices):
        try:
            age = (now_utc - datetime.fromisoformat(device["timestamp"])).total_seconds() if device.get("timestamp") else None
        except ValueError:
            age = None
        if age is None or age > METRICS_MAX_AGE_SECONDS:
            continue
        pv = (pv or 0) + (device.get("total_pv") or 0)
        if device.get("battery_soc") is not None:
            deye_soc.append(device["battery_soc"])
    if soc is None and deye_soc:
        soc = sum(deye_soc) / len(deye_soc)
    return {"soc": soc, "pv_w": pv}


def evaluate_rule(rule: dict, metrics: dict, now: datetime, currently_on: bool) -> tuple[bool, bool, str]:
    """Returns (window_active, conditions_ok, human readable reason)."""
    if not rule["enabled"]:
        return False, False, "Вимкнене правило"
    if not in_window(rule, now):
        return False, False, f"Очікує вікна {rule['start_time']}–{rule['end_time']}"

    soc, pv = metrics.get("soc"), metrics.get("pv_w")
    if rule.get("min_soc") is not None:
        need = rule["min_soc"] - (SOC_HYSTERESIS if currently_on else 0)
        if soc is None:
            return True, False, "Немає даних SOC"
        if soc < need:
            return True, False, f"SOC {soc:.0f}% < {rule['min_soc']:.0f}%"
    if rule.get("min_pv_w") is not None:
        need = rule["min_pv_w"] * (PV_HYSTERESIS_RATIO if currently_on else 1)
        if pv is None:
            return True, False, "Немає свіжих даних генерації"
        if pv < need:
            return True, False, f"Генерація {pv / 1000:.2f} кВт < {rule['min_pv_w'] / 1000:.2f} кВт"
    return True, True, "Умови виконані"


async def _switch(device: dict, turn_on: bool) -> bool:
    try:
        tapo = get_tapo_device(device["ip"], device["email"], device["password"])
        await asyncio.to_thread(tapo.turn_on if turn_on else tapo.turn_off)
        await asyncio.to_thread(db.update_tapo_device_by_ip, device["ip"], {"device_on": 1 if turn_on else 0})
        return True
    except Exception as e:
        print(f"❌ Schedule: failed to switch {device['ip']}: {e}")
        return False


# ---------------------------------------------------------------- engine

async def run_tapo_schedule_loop():
    while True:
        try:
            await tick()
        except Exception as e:
            print(f"❌ Tapo schedule error: {e}")
        await asyncio.sleep(POLL_SECONDS)


async def tick(now: Optional[datetime] = None):
    from python.tapo.manage_device_power import disabled_devices  # avoid import cycle at module load

    now = now or datetime.now()
    mono = time.monotonic()
    rules = await asyncio.to_thread(db.list_tapo_rules)
    if not rules:
        _engine_on.clear()
        return
    devices = {d["ip"]: d for d in await asyncio.to_thread(db.get_all_tapo_devices)}
    metrics = await collect_metrics()

    by_ip: dict[str, list[dict]] = {}
    for rule in rules:
        by_ip.setdefault(rule["ip"], []).append(rule)

    for ip, ip_rules in by_ip.items():
        device = devices.get(ip)
        if not device:
            continue
        currently_on = bool(device.get("device_on"))
        any_window = False
        wants_on: list[dict] = []
        must_off = False

        for rule in ip_rules:
            window, ok, reason = evaluate_rule(rule, metrics, now, currently_on)
            any_window = any_window or window
            rid = rule["id"]
            if ok:
                _unsatisfied_since.pop(rid, None)
                started = _satisfied_since.setdefault(rid, mono)
                if mono - started >= ON_DELAY_SECONDS:
                    wants_on.append(rule)
                else:
                    reason = f"Умови виконані, увімкнення через {int(ON_DELAY_SECONDS - (mono - started))} с"
            else:
                _satisfied_since.pop(rid, None)
                if rid in _engine_on.get(ip, set()):
                    since = _unsatisfied_since.setdefault(rid, mono)
                    # Window over -> off now; conditions lost -> off after OFF_DELAY.
                    if not window or mono - since >= OFF_DELAY_SECONDS:
                        if rule["turn_off_at_end"]:
                            must_off = True
                        _engine_on.get(ip, set()).discard(rid)
            _rule_status[rid] = {"window_active": window, "conditions_ok": ok, "reason": reason,
                                 "checked_at": now.isoformat(timespec="seconds")}

        if not any_window:
            _manual_override.discard(ip)
        if ip in _manual_override:
            for rule in ip_rules:
                if _rule_status.get(rule["id"], {}).get("window_active"):
                    _rule_status[rule["id"]]["reason"] = "Призупинено: ручне керування до кінця вікна"
            continue

        name = device.get("name") or ip
        if wants_on:
            if ip in disabled_devices:
                for rule in wants_on:
                    _rule_status[rule["id"]]["reason"] = "Вимкнено балансуванням навантаження"
                continue
            engine_rules = _engine_on.setdefault(ip, set())
            if not currently_on and await _switch(device, True):
                print(f"📅 Schedule: {name} ON ({wants_on[0].get('name') or 'rule'})")
                asyncio.create_task(send_push_notification(
                    "📅 Розклад", f"{name} увімкнено: {_metrics_text(metrics)}"))
            if currently_on and not engine_rules:
                continue  # it was already on (manually) — don't claim ownership, never auto-off it
            engine_rules.update(r["id"] for r in wants_on)
        elif must_off and not _engine_on.get(ip) and currently_on:
            if await _switch(device, False):
                print(f"📅 Schedule: {name} OFF")
                asyncio.create_task(send_push_notification(
                    "📅 Розклад", f"{name} вимкнено: вікно завершилось або умови не виконуються"))
            _engine_on.pop(ip, None)


def _metrics_text(metrics: dict) -> str:
    parts = []
    if metrics.get("soc") is not None:
        parts.append(f"SOC {metrics['soc']:.0f}%")
    if metrics.get("pv_w") is not None:
        parts.append(f"PV {metrics['pv_w'] / 1000:.2f} кВт")
    return ", ".join(parts) or "умови виконані"


# ---------------------------------------------------------------- API

class RuleBase(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    enabled: bool = True
    start_time: str
    end_time: str
    days: str = "0123456"
    min_soc: Optional[float] = Field(None, ge=0, le=100)
    min_pv_w: Optional[float] = Field(None, ge=0, le=100000)
    turn_off_at_end: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def check_time(cls, value):
        if value is None:
            return value
        if not TIME_RE.match(value):
            raise ValueError("Time must be HH:MM")
        return value

    @field_validator("days")
    @classmethod
    def check_days(cls, value):
        if value is None:
            return value
        days = "".join(sorted(set(value)))
        if not days or any(d not in "0123456" for d in days):
            raise ValueError("days: digits 0 (Mon) .. 6 (Sun)")
        return days


class RuleCreate(RuleBase):
    ip: str


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    enabled: Optional[bool] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days: Optional[str] = None
    min_soc: Optional[float] = Field(None, ge=0, le=100)
    min_pv_w: Optional[float] = Field(None, ge=0, le=100000)
    turn_off_at_end: Optional[bool] = None

    _check_time = field_validator("start_time", "end_time")(RuleBase.check_time.__func__)
    _check_days = field_validator("days")(RuleBase.check_days.__func__)


def _with_status(rule: dict) -> dict:
    return {**rule, "enabled": bool(rule["enabled"]), "turn_off_at_end": bool(rule["turn_off_at_end"]),
            "status": _rule_status.get(rule["id"]), "engine_on": rule["id"] in _engine_on.get(rule["ip"], set()),
            "paused": rule["ip"] in _manual_override}


@router.get("")
def list_rules():
    return [_with_status(r) for r in db.list_tapo_rules()]


@router.post("", dependencies=[Depends(require_admin)])
def create_rule(body: RuleCreate):
    if not db.get_tapo_device_by_ip(body.ip):
        raise HTTPException(status_code=404, detail="Tapo device not found")
    if body.start_time == body.end_time:
        raise HTTPException(status_code=400, detail="Start and end time must differ")
    data = body.model_dump()
    data.update(enabled=int(data["enabled"]), turn_off_at_end=int(data["turn_off_at_end"]))
    return _with_status(db.create_tapo_rule(**data))


@router.patch("/{rule_id}", dependencies=[Depends(require_admin)])
def update_rule(rule_id: int, body: RuleUpdate):
    if not db.get_tapo_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    data = body.model_dump(exclude_unset=True)
    for key in ("enabled", "turn_off_at_end"):
        if key in data and data[key] is not None:
            data[key] = int(data[key])
    _satisfied_since.pop(rule_id, None)
    return _with_status(db.update_tapo_rule(rule_id, **data))


@router.delete("/{rule_id}", dependencies=[Depends(require_admin)])
def delete_rule(rule_id: int):
    rule = db.get_tapo_rule(rule_id)
    if not rule or not db.delete_tapo_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    _engine_on.get(rule["ip"], set()).discard(rule_id)
    _rule_status.pop(rule_id, None)
    return {"deleted": True}

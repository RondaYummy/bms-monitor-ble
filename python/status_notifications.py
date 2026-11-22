"""Live system status in a notification ("as in banking apps") + SOC badge on the app icon.

Every minute a compact status is built (SOC, PV, house load, time until empty / when full, grid present).
Devices that enabled it get a push that REPLACES the previous status notification (same `tag` in the
service worker) every N minutes, immediately when the grid goes down / comes back, or when the SOC
crosses a 10% step. Status pushes have a short TTL: an outdated status is dropped by the push service
instead of being delivered later.

iOS shows every push as a new banner, so iPhones only get updates on real changes (grid, 10% SOC step)
or at most once an hour.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import python.db as db
from python.data_store import data_store
from python.push_notifications import send_to_subscription, vapid_key_from_config

router = APIRouter(prefix="/push", tags=["Live status notification"])

LOOP_SECONDS = 60
STATUS_TTL_SECONDS = 15 * 60
IOS_MIN_INTERVAL_MIN = 60
SOC_STEP = 10                   # crossing 70% -> 60% etc. counts as a change
GRID_PRESENT_MIN_V = 150.0
DEYE_MAX_AGE_SECONDS = 120
INTERVAL_CHOICES = (5, 10, 15, 30, 60)

_last_snapshot: dict = {}


# ---------------------------------------------------------------- snapshot

async def build_snapshot(now: Optional[datetime] = None) -> Optional[dict]:
    """Current state of the system, or None if there is no data at all."""
    from python.analytics import battery_analytics  # cached (60 s); local import avoids a cycle
    now = now or datetime.now()

    cells = list((await data_store.get_cell_info()).values())
    remaining = sum(c.get("remaining_capacity") or 0 for c in cells)
    capacity = sum(c.get("nominal_capacity") or 0 for c in cells)
    current = sum(c.get("charge_current") or 0 for c in cells)
    soc = remaining / capacity * 100 if capacity else None

    pv_w = load_w = None
    grid: Optional[bool] = None
    now_utc = datetime.utcnow()
    for device in await asyncio.to_thread(db.get_all_deye_devices):
        try:
            age = (now_utc - datetime.fromisoformat(device["timestamp"])).total_seconds() if device.get("timestamp") else None
        except ValueError:
            age = None
        if age is None or age > DEYE_MAX_AGE_SECONDS:
            continue
        pv_w = (pv_w or 0) + (device.get("total_pv") or 0)
        load_w = (load_w or 0) + (device.get("load_power") or 0)
        if soc is None and device.get("battery_soc") is not None:
            soc = float(device["battery_soc"])
        if device.get("grid_voltage") is not None:
            grid = bool(grid) or device["grid_voltage"] >= GRID_PRESENT_MIN_V

    if soc is None and pv_w is None:
        return None

    runtime = {}
    try:
        runtime = (await battery_analytics()).get("runtime") or {}
    except Exception as e:
        print(f"⚠️ Status: analytics unavailable: {e}")

    return {"at": now, "soc": soc, "current_a": current, "pv_w": pv_w, "load_w": load_w, "grid": grid,
            "runtime": runtime}


def _hm(minutes: Optional[float]) -> Optional[str]:
    if minutes is None:
        return None
    minutes = int(round(minutes))
    return f"{minutes // 60} год {minutes % 60:02d} хв" if minutes >= 60 else f"{minutes} хв"


def format_status(snapshot: dict) -> dict:
    """Notification title/body. Title stays short (it is what a locked screen shows)."""
    soc, runtime = snapshot.get("soc"), snapshot.get("runtime") or {}
    parts = []
    if soc is not None:
        parts.append(f"🔋 {round(soc)}%")
    if snapshot.get("pv_w") is not None:
        parts.append(f"☀️ {snapshot['pv_w'] / 1000:.1f} кВт")
    if snapshot.get("load_w") is not None:
        parts.append(f"🏠 {snapshot['load_w'] / 1000:.1f} кВт")
    title = " · ".join(parts) or "BMS Monitor"

    current = snapshot.get("current_a") or 0
    if snapshot.get("grid") is False:
        left = _hm(runtime.get("no_charge_min") or runtime.get("by_current_load_min"))
        body = "⚡ Мережі немає" + (f" — батареї вистачить ще ~{left}" if left else "")
    elif current < -0.3:
        left = _hm(runtime.get("by_profile_min") or runtime.get("by_current_load_min"))
        if runtime.get("self_sufficient"):
            body = "⏳ Розряд, але до вечора сонце зарядить батарею"
        else:
            body = f"⏳ Розряд — вистачить ще ~{left}" if left else "⏳ Розряд"
    elif current > 0.3:
        full_at = runtime.get("full_at")
        body = f"🔌 Заряд — повна о {full_at[11:16]}" if full_at else "🔌 Заряд"
    else:
        body = "✅ Батарея в режимі очікування"
    if snapshot.get("grid") is True and current >= -0.3:
        body += " · мережа є"
    body += f" · {snapshot['at']:%H:%M}"
    return {"title": title, "body": body}


def status_payload(snapshot: dict) -> str:
    text = format_status(snapshot)
    soc = snapshot.get("soc")
    return json.dumps({
        "type": "status",
        "tag": "bms-status",
        "title": text["title"],
        "body": text["body"],
        "badge": round(soc) if soc is not None else None,
    }, ensure_ascii=False)


# ---------------------------------------------------------------- scheduling

def _soc_band(soc: Optional[float]) -> Optional[int]:
    return None if soc is None else int(soc // SOC_STEP)


def decide(sub: dict, snapshot: dict, now: datetime) -> Optional[str]:
    """Why to send now ('grid', 'soc', 'interval') or None. Pure function."""
    last_at = datetime.fromisoformat(sub["last_status_at"]) if sub.get("last_status_at") else None
    grid = snapshot.get("grid")
    if grid is not None and sub.get("last_status_grid") is not None and bool(sub["last_status_grid"]) != grid:
        return "grid"
    if last_at is None:
        return "interval"
    if _soc_band(snapshot.get("soc")) != _soc_band(sub.get("last_status_soc")):
        return "soc"
    interval = IOS_MIN_INTERVAL_MIN if sub.get("platform") == "ios" else (sub.get("status_interval_min") or 10)
    if now - last_at >= timedelta(minutes=interval):
        return "interval"
    return None


def _status_subscriptions() -> list[dict]:
    with db.get_connection() as conn:
        conn.row_factory = __import__("sqlite3").Row
        rows = conn.execute(
            "SELECT endpoint, p256dh, auth, status_interval_min, platform, last_status_at, last_status_soc, last_status_grid "
            "FROM subscriptions WHERE status_enabled = 1"
        ).fetchall()
    return [{**dict(r), "keys": {"p256dh": r["p256dh"], "auth": r["auth"]}} for r in rows]


def _mark_sent(endpoint: str, snapshot: dict, now: datetime):
    grid = snapshot.get("grid")
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE subscriptions SET last_status_at = ?, last_status_soc = ?, last_status_grid = ? WHERE endpoint = ?",
            (now.isoformat(timespec="seconds"), snapshot.get("soc"), None if grid is None else int(grid), endpoint),
        )


def _send_round(snapshot: dict, now: datetime) -> int:
    subs = _status_subscriptions()
    if not subs:
        return 0
    key = vapid_key_from_config()
    if not key:
        return 0
    payload = status_payload(snapshot)
    sent = 0
    for sub in subs:
        reason = decide(sub, snapshot, now)
        if not reason:
            continue
        # A lost grid must arrive now; routine updates may wait for the phone to wake up.
        urgency = "high" if reason == "grid" else "normal"
        if send_to_subscription(sub, payload, key, ttl=STATUS_TTL_SECONDS, urgency=urgency):
            _mark_sent(sub["endpoint"], snapshot, now)
            sent += 1
    return sent


async def status_notification_loop():
    while True:
        try:
            snapshot = await build_snapshot()
            if snapshot:
                _last_snapshot.update(snapshot)
                await asyncio.to_thread(_send_round, snapshot, datetime.now())
        except Exception as e:
            print(f"❌ Status notification loop: {e}")
        await asyncio.sleep(LOOP_SECONDS)


# ---------------------------------------------------------------- API (the push endpoint identifies the device)

class StatusPreferences(BaseModel):
    endpoint: str = Field(..., max_length=1024)
    enabled: Optional[bool] = None
    interval_min: Optional[int] = None
    platform: Optional[Literal["ios", "android", "desktop"]] = None


@router.post("/status")
async def status_preferences(body: StatusPreferences):
    """Reads (no fields) or updates the live-status settings of this device's push subscription.

    The push endpoint is an unguessable URL known only to the device, so it identifies the subscription.
    """
    if body.interval_min is not None and body.interval_min not in INTERVAL_CHOICES:
        raise HTTPException(status_code=422, detail=f"interval_min must be one of {INTERVAL_CHOICES}")
    if not db.get_subscription_by_endpoint(body.endpoint):
        raise HTTPException(status_code=404, detail="Subscription not found: subscribe to push first")

    fields = {}
    if body.enabled is not None:
        fields["status_enabled"] = int(body.enabled)
        fields["last_status_at"] = None  # first status right away
    if body.interval_min is not None:
        fields["status_interval_min"] = body.interval_min
    if body.platform is not None:
        fields["platform"] = body.platform

    def _apply():
        with db.get_connection() as conn:
            if fields:
                assignments = ", ".join(f"{k} = ?" for k in fields)
                conn.execute(f"UPDATE subscriptions SET {assignments} WHERE endpoint = ?", [*fields.values(), body.endpoint])
            row = conn.execute(
                "SELECT status_enabled, status_interval_min, platform, last_status_at FROM subscriptions WHERE endpoint = ?",
                (body.endpoint,),
            ).fetchone()
        return {"enabled": bool(row[0]), "interval_min": row[1], "platform": row[2], "last_sent": row[3]}

    return await asyncio.to_thread(_apply)


@router.get("/status/preview")
async def status_preview():
    """What the notification would show right now (for the settings screen)."""
    snapshot = await build_snapshot()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No data yet")
    return {**format_status(snapshot), "soc": snapshot.get("soc")}

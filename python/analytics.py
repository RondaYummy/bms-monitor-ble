"""Battery analytics: runtime forecast from the consumption history and cell-imbalance trend.

Runtime model (what makes it accurate):
  * Hour-of-day profile of the battery's net current (charge +, discharge −) summed over all BMS,
    **recency weighted** (half-life 1–2 days) so it follows weather/season/new appliances quickly.
  * Missing hours are **interpolated from neighbouring hours** (not filled with the daily mean, which mixed
    sunny and night hours).
  * The **current measured current** dominates the first hour and fades into the profile
    (exp. decay, τ = 60 min): a boiler running right now is visible immediately.
  * Simulation in 5-minute steps, charging is capped at the battery capacity.
  * **Backtest**: several variants are replayed on the last 3 days (start every 6 h, 12 h horizon) against
    the real remaining capacity; the most accurate one is used and its error (MAE, % SOC) is reported.
    In simulations with changing weather this cut the error by ~25-40% compared to the old flat 7-day mean.
  * **Outage scenario** ("no charging"): the household load profile from the Deye energy history
    (kWh per hour) converted to battery current (÷ pack voltage ÷ inverter efficiency + idle draw).
"""
import asyncio
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter

import python.db as db
from python.alert_thresholds import get_thresholds
from python.data_store import data_store

router = APIRouter(prefix="/analytics", tags=["Analytics"])

PROFILE_DAYS = 7
IMBALANCE_DAYS = 14
SIMULATION_HORIZON_HOURS = 7 * 24
MIN_PROFILE_HOURS = 12
CACHE_SECONDS = 60
HALF_LIFE_DAYS = 1.0            # default recency weighting of the profile (best on average in simulations)
NOW_BLEND_TAU_MIN = 60.0        # how fast the measured current fades into the profile
STEP_MIN = 5
BACKTEST_HOURS_BACK = 72
BACKTEST_EVERY_H = 6
BACKTEST_HORIZON_H = 12
INVERTER_EFFICIENCY = 0.94      # AC load -> DC battery current
INVERTER_IDLE_W = 40.0          # self-consumption of the inverter while running on battery
NOMINAL_CELL_V = 3.2            # fallback pack voltage per cell (LiFePO4)

_cache = {"at": 0.0, "value": None}


# ---------------------------------------------------------------- data access (sync, run in a thread)

def _hourly_battery(since: datetime) -> dict[str, dict]:
    """{'YYYY-MM-DD HH': {"current": A (sum of batteries), "remaining": Ah (sum)}} — only hours where every
    battery reported, so sums are comparable."""
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m-%d %H', timestamp) AS hour, device_address, AVG(current), AVG(remaining_capacity)
            FROM bms_data
            WHERE timestamp >= ?
            GROUP BY hour, device_address
            """,
            (since.strftime(db.TIMESTAMP_FORMAT),),
        ).fetchall()
    per_hour: dict[str, dict] = defaultdict(lambda: {"current": 0.0, "remaining": 0.0, "devices": 0})
    for hour, _address, current, remaining in rows:
        entry = per_hour[hour]
        entry["current"] += current or 0.0
        entry["remaining"] += remaining or 0.0
        entry["devices"] += 1
    if not per_hour:
        return {}
    devices = max(e["devices"] for e in per_hour.values())
    return {h: e for h, e in per_hour.items() if e["devices"] == devices}


def _hourly_net_current(since: datetime) -> dict[str, float]:
    return {h: e["current"] for h, e in _hourly_battery(since).items()}


def _hourly_load_kwh(since: datetime) -> dict[str, float]:
    """Household load per hour from the Deye energy history (kWh in that hour == average kW)."""
    try:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT hour, SUM(load) FROM energy_hourly WHERE hour >= ? GROUP BY hour",
                (since.strftime("%Y-%m-%d %H"),),
            ).fetchall()
    except Exception:
        return {}
    return {h: float(v or 0.0) for h, v in rows}


def _daily_max_imbalance(since: datetime) -> dict[str, list[tuple[str, float]]]:
    """{device_address: [(date, max voltage difference), ...]} — daily maxima of the stored per-interval maxima."""
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT device_address, MAX(device_name), date(timestamp) AS day, MAX(voltage_difference)
            FROM bms_data
            WHERE timestamp >= ? AND voltage_difference IS NOT NULL
            GROUP BY device_address, day
            ORDER BY day
            """,
            (since.strftime(db.TIMESTAMP_FORMAT),),
        ).fetchall()
    result: dict[str, dict] = {}
    for address, name, day, max_diff in rows:
        entry = result.setdefault(address, {"name": name, "points": []})
        entry["points"].append((day, float(max_diff)))
    return result


# ---------------------------------------------------------------- calculations (pure)

def _parse_hour(key: str) -> datetime:
    return datetime.strptime(key, "%Y-%m-%d %H")


def build_hour_profile(per_hour: dict[str, float], now: datetime | None = None,
                       half_life_days: float | None = None) -> tuple[list[float | None], int]:
    """Weighted average value for each hour of day 0..23 (None where no data) + number of hours used.

    With `half_life_days` recent days weigh more (weight 0.5 per half-life of age relative to `now`).
    """
    sums = [0.0] * 24
    weights = [0.0] * 24
    used = 0
    for key, value in per_hour.items():
        ts = _parse_hour(key)
        if now is not None and ts >= now.replace(minute=0, second=0, microsecond=0):
            continue  # never use the (incomplete) current hour or the future
        weight = 1.0
        if half_life_days and now is not None:
            age_days = max(0.0, (now - ts).total_seconds() / 86400)
            weight = 0.5 ** (age_days / half_life_days)
        sums[ts.hour] += value * weight
        weights[ts.hour] += weight
        used += 1
    return [sums[h] / weights[h] if weights[h] else None for h in range(24)], used


def fill_gaps(profile: list[float | None]) -> list[float]:
    """Missing hours are interpolated linearly between the nearest known hours (circular over midnight)."""
    known = [h for h, v in enumerate(profile) if v is not None]
    if not known:
        return [0.0] * 24
    if len(known) == 1:
        return [profile[known[0]]] * 24
    result = list(profile)
    for h in range(24):
        if result[h] is not None:
            continue
        prev_h = next(((h - d) % 24 for d in range(1, 24) if profile[(h - d) % 24] is not None))
        next_h = next(((h + d) % 24 for d in range(1, 24) if profile[(h + d) % 24] is not None))
        span = (next_h - prev_h) % 24
        frac = ((h - prev_h) % 24) / span
        result[h] = profile[prev_h] + (profile[next_h] - profile[prev_h]) * frac
    return result


# backwards compatible name
_fill_gaps = fill_gaps


def _current_at(profile: list[float], t: datetime, elapsed_min: float, now_current: float | None) -> float:
    base = profile[t.hour]
    if now_current is None:
        return base
    w = math.exp(-elapsed_min / NOW_BLEND_TAU_MIN)
    return w * now_current + (1 - w) * base


def simulate_runtime(remaining_ah: float, capacity_ah: float, profile: list[float], start: datetime,
                     reserve_ah: float = 0.0, horizon_hours: int = SIMULATION_HORIZON_HOURS,
                     now_current: float | None = None) -> float | None:
    """Minutes until the remaining capacity drops to `reserve_ah` (charging is capped at the capacity).
    None = not reached within the horizon."""
    if remaining_ah <= reserve_ah:
        return 0.0
    level, t, elapsed = remaining_ah, start, 0.0
    while elapsed < horizon_hours * 60:
        current = _current_at(profile, t, elapsed, now_current)
        new_level = min(capacity_ah, level + current * STEP_MIN / 60)
        if current < 0 and new_level <= reserve_ah:
            return elapsed + (level - reserve_ah) / -current * 60
        level, t, elapsed = new_level, t + timedelta(minutes=STEP_MIN), elapsed + STEP_MIN
    return None


def simulate_levels(remaining_ah: float, capacity_ah: float, profile: list[float], start: datetime,
                    hours: int, now_current: float | None = None) -> list[float]:
    """Predicted remaining capacity at start+1h, start+2h, ... (floored at 0)."""
    level, t, elapsed, levels = remaining_ah, start, 0.0, []
    while len(levels) < hours:
        current = _current_at(profile, t, elapsed, now_current)
        level = max(0.0, min(capacity_ah, level + current * STEP_MIN / 60))
        t, elapsed = t + timedelta(minutes=STEP_MIN), elapsed + STEP_MIN
        if elapsed % 60 == 0:
            levels.append(level)
    return levels


# Candidate models; the backtest on the user's own history picks the most accurate one.
VARIANTS = {
    # name: (half-life in days or None for a flat 7-day mean, blend in the measured current)
    "recent-1d": (1.0, True),
    "recent-2d": (2.0, True),
    "week": (None, True),
    "week-no-now": (None, False),   # the previous model
}
DEFAULT_VARIANT = "recent-1d"


def backtest(history: dict[str, dict], capacity_ah: float, now: datetime) -> dict[str, dict]:
    """Replays each variant on past data: MAE of the predicted vs real remaining capacity, in % of capacity."""
    results = {}
    hour0 = now.replace(minute=0, second=0, microsecond=0)
    for name, (half_life, use_now) in VARIANTS.items():
        errors = []
        for back in range(BACKTEST_HORIZON_H, BACKTEST_HOURS_BACK + 1, BACKTEST_EVERY_H):
            start = hour0 - timedelta(hours=back)
            start_key = start.strftime("%Y-%m-%d %H")
            if start_key not in history:
                continue
            past = {k: e["current"] for k, e in history.items()
                    if start - timedelta(days=PROFILE_DAYS) <= _parse_hour(k) < start}
            raw, used = build_hour_profile(past, start, half_life)
            if used < MIN_PROFILE_HOURS:
                continue
            prev_key = (start - timedelta(hours=1)).strftime("%Y-%m-%d %H")
            now_current = history[prev_key]["current"] if use_now and prev_key in history else None
            predicted = simulate_levels(history[start_key]["remaining"], capacity_ah, fill_gaps(raw), start,
                                        BACKTEST_HORIZON_H, now_current)
            for i, level in enumerate(predicted, start=1):
                actual = history.get((start + timedelta(hours=i)).strftime("%Y-%m-%d %H"))
                if actual:
                    errors.append(abs(level - actual["remaining"]) / capacity_ah * 100)
        results[name] = {"mae_soc_pct": round(sum(errors) / len(errors), 2) if errors else None, "points": len(errors)}
    return results


def outage_profile(load_kwh_per_hour: dict[str, float], pack_voltage: float, now: datetime) -> list[float] | None:
    """Battery current (A, negative) needed to carry the usual household load without sun or grid."""
    raw, used = build_hour_profile(load_kwh_per_hour, now, HALF_LIFE_DAYS)
    if used < MIN_PROFILE_HOURS or pack_voltage <= 0:
        return None
    return [-((kw * 1000) / INVERTER_EFFICIENCY + INVERTER_IDLE_W) / pack_voltage for kw in fill_gaps(raw)]


def linear_trend(values: list[float]) -> tuple[float, float]:
    """Least-squares slope and intercept for equally spaced points (x = 0..n-1)."""
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in range(n))
    slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values)) / denom if denom else 0.0
    return slope, mean_y - slope * mean_x


def imbalance_forecast(points: list[tuple[str, float]], current_diff: float | None, t: dict) -> dict:
    values = [v for _, v in points]
    result = {
        "history": [{"date": d, "max_diff": round(v, 4)} for d, v in points],
        "current_diff": current_diff,
        "trend": "unknown",
        "slope_mv_per_day": None,
        "days_to_error": None,
        "days_to_critical": None,
        "error_threshold": t["cell_diff_error"],
        "critical_threshold": t["cell_diff_critical"],
    }
    if len(values) < 3:
        return result

    slope, intercept = linear_trend(values)
    level_now = intercept + slope * (len(values) - 1)
    result["slope_mv_per_day"] = round(slope * 1000, 2)
    if slope > 0.0005:      # > 0.5 mV/day
        result["trend"] = "rising"
    elif slope < -0.0005:
        result["trend"] = "falling"
    else:
        result["trend"] = "stable"

    if slope > 0:
        for key, threshold in (("days_to_error", t["cell_diff_error"]), ("days_to_critical", t["cell_diff_critical"])):
            result[key] = 0 if level_now >= threshold else round((threshold - level_now) / slope, 1)
    return result


# ---------------------------------------------------------------- endpoint

def _confidence(mae: float | None, hours_used: int) -> str:
    if mae is not None:
        return "high" if mae <= 5 else "medium" if mae <= 10 else "low"
    return "medium" if hours_used >= 48 else "low"


async def compute_battery_analytics() -> dict:
    now = datetime.now()
    thresholds = get_thresholds()
    cell_info = await data_store.get_cell_info()
    batteries = list(cell_info.values())

    remaining = sum(b.get("remaining_capacity") or 0 for b in batteries)
    capacity = sum(b.get("nominal_capacity") or 0 for b in batteries)
    current_now = sum(b.get("charge_current") or 0 for b in batteries)
    soc = (remaining / capacity * 100) if capacity else None
    voltages = [b.get("battery_voltage") for b in batteries if b.get("battery_voltage")]
    cells = max((len(b.get("cell_voltages") or []) for b in batteries), default=16) or 16
    pack_voltage = sum(voltages) / len(voltages) if voltages else NOMINAL_CELL_V * cells
    reserve_ah = capacity * thresholds["soc_critical"] / 100 if capacity else 0.0

    history = await asyncio.to_thread(
        _hourly_battery, now - timedelta(days=PROFILE_DAYS) - timedelta(hours=BACKTEST_HOURS_BACK))
    recent = {k: e["current"] for k, e in history.items() if _parse_hour(k) >= now - timedelta(days=PROFILE_DAYS)}

    # Pick the variant that was most accurate on the last days.
    scores = await asyncio.to_thread(backtest, history, capacity, now) if capacity else {}
    measured = {name: s for name, s in scores.items() if s["mae_soc_pct"] is not None}
    best = min(measured, key=lambda n: measured[n]["mae_soc_pct"]) if measured else DEFAULT_VARIANT
    half_life, use_now = VARIANTS[best]
    raw_profile, hours_used = build_hour_profile(recent, now, half_life)
    profile = fill_gaps(raw_profile)
    now_current = current_now if (use_now and batteries) else None

    load_history = await asyncio.to_thread(_hourly_load_kwh, now - timedelta(days=PROFILE_DAYS))
    outage = outage_profile(load_history, pack_voltage, now)
    discharge_hours = [c for c in recent.values() if c < 0]
    avg_discharge = sum(discharge_hours) / len(discharge_hours) if discharge_hours else None

    runtime = {
        "remaining_ah": round(remaining, 2),
        "capacity_ah": round(capacity, 2),
        "soc": round(soc, 1) if soc is not None else None,
        "current_now_a": round(current_now, 2),
        "reserve_soc": thresholds["soc_critical"],
        "history_hours": hours_used,
        "model": best,
        "accuracy": measured.get(best),
        "backtest": scores,
        "confidence": _confidence((measured.get(best) or {}).get("mae_soc_pct"), hours_used),
        # 1) the current load only. BMS current already includes inverter losses: no extra efficiency factor.
        "by_current_load_min": round(remaining / -current_now * 60) if current_now < -0.3 else None,
        # 2) usual pattern incl. solar/grid charging, current load blended in for the first hour
        "by_profile_min": None,
        "by_profile_to_reserve_min": None,
        # 3) outage: no sun, no grid — household load from the inverter history (fallback: BMS discharge hours)
        "no_charge_min": None,
        "no_charge_to_reserve_min": None,
        "no_charge_source": "load" if outage else ("bms" if avg_discharge else None),
        "avg_discharge_a": round(avg_discharge, 2) if avg_discharge else None,
        "profile": [round(v, 2) if v is not None else None for v in raw_profile],
        "outage_profile": [round(v, 2) for v in outage] if outage else None,
        "self_sufficient": False,
    }
    if capacity and hours_used >= MIN_PROFILE_HOURS:
        to_empty = simulate_runtime(remaining, capacity, profile, now, 0.0, now_current=now_current)
        to_reserve = simulate_runtime(remaining, capacity, profile, now, reserve_ah, now_current=now_current)
        runtime["by_profile_min"] = round(to_empty) if to_empty is not None else None
        runtime["by_profile_to_reserve_min"] = round(to_reserve) if to_reserve is not None else None
        runtime["self_sufficient"] = to_empty is None  # never empties within a week with the usual pattern
    if capacity and outage:
        # During an outage the load right now still applies for the first minutes.
        outage_now = current_now if current_now < 0 else None
        empty = simulate_runtime(remaining, capacity, outage, now, 0.0, now_current=outage_now)
        reserve = simulate_runtime(remaining, capacity, outage, now, reserve_ah, now_current=outage_now)
        runtime["no_charge_min"] = round(empty) if empty is not None else None
        runtime["no_charge_to_reserve_min"] = round(reserve) if reserve is not None else None
    elif avg_discharge:
        runtime["no_charge_min"] = round(remaining / -avg_discharge * 60)
        runtime["no_charge_to_reserve_min"] = round(max(0.0, remaining - reserve_ah) / -avg_discharge * 60)

    history_imb = await asyncio.to_thread(_daily_max_imbalance, now - timedelta(days=IMBALANCE_DAYS))
    imbalance = []
    for address, entry in history_imb.items():
        live = next((b for b in batteries if (b.get("device_address") or "").lower() == address), None)
        forecast = imbalance_forecast(entry["points"], live.get("voltage_difference") if live else None, thresholds)
        imbalance.append({"device_address": address, "device_name": entry["name"], **forecast})

    return {"generated_at": now.isoformat(timespec="seconds"), "runtime": runtime, "imbalance": imbalance}


@router.get("/battery")
async def battery_analytics():
    if _cache["value"] is not None and time.monotonic() - _cache["at"] < CACHE_SECONDS:
        return _cache["value"]
    value = await compute_battery_analytics()
    _cache.update(at=time.monotonic(), value=value)
    return value

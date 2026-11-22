"""Battery analytics: runtime forecast from the consumption history and cell-imbalance trend."""
import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter

import python.db as db
from python.alert_thresholds import get_thresholds
from python.data_store import data_store

router = APIRouter(prefix="/analytics", tags=["Analytics"])

PROFILE_DAYS = 7               # consumption profile: average net current per hour of day
IMBALANCE_DAYS = 14            # imbalance trend window
SIMULATION_HORIZON_HOURS = 7 * 24
MIN_PROFILE_HOURS = 12         # below this the history-based forecast is not trustworthy
CACHE_SECONDS = 60

_cache = {"at": 0.0, "value": None}


# ---------------------------------------------------------------- data access (sync, run in a thread)

def _hourly_net_current(since: datetime) -> dict[str, float]:
    """{'YYYY-MM-DD HH': summed average current of all batteries (A, + charge / - discharge)}."""
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m-%d %H', timestamp) AS hour, device_address, AVG(current)
            FROM bms_data
            WHERE timestamp >= ?
            GROUP BY hour, device_address
            """,
            (since.strftime(db.TIMESTAMP_FORMAT),),
        ).fetchall()
    per_hour: dict[str, float] = defaultdict(float)
    for hour, _address, avg_current in rows:
        per_hour[hour] += avg_current or 0.0
    return per_hour


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

def build_hour_profile(per_hour: dict[str, float]) -> tuple[list[float | None], int]:
    """Average net current for each hour of day 0..23 (None where no data) and the number of hours used."""
    buckets: dict[int, list[float]] = defaultdict(list)
    for hour_key, current in per_hour.items():
        buckets[int(hour_key[-2:])].append(current)
    profile = [sum(v) / len(v) if v else None for v in (buckets.get(h, []) for h in range(24))]
    return profile, sum(len(v) for v in buckets.values())


def _fill_gaps(profile: list[float | None]) -> list[float]:
    known = [v for v in profile if v is not None]
    fallback = sum(known) / len(known) if known else 0.0
    return [fallback if v is None else v for v in profile]


def simulate_runtime(remaining_ah: float, capacity_ah: float, profile: list[float], start: datetime,
                     reserve_ah: float = 0.0, horizon_hours: int = SIMULATION_HORIZON_HOURS) -> float | None:
    """Minutes until remaining capacity drops to `reserve_ah`, following the hourly profile
    (charging hours refill the battery up to its capacity). None = not reached within the horizon."""
    if remaining_ah <= reserve_ah:
        return 0.0
    level = remaining_ah
    t = start
    elapsed_min = 0.0
    end = start + timedelta(hours=horizon_hours)
    while t < end:
        next_hour = (t + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        span_h = (next_hour - t).total_seconds() / 3600
        current = profile[t.hour]
        new_level = min(capacity_ah, level + current * span_h)
        if current < 0 and new_level <= reserve_ah:
            return elapsed_min + (level - reserve_ah) / -current * 60
        level = new_level
        elapsed_min += span_h * 60
        t = next_hour
    return None


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

async def compute_battery_analytics() -> dict:
    now = datetime.now()
    thresholds = get_thresholds()
    cell_info = await data_store.get_cell_info()
    batteries = list(cell_info.values())

    remaining = sum(b.get("remaining_capacity") or 0 for b in batteries)
    capacity = sum(b.get("nominal_capacity") or 0 for b in batteries)
    current_now = sum(b.get("charge_current") or 0 for b in batteries)
    soc = (remaining / capacity * 100) if capacity else None

    per_hour = await asyncio.to_thread(_hourly_net_current, now - timedelta(days=PROFILE_DAYS))
    raw_profile, hours_used = build_hour_profile(per_hour)
    profile = _fill_gaps(raw_profile)
    reserve_ah = capacity * thresholds["soc_critical"] / 100 if capacity else 0.0

    discharge_hours = [c for c in per_hour.values() if c < 0]
    avg_discharge = sum(discharge_hours) / len(discharge_hours) if discharge_hours else None

    runtime = {
        "remaining_ah": round(remaining, 2),
        "capacity_ah": round(capacity, 2),
        "soc": round(soc, 1) if soc is not None else None,
        "current_now_a": round(current_now, 2),
        "reserve_soc": thresholds["soc_critical"],
        "history_hours": hours_used,
        "confidence": "high" if hours_used >= 24 * 5 else "medium" if hours_used >= 48 else "low",
        # 1) the current load only (what the dashboard showed before)
        "by_current_load_min": round(remaining / -current_now * 60) if current_now < 0 else None,
        # 2) typical consumption pattern incl. solar charging, simulated hour by hour
        "by_profile_min": None,
        "by_profile_to_reserve_min": None,
        # 3) "no charging at all" (outage at night / cloudy days): average discharge current
        "no_charge_min": round(remaining / -avg_discharge * 60) if avg_discharge else None,
        "avg_discharge_a": round(avg_discharge, 2) if avg_discharge else None,
        "profile": [round(v, 2) if v is not None else None for v in raw_profile],
        "self_sufficient": False,
    }
    if capacity and hours_used >= MIN_PROFILE_HOURS:
        to_empty = simulate_runtime(remaining, capacity, profile, now, 0.0)
        to_reserve = simulate_runtime(remaining, capacity, profile, now, reserve_ah)
        runtime["by_profile_min"] = round(to_empty) if to_empty is not None else None
        runtime["by_profile_to_reserve_min"] = round(to_reserve) if to_reserve is not None else None
        runtime["self_sufficient"] = to_empty is None  # never empties within a week with the usual pattern

    history = await asyncio.to_thread(_daily_max_imbalance, now - timedelta(days=IMBALANCE_DAYS))
    imbalance = []
    for address, entry in history.items():
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

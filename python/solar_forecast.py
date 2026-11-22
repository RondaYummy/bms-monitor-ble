"""Solar generation forecast from Open-Meteo (free, no API key) calibrated on the station's real PV output.

* Every hour the plane-of-array irradiance (global tilted irradiance, W/m² for the configured panel tilt and
  orientation), cloud cover and temperature are fetched for the past 7 days and the next 3 days.
* Calibration: the real hourly PV energy from the Deye history (`energy_hourly.pv`) is compared with the
  irradiance of the same hour -> kWh per (W/m²) for this particular station (panels, shading, inverter...).
  A robust estimator (middle-upper ratios) ignores hours where generation was curtailed because the
  battery was full. Without enough history the configured peak power is used (performance ratio 0.85).
* The forecast feeds the battery model (python/analytics.py): tomorrow's sun is no longer "a typical day".

Open-Meteo radiation values are the mean of the *preceding* hour: the value at 13:00 belongs to our
hour bucket "12" (12:00–13:00).
"""
import asyncio
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import python.db as db
from python.auth.verify_token import require_admin

router = APIRouter(prefix="/solar", tags=["Solar forecast"])

OPEN_METEO_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
FETCH_INTERVAL_SECONDS = 60 * 60
PAST_DAYS = 7
FORECAST_DAYS = 3
KEEP_DAYS = 120
CALIBRATION_DAYS = 30
MIN_CALIBRATION_POINTS = 12
MIN_IRRADIANCE = 80.0           # W/m²: ignore dawn/dusk hours for calibration
PERFORMANCE_RATIO = 0.85        # fallback when the station has no history yet
REQUEST_TIMEOUT = 20

DEFAULT_SETTINGS = {
    "enabled": False,
    "latitude": None,
    "longitude": None,
    "tilt": 30,          # degrees from horizontal
    "azimuth": 0,        # Open-Meteo convention: 0 = south, -90 = east, 90 = west, 180 = north
    "peak_kw": None,     # optional: installed PV power, only used until enough history exists
}

_state = {"last_fetch": None, "last_error": None}


def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solar_forecast (
        hour TEXT PRIMARY KEY,           -- 'YYYY-MM-DD HH' (hour bucket start, local time)
        gti REAL,                        -- global tilted irradiance, W/m² (hour mean)
        cloud_cover REAL,                -- %
        temperature REAL,                -- °C
        updated_at TEXT NOT NULL
    )
    """)


# ---------------------------------------------------------------- settings

def get_settings() -> dict:
    raw = (db.get_config() or {}).get("solar_settings")
    settings = dict(DEFAULT_SETTINGS)
    if raw:
        try:
            settings.update(json.loads(raw))
        except (TypeError, ValueError):
            pass
    return settings


def is_configured(settings: Optional[dict] = None) -> bool:
    s = settings or get_settings()
    return bool(s.get("enabled")) and s.get("latitude") is not None and s.get("longitude") is not None


# ---------------------------------------------------------------- fetching

def build_url(settings: dict) -> str:
    params = {
        # 2 decimals ≈ 1 km: enough for weather, does not send the exact address to a third party
        "latitude": round(float(settings["latitude"]), 2),
        "longitude": round(float(settings["longitude"]), 2),
        "hourly": "global_tilted_irradiance,cloud_cover,temperature_2m",
        "tilt": settings.get("tilt", 30),
        "azimuth": settings.get("azimuth", 0),
        "past_days": PAST_DAYS,
        "forecast_days": FORECAST_DAYS,
        "timezone": "auto",
    }
    return f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"


def parse_response(payload: dict) -> list[tuple]:
    """Open-Meteo hourly arrays -> rows (hour_bucket, gti, cloud, temperature). Time T is the mean of T-1h..T."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    gti = hourly.get("global_tilted_irradiance") or [None] * len(times)
    cloud = hourly.get("cloud_cover") or [None] * len(times)
    temp = hourly.get("temperature_2m") or [None] * len(times)
    rows = []
    for i, stamp in enumerate(times):
        bucket = datetime.strptime(stamp, "%Y-%m-%dT%H:%M") - timedelta(hours=1)
        rows.append((bucket.strftime("%Y-%m-%d %H"), gti[i], cloud[i], temp[i]))
    return rows


def fetch_and_store(settings: Optional[dict] = None) -> int:
    settings = settings or get_settings()
    if not is_configured(settings):
        return 0
    request = urllib.request.Request(build_url(settings), headers={"User-Agent": "bms-monitor"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = parse_response(payload)
    now = datetime.now().isoformat(timespec="seconds")
    with db.get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO solar_forecast (hour, gti, cloud_cover, temperature, updated_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(hour) DO UPDATE SET gti = excluded.gti, cloud_cover = excluded.cloud_cover,
                temperature = excluded.temperature, updated_at = excluded.updated_at
            """,
            [(*row, now) for row in rows],
        )
        cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d %H")
        conn.execute("DELETE FROM solar_forecast WHERE hour < ?", (cutoff,))
    return len(rows)


async def refresh_now() -> dict:
    try:
        count = await asyncio.to_thread(fetch_and_store)
        _state.update(last_fetch=datetime.now().isoformat(timespec="seconds"), last_error=None)
        _invalidate()
        return {"rows": count}
    except Exception as e:
        _state["last_error"] = str(e)
        print(f"❌ Open-Meteo fetch failed: {e}")
        raise


async def solar_forecast_loop():
    while True:
        if is_configured():
            try:
                await refresh_now()
            except Exception:
                pass  # logged; retry next hour
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


# ---------------------------------------------------------------- data + calibration

_cache = {"at": 0.0, "value": None}


def _invalidate():
    _cache.update(at=0.0, value=None)


def load_irradiance(since: datetime, until: datetime) -> dict[str, dict]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT hour, gti, cloud_cover, temperature FROM solar_forecast WHERE hour >= ? AND hour < ? ORDER BY hour",
            (since.strftime("%Y-%m-%d %H"), until.strftime("%Y-%m-%d %H")),
        ).fetchall()
    return {h: {"gti": g, "cloud": c, "temp": t} for h, g, c, t in rows}


def load_pv_history(since: datetime) -> dict[str, float]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT hour, SUM(pv) FROM energy_hourly WHERE hour >= ? GROUP BY hour", (since.strftime("%Y-%m-%d %H"),)
        ).fetchall()
    return {h: float(v or 0.0) for h, v in rows}


def calibrate(irradiance: dict[str, dict], pv: dict[str, float], peak_kw: Optional[float]) -> dict:
    """kWh produced per hour per 1 W/m² of tilted irradiance."""
    ratios = sorted(pv[h] / v["gti"] for h, v in irradiance.items()
                    if h in pv and v.get("gti") and v["gti"] >= MIN_IRRADIANCE and pv[h] > 0)
    if len(ratios) >= MIN_CALIBRATION_POINTS:
        # Middle-upper part: hours with curtailment (battery full) or snow/shade outliers have low ratios.
        lo, hi = int(len(ratios) * 0.5), max(int(len(ratios) * 0.9), int(len(ratios) * 0.5) + 1)
        segment = ratios[lo:hi]
        k = sum(segment) / len(segment)
        return {"method": "learned", "k": k, "points": len(ratios), "kw_per_1000_wm2": round(k * 1000, 2)}
    if peak_kw:
        k = float(peak_kw) * PERFORMANCE_RATIO / 1000
        return {"method": "peak_power", "k": k, "points": len(ratios), "kw_per_1000_wm2": round(k * 1000, 2)}
    return {"method": None, "k": None, "points": len(ratios), "kw_per_1000_wm2": None}


def solar_context(now: Optional[datetime] = None) -> Optional[dict]:
    """Everything the battery model needs: irradiance per hour (past + future) and the calibration."""
    settings = get_settings()
    if not is_configured(settings):
        return None
    now = now or datetime.now()
    irradiance = load_irradiance(now - timedelta(days=CALIBRATION_DAYS), now + timedelta(days=FORECAST_DAYS + 1))
    if not irradiance:
        return None
    pv = load_pv_history(now - timedelta(days=CALIBRATION_DAYS))
    calibration = calibrate(irradiance, pv, settings.get("peak_kw"))
    if calibration["k"] is None:
        return None
    predicted = {h: round((v["gti"] or 0.0) * calibration["k"], 3) for h, v in irradiance.items()}
    return {"irradiance": irradiance, "pv": pv, "predicted_kwh": predicted, "calibration": calibration}


def forecast_summary(now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    if _cache["value"] is not None and time.monotonic() - _cache["at"] < 300:
        return _cache["value"]
    settings = get_settings()
    result = {"configured": is_configured(settings), "settings": settings, **_state, "calibration": None,
              "days": [], "hours": []}
    ctx = solar_context(now) if result["configured"] else None
    if ctx:
        result["calibration"] = ctx["calibration"]
        today = now.date()
        days: dict[str, dict] = {}
        for hour, kwh in ctx["predicted_kwh"].items():
            day = hour[:10]
            if day < today.isoformat():
                continue
            entry = days.setdefault(day, {"date": day, "pv_kwh": 0.0, "cloud_sum": 0.0, "n": 0, "actual_kwh": None})
            entry["pv_kwh"] += kwh
            cloud = ctx["irradiance"][hour].get("cloud")
            if cloud is not None and 8 <= int(hour[11:13]) <= 17:
                entry["cloud_sum"] += cloud
                entry["n"] += 1
        actual_today = sum(v for h, v in ctx["pv"].items() if h.startswith(today.isoformat()))
        for entry in days.values():
            entry["pv_kwh"] = round(entry["pv_kwh"], 1)
            entry["cloud_avg"] = round(entry.pop("cloud_sum") / entry["n"]) if entry["n"] else None
            entry.pop("n")
        if today.isoformat() in days:
            days[today.isoformat()]["actual_kwh"] = round(actual_today, 1)
        result["days"] = sorted(days.values(), key=lambda d: d["date"])[:FORECAST_DAYS]
        start = now.replace(minute=0, second=0, microsecond=0)
        for i in range(48):
            key = (start + timedelta(hours=i)).strftime("%Y-%m-%d %H")
            if key in ctx["predicted_kwh"]:
                result["hours"].append({"hour": key, "pv_kwh": ctx["predicted_kwh"][key],
                                        "cloud": ctx["irradiance"][key].get("cloud"),
                                        "gti": ctx["irradiance"][key].get("gti")})
    _cache.update(at=time.monotonic(), value=result)
    return result


# ---------------------------------------------------------------- API

class SolarSettings(BaseModel):
    enabled: bool = True
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    tilt: float = Field(30, ge=0, le=90)
    azimuth: float = Field(0, ge=-180, le=180)
    peak_kw: Optional[float] = Field(None, gt=0, le=1000)


@router.get("/forecast")
async def get_forecast():
    return await asyncio.to_thread(forecast_summary)


@router.get("/settings")
def read_settings():
    return get_settings()


@router.put("/settings", dependencies=[Depends(require_admin)])
async def update_settings(body: SolarSettings):
    db.update_config_fields(solar_settings=json.dumps(body.model_dump()))
    _invalidate()
    if body.enabled:
        try:
            await refresh_now()
        except Exception:
            raise HTTPException(status_code=502, detail="Налаштування збережено, але Open-Meteo зараз недоступний")
    return get_settings()


@router.post("/refresh", dependencies=[Depends(require_admin)])
async def refresh():
    if not is_configured():
        raise HTTPException(status_code=400, detail="Solar forecast is not configured")
    try:
        return await refresh_now()
    except Exception:
        raise HTTPException(status_code=502, detail="Open-Meteo is not reachable")

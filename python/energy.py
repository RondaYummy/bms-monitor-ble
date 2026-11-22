"""Energy accounting and economics.

Deye exposes only *daily* counters (kWh since the inverter's midnight) that we overwrite every poll, so
history is built here: every poll the increase of each counter is added to the current hour
(`energy_hourly`). A counter that goes down means the daily reset happened -> the new value is the delta.
The last counters are persisted (`energy_counter_state`), so restarts don't lose or double-count energy.
"""
import json
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta

import python.db as db

# Our field -> Deye daily counter (see read_deye.py)
COUNTERS = {
    "pv": "stat_daily_pv",
    "load": "daily_load",
    "grid_in": "stat_daily_grid_in",
    "grid_out": "stat_daily_grid_out",
    "bat_charge": "daily_bat_charge",
    "bat_discharge": "stat_daily_bat_discharge",
}
FIELDS = tuple(COUNTERS)
MAX_PLAUSIBLE_STEP_KWH = 50.0  # one poll can't add more than this -> glitch, ignore
FLUSH_INTERVAL_SECONDS = 60

DEFAULT_TARIFFS = {
    "currency": "грн",
    "day_price": 4.32,       # UAH/kWh, household tariff
    "two_zone": False,       # two-zone meter (cheaper night)
    "night_price": 2.16,
    "night_start": "23:00",
    "night_end": "07:00",
    "export_price": 0.0,     # "green" tariff / selling price per kWh
}


def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS energy_hourly (
        ip TEXT NOT NULL,
        hour TEXT NOT NULL,              -- 'YYYY-MM-DD HH' (server local time)
        pv REAL NOT NULL DEFAULT 0,
        load REAL NOT NULL DEFAULT 0,
        grid_in REAL NOT NULL DEFAULT 0,
        grid_out REAL NOT NULL DEFAULT 0,
        bat_charge REAL NOT NULL DEFAULT 0,
        bat_discharge REAL NOT NULL DEFAULT 0,
        PRIMARY KEY (ip, hour)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS energy_counter_state (
        ip TEXT PRIMARY KEY,
        counters TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)


# ---------------------------------------------------------------- accumulation

class EnergyAccumulator:
    def __init__(self):
        self._lock = threading.Lock()
        self._last: dict[str, dict] = {}                       # ip -> {field: counter}
        self._pending: dict[tuple, dict] = defaultdict(lambda: defaultdict(float))  # (ip, hour) -> deltas
        self._loaded = False

    def _load_state(self):
        if self._loaded:
            return
        try:
            with db.get_connection() as conn:
                for ip, counters in conn.execute("SELECT ip, counters FROM energy_counter_state").fetchall():
                    self._last[ip] = json.loads(counters)
        except Exception as e:
            print(f"⚠️ Energy state not loaded: {e}")
        self._loaded = True

    def record(self, ip: str, data: dict, now: datetime | None = None):
        """Called after every successful inverter read with the dict from read_deye."""
        now = now or datetime.now()
        hour = now.strftime("%Y-%m-%d %H")
        with self._lock:
            self._load_state()
            current = {f: data.get(key) for f, key in COUNTERS.items()}
            last = self._last.get(ip)
            if last is not None:
                for field, value in current.items():
                    if value is None or last.get(field) is None:
                        continue
                    previous = float(last[field])
                    value = float(value)
                    delta = value - previous if value >= previous else value  # drop = daily reset
                    if 0 < delta <= MAX_PLAUSIBLE_STEP_KWH:
                        self._pending[(ip, hour)][field] += delta
            self._last[ip] = {f: v for f, v in current.items() if v is not None} or (last or {})

    def flush(self):
        """Writes accumulated deltas and the last counters (one short transaction)."""
        with self._lock:
            pending, self._pending = self._pending, defaultdict(lambda: defaultdict(float))
            last = dict(self._last)
        if not pending and not last:
            return
        now = datetime.now().isoformat(timespec="seconds")
        with db.get_connection() as conn:
            for (ip, hour), deltas in pending.items():
                conn.execute(
                    f"""
                    INSERT INTO energy_hourly (ip, hour, {", ".join(FIELDS)})
                    VALUES (?, ?, {", ".join("?" for _ in FIELDS)})
                    ON CONFLICT(ip, hour) DO UPDATE SET
                    {", ".join(f"{f} = {f} + excluded.{f}" for f in FIELDS)}
                    """,
                    (ip, hour, *(round(deltas.get(f, 0.0), 4) for f in FIELDS)),
                )
            for ip, counters in last.items():
                conn.execute(
                    "INSERT INTO energy_counter_state (ip, counters, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(ip) DO UPDATE SET counters = excluded.counters, updated_at = excluded.updated_at",
                    (ip, json.dumps(counters), now),
                )


accumulator = EnergyAccumulator()


# ---------------------------------------------------------------- tariffs

def get_tariffs() -> dict:
    raw = (db.get_config() or {}).get("energy_tariffs")
    tariffs = dict(DEFAULT_TARIFFS)
    if raw:
        try:
            tariffs.update(json.loads(raw))
        except (TypeError, ValueError):
            pass
    return tariffs


def save_tariffs(tariffs: dict) -> dict:
    db.update_config_fields(energy_tariffs=json.dumps(tariffs))
    return get_tariffs()


def is_night_hour(hour: int, tariffs: dict) -> bool:
    if not tariffs.get("two_zone"):
        return False
    start = int(tariffs["night_start"][:2])
    end = int(tariffs["night_end"][:2])
    if start == end:
        return False
    return start <= hour < end if start < end else hour >= start or hour < end


# ---------------------------------------------------------------- reports

def _hourly_rows(start: date, end: date) -> list[tuple]:
    with db.get_connection() as conn:
        return conn.execute(
            f"""
            SELECT hour, {", ".join(f"SUM({f})" for f in FIELDS)}
            FROM energy_hourly
            WHERE hour >= ? AND hour < ?
            GROUP BY hour
            ORDER BY hour
            """,
            (start.strftime("%Y-%m-%d 00"), (end + timedelta(days=1)).strftime("%Y-%m-%d 00")),
        ).fetchall()


def _empty_day(day: str) -> dict:
    return {"date": day, **{f: 0.0 for f in FIELDS}, "grid_in_day": 0.0, "grid_in_night": 0.0,
            "load_day": 0.0, "load_night": 0.0}


def _finish(row: dict, tariffs: dict) -> dict:
    day_price = tariffs["day_price"]
    night_price = tariffs["night_price"] if tariffs.get("two_zone") else day_price
    row["cost"] = row["grid_in_day"] * day_price + row["grid_in_night"] * night_price
    # What the same consumption would have cost with everything bought from the grid.
    row["cost_without_system"] = row["load_day"] * day_price + row["load_night"] * night_price
    row["export_income"] = row["grid_out"] * tariffs.get("export_price", 0.0)
    row["savings"] = row["cost_without_system"] - row["cost"] + row["export_income"]
    row["self_sufficiency"] = (max(0.0, min(1.0, 1 - row["grid_in"] / row["load"])) if row["load"] > 0 else None)
    row["self_consumption"] = (max(0.0, min(1.0, (row["pv"] - row["grid_out"]) / row["pv"])) if row["pv"] > 0 else None)
    for key, value in list(row.items()):
        if isinstance(value, float):
            row[key] = round(value, 3 if key in FIELDS or key.startswith(("grid_in_", "load_")) else 2)
    return row


def summary(start: date, end: date, tariffs: dict | None = None) -> dict:
    tariffs = tariffs or get_tariffs()
    days: dict[str, dict] = {}
    for hour_key, *values in _hourly_rows(start, end):
        day, hour = hour_key[:10], int(hour_key[11:13])
        row = days.setdefault(day, _empty_day(day))
        hourly = dict(zip(FIELDS, (v or 0.0 for v in values)))
        for field, value in hourly.items():
            row[field] += value
        zone = "night" if is_night_hour(hour, tariffs) else "day"
        row[f"grid_in_{zone}"] += hourly["grid_in"]
        row[f"load_{zone}"] += hourly["load"]

    day_rows = [_finish(days[d], tariffs) for d in sorted(days)]
    totals = _empty_day("total")
    for row in day_rows:
        for key in (*FIELDS, "grid_in_day", "grid_in_night", "load_day", "load_night"):
            totals[key] += row[key]
    totals = _finish(totals, tariffs)
    totals.pop("date")
    return {"from": start.isoformat(), "to": end.isoformat(), "tariffs": tariffs, "totals": totals, "days": day_rows}


def months_overview() -> list[dict]:
    with db.get_connection() as conn:
        months = [r[0] for r in conn.execute("SELECT DISTINCT substr(hour, 1, 7) FROM energy_hourly ORDER BY 1 DESC")]
    result = []
    for month in months:
        first = date.fromisoformat(month + "-01")
        last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        totals = summary(first, last)["totals"]
        result.append({"month": month, **{k: totals[k] for k in ("pv", "load", "grid_in", "grid_out", "cost", "savings")}})
    return result

"""Per-cell voltage history and weak-cell detection.

Every 5 minutes the average voltage of each cell (and the pack SOC) is stored per BMS. The heatmap shows
each cell's deviation from the pack average over weeks. A cell with less capacity than the others drifts
*below* the average when the battery is nearly empty and *above* it when nearly full — long before any
alert threshold is reached — so the "weak cell score" is: deviation at high SOC − deviation at low SOC.
"""
import asyncio
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import python.db as db

router = APIRouter(prefix="/cells", tags=["Cell history"])

SAMPLE_SECONDS = 300
HOURLY_RESOLUTION = 3600
MAX_COLUMNS = 168              # heatmap width
LOW_SOC = 30
HIGH_SOC = 90
BUCKET_CHOICES_HOURS = (1, 2, 3, 4, 6, 8, 12, 24)


def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cell_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        device_address TEXT NOT NULL,
        device_name TEXT,
        soc REAL,
        voltages TEXT NOT NULL,          -- JSON list of average cell voltages (V)
        resolution INTEGER NOT NULL DEFAULT 300
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cell_history_device_ts ON cell_history (device_address, timestamp)")


# ---------------------------------------------------------------- recording

class CellRecorder:
    def __init__(self):
        self._acc: dict[str, dict] = {}

    def add(self, device_address: str, device_name: str, voltages: list[float], soc, now: Optional[float] = None):
        """Accumulates a cell-info frame; returns a row to store when the 5-minute interval is complete."""
        now = time.monotonic() if now is None else now
        acc = self._acc.get(device_address)
        if acc is None or len(acc["sums"]) != len(voltages):
            acc = self._acc[device_address] = {"started": now, "sums": [0.0] * len(voltages), "soc": 0.0, "n": 0}
        acc["sums"] = [s + v for s, v in zip(acc["sums"], voltages)]
        acc["soc"] += soc or 0
        acc["n"] += 1
        if now - acc["started"] < SAMPLE_SECONDS:
            return None
        row = (
            datetime.now().strftime(db.TIMESTAMP_FORMAT),
            device_address,
            device_name,
            round(acc["soc"] / acc["n"], 1),
            json.dumps([round(s / acc["n"], 4) for s in acc["sums"]]),
        )
        del self._acc[device_address]
        return row


recorder = CellRecorder()


def _insert(row: tuple):
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO cell_history (timestamp, device_address, device_name, soc, voltages) VALUES (?, ?, ?, ?, ?)",
            row,
        )


async def record_cell_info(device_address: str, device_name: str, voltages: list[float], soc):
    if not voltages:
        return
    row = recorder.add(device_address, device_name, voltages, soc)
    if row:
        try:
            await asyncio.to_thread(_insert, row)
        except Exception as e:
            print(f"❌ Failed to store cell history for {device_name}: {e}")


# ---------------------------------------------------------------- retention

def rollup_old_cell_history(older_than_days: int) -> int:
    """Old 5-minute rows -> hourly averages (same idea as bms_data). Returns removed rows."""
    cutoff = (datetime.now() - timedelta(days=older_than_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_str = cutoff.strftime(db.TIMESTAMP_FORMAT)
    removed = 0
    while True:
        with db.get_connection() as conn:
            first = conn.execute(
                "SELECT MIN(timestamp) FROM cell_history WHERE timestamp < ? AND resolution < ?",
                (cutoff_str, HOURLY_RESOLUTION),
            ).fetchone()[0]
            if not first:
                break
            day_start = datetime.strptime(first[:10], "%Y-%m-%d")
            day_end = min(day_start + timedelta(days=1), cutoff)
            params = (day_start.strftime(db.TIMESTAMP_FORMAT), day_end.strftime(db.TIMESTAMP_FORMAT), HOURLY_RESOLUTION)
            rows = conn.execute(
                "SELECT timestamp, device_address, device_name, soc, voltages FROM cell_history "
                "WHERE timestamp >= ? AND timestamp < ? AND resolution < ?",
                params,
            ).fetchall()
            groups: dict[tuple, list] = defaultdict(list)
            for ts, address, name, soc, voltages in rows:
                groups[(address, ts[:13])].append((name, soc, json.loads(voltages)))
            for (address, hour), items in groups.items():
                width = max(len(v) for _, _, v in items)
                same = [v for _, _, v in items if len(v) == width]
                avg = [round(sum(col) / len(same), 4) for col in zip(*same)]
                socs = [s for _, s, _ in items if s is not None]
                conn.execute(
                    "INSERT INTO cell_history (timestamp, device_address, device_name, soc, voltages, resolution) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (f"{hour}:00:00", address, items[-1][0], round(sum(socs) / len(socs), 1) if socs else None,
                     json.dumps(avg), HOURLY_RESOLUTION),
                )
            removed += conn.execute(
                "DELETE FROM cell_history WHERE timestamp >= ? AND timestamp < ? AND resolution < ?", params
            ).rowcount
    return removed


# ---------------------------------------------------------------- analysis

def _bucket_hours(days: int) -> int:
    needed = days * 24 / MAX_COLUMNS
    return next((h for h in BUCKET_CHOICES_HOURS if h >= needed), 24)


def analyze(rows: list[tuple], days: int, now: Optional[datetime] = None) -> dict:
    """rows: (timestamp, soc, voltages_json). Pure function (unit-tested)."""
    now = now or datetime.now()
    bucket_h = _bucket_hours(days)
    start = (now - timedelta(days=days)).replace(minute=0, second=0, microsecond=0)
    start = start.replace(hour=start.hour - start.hour % bucket_h)
    n_buckets = math.ceil((now - start).total_seconds() / (bucket_h * 3600))

    parsed = [(datetime.strptime(ts[:19], db.TIMESTAMP_FORMAT), soc, json.loads(v)) for ts, soc, v in rows]
    cells = max((len(v) for _, _, v in parsed), default=0)
    parsed = [p for p in parsed if len(p[2]) == cells]

    sums = [[0.0] * n_buckets for _ in range(cells)]
    counts = [0] * n_buckets
    low = [[] for _ in range(cells)]
    high = [[] for _ in range(cells)]
    all_dev = [[] for _ in range(cells)]
    for ts, soc, voltages in parsed:
        index = int((ts - start).total_seconds() // (bucket_h * 3600))
        mean = sum(voltages) / cells
        deviations = [(v - mean) * 1000 for v in voltages]  # mV
        if 0 <= index < n_buckets:
            counts[index] += 1
            for c in range(cells):
                sums[c][index] += deviations[c]
        for c in range(cells):
            all_dev[c].append(deviations[c])
            if soc is not None and soc <= LOW_SOC:
                low[c].append(deviations[c])
            elif soc is not None and soc >= HIGH_SOC:
                high[c].append(deviations[c])

    matrix = [[round(sums[c][b] / counts[b], 1) if counts[b] else None for b in range(n_buckets)] for c in range(cells)]
    avg = lambda values: sum(values) / len(values) if values else None  # noqa: E731
    stats = []
    for c in range(cells):
        low_dev, high_dev = avg(low[c]), avg(high[c])
        score = (high_dev - low_dev) if low_dev is not None and high_dev is not None else None
        stats.append({
            "cell": c + 1,
            "mean_dev_mv": round(avg(all_dev[c]), 1) if all_dev[c] else None,
            "max_abs_dev_mv": round(max((abs(d) for d in all_dev[c]), default=0), 1),
            "low_soc_dev_mv": round(low_dev, 1) if low_dev is not None else None,
            "high_soc_dev_mv": round(high_dev, 1) if high_dev is not None else None,
            "weak_score_mv": round(score, 1) if score is not None else None,
        })

    has_scores = any(s["weak_score_mv"] is not None for s in stats)
    key = (lambda s: s["weak_score_mv"] if s["weak_score_mv"] is not None else -1e9) if has_scores else (lambda s: s["max_abs_dev_mv"])
    ranking = sorted(stats, key=key, reverse=True)
    suspects = [s["cell"] for s in ranking[:3] if (s["weak_score_mv"] or 0) >= 15 or (not has_scores and s["max_abs_dev_mv"] >= 30)]

    return {
        "cells": cells,
        "bucket_hours": bucket_h,
        "buckets": [(start + timedelta(hours=bucket_h * b)).isoformat(timespec="minutes") for b in range(n_buckets)],
        "deviation_mv": matrix,
        "cell_stats": stats,
        "suspects": suspects,
        "method": "soc" if has_scores else "spread",
        "samples": len(parsed),
    }


def _devices() -> list[dict]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT device_address, MAX(device_name), MIN(timestamp), MAX(timestamp), COUNT(*) "
            "FROM cell_history GROUP BY device_address ORDER BY 2"
        ).fetchall()
    return [{"device_address": a, "device_name": n, "first": f, "last": l, "samples": c} for a, n, f, l, c in rows]


def _rows(device_address: str, since: datetime) -> list[tuple]:
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT timestamp, soc, voltages FROM cell_history WHERE device_address = ? AND timestamp >= ? ORDER BY timestamp",
            (device_address, since.strftime(db.TIMESTAMP_FORMAT)),
        ).fetchall()


@router.get("/devices")
async def cell_history_devices():
    return await asyncio.to_thread(_devices)


@router.get("/history")
async def cell_history(device: str = Query(..., max_length=32), days: int = Query(14, ge=1, le=180)):
    device = device.strip().lower()
    rows = await asyncio.to_thread(_rows, device, datetime.now() - timedelta(days=days))
    if not rows:
        raise HTTPException(status_code=404, detail="No cell history for this device yet")
    result = await asyncio.to_thread(analyze, rows, days)
    return {"device_address": device, "days": days, **result}

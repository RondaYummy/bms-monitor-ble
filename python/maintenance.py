"""Data retention (rollup of old per-minute rows into hourly rows) and SQLite backups."""
import asyncio
import gzip
import os
import re
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import python.db as db
from python.auth.verify_token import TOKEN_LIFETIME_SECONDS, require_admin

router = APIRouter(prefix="/maintenance", tags=["Maintenance"], dependencies=[Depends(require_admin)])

BACKUP_DIR = os.getenv("BACKUP_DIR", os.path.join(os.path.dirname(db.DB_NAME) or ".", "backups"))
BACKUP_NAME_RE = re.compile(r"^bms_data-\d{8}-\d{6}\.db\.gz$")
BACKUP_INTERVAL_HOURS = 24
HOURLY_RESOLUTION = 3600

_state = {"last_rollup": None, "last_rollup_result": None, "last_backup_error": None}
_backup_lock = asyncio.Lock()


# ---------------------------------------------------------------- retention

def rollup_old_bms_data(older_than_days: int, now: Optional[datetime] = None) -> dict:
    """Replaces raw rows older than N days with hourly averages (one transaction per day, so writers
    are never blocked for long). Charts and analytics keep working: rows keep the same columns."""
    now = now or datetime.now()
    cutoff = (now - timedelta(days=older_than_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_str = cutoff.strftime(db.TIMESTAMP_FORMAT)
    days_done = rows_removed = rows_added = 0

    while True:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT MIN(timestamp) FROM bms_data WHERE timestamp < ? AND COALESCE(resolution, 60) < ?",
                (cutoff_str, HOURLY_RESOLUTION),
            ).fetchone()
            if not row or not row[0]:
                break
            day_start = datetime.strptime(row[0][:10], "%Y-%m-%d")
            day_end = min(day_start + timedelta(days=1), cutoff)
            params = (day_start.strftime(db.TIMESTAMP_FORMAT), day_end.strftime(db.TIMESTAMP_FORMAT), HOURLY_RESOLUTION)

            added = conn.execute(
                """
                INSERT INTO bms_data (timestamp, current, power, remaining_capacity, device_address, device_name,
                                      voltage_difference, resolution)
                SELECT strftime('%Y-%m-%d %H:00:00', timestamp), AVG(current), AVG(power), AVG(remaining_capacity),
                       device_address, MAX(device_name), MAX(voltage_difference), 3600
                FROM bms_data
                WHERE timestamp >= ? AND timestamp < ? AND COALESCE(resolution, 60) < ?
                GROUP BY device_address, strftime('%Y-%m-%d %H', timestamp)
                """,
                params,
            ).rowcount
            removed = conn.execute(
                "DELETE FROM bms_data WHERE timestamp >= ? AND timestamp < ? AND COALESCE(resolution, 60) < ?",
                params,
            ).rowcount
        days_done += 1
        rows_added += max(added, 0)
        rows_removed += max(removed, 0)

    if days_done:
        db.AGGREGATED_CACHE.clear()
    return {"days": days_done, "rows_removed": rows_removed, "rows_added": rows_added, "cutoff": cutoff_str}


def purge_old_alerts(older_than_days: int) -> int:
    cutoff = (datetime.now() - timedelta(days=older_than_days)).strftime(db.TIMESTAMP_FORMAT)
    with db.get_connection() as conn:
        return conn.execute("DELETE FROM error_notifications WHERE occurred_at < ?", (cutoff,)).rowcount


def data_stats() -> dict:
    with db.get_connection() as conn:
        raw, hourly, oldest = conn.execute(
            """
            SELECT SUM(CASE WHEN COALESCE(resolution, 60) < 3600 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(resolution, 60) >= 3600 THEN 1 ELSE 0 END),
                   MIN(timestamp)
            FROM bms_data
            """
        ).fetchone()
        alerts = conn.execute("SELECT COUNT(*) FROM error_notifications").fetchone()[0]
    size = sum(os.path.getsize(db.DB_NAME + suffix) for suffix in ("", "-wal") if os.path.exists(db.DB_NAME + suffix))
    return {"raw_rows": raw or 0, "hourly_rows": hourly or 0, "oldest": oldest, "alerts": alerts, "db_size_bytes": size}


# ---------------------------------------------------------------- backups

def list_backups() -> list[dict]:
    if not os.path.isdir(BACKUP_DIR):
        return []
    items = []
    for name in os.listdir(BACKUP_DIR):
        if BACKUP_NAME_RE.match(name):
            path = os.path.join(BACKUP_DIR, name)
            items.append({"name": name, "size_bytes": os.path.getsize(path),
                          "created_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")})
    return sorted(items, key=lambda b: b["name"], reverse=True)


def create_backup(keep: int) -> dict:
    """Consistent online copy via the SQLite backup API (safe while the app writes), gzip-compressed.

    The encryption key (secret.key) is intentionally NOT part of the backup.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = f"bms_data-{datetime.now():%Y%m%d-%H%M%S}.db.gz"
    tmp_db = os.path.join(BACKUP_DIR, f".{name}.tmp.db")
    tmp_gz = os.path.join(BACKUP_DIR, f".{name}.tmp")
    try:
        src = sqlite3.connect(db.DB_NAME, timeout=30)
        dst = sqlite3.connect(tmp_db)
        try:
            src.backup(dst, pages=1024, sleep=0.01)  # in chunks: writers are never blocked for long
        finally:
            dst.close()
            src.close()
        with open(tmp_db, "rb") as f_in, gzip.open(tmp_gz, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out, 1024 * 1024)
        os.replace(tmp_gz, os.path.join(BACKUP_DIR, name))
    finally:
        for path in (tmp_db, tmp_gz):
            if os.path.exists(path):
                os.remove(path)

    for old in list_backups()[max(1, keep):]:
        os.remove(os.path.join(BACKUP_DIR, old["name"]))
    return next(b for b in list_backups() if b["name"] == name)


def _backup_path(name: str) -> str:
    if not BACKUP_NAME_RE.match(name):  # also blocks path traversal
        raise HTTPException(status_code=400, detail="Invalid backup name")
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Backup not found")
    return path


# ---------------------------------------------------------------- background loop

async def run_backup_now() -> dict:
    async with _backup_lock:
        keep = int((db.get_config() or {}).get("backup_keep") or 7)
        try:
            backup = await asyncio.to_thread(create_backup, keep)
            _state["last_backup_error"] = None
            print(f"💾 Backup created: {backup['name']} ({backup['size_bytes'] / 1e6:.1f} MB)")
            return backup
        except Exception as e:
            _state["last_backup_error"] = str(e)
            print(f"❌ Backup failed: {e}")
            raise


async def run_retention_now() -> dict:
    config = db.get_config() or {}
    result = await asyncio.to_thread(rollup_old_bms_data, int(config.get("raw_retention_days") or 90))
    result["alerts_removed"] = await asyncio.to_thread(purge_old_alerts, int(config.get("alerts_retention_days") or 365))
    _state["last_rollup"] = datetime.now().isoformat(timespec="seconds")
    _state["last_rollup_result"] = result
    if result["days"] or result["alerts_removed"]:
        print(f"🗜️ Retention: {result}")
    return result


async def maintenance_loop():
    await asyncio.sleep(10 * 60)  # let the system settle after boot
    last_rollup_day = None
    while True:
        try:
            await asyncio.to_thread(db.purge_expired_tokens, TOKEN_LIFETIME_SECONDS)

            today = datetime.now().date()
            if last_rollup_day != today:
                await run_retention_now()
                last_rollup_day = today

            config = db.get_config() or {}
            if config.get("backup_enabled", 1):
                backups = list_backups()
                newest = datetime.fromisoformat(backups[0]["created_at"]) if backups else None
                if newest is None or datetime.now() - newest >= timedelta(hours=BACKUP_INTERVAL_HOURS):
                    await run_backup_now()
        except Exception as e:
            print(f"❌ Maintenance error: {e}")
        await asyncio.sleep(60 * 60)


# ---------------------------------------------------------------- API (admin only)

class MaintenanceSettings(BaseModel):
    raw_retention_days: Optional[int] = Field(None, ge=7, le=3650)
    alerts_retention_days: Optional[int] = Field(None, ge=7, le=3650)
    backup_enabled: Optional[bool] = None
    backup_keep: Optional[int] = Field(None, ge=1, le=60)


def _settings(config: dict) -> dict:
    return {
        "raw_retention_days": config.get("raw_retention_days") or 90,
        "alerts_retention_days": config.get("alerts_retention_days") or 365,
        "backup_enabled": bool(config.get("backup_enabled", 1)),
        "backup_keep": config.get("backup_keep") or 7,
    }


@router.get("")
async def maintenance_status():
    return {
        "settings": _settings(db.get_config() or {}),
        "stats": await asyncio.to_thread(data_stats),
        "backups": await asyncio.to_thread(list_backups),
        **_state,
    }


@router.post("/settings")
def update_settings(body: MaintenanceSettings):
    fields = body.model_dump(exclude_none=True)
    if "backup_enabled" in fields:
        fields["backup_enabled"] = int(fields["backup_enabled"])
    return _settings(db.update_config_fields(**fields) or {})


@router.post("/backups")
async def backup_now():
    try:
        return await run_backup_now()
    except Exception:
        raise HTTPException(status_code=500, detail="Backup failed, see server logs")


@router.post("/rollup")
async def rollup_now():
    return await run_retention_now()


@router.get("/backups/{name}")
def download_backup(name: str):
    return FileResponse(_backup_path(name), media_type="application/gzip", filename=name)


@router.delete("/backups/{name}")
def delete_backup(name: str):
    os.remove(_backup_path(name))
    return {"deleted": True}

import asyncio
import base64
import hashlib
import math
import os
import secrets
import sqlite3
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from python import security
from python.pwd import hash_password

data_aggregator = defaultdict(lambda: {
    "device_name": None,
    "device_address": None,
    "current_sum": 0,
    "remaining_capacity": 0,
    "power_sum": 0,
    "current_min": float('inf'),
    "current_max": float('-inf'),
    "voltage_diff_max": None,
    "count": 0,
    "last_insert_time": None
})

DB_NAME = os.getenv("DB_PATH", '/app/data/bms_data.db')
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Charts never need more than this many points per device; longer ranges are averaged into buckets.
MAX_CHART_POINTS_PER_DEVICE = 1500

CONFIG_CACHE = None
CONFIG_CACHE_TIMESTAMP = 0
CONFIG_CACHE_EXPIRY = 60

# Single snapshot of the (tiny) devices table, invalidated on every write.
DEVICE_CACHE = {"data": None, "timestamp": 0.0}  # data: {address: device_dict}
DEVICE_CACHE_EXPIRY = 60

DEVICE_COLUMNS = (
    "id", "address", "name", "added_at", "connected", "enabled", "frame_type", "frame_counter",
    "vendor_id", "hardware_version", "software_version", "device_uptime", "power_on_count",
    "manufacturing_date", "serial_number", "user_data",
)
DEVICE_UPDATABLE_COLUMNS = set(DEVICE_COLUMNS) - {"id", "address", "added_at"}

ALERT_CACHE = {}  # {device_address: {error_code: {"timestamp": occurred_at, "id": alert_id}}}
ALERT_CACHE_EXPIRY = 60

AGGREGATED_CACHE = {}
AGGREGATED_CACHE_EXPIRY = 60 * 4

async def process_devices():
    """Cyclically calls update_aggregated_data and saves the aggregated data."""
    global data_aggregator
    while True:
        for device_address, device_data in data_aggregator.items():
            try:
                device_name = device_data["device_name"]
                save_aggregated_data(device_name, device_address, device_data)
            except Exception as e:
                print(f"Error processing {device_data['device_name']} ({device_address}): {e}")

        await asyncio.sleep(60 * 5)

def update_aggregated_data(device_name, device_address, current, power, remaining_capacity, voltage_difference=None):
    """Updates intermediate data for aggregation."""
    global data_aggregator
    now = datetime.now()

    if not isinstance(device_name, str) or not device_name.strip():
        raise ValueError(f"Invalid device_name: {device_name}")
    if not isinstance(device_address, str) or not device_address.strip():
        raise ValueError(f"Invalid device_address: {device_address}")
    if not isinstance(current, (int, float)):
        raise ValueError(f"Invalid current: {current}")
    if not isinstance(power, (int, float)) or power < 0:
        raise ValueError(f"Invalid power: {power}")
    if not isinstance(power, (int, float)) or remaining_capacity < 0:
        raise ValueError(f"Invalid remaining_capacity: {remaining_capacity}")

    device_data = data_aggregator[device_address]

    if device_data["device_name"] is None:
        device_data["device_name"] = device_name
    if device_data["device_address"] is None:
        device_data["device_address"] = device_address

    device_data["current_sum"] += current
    device_data["power_sum"] += power
    device_data["remaining_capacity"] += remaining_capacity

    device_data["current_min"] = min(device_data["current_min"], current)
    device_data["current_max"] = max(device_data["current_max"], current)
    if isinstance(voltage_difference, (int, float)):
        previous = device_data.get("voltage_diff_max")
        device_data["voltage_diff_max"] = voltage_difference if previous is None else max(previous, voltage_difference)

    # Increase the number of records
    device_data["count"] += 1
    if device_data["last_insert_time"] is None:
        device_data["last_insert_time"] = now

def save_aggregated_data(device_name, device_address, device_data, interval=60):
    now = datetime.now()
    last_insert_time = device_data["last_insert_time"]

    if last_insert_time and (now - last_insert_time).total_seconds() < interval:
        return  # The interval has not yet expired

    # Calculating the average value
    if device_data["count"] > 0:
        current_avg = device_data["current_sum"] / device_data["count"]
        power_avg = device_data["power_sum"] / device_data["count"]
        remaining_capacity_avg = device_data["remaining_capacity"] / device_data["count"]
    else:
        return  # No data to save

    timestamp = now.strftime(TIMESTAMP_FORMAT)

    try:
        insert_data(
            timestamp=timestamp,
            current=current_avg,
            power=power_avg,
            remaining_capacity=remaining_capacity_avg,
            device_address=device_address,
            device_name=device_name,
            voltage_difference=device_data.get("voltage_diff_max"),
        )
        # print(f"Aggregated data saved for {device_name} ({device_address}) at {timestamp}")
    except Exception as e:
        print(f"Error saving aggregated data: {e}")

    device_data.update({
        "current_sum": 0,
        "power_sum": 0,
        "current_min": float('inf'),
        "current_max": float('-inf'),
        "voltage_diff_max": None,
        "remaining_capacity": 0,
        "count": 0,
        "last_insert_time": now
    })

@contextmanager
def get_connection():
    """Opens a connection, commits on success, rolls back on error and ALWAYS closes it.

    (`with sqlite3.connect(...) as conn` only manages the transaction and leaks the connection.)
    """
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise
    try:
        conn.execute("PRAGMA busy_timeout = 10000")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Convert private key to PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")

    # Convert public key to Base64
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_base64 = base64.urlsafe_b64encode(public_pem).decode("utf-8").rstrip("=")  # Without '=' at the end

    return private_pem, public_base64

def _initial_admin_password() -> str:
    """Password for a freshly created database: ADMIN_PASSWORD env or a random one printed once."""
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if password:
        return password
    password = secrets.token_urlsafe(12)
    print("=" * 70)
    print(f"🔐 Initial admin password (change it in Settings): {password}")
    print("=" * 70)
    return password

def create_table():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # WAL lets the API read while background loops write (fewer "database is locked").
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bms_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                current REAL NOT NULL,
                remaining_capacity REAL NOT NULL,
                power REAL NOT NULL,
                device_address TEXT NOT NULL,
                device_name TEXT NOT NULL
            )
            ''')
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON bms_data (timestamp)
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_address TEXT NOT NULL,
                error_code TEXT NOT NULL,
                device_name TEXT NOT NULL,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_notifications_lookup
            ON error_notifications (device_address, error_code, occurred_at)
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password TEXT DEFAULT '',
                VAPID_PUBLIC_KEY TEXT DEFAULT '',
                VAPID_PRIVATE_KEY TEXT DEFAULT '',
                n_hours INTEGER DEFAULT 12,
                auto_power_management_enabled INTEGER DEFAULT 0
            )
            ''')
            cursor.execute("SELECT COUNT(*) FROM configs")
            if cursor.fetchone()[0] == 0:
                private_pem, public_base64 = generate_vapid_keys()
                hashed_password = hash_password(_initial_admin_password())
                cursor.execute('''
                INSERT INTO configs (password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours)
                VALUES (?, ?, ?, ?)
                ''', (hashed_password, public_base64, private_pem, 12))

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                connected BOOLEAN DEFAULT FALSE,
                enabled BOOLEAN DEFAULT TRUE,
                frame_type INTEGER,
                frame_counter INTEGER,
                vendor_id TEXT,
                hardware_version TEXT,
                software_version TEXT,
                device_uptime INTEGER,
                power_on_count INTEGER,
                manufacturing_date TEXT,
                serial_number TEXT,
                user_data TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tapo_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                device_on BOOLEAN DEFAULT FALSE,
                auto_enabled BOOLEAN DEFAULT FALSE,
                auto_power_off_enabled INTEGER DEFAULT 0,
                device_id TEXT,
                name TEXT,
                model TEXT,
                fw_ver TEXT,
                hw_ver TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                power_watt INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS deye_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL UNIQUE,
                serial_number TEXT NOT NULL,
                slave_id INTEGER DEFAULT 1,
                timestamp TEXT,
                pv1_power REAL,
                pv2_power REAL,
                total_pv REAL,
                load_power REAL,
                grid_power REAL,
                battery_power REAL,
                battery_voltage REAL,
                battery_soc REAL,
                net_balance REAL,
                device_on INTEGER DEFAULT 1,
                stat_daily_pv REAL,
                stat_total_pv REAL,
                stat_daily_bat_discharge REAL,
                stat_daily_grid_in REAL,
                stat_daily_grid_out REAL,
                stat_total_grid_out REAL,
                stat_total_load REAL
            )
            ''')
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_tokens (
                token TEXT PRIMARY KEY,
                created_at TEXT
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ssl_certificates (
                created_at TEXT,
                days INTEGER DEFAULT 90
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'viewer')),
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                totp_last_step INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tapo_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                name TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                days TEXT NOT NULL DEFAULT '0123456',
                min_soc REAL,
                min_pv_w REAL,
                turn_off_at_end INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # ---- Additive migrations for existing databases ----
            _ensure_column(cursor, "bms_data", "voltage_difference", "REAL")
            _ensure_column(cursor, "bms_data", "resolution", "INTEGER DEFAULT 60")
            _ensure_column(cursor, "error_notifications", "message", "TEXT")
            _ensure_column(cursor, "active_tokens", "user_id", "INTEGER")
            _ensure_column(cursor, "configs", "public_read", "INTEGER DEFAULT 1")
            _ensure_column(cursor, "configs", "alert_thresholds", "TEXT")
            _ensure_column(cursor, "configs", "raw_retention_days", "INTEGER DEFAULT 90")
            _ensure_column(cursor, "configs", "alerts_retention_days", "INTEGER DEFAULT 365")
            _ensure_column(cursor, "configs", "backup_enabled", "INTEGER DEFAULT 1")
            _ensure_column(cursor, "configs", "backup_keep", "INTEGER DEFAULT 7")
            _ensure_column(cursor, "configs", "energy_tariffs", "TEXT")
            _ensure_column(cursor, "configs", "solar_settings", "TEXT")
            # Live status notification preferences (per device = per push subscription)
            _ensure_column(cursor, "subscriptions", "status_enabled", "INTEGER NOT NULL DEFAULT 0")
            _ensure_column(cursor, "subscriptions", "status_interval_min", "INTEGER NOT NULL DEFAULT 10")
            _ensure_column(cursor, "subscriptions", "platform", "TEXT")
            _ensure_column(cursor, "subscriptions", "last_status_at", "TEXT")
            _ensure_column(cursor, "subscriptions", "last_status_soc", "REAL")
            _ensure_column(cursor, "subscriptions", "last_status_grid", "INTEGER")
            _ensure_column(cursor, "deye_devices", "grid_voltage", "REAL")

            # Feature modules own their tables (imported here to avoid import cycles).
            from python import cell_history, energy, solar_forecast
            energy.create_tables(cursor)
            cell_history.create_tables(cursor)
            solar_forecast.create_tables(cursor)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bms_data_device_ts ON bms_data (device_address, timestamp)")

            # The single legacy password becomes the "admin" user.
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("SELECT password FROM configs LIMIT 1")
                row = cursor.fetchone()
                legacy_hash = row[0] if row and row[0] else hash_password(_initial_admin_password())
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES ('admin', ?, 'admin')",
                    (legacy_hash,),
                )
                print("👤 Created user 'admin' (role: admin) from the existing password.")

            # Encrypt Tapo passwords that are still stored in plaintext.
            cursor.execute("SELECT id, password FROM tapo_devices")
            for device_id, password in cursor.fetchall():
                if password and not security.is_encrypted(password):
                    cursor.execute("UPDATE tapo_devices SET password = ? WHERE id = ?",
                                   (security.encrypt(password), device_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        raise

def _ensure_column(cursor, table: str, column: str, ddl: str):
    cursor.execute(f"PRAGMA table_info({table})")
    if column not in {row[1] for row in cursor.fetchall()}:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

def get_latest_ssl_certificate():
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            cursor.execute('''
            SELECT created_at, days 
            FROM ssl_certificates 
            ORDER BY created_at DESC 
            LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                return None
    except sqlite3.Error as e:
        print(f"❌ Error fetching latest SSL certificate: {e}")
        return None

def cleanup_ssl_certificates():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT MAX(created_at) FROM ssl_certificates
            ''')
            latest_created_at = cursor.fetchone()[0]
            
            if not latest_created_at:
                print("⚠️ Table ssl_certificates is empty. Nothing to delete.")
                return 0
            cursor.execute('''
            DELETE FROM ssl_certificates
            WHERE created_at NOT IN (
                SELECT created_at
                FROM ssl_certificates
                ORDER BY created_at DESC
                LIMIT 1
            );
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                print(f"🧹 Successfully deleted {deleted_count} old SSL certificate record(s).")
            else:
                print("✅ No old SSL certificate records were found for deletion.")
            
            return deleted_count

    except sqlite3.Error as e:
        print(f"❌ Error cleaning up SSL certificates: {e}")
        return None

def delete_alert_by_id(alert_id):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id FROM error_notifications
            WHERE id = ?
            ''', (alert_id,))
            existing = cursor.fetchone()

            if not existing:
                print(f"No notification found with ID {alert_id}.")
                return

            cursor.execute('''
            DELETE FROM error_notifications
            WHERE id = ?
            ''', (alert_id,))
            conn.commit()

            print(f"Notification with ID {alert_id} has been deleted successfully.")
    except sqlite3.Error as e:
        print(f"Error deleting alert data: {e}")
        raise

def delete_all_alerts():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM error_notifications')
            conn.commit()

            print("✅ All notifications have been deleted successfully.")
    except sqlite3.Error as e:
        print(f"❌ Error deleting all alerts: {e}")
        raise
        
def _invalidate_device_cache():
    DEVICE_CACHE["data"] = None
    DEVICE_CACHE["timestamp"] = 0.0

def _row_to_device(row) -> dict:
    device = dict(zip(DEVICE_COLUMNS, row))
    device["connected"] = bool(device["connected"])
    device["enabled"] = bool(device["enabled"])
    return device

def _load_all_devices() -> dict:
    now = time.time()
    if DEVICE_CACHE["data"] is not None and (now - DEVICE_CACHE["timestamp"]) < DEVICE_CACHE_EXPIRY:
        return DEVICE_CACHE["data"]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {', '.join(DEVICE_COLUMNS)} FROM devices")
        devices = {row[1].lower(): _row_to_device(row) for row in cursor.fetchall()}

    DEVICE_CACHE["data"] = devices
    DEVICE_CACHE["timestamp"] = now
    return devices

def set_all_devices_disconnected():
    try:
        with get_connection() as conn:
            conn.execute("UPDATE devices SET connected = ?", (False,))
        _invalidate_device_cache()
        print("✅ All devices set to `connected = False` on startup.")
    except sqlite3.Error as e:
        print(f"❌ Error resetting device connection status: {e}")

def get_all_devices(only_enabled: bool = False):
    try:
        devices = _load_all_devices()
    except sqlite3.Error as e:
        print(f"❌ Error fetching devices: {e}")
        return []
    # Copies, so callers can never corrupt the cache.
    return [dict(d) for d in devices.values() if not only_enabled or d["enabled"]]

def get_device_by_address(address, force_refresh: bool = False):
    if force_refresh:
        _invalidate_device_cache()
    try:
        device = _load_all_devices().get(address.lower())
    except sqlite3.Error as e:
        print(f"❌ Error when receiving the device: {e}")
        raise
    return dict(device) if device else None

def update_device(address: str, **kwargs):
    # Column names are interpolated into SQL, so only known columns are allowed.
    kwargs = {k: v for k, v in kwargs.items() if k in DEVICE_UPDATABLE_COLUMNS}
    if not kwargs:
        return

    try:
        with get_connection() as conn:
            fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
            values = list(kwargs.values()) + [address.lower()]
            conn.execute(f"UPDATE devices SET {fields} WHERE address = ?", values)
        _invalidate_device_cache()
    except sqlite3.Error as e:
        print(f"❌ Error updating the device: {e}")
        raise

def update_device_status(address, connected: bool, enabled: bool):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE devices SET connected = ?, enabled = ? WHERE address = ?",
                (connected, enabled, address.lower()),
            )
        _invalidate_device_cache()
    except sqlite3.Error as e:
        print(f"❌ Error updating status: {e}")
        raise

def insert_device(
    address, name=None, frame_type=None, frame_counter=None, vendor_id=None,
    hardware_version=None, software_version=None, device_uptime=None, power_on_count=None,
    manufacturing_date=None, serial_number=None, user_data=None, connected=False, enabled=True
):
    address = address.lower()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT OR IGNORE INTO devices (
                address, name, added_at, connected, enabled, frame_type, frame_counter, vendor_id,
                hardware_version, software_version, device_uptime, power_on_count,
                manufacturing_date, serial_number, user_data
            ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                address, name, connected, enabled, frame_type, frame_counter, vendor_id,
                hardware_version, software_version, device_uptime, power_on_count,
                manufacturing_date, serial_number, user_data
            ))
        _invalidate_device_cache()
        return get_device_by_address(address)

    except sqlite3.Error as e:
        print(f"❌ Error inserting the device: {e}")
        raise


def insert_alert_data(device_address, device_name, error_code, occurred_at, n_hours=1, message=None) -> bool:
    """Stores an alert unless the same code was already raised for the device in the last n_hours.

    Returns True if a new alert was stored (i.e. a notification should be sent).
    """
    if isinstance(occurred_at, datetime):
        occurred_at = occurred_at.strftime(TIMESTAMP_FORMAT)
    error_code = int(error_code)
    time_limit_str = (datetime.now() - timedelta(hours=n_hours or 1)).strftime(TIMESTAMP_FORMAT)

    cached_alert = ALERT_CACHE.get(device_address, {}).get(error_code)
    if cached_alert and str(cached_alert["timestamp"]) > time_limit_str:
        return False

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, occurred_at FROM error_notifications
            WHERE device_address = ? AND error_code = ? AND occurred_at > ?
            ''', (device_address, str(error_code), time_limit_str))

            existing = cursor.fetchone()
            if existing:
                ALERT_CACHE.setdefault(device_address, {})[error_code] = {"timestamp": str(existing[1]), "id": existing[0]}
                return False

            cursor.execute('''
            INSERT INTO error_notifications (device_address, error_code, occurred_at, device_name, message)
            VALUES (?, ?, ?, ?, ?)
            ''', (device_address, str(error_code), occurred_at, device_name, message))
            ALERT_CACHE.setdefault(device_address, {})[error_code] = {"timestamp": occurred_at, "id": cursor.lastrowid}
            return True

    except sqlite3.Error as e:
        print(f"Error inserting alerts data: {e}")
        raise

def insert_data(timestamp, current, power, remaining_capacity, device_address, device_name, voltage_difference=None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO bms_data (timestamp, current, power, remaining_capacity, device_address, device_name, voltage_difference)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, current, power, remaining_capacity, device_address, device_name, voltage_difference))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        raise

def _fetch_bms_data(from_dt: datetime, to_dt: datetime | None):
    """Returns rows (timestamp, current, power, device_address, device_name, remaining_capacity).

    Short ranges return raw per-minute rows; long ranges are averaged into time buckets so the
    response never exceeds ~MAX_CHART_POINTS_PER_DEVICE points per device.
    """
    from_str = from_dt.strftime(TIMESTAMP_FORMAT)
    end = to_dt or datetime.now()
    span_seconds = max(0, (end - from_dt).total_seconds())
    bucket_seconds = 0
    if span_seconds > MAX_CHART_POINTS_PER_DEVICE * 60:
        bucket_seconds = int(math.ceil(span_seconds / MAX_CHART_POINTS_PER_DEVICE / 60.0)) * 60

    where = "timestamp >= ?"
    params: list = [from_str]
    if to_dt is not None:
        where += " AND timestamp <= ?"
        params.append(to_dt.strftime(TIMESTAMP_FORMAT))

    with get_connection() as conn:
        cursor = conn.cursor()
        if bucket_seconds:
            cursor.execute(f'''
                SELECT datetime((CAST(strftime('%s', timestamp) AS INTEGER) / ?) * ?, 'unixepoch') AS bucket_ts,
                       AVG(current), AVG(power), device_address, device_name, AVG(remaining_capacity)
                FROM bms_data
                WHERE {where}
                GROUP BY device_address, device_name, bucket_ts
                ORDER BY bucket_ts
            ''', [bucket_seconds, bucket_seconds, *params])
        else:
            cursor.execute(f'''
                SELECT timestamp, current, power, device_address, device_name, remaining_capacity
                FROM bms_data
                WHERE {where}
                ORDER BY timestamp
            ''', params)
        return cursor.fetchall()

def fetch_all_data_range(from_dt: datetime, to_dt: datetime):
    try:
        return _fetch_bms_data(from_dt, to_dt)
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        raise

def fetch_all_data(days=None):
    if days is None:
        print("No 'days' parameter provided. No data will be fetched.")
        return None

    now = datetime.now()
    cache_key = days

    if cache_key in AGGREGATED_CACHE:
        cached_result, cache_time = AGGREGATED_CACHE[cache_key]
        if (now - cache_time).total_seconds() < AGGREGATED_CACHE_EXPIRY:
            return cached_result

    try:
        if days == 1:
            cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            cutoff_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

        result = _fetch_bms_data(cutoff_date, None)
        # Save to cache: the key is days, the value is a tuple (result, time)
        AGGREGATED_CACHE[cache_key] = (result, now)
        return result
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        raise

def fetch_all_notifications():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, device_address, error_code, device_name, occurred_at, message
                FROM error_notifications
                ORDER BY occurred_at DESC
            ''')
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching notifications: {e}")
        raise

def get_subscription_by_endpoint(endpoint: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE endpoint = ?", (endpoint,))
        return cursor.fetchone()
    
def count_subscriptions() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]

def add_subscription(subscription: dict):
    with get_connection() as conn:
        cursor = conn.cursor()

        endpoint = subscription["endpoint"]
        p256dh = subscription["keys"]["p256dh"]
        auth = subscription["keys"]["auth"]

        # Check if this subscription exists with the same `p256dh` (same user)
        cursor.execute("SELECT id, endpoint FROM subscriptions WHERE p256dh = ?", (p256dh,))
        existing = cursor.fetchone()

        if existing:
            old_id, old_endpoint = existing

            if old_endpoint != endpoint:
                print(f"🔄 The old endpoint {old_endpoint} is changed to {endpoint}, delete the old one...")
                cursor.execute("DELETE FROM subscriptions WHERE id = ?", (old_id,))

        # Add a new subscription (or update an existing one)
        cursor.execute('''
        INSERT INTO subscriptions (endpoint, p256dh, auth) 
        VALUES (?, ?, ?)
        ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth
        ''', (endpoint, p256dh, auth))

        conn.commit()

def remove_old_subscription(endpoint: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE endpoint = ?", (endpoint,))
            conn.commit()

            print(f"🗑️ Subscription deleted: {endpoint}")

    except sqlite3.Error as e:
        print(f"❌ Error when deleting a subscription: {e}")

def get_all_subscriptions():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT endpoint, p256dh, auth FROM subscriptions")
            rows = cursor.fetchall()

            subscriptions = [
                {
                    "endpoint": row[0],
                    "keys": {
                        "p256dh": row[1],
                        "auth": row[2]
                    }
                }
                for row in rows
            ]
            return subscriptions
    except sqlite3.Error as e:
        print(f"❌ Error receiving subscriptions: {e}")
        return []

CONFIG_UPDATABLE_COLUMNS = {
    "n_hours", "auto_power_management_enabled", "public_read", "alert_thresholds",
    "raw_retention_days", "alerts_retention_days", "backup_enabled", "backup_keep", "energy_tariffs", "solar_settings",
}

def get_config():
    global CONFIG_CACHE, CONFIG_CACHE_TIMESTAMP

    if CONFIG_CACHE and (time.time() - CONFIG_CACHE_TIMESTAMP) < CONFIG_CACHE_EXPIRY:
        return CONFIG_CACHE

    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM configs ORDER BY id LIMIT 1").fetchone()
            if not row:
                return None
            CONFIG_CACHE = dict(row)
            CONFIG_CACHE_TIMESTAMP = time.time()
            return CONFIG_CACHE
    except sqlite3.Error as e:
        print(f"Error fetching config: {e}")
        return None

def update_config_fields(**fields):
    """Updates whitelisted config columns (None values are ignored). Returns the fresh config."""
    fields = {k: v for k, v in fields.items() if k in CONFIG_UPDATABLE_COLUMNS and v is not None}
    if fields:
        with get_connection() as conn:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(f"UPDATE configs SET {assignments}", list(fields.values()))
    invalidate_config_cache()
    return get_config()

def invalidate_config_cache():
    global CONFIG_CACHE, CONFIG_CACHE_TIMESTAMP
    CONFIG_CACHE = None
    CONFIG_CACHE_TIMESTAMP = 0

def update_config(password=None, vapid_public=None, vapid_private=None, n_hours=None, auto_power_management_enabled=None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours, auto_power_management_enabled
                FROM configs LIMIT 1
            """)
            existing_config = cursor.fetchone()

            if not existing_config:
                raise ValueError("Config record not found!")

            # Always invalidate: a stale cached password hash would keep the OLD password valid.
            invalidate_config_cache()

            updated_config = {
                "password": password if password is not None else existing_config[0],
                "VAPID_PUBLIC_KEY": vapid_public if vapid_public is not None else existing_config[1],
                "VAPID_PRIVATE_KEY": vapid_private if vapid_private is not None else existing_config[2],
                "n_hours": n_hours if n_hours is not None else existing_config[3],
                "auto_power_management_enabled": auto_power_management_enabled if auto_power_management_enabled is not None else existing_config[4],
            }

            cursor.execute("""
                UPDATE configs
                SET password = ?,
                    VAPID_PUBLIC_KEY = ?,
                    VAPID_PRIVATE_KEY = ?,
                    n_hours = ?,
                    auto_power_management_enabled = ?
            """, (
                updated_config["password"],
                updated_config["VAPID_PUBLIC_KEY"],
                updated_config["VAPID_PRIVATE_KEY"],
                updated_config["n_hours"],
                updated_config["auto_power_management_enabled"],
            ))

            conn.commit()
            return updated_config

    except sqlite3.Error as e:
        print(f"Error updating config: {e}")
        return None

def _tapo_row(row: dict | None) -> dict | None:
    """Tapo passwords are encrypted at rest; callers always get the plaintext."""
    if row is not None and row.get("password"):
        row["password"] = security.decrypt(row["password"])
    return row

def get_tapo_device_by_ip(ip):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tapo_devices WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return _tapo_row(dict(zip(columns, row)))
        return None

def insert_tapo_device(ip, email, password, power_watt=0, priority=0):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM tapo_devices WHERE ip = ?", (ip,))
            existing = cursor.fetchone()
            if existing:
                return get_tapo_device_by_ip(ip)

            cursor.execute('''
                INSERT INTO tapo_devices (
                    ip, email, password, added_at, device_on, power_watt, priority
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            ''', (ip, email, security.encrypt(password), False, power_watt, priority))

            conn.commit()
            return get_tapo_device_by_ip(ip)

    except sqlite3.Error as e:
        print(f"❌ Error inserting the Tapo device: {e}")
        raise

def update_tapo_device_by_ip(ip, info: dict):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            fields = []
            values = []

            allowed_fields = ["name", "model", "fw_ver", "hw_ver", "device_id", "device_on", "power_watt"]

            for field in allowed_fields:
                if field in info:
                    fields.append(f"{field} = ?")
                    values.append(info[field])

            if not fields:
                return get_tapo_device_by_ip(ip)

            values.append(ip)

            sql = f'''
                UPDATE tapo_devices
                SET {", ".join(fields)}
                WHERE ip = ?
            '''

            cursor.execute(sql, values)
            conn.commit()

            return get_tapo_device_by_ip(ip)

    except sqlite3.Error as e:
        print(f"❌ Error updating the Tapo device: {e}")
        raise

def update_tapo_device_config_by_ip(ip: str, updates: dict):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []

            # Empty email/password from the edit form mean "keep the current value".
            if updates.get("email"):
                fields.append("email = ?")
                values.append(updates["email"])
            if updates.get("password"):
                fields.append("password = ?")
                values.append(security.encrypt(updates["password"]))
            if "power_watt" in updates:
                fields.append("power_watt = ?")
                values.append(updates["power_watt"])
            if "priority" in updates:
                fields.append("priority = ?")
                values.append(updates["priority"])
            if "auto_power_off_enabled" in updates:
                fields.append("auto_power_off_enabled = ?")
                values.append(updates["auto_power_off_enabled"])

            if not fields:
                return get_tapo_device_by_ip(ip)  # Nothing is updated

            values.append(ip)
            sql = f'''
                UPDATE tapo_devices
                SET {", ".join(fields)}
                WHERE ip = ?
            '''
            cursor.execute(sql, values)
            conn.commit()
            return get_tapo_device_by_ip(ip)
    except sqlite3.Error as e:
        print(f"❌ DB update config error: {e}")
        raise

def get_top_priority_tapo_devices(limit: int | None = None):
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql_query = """
                SELECT * FROM tapo_devices
                ORDER BY priority DESC, ip ASC
            """
            params = ()

            if limit is not None:
                sql_query += " LIMIT ?"
                params = (limit,)

            cursor.execute(sql_query, params)
            devices = [_tapo_row(dict(row)) for row in cursor.fetchall()]
            return devices
    except sqlite3.Error as e:
        print(f"❌ DB error in get_top_priority_tapo_devices: {e}")
        raise

def get_all_tapo_devices():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tapo_devices")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [_tapo_row(dict(zip(columns, row))) for row in rows]

def get_tapo_device_by_id(id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tapo_devices WHERE id = ?", (id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return _tapo_row(dict(zip(columns, row)))
        return None

def delete_tapo_device_by_ip(ip: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tapo_devices WHERE ip = ?", (ip,))
            deleted = cursor.rowcount
            cursor.execute("DELETE FROM tapo_rules WHERE ip = ?", (ip,))
            return deleted > 0  # True if at least 1 line was deleted
    except sqlite3.Error as e:
        print(f"❌ Error deleting the Tapo device with IP {ip}: {e}")
        raise

def create_deye_device(ip, serial_number, slave_id=1, device_on=1):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM deye_devices WHERE ip = ?", (ip,))
            existing = cursor.fetchone()
            if existing:
                return get_deye_device_by_ip(ip)

            cursor.execute('''
                INSERT INTO deye_devices (ip, serial_number, slave_id, device_on)
                VALUES (?, ?, ?, ?)
            ''', (ip, serial_number, slave_id, device_on))
            conn.commit()
            return get_deye_device_by_ip(ip)
    except sqlite3.Error as e:
        print(f"❌ Error inserting Deye device: {e}")
        raise

def update_deye_device_data(ip, data: dict):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []

            for key in [
                "pv1_power", "pv2_power", "total_pv", "load_power", "grid_power",
                "battery_power", "battery_voltage", "battery_soc", "net_balance", "timestamp", "grid_voltage", "stat_daily_pv", "stat_total_pv", "stat_daily_bat_discharge", "stat_daily_grid_in", "stat_daily_grid_out", "stat_total_grid_out", "stat_total_load"
            ]:
                if key in data:
                    fields.append(f"{key} = ?")
                    values.append(data[key])

            if not fields:
                raise ValueError("No valid fields to update.")

            values.append(ip)
            sql = f'''
                UPDATE deye_devices
                SET {", ".join(fields)}
                WHERE ip = ?
            '''
            cursor.execute(sql, values)
            conn.commit()
            return get_deye_device_by_ip(ip)
    except sqlite3.Error as e:
        print(f"❌ Error updating Deye device {ip}: {e}")
        raise

def get_deye_device_by_ip(ip):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deye_devices WHERE ip = ?", (ip,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except sqlite3.Error as e:
        print(f"❌ Error fetching Deye device by IP {ip}: {e}")
        return None

def get_all_deye_devices():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deye_devices")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except sqlite3.Error as e:
        print(f"❌ Error fetching all Deye devices: {e}")
        return []

def delete_deye_device_by_ip(ip: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM deye_devices WHERE ip = ?", (ip,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"❌ Error deleting Deye device with IP {ip}: {e}")
        raise

def _hash_token(token: str) -> str:
    # Tokens are stored hashed, so a leaked DB file/backup does not contain usable sessions.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def add_token_to_db(token: str, user_id: int | None = None):
    try:
        with get_connection() as conn:
            created_at = datetime.now().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO active_tokens (token, created_at, user_id) VALUES (?, ?, ?)",
                (_hash_token(token), created_at, user_id),
            )
    except sqlite3.Error as e:
        print(f"❌ Error adding token to DB: {e}")
        raise

def remove_token_from_db(token: str):
    try:
        with get_connection() as conn:
            # The raw value covers sessions created before tokens were hashed.
            conn.execute("DELETE FROM active_tokens WHERE token IN (?, ?)", (_hash_token(token), token))
    except sqlite3.Error as e:
        print(f"❌ Error removing token from DB: {e}")
        raise

def _first_admin_id(conn) -> int | None:
    row = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    return row[0] if row else None

def remove_all_tokens_except(token: str | None = None, user_id: int | None = None):
    """Revokes sessions (e.g. after a password change), optionally keeping the current one.

    With `user_id` only that user's sessions are revoked (legacy sessions without user belong to the first admin).
    """
    try:
        with get_connection() as conn:
            keep = (_hash_token(token), token) if token else ("", "")
            if user_id is None:
                conn.execute("DELETE FROM active_tokens WHERE token NOT IN (?, ?)", keep)
            else:
                legacy_owner = _first_admin_id(conn)
                conn.execute(
                    "DELETE FROM active_tokens WHERE token NOT IN (?, ?) "
                    "AND (user_id = ? OR (user_id IS NULL AND ? = ?))",
                    (*keep, user_id, user_id, legacy_owner),
                )
    except sqlite3.Error as e:
        print(f"❌ Error revoking tokens: {e}")
        raise

def purge_expired_tokens(lifetime_seconds: int):
    try:
        cutoff = (datetime.now() - timedelta(seconds=lifetime_seconds)).isoformat()
        with get_connection() as conn:
            deleted = conn.execute("DELETE FROM active_tokens WHERE created_at < ?", (cutoff,)).rowcount
        if deleted:
            print(f"🧹 Removed {deleted} expired session token(s).")
    except sqlite3.Error as e:
        print(f"❌ Error purging expired tokens: {e}")

def get_session(token: str, lifetime_seconds: int) -> dict | None:
    """Returns {"user_id", "username", "role"} for a valid session, otherwise None."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT token, created_at, user_id FROM active_tokens WHERE token IN (?, ?)",
                (_hash_token(token), token),
            ).fetchone()
            if not row:
                return None

            stored_token, created_at_str, user_id = row
            if datetime.now() >= datetime.fromisoformat(created_at_str) + timedelta(seconds=lifetime_seconds):
                print("⚠️ Session token expired. Removing from DB.")
                conn.execute("DELETE FROM active_tokens WHERE token = ?", (stored_token,))
                return None

            # Sessions created before multi-user support belong to the (first) admin.
            if user_id is None:
                user_id = _first_admin_id(conn)
            user = conn.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                conn.execute("DELETE FROM active_tokens WHERE token = ?", (stored_token,))
                return None
            return {"user_id": user[0], "username": user[1], "role": user[2]}
    except sqlite3.Error as e:
        print(f"❌ Error validating token in DB: {e}")
        return None

def is_token_valid_in_db(token: str, lifetime_seconds: int) -> bool:
    return get_session(token, lifetime_seconds) is not None

# ---------------------------------------------------------------- users

USER_PUBLIC_COLUMNS = "id, username, role, totp_enabled, created_at"

def _user_row(row) -> dict | None:
    if row is None:
        return None
    user = dict(row)
    if "totp_secret" in user:
        user["totp_secret"] = security.decrypt(user["totp_secret"])
    if "totp_enabled" in user:
        user["totp_enabled"] = bool(user["totp_enabled"])
    return user

def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return _user_row(conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone())

def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return _user_row(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

def list_users() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT {USER_PUBLIC_COLUMNS} FROM users ORDER BY id").fetchall()
        return [_user_row(r) for r in rows]

def count_admins() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]

def create_user(username: str, password_hash: str, role: str) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), password_hash, role),
        )
        user_id = cursor.lastrowid
    return get_user_by_id(user_id)

USER_UPDATABLE_COLUMNS = {"password_hash", "role", "totp_secret", "totp_enabled", "totp_last_step"}

def update_user(user_id: int, **fields):
    fields = {k: v for k, v in fields.items() if k in USER_UPDATABLE_COLUMNS}
    if "totp_secret" in fields:
        fields["totp_secret"] = security.encrypt(fields["totp_secret"]) if fields["totp_secret"] else None
    if not fields:
        return get_user_by_id(user_id)
    with get_connection() as conn:
        assignments = ", ".join(f"{key} = ?" for key in fields)
        conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", [*fields.values(), user_id])
    return get_user_by_id(user_id)

def delete_user(user_id: int) -> bool:
    with get_connection() as conn:
        deleted = conn.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount
        conn.execute("DELETE FROM active_tokens WHERE user_id = ?", (user_id,))
        return deleted > 0

# ---------------------------------------------------------------- tapo schedule rules

TAPO_RULE_COLUMNS = ("ip", "name", "enabled", "start_time", "end_time", "days", "min_soc", "min_pv_w", "turn_off_at_end")

def list_tapo_rules() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM tapo_rules ORDER BY ip, start_time").fetchall()]

def get_tapo_rule(rule_id: int) -> dict | None:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM tapo_rules WHERE id = ?", (rule_id,)).fetchone()
        return dict(row) if row else None

def create_tapo_rule(**fields) -> dict:
    fields = {k: v for k, v in fields.items() if k in TAPO_RULE_COLUMNS}
    with get_connection() as conn:
        columns = ", ".join(fields)
        placeholders = ", ".join("?" for _ in fields)
        rule_id = conn.execute(f"INSERT INTO tapo_rules ({columns}) VALUES ({placeholders})", list(fields.values())).lastrowid
    return get_tapo_rule(rule_id)

def update_tapo_rule(rule_id: int, **fields) -> dict | None:
    fields = {k: v for k, v in fields.items() if k in TAPO_RULE_COLUMNS}
    if fields:
        with get_connection() as conn:
            assignments = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(f"UPDATE tapo_rules SET {assignments} WHERE id = ?", [*fields.values(), rule_id])
    return get_tapo_rule(rule_id)

def delete_tapo_rule(rule_id: int) -> bool:
    with get_connection() as conn:
        return conn.execute("DELETE FROM tapo_rules WHERE id = ?", (rule_id,)).rowcount > 0

def refresh_ssl_certificate():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE ssl_certificates
                SET created_at = datetime('now')
                WHERE created_at = (
                    SELECT created_at 
                    FROM ssl_certificates 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            ''')

            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO ssl_certificates (created_at, days)
                    VALUES (datetime('now'), 90)
                ''')

            conn.commit()
            return True

    except sqlite3.Error as e:
        print(f"❌ Error updating SSL certificate: {e}")
        return False

def toggle_auto_power_management(enabled: bool):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE configs
                SET auto_power_management_enabled = ?
            ''', (int(enabled),))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"❌ Error updating config: {e}")
        return False
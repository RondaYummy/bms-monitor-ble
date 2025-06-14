import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64
import time
from python.pwd import hash_password

data_aggregator = defaultdict(lambda: {
    "device_name": None,
    "device_address": None,
    "current_sum": 0,
    "remaining_capacity": 0,
    "power_sum": 0,
    "current_min": float('inf'),
    "current_max": float('-inf'),
    "count": 0,
    "last_insert_time": None
})

DB_NAME = '/app/data/bms_data.db'

CONFIG_CACHE = None
CONFIG_CACHE_TIMESTAMP = 0
CONFIG_CACHE_EXPIRY = 60

DEVICE_CACHE = {}  # {address: {"data": device_data, "timestamp": last_update}}
DEVICE_CACHE_EXPIRY = 60

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

def update_aggregated_data(device_name, device_address, current, power, remaining_capacity):
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

    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        insert_data(
            timestamp=timestamp,
            current=current_avg,
            power=power_avg,
            remaining_capacity=remaining_capacity_avg,
            device_address=device_address,
            device_name=device_name
        )
        # print(f"Aggregated data saved for {device_name} ({device_address}) at {timestamp}")
    except Exception as e:
        print(f"Error saving aggregated data: {e}")

    device_data.update({
        "current_sum": 0,
        "power_sum": 0,
        "current_min": float('inf'),
        "current_max": float('-inf'),
        "remaining_capacity": 0,
        "count": 0,
        "last_insert_time": now
    })

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        # conn.set_trace_callback(print)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise

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

def create_table():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
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
                n_hours INTEGER DEFAULT 12
            )
            ''')
            cursor.execute("SELECT COUNT(*) FROM configs")
            if cursor.fetchone()[0] == 0:
                private_pem, public_base64 = generate_vapid_keys()
                hashed_password = hash_password('123456')
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
                device_on INTEGER DEFAULT 1
            )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        raise

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
        
def set_all_devices_disconnected():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE devices
                SET connected = ?
            ''', (False,))
            conn.commit()
            print("✅ All devices set to `connected = False` on startup.")
    except sqlite3.Error as e:
        print(f"❌ Error resetting device connection status: {e}")

def get_all_devices(only_enabled: bool = False):
    global DEVICE_CACHE
    now = time.time()

    if DEVICE_CACHE and all((now - data["timestamp"]) < DEVICE_CACHE_EXPIRY for data in DEVICE_CACHE.values()):
        return list({tuple(device["data"].items()): device["data"] for device in DEVICE_CACHE.values()}.values())

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, address, name, added_at, connected, enabled, frame_type, frame_counter, 
                   vendor_id, hardware_version, software_version, device_uptime, power_on_count, 
                   manufacturing_date, serial_number, user_data 
                FROM devices
            '''
            params = ()
            if only_enabled:
                query += " WHERE enabled = ?"
                params = (True,)

            cursor.execute(query, params)
            devices = cursor.fetchall()

            now = time.time()
            DEVICE_CACHE.clear()

            for device in devices:
                device_data = {
                    "id": device[0], "address": device[1], "name": device[2], "added_at": device[3],
                    "connected": bool(device[4]), "enabled": bool(device[5]), "frame_type": device[6],
                    "frame_counter": device[7], "vendor_id": device[8], "hardware_version": device[9],
                    "software_version": device[10], "device_uptime": device[11], "power_on_count": device[12],
                    "manufacturing_date": device[13], "serial_number": device[14], "user_data": device[15]
                }

                DEVICE_CACHE[device[1]] = {"data": device_data, "timestamp": now}

            return list({tuple(device["data"].items()): device["data"] for device in DEVICE_CACHE.values()}.values())

    except sqlite3.Error as e:
        print(f"❌ Error fetching devices: {e}")
        return []

def get_device_by_address(address, force_refresh: bool = False):
    global DEVICE_CACHE
    now = time.time()

    if not force_refresh and address in DEVICE_CACHE and (now - DEVICE_CACHE[address]["timestamp"]) < DEVICE_CACHE_EXPIRY:
        return DEVICE_CACHE[address]["data"]

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, address, name, added_at, connected, enabled, frame_type, frame_counter, 
                   vendor_id, hardware_version, software_version, device_uptime, power_on_count, 
                   manufacturing_date, serial_number, user_data 
            FROM devices WHERE address = ?
            ''', (address.lower(),))
            device = cursor.fetchone()

            if not device:
                return None

            device_data = {
                "id": device[0], "address": device[1], "name": device[2], "added_at": device[3],
                "connected": bool(device[4]), "enabled": bool(device[5]), "frame_type": device[6],
                "frame_counter": device[7], "vendor_id": device[8], "hardware_version": device[9],
                "software_version": device[10], "device_uptime": device[11], "power_on_count": device[12],
                "manufacturing_date": device[13], "serial_number": device[14], "user_data": device[15]
            }

            DEVICE_CACHE[address] = {"data": device_data, "timestamp": now}

            return device_data

    except sqlite3.Error as e:
        print(f"❌ Error when receiving the device: {e}")
        raise

def update_device(address: str, **kwargs):
    if not kwargs:
        return

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
            values = list(kwargs.values()) + [address]

            query = f"UPDATE devices SET {fields} WHERE address = ?"

            cursor.execute(query, values)
            conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Error updating the device: {e}")
        raise

def update_device_status(address, connected: bool, enabled: bool):
    global DEVICE_CACHE
    try:
        now = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE devices
            SET connected = ?, enabled = ?
            WHERE address = ?
            ''', (connected, enabled, address))
            conn.commit()

            device_data = get_device_by_address(address, force_refresh=True)
            DEVICE_CACHE[address] = {"data": device_data, "timestamp": now}
    except sqlite3.Error as e:
        print(f"❌ Error updating status: {e}")
        raise

def insert_device(
    address, name=None, frame_type=None, frame_counter=None, vendor_id=None,
    hardware_version=None, software_version=None, device_uptime=None, power_on_count=None,
    manufacturing_date=None, serial_number=None, user_data=None, connected=False, enabled=True
):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM devices WHERE address = ?", (address,))
            existing = cursor.fetchone()
            if existing:
                return get_device_by_address(address)

            cursor.execute('''
            INSERT INTO devices (
                address, name, added_at, connected, enabled, frame_type, frame_counter, vendor_id,
                hardware_version, software_version, device_uptime, power_on_count,
                manufacturing_date, serial_number, user_data
            ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                address, name, connected, enabled, frame_type, frame_counter, vendor_id,
                hardware_version, software_version, device_uptime, power_on_count,
                manufacturing_date, serial_number, user_data
            ))

            conn.commit()

            return get_device_by_address(address)
    
    except sqlite3.Error as e:
        print(f"❌ Error inserting the device: {e}")
        raise


def insert_alert_data(device_address, device_name, error_code, occurred_at, n_hours=1):
    global ALERT_CACHE

    now = datetime.now()
    time_limit = now - timedelta(hours=n_hours)
    time_limit_str = time_limit.strftime('%Y-%m-%d %H:%M:%S')

    if device_address in ALERT_CACHE and error_code in ALERT_CACHE[device_address]:
        cached_alert = ALERT_CACHE[device_address][error_code]
        
        if cached_alert["timestamp"] > time_limit_str:
            raise ValueError(f"❌ Error: An alert for {device_address} with code {error_code} has already existed for {n_hours} hours.")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, occurred_at FROM error_notifications
            WHERE device_address = ? AND error_code = ? AND occurred_at > ?
            ''', (device_address, error_code, time_limit_str))

            existing = cursor.fetchone()
            if existing:
                if device_address not in ALERT_CACHE:
                    ALERT_CACHE[device_address] = {}
                
                ALERT_CACHE[device_address][error_code] = {"timestamp": existing[1], "id": existing[0]}
                raise ValueError(f"❌ Error: An alert for {device_address} with code {error_code} has already existed for {n_hours} hours.")

            cursor.execute('''
            INSERT INTO error_notifications (device_address, error_code, occurred_at, device_name)
            VALUES (?, ?, ?, ?)
            ''', (device_address, error_code, occurred_at, device_name))
            conn.commit()

            alert_id = cursor.lastrowid
            if device_address not in ALERT_CACHE:
                ALERT_CACHE[device_address] = {}

            ALERT_CACHE[device_address][error_code] = {"timestamp": occurred_at, "id": alert_id}

    except sqlite3.Error as e:
        print(f"Error inserting alerts data: {e}")
        raise

def insert_data(timestamp, current, power, remaining_capacity, device_address, device_name):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO bms_data (timestamp, current, power, remaining_capacity, device_address, device_name)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, current, power, remaining_capacity, device_address, device_name))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        raise

def fetch_all_data_range(from_dt: datetime, to_dt: datetime):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            from_str = from_dt.strftime('%Y-%m-%d %H:%M:%S')
            to_str = to_dt.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('SELECT timestamp, current, power, device_address, device_name, remaining_capacity FROM bms_data WHERE timestamp BETWEEN ? AND ?', (from_str, to_str))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        raise
    
def fetch_all_data(days=None):
    """
    Gets records from the table for the current day if days=1.
    If the days parameter is not passed, no data is returned.
    Results are cached for 1 minute, and the cache key include days.
    """
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
        with get_connection() as conn:
            cursor = conn.cursor()

            if days == 1:
                cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                cutoff_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('SELECT timestamp, current, power, device_address, device_name, remaining_capacity FROM bms_data WHERE timestamp >= ?', (cutoff_date_str,))
            result = cursor.fetchall()

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
            cursor.execute('SELECT * FROM error_notifications')
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching notifications: {e}")
        raise

def get_subscription_by_endpoint(endpoint: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE endpoint = ?", (endpoint,))
        return cursor.fetchone()
    
def add_subscription(subscription: dict):
    with sqlite3.connect(DB_NAME) as conn:
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
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE endpoint = ?", (endpoint,))
            conn.commit()

            print(f"🗑️ Subscription deleted: {endpoint}")

    except sqlite3.Error as e:
        print(f"❌ Error when deleting a subscription: {e}")

def get_all_subscriptions():
    try:
        with sqlite3.connect(DB_NAME) as conn:
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

def get_config():
    global CONFIG_CACHE, CONFIG_CACHE_TIMESTAMP

    if CONFIG_CACHE and (time.time() - CONFIG_CACHE_TIMESTAMP) < CONFIG_CACHE_EXPIRY:
        return CONFIG_CACHE

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours FROM configs LIMIT 1")
            config = cursor.fetchone()
            if config:
                CONFIG_CACHE = {
                    "password": config[0],
                    "VAPID_PUBLIC_KEY": config[1],
                    "VAPID_PRIVATE_KEY": config[2],
                    "n_hours": config[3],
                }
                CONFIG_CACHE_TIMESTAMP = time.time()
                return CONFIG_CACHE
            else:
                return None
    except sqlite3.Error as e:
        print(f"Error fetching config: {e}")
        return None

def update_config(password=None, vapid_public=None, vapid_private=None, n_hours=None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours FROM configs LIMIT 1")
            existing_config = cursor.fetchone()
            if not existing_config:
                raise ValueError("Config record not found!")
            
            if n_hours:
                global CONFIG_CACHE, CONFIG_CACHE_TIMESTAMP
                CONFIG_CACHE = None  # Clearing the cache after an update
                CONFIG_CACHE_TIMESTAMP = 0

            updated_config = {
                "password": password if password is not None else existing_config[0],
                "VAPID_PUBLIC_KEY": vapid_public if vapid_public is not None else existing_config[1],
                "VAPID_PRIVATE_KEY": vapid_private if vapid_private is not None else existing_config[2],
                "n_hours": n_hours if n_hours is not None else existing_config[3],
            }

            cursor.execute("""
                UPDATE configs
                SET password = ?, VAPID_PUBLIC_KEY = ?, VAPID_PRIVATE_KEY = ?, n_hours = ?
            """, (updated_config["password"], updated_config["VAPID_PUBLIC_KEY"], updated_config["VAPID_PRIVATE_KEY"], updated_config["n_hours"]))

            conn.commit()
            return updated_config
    except sqlite3.Error as e:
        print(f"Error updating config: {e}")
        return None

def get_tapo_device_by_ip(ip):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tapo_devices WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
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
            ''', (ip, email, password, False, power_watt, priority))

            conn.commit()
            return get_tapo_device_by_ip(ip)

    except sqlite3.Error as e:
        print(f"❌ Error inserting the Tapo device: {e}")
        raise

def update_tapo_device_by_ip(ip, info: dict):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Main fields to update
            fields = [
                "name = ?",
                "model = ?",
                "fw_ver = ?",
                "hw_ver = ?",
                "device_id = ?",
                "device_on = ?"
            ]
            values = [
                info.get("name"),
                info.get("model"),
                info.get("fw_ver"),
                info.get("hw_ver"),
                info.get("device_id"),
                info.get("device_on", False)
            ]
            # Additional field power_watt (optional)
            if "power_watt" in info:
                fields.append("power_watt = ?")
                values.append(info["power_watt"])
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

            if "email" in updates:
                fields.append("email = ?")
                values.append(updates["email"])
            if "password" in updates:
                fields.append("password = ?")
                values.append(updates["password"])
            if "power_watt" in updates:
                fields.append("power_watt = ?")
                values.append(updates["power_watt"])
            if "priority" in updates:
                fields.append("priority = ?")
                values.append(updates["priority"])

            if not fields:
                return False  # Nothing is updated

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

def get_top_priority_tapo_devices(limit: int = 2):
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tapo_devices
                ORDER BY priority DESC, ip ASC
                LIMIT ?
            ''', (limit,))
            devices = [dict(row) for row in cursor.fetchall()]
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
        return [dict(zip(columns, row)) for row in rows]

def get_tapo_device_by_id(id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tapo_devices WHERE id = ?", (id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

def delete_tapo_device_by_ip(ip: str):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tapo_devices WHERE ip = ?", (ip,))
            conn.commit()
            return cursor.rowcount > 0  # True if at least 1 line was deleted
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
                "battery_power", "battery_voltage", "battery_soc", "net_balance", "timestamp"
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
            return cursor.rowcount > 0  # True якщо щось видалилось
    except sqlite3.Error as e:
        print(f"❌ Error deleting Deye device with IP {ip}: {e}")
        raise

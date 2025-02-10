import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

data_aggregator = defaultdict(lambda: {
    "device_name": None,
    "device_address": None,
    "current_sum": 0,
    "power_sum": 0,
    "current_min": float('inf'),
    "current_max": float('-inf'),
    "count": 0,
    "last_insert_time": None
})

DB_NAME = '/app/data/bms_data.db'

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

        await asyncio.sleep(60)

def update_aggregated_data(device_name, device_address, current, power):
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

    device_data = data_aggregator[device_address]

    if device_data["device_name"] is None:
        device_data["device_name"] = device_name
    if device_data["device_address"] is None:
        device_data["device_address"] = device_address

    device_data["current_sum"] += current
    device_data["power_sum"] += power

    device_data["current_min"] = min(device_data["current_min"], current)
    device_data["current_max"] = max(device_data["current_max"], current)

    # Increase the number of records
    device_data["count"] += 1
    if device_data["last_insert_time"] is None:
        device_data["last_insert_time"] = now

def save_aggregated_data(device_name, device_address, device_data, interval=60):
    """Saves the aggregated data to the database if the time interval has passed."""
    now = datetime.now()
    last_insert_time = device_data["last_insert_time"]

    if last_insert_time and (now - last_insert_time).total_seconds() < interval:
        return  # The interval has not yet expired

    # Calculating the average value
    if device_data["count"] > 0:
        current_avg = device_data["current_sum"] / device_data["count"]
        power_avg = device_data["power_sum"] / device_data["count"]
    else:
        return  # No data to save

    # Generate timestamp
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        insert_data(
            timestamp=timestamp,
            current=current_avg,
            power=power_avg,
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
        "count": 0,
        "last_insert_time": now
    })

def get_connection():
    """Creates and returns a connection to the database."""
    try:
        return sqlite3.connect(DB_NAME)
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise

def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Конвертація приватного ключа в PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")

    # Конвертація публічного ключа в Base64
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_base64 = base64.urlsafe_b64encode(public_pem).decode("utf-8").rstrip("=")  # Без '=' в кінці

    return private_pem, public_base64

def create_table():
    """Creates a table if it does not exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bms_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                current REAL NOT NULL,
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
                password TEXT DEFAULT '123456',
                VAPID_PUBLIC_KEY TEXT DEFAULT '',
                VAPID_PRIVATE_KEY TEXT DEFAULT '',
                n_hours INTEGER DEFAULT 12
            )
            ''')
            cursor.execute("SELECT COUNT(*) FROM configs")
            if cursor.fetchone()[0] == 0:
                vapid_public, vapid_private = generate_vapid_keys()
                cursor.execute('''
                INSERT INTO configs (password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours)
                VALUES (?, ?, ?, ?)
                ''', ('123456', vapid_public, vapid_private, 12))

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
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        raise

def delete_alert_by_id(alert_id):
    """Deletes a record from the table by its ID."""
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

            result = [
                {
                    "id": device[0], "address": device[1], "name": device[2], "added_at": device[3],
                    "connected": bool(device[4]), "enabled": bool(device[5]), "frame_type": device[6],
                    "frame_counter": device[7], "vendor_id": device[8], "hardware_version": device[9],
                    "software_version": device[10], "device_uptime": device[11], "power_on_count": device[12],
                    "manufacturing_date": device[13], "serial_number": device[14], "user_data": device[15]
                }
                for device in devices
            ]

            return result
    except sqlite3.Error as e:
        print(f"❌ Error fetching devices: {e}")
        return []

def get_device_by_address(address):
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

            return {
                "id": device[0], "address": device[1], "name": device[2], "added_at": device[3],
                "connected": bool(device[4]), "enabled": bool(device[5]), "frame_type": device[6],
                "frame_counter": device[7], "vendor_id": device[8], "hardware_version": device[9],
                "software_version": device[10], "device_uptime": device[11], "power_on_count": device[12],
                "manufacturing_date": device[13], "serial_number": device[14], "user_data": device[15]
            }
    
    except sqlite3.Error as e:
        print(f"❌ Помилка при отриманні пристрою: {e}")
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
        print(f"❌ Помилка при оновленні пристрою: {e}")
        raise

def update_device_status(address, connected: bool, enabled: bool):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE devices
            SET connected = ?, enabled = ?
            WHERE address = ?
            ''', (connected, enabled, address))
            conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Помилка при оновленні статусу: {e}")
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
        print(f"❌ Помилка при вставці пристрою: {e}")
        raise


def insert_alert_data(device_address, device_name, error_code, occurred_at, n_hours=1):
    """Adds a new record to the table."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            now = datetime.now()
            time_limit = now - timedelta(hours=n_hours)
            time_limit_str = time_limit.strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute('''
            SELECT id FROM error_notifications
            WHERE device_address = ? AND error_code = ? AND occurred_at > ?
            ''', (device_address, error_code, time_limit_str))

            existing = cursor.fetchone()
            if existing:
                raise ValueError(f"❌ Помилка: Сповіщення для {device_address} з кодом {error_code} вже існує упродовж {n_hours} годин.")

            cursor.execute('''
            INSERT INTO error_notifications (device_address, error_code, occurred_at, device_name)
            VALUES (?, ?, ?, ?)
            ''', (device_address, error_code, occurred_at, device_name))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting alerts data: {e}")
        raise

def insert_data(timestamp, current, power, device_address, device_name):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO bms_data (timestamp, current, power, device_address, device_name)
            VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, current, power, device_address, device_name))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        raise

def fetch_all_data(days=None):
    """
    Gets records from the table for the current day if days=1.
    If the days parameter is not passed, no data is returned.
    """
    if days is None:
        print("No 'days' parameter provided. No data will be fetched.")
        return None

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if days == 1:
                # Start of the current day
                cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Start of day “n days ago”
                cutoff_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('SELECT * FROM bms_data WHERE timestamp >= ?', (cutoff_date_str,)) # Query with filtering by timestamp
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        raise

def fetch_all_notifications():
    """
    Fetches all records from the error_notifications table.
    Returns:
        List of tuples containing all rows from the table.
    """
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
                print(f"🔄 Старий endpoint {old_endpoint} змінено на {endpoint}, видаляємо старий...")
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

            print(f"🗑️ Видалено підписку: {endpoint}")

    except sqlite3.Error as e:
        print(f"❌ Помилка при видаленні підписки: {e}")

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
        print(f"❌ Помилка отримання підписок: {e}")
        return []

def get_config():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, n_hours FROM configs LIMIT 1")
            config = cursor.fetchone()
            if config:
                return {
                    "password": config[0],
                    "VAPID_PUBLIC_KEY": config[1],
                    "VAPID_PRIVATE_KEY": config[2],
                    "n_hours": config[3],
                }
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

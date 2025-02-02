import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

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
                print(f"Notification already exists for {device_address} and {error_code} within {n_hours} hours.")
                return

            cursor.execute('''
            INSERT INTO error_notifications (device_address, error_code, occurred_at, device_name)
            VALUES (?, ?, ?, ?)
            ''', (device_address, error_code, occurred_at, device_name))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting alerts data: {e}")
        raise

def insert_data(timestamp, current, power, device_address, device_name):
    """Adds a new record to the table."""
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

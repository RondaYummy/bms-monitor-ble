import sqlite3
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Структура для зберігання проміжних даних
data_aggregator = defaultdict(lambda: {
    "voltage_sum": 0,
    "current_sum": 0,
    "voltage_min": float('inf'),
    "voltage_max": float('-inf'),
    "current_min": float('inf'),
    "current_max": float('-inf'),
    "count": 0,
    "last_insert_time": None
})

DB_NAME = '/app/data/bms_data.db'

def update_aggregated_data(device_name, voltage, current):
    """Оновлює проміжні дані для агрегування."""
    global data_aggregator
    now = datetime.now(timezone.utc)
    device_data = data_aggregator[device_name]

    # Оновлення сум
    device_data["voltage_sum"] += voltage
    device_data["current_sum"] += current

    # Оновлення мінімуму та максимуму
    device_data["voltage_min"] = min(device_data["voltage_min"], voltage)
    device_data["voltage_max"] = max(device_data["voltage_max"], voltage)
    device_data["current_min"] = min(device_data["current_min"], current)
    device_data["current_max"] = max(device_data["current_max"], current)

    # Збільшуємо кількість записів
    device_data["count"] += 1

    # Оновлюємо час останнього запису
    if device_data["last_insert_time"] is None:
        device_data["last_insert_time"] = now

def save_aggregated_data(device_name, device_address, device_data, interval=60):
    """Зберігає агреговані дані в базу, якщо минув інтервал часу."""
    now = datetime.now(timezone.utc)
    last_insert_time = device_data["last_insert_time"]

    # Перевірка інтервалу часу
    if last_insert_time and (now - last_insert_time).total_seconds() < interval:
        return  # Інтервал ще не минув

    # Розрахунок середнього значення
    if device_data["count"] > 0:
        voltage_avg = device_data["voltage_sum"] / device_data["count"]
        current_avg = device_data["current_sum"] / device_data["count"]
    else:
        return  # Немає даних для збереження

    # Формуємо timestamp
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    # Зберігаємо в базу
    try:
        insert_data(
            timestamp=timestamp,
            voltage=voltage_avg,
            current=current_avg,
            device_address=device_address,
            device_name=device_name
        )
        print(f"Aggregated data saved for {device_name} at {timestamp}")
    except Exception as e:
        print(f"Error saving aggregated data: {e}")

    # Скидаємо агреговані дані
    device_data.update({
        "voltage_sum": 0,
        "current_sum": 0,
        "voltage_min": float('inf'),
        "voltage_max": float('-inf'),
        "current_min": float('inf'),
        "current_max": float('-inf'),
        "count": 0,
        "last_insert_time": now
    })


def get_connection():
    """Створює і повертає з'єднання з базою даних."""
    try:
        return sqlite3.connect(DB_NAME)
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise

def create_table():
    """Створює таблицю, якщо вона не існує."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bms_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                voltage REAL NOT NULL,
                current REAL NOT NULL,
                device_address TEXT NOT NULL,
                device_name TEXT NOT NULL
            )
            ''')
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON bms_data (timestamp)
            ''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        raise

def insert_data(timestamp, voltage, current, device_address, device_name, min_interval_seconds=60):
    """Додає новий запис у таблицю з перевіркою інтервалу часу."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Отримуємо час останнього запису для цього device_address
            cursor.execute('''
            SELECT timestamp FROM bms_data
            WHERE device_address = ?
            ORDER BY timestamp DESC
            LIMIT 1
            ''', (device_address,))
            last_record = cursor.fetchone()

            if last_record:
                last_timestamp = datetime.strptime(last_record[0], '%Y-%m-%d %H:%M:%S')
                current_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

                # Перевіряємо, чи пройшло достатньо часу
                if (current_timestamp - last_timestamp).total_seconds() < min_interval_seconds:
                    raise ValueError(f"Cannot insert data for {device_address} more than once every {min_interval_seconds} seconds.")

            # Вставка нового запису
            cursor.execute('''
            INSERT INTO bms_data (timestamp, voltage, current, device_address, device_name)
            VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, voltage, current, device_address, device_name))
            conn.commit()
    except ValueError as e:
        print(f"Validation error: {e}")
        raise
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        raise

def fetch_all_data():
    """Отримує всі записи з таблиці."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bms_data')
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching all data: {e}")
        raise

def fetch_data_by_voltage(min_voltage):
    """Отримує записи, де напруга перевищує заданий мінімум."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bms_data WHERE voltage > ?', (min_voltage,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching data by voltage: {e}")
        raise

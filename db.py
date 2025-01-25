import sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio

# Структура для зберігання проміжних даних
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
    """Циклічно викликає update_aggregated_data та зберігає агреговані дані."""
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
    """Оновлює проміжні дані для агрегування."""
    global data_aggregator
    now = datetime.now(timezone.utc)

    if not isinstance(device_name, str) or not device_name.strip():
        raise ValueError(f"Invalid device_name: {device_name}")
    if not isinstance(device_address, str) or not device_address.strip():
        raise ValueError(f"Invalid device_address: {device_address}")
    if not isinstance(current, (int, float)):
        raise ValueError(f"Invalid current: {current}")
    if not isinstance(power, (int, float)) or power < 0:
        raise ValueError(f"Invalid power: {power}")

    # Ініціалізуємо дані для пристрою, якщо він ще не доданий
    device_data = data_aggregator[device_address]

    # Оновлюємо загальні дані пристрою
    if device_data["device_name"] is None:
        device_data["device_name"] = device_name
    if device_data["device_address"] is None:
        device_data["device_address"] = device_address

    # Оновлення сум
    device_data["current_sum"] += current
    device_data["power_sum"] += power

    # Оновлення мінімуму та максимуму
    device_data["current_min"] = min(device_data["current_min"], current)
    device_data["current_max"] = max(device_data["current_max"], current)

    # Збільшуємо кількість записів
    device_data["count"] += 1
    if device_data["last_insert_time"] is None:
        device_data["last_insert_time"] = now

def save_aggregated_data(device_name, device_address, device_data, interval=60):
    """Зберігає агреговані дані в базу, якщо минув інтервал часу."""
    now = datetime.now(timezone.utc)
    last_insert_time = device_data["last_insert_time"]

    if last_insert_time and (now - last_insert_time).total_seconds() < interval:
        return  # Інтервал ще не минув

    # Розрахунок середнього значення
    if device_data["count"] > 0:
        current_avg = device_data["current_sum"] / device_data["count"]
        power_avg = device_data["power_sum"] / device_data["count"]
    else:
        return  # Немає даних для збереження

    # Формуємо timestamp
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        print(f"timestamp: {timestamp},device_name: {device_name}, device_address: {device_address}, current: {current_avg}, power: {power_avg}")
        insert_data(
            timestamp=timestamp,
            current=current_avg,
            power=power_avg,
            device_address=device_address,
            device_name=device_name
        )
        print(f"Aggregated data saved for {device_name} ({device_address}) at {timestamp}")
    except Exception as e:
        print(f"Error saving aggregated data: {e}")

    # Скидаємо агреговані дані
    device_data.update({
        "current_sum": 0,
        "power_sum": 0,
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
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        raise

def insert_data(timestamp, current, power, device_address, device_name):
    """Додає новий запис у таблицю."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO bms_data (timestamp, current, power, device_address, device_name)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, current, power, device_address, device_name))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        raise

def fetch_all_data(days=None):
    """
    Отримує записи з таблиці за поточний день, якщо days=1.
    Якщо параметр days не передано, дані не повертаються.
    """
    if days is None:
        print("No 'days' parameter provided. No data will be fetched.")
        return None  # Або повернути []

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Розраховуємо початок дня
            if days == 1:
                # Початок поточного дня
                cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Початок дня "n днів тому"
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Запит із фільтрацією за timestamp
            cursor.execute('SELECT * FROM bms_data WHERE timestamp >= ?', (cutoff_date_str,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        raise

# Базовий образ з підтримкою Python
FROM python:3.11-slim

# Встановлення оновлень і необхідних утиліт
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Створення робочої директорії в контейнері
WORKDIR /app

# Копіюємо файли проекту в контейнер
COPY requirements.txt .
COPY main.py .
COPY colors.py .

# Встановлення залежностей
RUN pip install --no-cache-dir -r requirements.txt

# Вказуємо команду для запуску вашого коду
CMD ["python", "main.py"]

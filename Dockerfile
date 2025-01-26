FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    dbus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо файли проекту в контейнер
COPY requirements.txt .
COPY main.py .
COPY python/colors.py .

# Встановлення залежностей
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]

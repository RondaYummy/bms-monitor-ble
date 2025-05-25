FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bluez \
    dbus \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY main.py .
COPY python/colors.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]

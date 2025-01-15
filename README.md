# BMS Monitor [BLE]
Simple application for controlling JK-BMS via Bluetooth low energy

## Створення образу Docker:
```bash
docker build -t bms-monitor-ble .
```

## Запуск контейнера:
```bash
docker run --rm -it --name bms-monitor-ble bms-monitor-ble
```

## Перебудова Docker-образу:
```bash
docker build --no-cache -t bms-monitor-ble .
```

## [PROD]
```bash
docker run -d --privileged --name bms-monitor-ble --net=host \
    -v /var/run/dbus:/var/run/dbus \
    bms-monitor-ble
```
- `-d`: Для запуску контейнера у фоновому режимі.

## [DEV] Робота з BLE на Raspberry Pi: Щоб надати доступ до BLE пристроїв усередині контейнера, додайте прапор --privileged і змонтуйте необхідні пристрої:
```bash
docker run --rm -it --privileged --name bms-monitor-ble --net=host \
    -v /var/run/dbus:/var/run/dbus \
    bms-monitor-ble
```
- `--net=host`: Дозволяє контейнеру використовувати мережу хоста (необхідно для Bluetooth).
- `--privileged`: Дає розширений доступ до хост-системи.
- `-v`: Для передачі DBus сокета в контейнер.

## Docker LOGS REALTIME
```bash
docker logs -f bms-monitor-ble
```

## Docker LOGS
```bash
docker logs bms-monitor-ble
```

### Deploy
```bash
chmod +x deploy.sh
```
```bash
./deploy.sh
```

### PM2
```bash
npm install pm2 -g
```
```bash
pm2 start ecosystem.config.js
```
## Motivation
The official app left me dissatisfied due to its lack of essential features. It doesn't provide critical notifications, such as alerts in Telegram for a low battery level, missing charging, or potential issues with the BMS itself. Monitoring these parameters while standing next to the BMS with my phone felt inefficient and inconvenient. I envisioned a solution where I could access all this data and functionality from anywhere in the world, without being tethered to a specific location.

Inspired by this need, I decided to create my own project using Python and develop a web application that integrates all these features in one place. Unlike the official app, my application includes real-time notifications, remote accessibility, and, importantly, data visualization through detailed charts—something the official app also lacks. This project is a step toward simplifying BMS monitoring and ensuring a seamless user experience, no matter where I am.

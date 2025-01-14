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

## Робота з BLE на Raspberry Pi: Щоб надати доступ до BLE пристроїв усередині контейнера, додайте прапор --privileged і змонтуйте необхідні пристрої:
```bash
docker run --rm -it --privileged --name bms-monitor-ble --net=host \
    -v /var/run/dbus:/var/run/dbus \
    bms-monitor-ble
```
- `--net=host`: Дозволяє контейнеру використовувати мережу хоста (необхідно для Bluetooth).
- `--privileged`: Дає розширений доступ до хост-системи.
- `-v`: Для передачі DBus сокета в контейнер.

### Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

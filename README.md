# BMS Monitor [BLE]
## Battery Management System JK-BMS control via Bluetooth low energy

<p align="center">
  <img src="devices.png" style="height: 500px; object-fit: contain;">
  <img src="summary.png" style="height: 500px; object-fit: contain;">
  <img src="settings.png" style="height: 500px; object-fit: contain;">
</p>

## Supported devices
#### All JK-BMS models with software version >=6.0 are using the implemented protocol and should be supported.
* JK_BD6A20S6P, hw 17U, sw 17.02
* JK_BD6A17S6P, hw 11.XA, sw 11.48

## First steeps:
### Clone project:
```bash
git clone https://github.com/RondaYummy/bms-monitor-ble.git
```
1. Install Node.
2. Install Yarn.
3. Install Docker-compose.
4. Setup Nginx and SSL ( https://github.com/RondaYummy/bms-monitor-ble/blob/main/docs/nginx.md )
5. To access from outside the local network, you need to get a static IP address.

### Make sure that the systemctl service is running:
```bash
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

### Build Docker:
```bash
yarn build
```

### To copy static resources after a manual build:
```bash
yarn static
```

### [PROD]
```bash
yarn prod
```

### [DEV] 
```bash
yarn dev
```

### [AUTO] Deploy via PM2
```bash
chmod +x deploy.sh
npm install pm2 -g
pm2 start ecosystem.config.js
```
### Clear Database
```bash
docker ps
docker exec -it bms-monitor-ble-python-app-1 bash
rm /app/data/*.db
exit
docker compose restart
```

## Motivation
The official app left me dissatisfied due to its lack of essential features. It doesn't provide critical notifications, such as alerts in Telegram for a low battery level, missing charging, or potential issues with the BMS itself. Monitoring these parameters while standing next to the BMS with my phone felt inefficient and inconvenient. I envisioned a solution where I could access all this data and functionality from anywhere in the world, without being tethered to a specific location.

Inspired by this need, I decided to create my own project using Python and develop a web application that integrates all these features in one place. Unlike the official app, my application includes real-time notifications, remote accessibility, and, importantly, data visualization through detailed charts—something the official app also lacks. This project is a step toward simplifying BMS monitoring and ensuring a seamless user experience, no matter where I am.

### Top contributors:

<a href="https://github.com/RondaYummy/bms-monitor-ble/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RondaYummy/bms-monitor-ble" alt="contrib.rocks image" />
</a>

## References
- https://github.com/syssi/esphome-jk-bms - ESPHome component [RS485 BLE, rw] (C++, Python)
- https://github.com/PurpleAlien/jk-bms_grafana - Read data and graph in Grafana [RS485, ro] (Python)
- https://github.com/jblance/jkbms - Read data, used in jblance/mpp-solar [BLE, ro] (Python)
- https://github.com/sshoecraft/jktool - Linux utility [RS485 CAN BLE, ro] (C)
- https://github.com/maxx-ukoo/jk-bms2pylontech - Pylontech low voltage US2000 Bridge [RS485, ro] (C)
- https://github.com/ismarintan98/JK_BMS - Simple data monitor [RS485] (C++)
- https://github.com/Louisvdw/dbus-serialbattery/blob/master/etc/dbus-serialbattery/jkbms.py VenusOS drive [RS485, ro] (Python)
- https://secondlifestorage.com/index.php?threads/jk-b1a24s-jk-b2a24s-active-balancer.9591/ - JK-B1A24S / JK-B2A24S Active Balancer
- https://github.com/jblance/jkbms
- https://github.com/jblance/mpp-solar/issues/112 - JK BMS RS485 protocol
- https://github.com/jblance/mpp-solar/blob/master/mppsolar/protocols/jk232.py
- https://github.com/jblance/mpp-solar/blob/master/mppsolar/protocols/jk485.py
- https://github.com/sshoecraft/jktool
- https://github.com/Louisvdw/dbus-serialbattery/blob/master/etc/dbus-serialbattery/jkbms.py
- https://blog.ja-ke.tech/2020/02/07/ltt-power-bms-chinese-protocol.html

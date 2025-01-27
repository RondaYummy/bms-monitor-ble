# BMS Monitor [BLE]
# Battery Management System JK-BMS control via Bluetooth low energy

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

## Build Docker:
```bash
yarn build
```

## To copy static resources after a manual build:
```bash
yarn static
```

## [PROD]
```bash
yarn prod
```

## [DEV] 
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
```

### docker exec -it <python-app-name> bash
```bash
docker exec -it bms-monitor-ble-python-app-1 bash
rm /app/data/*.db
exit
docker compose restart
```

Спершу ми підключаємось до усіх пристроїв добавлених в configs/allowed_devices.txt, як тільки ми доєднались до усіх пристроїв та отримали з них усіх Cell info, ми починаємо зберігати дані в базу даних ( для графіків ). При кожному отриманні Cell info ми викликаємо функцію evaluate_alerts(), яка перевіряє чи значення в межах норми для кожної з BMS і якщо є якісь відхилення надсилає сповіщення з configs/error_codes.yml. Одне і те саме сповіщення не може бути збережено та надіслано швидше чим N_HOURS ( Стандартно 12 годин ).

## Motivation
The official app left me dissatisfied due to its lack of essential features. It doesn't provide critical notifications, such as alerts in Telegram for a low battery level, missing charging, or potential issues with the BMS itself. Monitoring these parameters while standing next to the BMS with my phone felt inefficient and inconvenient. I envisioned a solution where I could access all this data and functionality from anywhere in the world, without being tethered to a specific location.

Inspired by this need, I decided to create my own project using Python and develop a web application that integrates all these features in one place. Unlike the official app, my application includes real-time notifications, remote accessibility, and, importantly, data visualization through detailed charts—something the official app also lacks. This project is a step toward simplifying BMS monitoring and ensuring a seamless user experience, no matter where I am.

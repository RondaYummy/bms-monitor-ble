# BMS Monitor [BLE]
Simple application for controlling JK-BMS via Bluetooth low energy

1. Install Node 22.
2. Install Yarn.
3. Install Docker-compose.

## Build Docker:
```bash
yarn build
```

## [PROD]
```bash
yarn prod
```

## [DEV] 
```bash
yarn dev
```

### Deploy
```bash
chmod +x deploy.sh
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

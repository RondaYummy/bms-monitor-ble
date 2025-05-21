<p align="center">
  <img src="devices.png" style="height: 500px; object-fit: contain;">
  <img src="summary.png" style="height: 500px; object-fit: contain;">
  <img src="settings.png" style="height: 500px; object-fit: contain;">
</p>

## Підтримувані пристрої
#### Усі моделі JK-BMS із версією прошивки >=6.0 використовують реалізований протокол і повинні підтримуватись.
* JK_BD6A20S6P, hw 17U, sw 17.02  
* JK_BD6A17S6P, hw 11.XA, sw 11.48

#### Усі моделі Deye зі списку підтримуються:
* SUN-6K-SG01/03/LP1-EU/AU

#### Усі TP-Link Tapo P110 Wi-Fi з прошивкою >=1.2.1
* Tapo P100

# Моніторинг BMS [BLE]
## 🔋 Система моніторингу для JK-BMS та інвертора Deye

Цей застосунок забезпечує повний моніторинг вашої енергосистеми в реальному часі.  
Він підключається до:

- **JK-BMS** через Bluetooth Low Energy (за допомогою бібліотеки `bleak`)
- **Інвертора Deye** через WiFi-стік (з використанням `pysolarmanv5`)

### 🧠 Основні функції:
- Напруга, струм, потужність батареї, SOC, SOH
- Температури елементів, внутрішній опір, кількість циклів, балансування
- Генерація з сонця, споживання будинком, імпорт/експорт із мережі

### ⚠️ Веб-сповіщення (Web Push)
Критичні події (наприклад, перегрів, розбалансування комірок, низький заряд) надсилаються як push-сповіщення на фронтенд PWA.

### 📱 Прогресивний веб-додаток (PWA)
Фронтенд є PWA-додатком, який працює офлайн, підтримує мобільні пристрої та отримує push-сповіщення через браузер.

### 🚀 Чому це краще:
- **Без обмежень нативних застосунків** (наприклад, Bluetooth тільки з телефона)
- **Усі дані в одному місці** — доступні з будь-якого пристрою
- **Працює автономно на Raspberry Pi 5**, без залежності від хмари, 24/7

> Повний контроль над вашою енергосистемою — стабільно, локально, зручно.

## ⚠️ ВАЖЛИВО: перед використанням інвертора Deye та розеток Tapo

Щоб забезпечити стабільну роботу системи, потрібно **призначити статичні IP-адреси** для інвертора та розеток Tapo через налаштування роутера. Це запобігає випадковій зміні IP після перезавантаження та гарантує постійне з'єднання.

## ✅ Як це зробити

1. Відкрийте панель керування роутером у браузері:
   ```
   http://192.168.31.1
   ```

2. Перейдіть до розділу:
   ```
   DHCP > Статичні адреси / Резервація IP / Прив’язка IP
   ```

3. Додайте **MAC-адресу WiFi-стіка інвертора** і прив’яжіть до неї статичну IP. Приклад:

   - **MAC:** `DC:4F:22:xx:xx:xx`
   - **IP:** `192.168.31.39`

4. Додайте свою **розетку Tapo** аналогічно:

   - **MAC:** `AC:84:C6:xx:xx:xx`
   - **IP:** `192.168.31.110`

5. Збережіть конфігурацію.

6. Перезавантажте **роутер** або **пристрої**, щоб зміни набули чинності.

---

🔁 **Після цього налаштування** IP-адреси більше не змінюватимуться, і система зберігатиме стабільне з'єднання з інвертором та розетками.

✅ Це настійно рекомендується для всіх систем автоматизації, які залежать від стабільних локальних IP-адрес.

#### Deye
Для підключення до інвертора потрібно передати змінні: `INVERTER_IP`, `LOGGER_SN`.

#### TP-Link Tapo
Для підключення до розетки Tapo потрібно вказати IP розетки, EMAIL і PASSWORD з офіційного додатку Tapo.

### ⚙️ Архітектура системи

<code>Graph TD
  BMS[JK-BMS] --> PythonApp[Бекенд на Python]
  Deye[Інвертор Deye] --> PythonApp
  PythonApp --> DB[SQLite База Даних]
  PythonApp --> PWA[Фронтенд (PWA)]
  PythonApp --> Push[Web Push Сповіщення]
</code>

## Перші кроки:
#### Щоб мати доступ до застосунку ззовні локальної мережі, потрібно отримати статичну IP-адресу у провайдера. Також налаштувати Nginx та SSL (https://github.com/RondaYummy/bms-monitor-ble/blob/main/docs/nginx.md)

### Переконайтесь, що сервіс systemctl активний:
```bash
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

### Побудова Docker:
```bash
yarn build
```

### Щоб скопіювати статичні ресурси після ручної збірки:
```bash
yarn static
```

### [PROD] - [DEV]
```bash
yarn prod
yarn dev
```

### [AUTO] Деплой через PM2

#### Підготовка:
```bash
echo "$(whoami) ALL=(ALL) NOPASSWD: /sbin/reboot" | sudo tee /etc/sudoers.d/reboot-nopasswd
chmod +x deploy.sh
npm install pm2 -g
```

### [AUTO] Старт деплою:
```bash
pm2 start ecosystem.config.js
```

### Очистити базу даних [Приклад]
```bash
docker ps
docker exec -it bms-monitor-ble-python-app-1 bash
rm /app/data/*.db
exit
docker compose restart
```

## 🚀 Мотивація

Офіційний застосунок для BMS залишив мене глибоко розчарованим через відсутність критично важливих функцій та обмеження в зручності використання. Він не надавав **сповіщень у реальному часі** про важливі події, такі як низький рівень заряду, пропущені сесії зарядки чи аномальну поведінку елементів батареї. Контролювати ці параметри, стоячи поруч із BMS і тримаючи смартфон, здавалося мені неефективним і застарілим способом.

Я уявив рішення, яке дозволило б **керувати та стежити за всією енергосистемою з будь-якої точки світу**, не будучи прив’язаним до конкретного пристрою чи мобільного додатку.

Тому я вирішив створити власну систему — почавши з **Python** та легкого **веб-інтерфейсу**, який об’єднує всі критично важливі функції, яких бракувало в офіційних інструментах. Мій застосунок додає:

- 🔔 **Web push-сповіщення** про перегрів, дисбаланс комірок і проблеми з батареєю  
- 🌍 **Віддалений доступ через PWA**, доступний з будь-якого браузера або пристрою  
- 📊 **Розширену візуалізацію даних** через графіки та логи в реальному часі  

У процесі розвитку проєкту я вийшов за межі одного лише BMS:

- 💡 **Розетки TP-Link Tapo** були інтегровані для **віддаленого керування живленням** підключених пристроїв (зарядки, інвертори, роутери). Тепер я можу автоматично вмикати або вимикати їх залежно від стану батареї або за розкладом.  
- ⚡ Була додана підтримка **інвертора Deye** через Wi-Fi стік для моніторингу **генерації від сонця**, **споживання з мережі** та **балансування системи**.  
- 🧠 Усі ці компоненти тепер працюють **разом як єдина інтелектуальна система**, автономно на **Raspberry Pi 5**, без потреби у хмарних сервісах.

> Мета була проста: **забезпечити прозорість, контроль і автоматизацію** моєї енергосистеми — стабільно, відкрито та з повагою до приватності.

Цей проєкт — моя спроба створити повністю локальну, інтегровану та розширювану платформу для керування енергією — саме те, що, на мою думку, має бути доступне кожному ентузіасту DIY-енергетики.

## 🗺️ Дорожня карта / Функції

- [x] Моніторинг JK-BMS через BLE
- [x] Моніторинг інвертора Deye через WiFi
- [x] Інтеграція з розетками TP-Link Tapo
- [x] PWA фронтенд з офлайн підтримкою
- [x] Web push сповіщення
- [x] Docker-бекенд
- [ ] Сповіщення через Telegram-бота
- [ ] Адмін-панель з графіками

## 🛠️ Технологічний стек

| Рівень | Технологія |
|--------|------------|
| BLE-комунікація | [bleak](https://github.com/hbldh/bleak) (Python) |
| API інвертора | [pysolarmanv5](https://github.com/srph/pysolarmanv5) |
| Розетки Tapo | [TapoP100 fork](https://github.com/almottier/TapoP100) |
| Бекенд | Python / FastAPI / SQLite |
| Фронтенд | Vue 3 + TypeScript + Quasar + PWA |
| Деплой | Docker + PM2 |

### Топ-контриб’ютори:
<a href="https://github.com/RondaYummy/bms-monitor-ble/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RondaYummy/bms-monitor-ble" alt="contrib.rocks image" />
</a>

## 💬 Зворотній зв’язок та підтримка

Якщо ви зіткнулися з проблемою або маєте ідеї для нових функцій — відкрийте issue тут:  
👉 [GitHub Issues](https://github.com/RondaYummy/bms-monitor-ble/issues)

## Посилання
- https://github.com/syssi/esphome-jk-bms
- https://github.com/PurpleAlien/jk-bms_grafana
- https://github.com/jblance/jkbms
- https://github.com/sshoecraft/jktool
- https://github.com/maxx-ukoo/jk-bms2pylontech
- https://github.com/ismarintan98/JK_BMS
- https://github.com/Louisvdw/dbus-serialbattery/blob/master/etc/dbus-serialbattery/jkbms.py
- https://secondlifestorage.com/index.php?threads/jk-b1a24s-jk-b2a24s-active-balancer.9591/
- https://github.com/jblance/jkbms
- https://github.com/jblance/mpp-solar/issues/112
- https://github.com/jblance/mpp-solar/blob/master/mppsolar/protocols/jk232.py
- https://github.com/jblance/mpp-solar/blob/master/mppsolar/protocols/jk485.py
- https://github.com/sshoecraft/jktool
- https://github.com/Louisvdw/dbus-serialbattery/blob/master/etc/dbus-serialbattery/jkbms.py
- https://blog.ja-ke.tech/2020/02/07/ltt-power-bms-chinese-protocol.html
- https://dy-support.org/community/postid/19450
- https://github.com/kellerza/sunsynk/issues/59

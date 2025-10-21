# 🛡️ Отримання SSL-сертифіката: Метод DNS-01 (Certbot Manual)
Оскільки порти 80/443 можуть бути заблоковані, ми використовуємо метод DNS-01 (через --manual та --preferred-challenges dns), який доводить володіння доменом шляхом додавання спеціального TXT-запису до вашого DNS.

**Цей процес є напівавтоматичним і вимагає ручного втручання.**

### Попередження
- Сертифікати Let's Encrypt дійсні **90 днів** — необхідне регулярне поновлення.
- Метод `--manual` не підходить для автоматичного оновлення без інтеграції DNS-API; доведеться вручну повторювати процедуру при кожному продовженні.
- ertbot може логувати ваш IP у публічні логи при `--manual` (додатково: додавайте `--manual-public-ip-logging-ok`, якщо погоджуєтесь).

## 1. Команди для отримання / поновлення сертифіката
 1.1 Базова (інтерактивна) команда

 ```bash
 sudo certbot certonly --manual --preferred-challenges dns -d solar.levych.com
```

 1.2 Команда з автоматичним записом дати поновлення в SQLite (виконується тільки якщо Certbot успішний)
(Перша версія записує поточний час з оболонки; друга — використовує sqlite datetime('now','utc').)

```bash
sudo certbot certonly --manual --preferred-challenges dns -d solar.levych.com \
  && CURRENT_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  && docker exec bms-monitor-ble-python-app-1 sqlite3 /app/data/bms_data.db "INSERT INTO ssl_certificates (created_at, days) VALUES ('$CURRENT_DATE', 90);"

```

Альтернатива (безпечніше, щоб час встановив sqlite всередині контейнера):

```bash
sudo certbot certonly --manual --preferred-challenges dns -d solar.levych.com \
  && docker exec bms-monitor-ble-python-app-1 sqlite3 /app/data/bms_data.db "INSERT INTO ssl_certificates (created_at, days) VALUES (datetime('now', 'utc'), 90);"
```

**Примітка:** && гарантує, що запис в БД виконається лише при успішному завершенні Certbot.

## 2. Процес перевірки (Challenge)
Після запуску Certbot:
- 1. Certbot згенерує унікальний рядок перевірки (Challenge).
- 2. Він виведе інструкцію додати TXT-запис до DNS:

```bash
Please deploy a DNS TXT record under the name
_acme-challenge.solar.levych.com with the following value:

[УНІКАЛЬНИЙ_СТРОК_ПЕРЕВІРКИ]

Before continuing, verify the record is deployed.
- Press Enter to Continue
```

## 3. Ваші дії у панелі DNS-провайдера
Вам необхідно зайти в панель керування вашого DNS-провайдера (наприклад, GoDaddy) і додати новий запис:

- **Тип:** TXT	Тип запису
- **Ім'я / Хост:** `_acme-challenge.solar`	**Важливо:** Certbot просить повне ім'я `_acme-challenge.solar.levych.com`. На більшості панелей потрібно ввести лише префікс `_acme-challenge.solar`.
- **Значення:** `[УНІКАЛЬНИЙ_РЯДОК_ПЕРЕВІРКИ]`	Унікальний рядок, який Certbot щойно надав.
- **TTL:** 60 або 300 (мінімальне)	Рекомендовано встановити мінімальний час життя (Time To Live), щоб запис швидко поширився.

## 4. Завершення перевірки
- Почекайте 30–300 с (залежить від TTL і провайдера).
- Перевірте TXT-запис (наприклад, `dig` або онлайн-інструменти):
https://toolbox.googleapps.com/apps/dig/#TXT/_acme-challenge.solar.levych.com
- Поверніться в термінал → натисніть `Enter`. Certbot перевірить запис і, якщо він правильний, збере та збереже сертифікат.

Результат: файли зберігаються у `/etc/letsencrypt/live/solar.levych.com/`:
- `fullchain.pem` — сертифікат
- `privkey.pem` — приватний ключ

**ВАЖЛИВО:** Цей TXT-запис є тимчасовим. Ви можете видалити його після успішного отримання сертифіката. Однак, його потрібно буде створювати знову при кожному поновленні.

5. Після успіху — перезавантаження сервера
Щоб `nginx` (або інший сервер) підхопив сертифікат:

```bash
sudo systemctl reload nginx
# або якщо reload не спрацює:
# sudo systemctl restart nginx
```

Якщо nginx працює всередині Docker, то перезавантаження контейнера/сервісу:

```bash
docker exec <nginx-container> nginx -s reload
# або docker restart <nginx-container>
```

6. Поради та поліпшення
- **Автоматизація**: замість `--manual` використовуй DNS-плагіни Certbot (наприклад `certbot-dns-cloudflare`, `certbot-dns-google` тощо). Вони дозволяють автоматично створювати `TXT-записи` і **повністю автоматизувати** поновлення. Дуже рекомендовано для `production`.
- **Безпека ключів**: переконайся, що `privkey.pem` захищений (правильні права доступу).
- **Перевірка**: `certbot certificates` показує встановлені сертифікати та шляхи.
- **Планування поновлень**: якщо лишаєш manual, став собі нагадування `~60 днів` після створення, бо Certbot не зможе автоматично оновити. Краще налаштувати `cron/systemd timer`, якщо автоматизація доступна.
- **Логи**: дивись `/var/log/letsencrypt/letsencrypt.log` при помилках.
- **Контейнер/шляхи**: переконайся, що шлях до БД `/app/data/bms_data.db` і назва контейнера `bms-monitor-ble-python-app-1` актуальні.
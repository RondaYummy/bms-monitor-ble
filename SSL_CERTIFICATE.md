# 🛡️ SSL-сертифікат: автоматичне отримання та поновлення

Сертифікат Let's Encrypt отримується методом **DNS-01** (порти 80/443 не потрібні) через **DNS-плагін certbot**:
certbot сам створює TXT-запис через API вашого DNS-провайдера, тож поновлення кожні ~60 днів відбувається
**без жодної ручної роботи**. Застосунок читає дату закінчення **з самого сертифіката** — ручні записи в базу
більше не потрібні.

## 1. Оберіть DNS-провайдера

| Провайдер | Плагін | Примітка |
|---|---|---|
| **Cloudflare** (рекомендовано) | `certbot-dns-cloudflare` | Безкоштовно. Можна перенести лише DNS-зону, домен лишається у реєстратора. |
| GoDaddy | `certbot-dns-godaddy` (сторонній) | GoDaddy обмежує DNS API для невеликих акаунтів; якщо отримуєте `ACCESS_DENIED` — перенесіть DNS на Cloudflare. |
| DigitalOcean, Route53, Google, OVH | офіційні плагіни | |

Для Cloudflare створіть **API Token** з правом `Zone → DNS → Edit` лише для вашої зони.

## 2. Запустіть скрипт налаштування (на сервері, один раз)

```bash
cd ~/bms-monitor-ble
sudo ./scripts/ssl/setup-certbot-dns.sh cloudflare solar.example.com you@example.com
```

Перший запуск створить файл `/etc/letsencrypt/dns-cloudflare.ini` (права `600`) і попросить вписати туди токен.
Впишіть його та запустіть скрипт ще раз. Скрипт:

1. встановить certbot і DNS-плагін в окреме середовище `/opt/certbot`;
2. отримає новий сертифікат (існуючий ручний буде замінено — certbot запитає підтвердження);
3. увімкне таймер `certbot-dns-renew.timer` (перевірка двічі на добу, поновлення за 30 днів до закінчення);
4. встановить deploy-hook `/etc/letsencrypt/renewal-hooks/deploy/bms-monitor.sh`, який після кожного поновлення
   перевіряє конфіг і перезавантажує nginx та публікує **лише публічний** сертифікат у `/var/lib/bms-monitor/ssl/`;
5. виконає `certbot renew --dry-run`, щоб переконатися, що поновлення працює.

Перевірка:
```bash
systemctl list-timers certbot-dns-renew.timer
sudo certbot-dns certificates
```

## 3. Як застосунок дізнається дату закінчення

Бекенд перевіряє (у такому порядку):

1. **`SSL_CERT_FILE`** (за замовчуванням `/ssl/fullchain.pem`) — копія з deploy-hook; у `docker-compose.yml`
   змонтовано `/var/lib/bms-monitor/ssl:/ssl:ro`. Приватний ключ у контейнер **не потрапляє**.
2. **`SSL_CHECK_HOST`** (у `.env`, напр. `solar.example.com:8443`) — живе TLS-підключення до домену: показує саме те,
   що бачать браузери, і ловить ситуації «сертифікат поновлено, але nginx не перезавантажено» або недовірений ланцюжок
   (`ERR_CERT_AUTHORITY_INVALID`). Може не працювати, якщо роутер не підтримує hairpin NAT.
3. Старий ручний запис у таблиці `ssl_certificates` — лише для сумісності, поки не налаштовано п. 1 або 2.

Попередження: якщо до закінчення лишилось **менше 20 днів** (тобто автоматичне поновлення не спрацювало) або браузери
не довіряють сертифікату, у застосунку загориться статус і прийде push-сповіщення (не частіше разу на добу).

## Додатково: ручний метод (якщо DNS API недоступний)

```bash
sudo certbot certonly --manual --preferred-challenges dns -d solar.example.com
```
Certbot попросить додати TXT-запис `_acme-challenge.solar.example.com`; після перевірки виконайте
`sudo RENEWED_LINEAGE=/etc/letsencrypt/live/solar.example.com ./scripts/ssl/deploy-hook.sh`, щоб перезавантажити
nginx і оновити дані для картки статусу. Цю процедуру доведеться повторювати кожні ~60 днів.

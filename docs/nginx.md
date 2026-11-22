## Встановлення сервера

Встановлюємо файрвол

```
sudo apt install ufw
```

Додаємо репозиторій

```
sudo apt install -y software-properties-common
sudo apt update
sudo apt-add-repository -y ppa:hda-me/nginx-stable
```

Встановлюємо сервер та модулі

```
sudo apt-get install brotli nginx nginx-module-brotli
```

Ремонтуємо сервіс nginx 👀 ( Переважно проблема на Ubintu 18, на 20.04 все працює )

```
sudo systemctl unmask nginx.service
```

Відкриваємо налаштування сервера

```
sudo nano /etc/nginx/nginx.conf
```

## Налаштування файрвола

Перевіряємо статус

```
sudo ufw enable
sudo ufw status
sudo ufw app list
```
```
Available applications:
  Nginx Full
  Nginx HTTP
  Nginx HTTPS
  OpenSSH
```

Додаємо nginx в ufw, якщо його немає

```
sudo nano /etc/ufw/applications.d/nginx.ini
```

```
[Nginx HTTP]
title=Web Server
description=Enable NGINX HTTP traffic
ports=80/tcp

[Nginx HTTPS] \
title=Web Server (HTTPS) \
description=Enable NGINX HTTPS traffic
ports=443/tcp

[Nginx Full]
title=Web Server (HTTP,HTTPS)
description=Enable NGINX HTTP and HTTPS traffic
ports=80,443/tcp
```

Включаємо

```
sudo ufw enable
```

Дозволяємо nginx

```
sudo ufw allow 'Nginx Full'
```

Видалити надлишковий дозвіл профілю «Nginx HTTP»:

```
sudo ufw delete allow 'Nginx HTTP'
sudo ufw allow 443
sudo ufw allow 80
```

Дозволяється OpenSSH

```
sudo ufw allow 'OpenSSH'
```

Перевіряємо статус

```
sudo ufw status
```

```
Status: active

To                         Action      From
--                         ------      ----
Nginx Full                 ALLOW       Anywhere
OpenSSH                    ALLOW       Anywhere
Nginx Full (v6)            ALLOW       Anywhere (v6)
OpenSSH (v6)               ALLOW       Anywhere (v6)
```
## Установка certbot

Додаємо джерела

```
sudo apt-get install software-properties-common
sudo add-apt-repository ppa:certbot/certbot
```

Оновлюємося

```
sudo apt-get update
```

Ставимо certbot

```
sudo apt install certbot python3-certbot-nginx
```

Генеруємо ключ

```
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
```

Створюємо папку для сніпетів nginx ( для зручності )

```
sudo mkdir -p /etc/nginx/snippets/
```

Створюємо сніпет для SSL

```
sudo nano /etc/nginx/snippets/ssl-params.conf
```

```
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

ssl_dhparam /etc/ssl/certs/dhparam.pem;

ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

add_header Strict-Transport-Security "max-age=63072000" always;
```
## Додавання сайту

Створюємо конфіг сайту

```
sudo nano /etc/nginx/sites-available/solar.levych.com.conf
```

```
server {
    listen 8080;
    listen [::]:8080;

    server_name solar.levych.com;
}
```

Створіть символьне посилання до файлу конфігурації з директорії /etc/nginx/sites-enabled/ до директорії
/etc/nginx/sites-available/, виконавши наступну команду

```
sudo ln -s /etc/nginx/sites-available/solar.levych.com.conf /etc/nginx/sites-enabled/
```

Перевіряємо конфіги nginx на помилки

```
sudo nginx -t
```

Рестартуємо nginx

```
sudo systemctl restart nginx
```

## Додавання сертифіката

Запускаємо certbot

Через ДНС запис
```
sudo certbot certonly --manual --preferred-challenges dns -d solar.levych.com
```
Без емейла, може не працювати
```
sudo certbot --nginx certonly -d solar.levych.com --register-unsafely-without-email
```

Оновлюємо конфіг сайту

```
sudo nano /etc/nginx/sites-available/solar.levych.com.conf
```

Тут ми зробимо також редірект з 80 порту, на порт, на якому працює наш бекенд, у моєму випадку це 3000 та добавимо
сертифікати SSL

```
# Перенаправлення HTTP на HTTPS
server {
    listen 8080;
    listen [::]:8080;

    server_name solar.levych.com;

    # Перенаправлення HTTP на HTTPS
    return 301 https://solar.levych.com$request_uri;
}

# HTTPS сервер
server {
    listen 8443 ssl http2;
    listen [::]:8443 ssl http2;

    server_name solar.levych.com;

    # SSL сертифікати
    ssl_certificate /etc/letsencrypt/live/solar.levych.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/solar.levych.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/solar.levych.com/chain.pem;

    include snippets/ssl-params.conf;

    # Live-оновлення (Server-Sent Events): без буферизації і з довгим таймаутом
    location = /api/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }

    # Проксі на Python-додаток
    location /api/ {
        proxy_pass http://127.0.0.1:8000; # Проксі-запити до Python-додатка
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Обслуговування фронтенда (статичні файли Quasar)
    root /usr/share/nginx/html/pwa; # Де розміщені статичні файли Quasar
    index index.html;

    location / {
        try_files $uri /index.html; # Файли фронтенда
    }

    # Кешування статичних файлів
    location ~* \.(?:ico|css|js|woff2?|eot|ttf|otf|svg|jpg|jpeg|gif|png|webp|avif|mp4|webm|ogg|mp3|wav|flac|aac|m4a)$ {
        expires 6M;
        access_log off;
    }

    # Забезпечення актуальності Service Worker
    location /service-worker.js {
        add_header Cache-Control "no-cache";
    }

    # Перенаправлення помилок 404 на index.html (для SPA)
    error_page 404 /index.html;
}
```

Перевіряємо конфіг у nginx

```
sudo nginx -t
```

Рестартуємо nginx

```
sudo systemctl restart nginx
```

## Додавання DNS records

Щоб підключити наш домен, нам потрібно добавити такі записи

Type: A; Name: @ чи www Value: 00.000.0.00 - ( Ваша IP адреса серверу ) Записи DNS обновляються деякий час, тому зміни
запрацюють не одразу.

Перевіряємо сайт та радуємось

```
curl solar.levych.com
```

## Автоматичне поновлення SSL сертифікатів

Автоматичне поновлення SSL-сертифікатів з Nginx можна налаштувати з використанням Certbot та системи автоматичного
планування задач cron. Цей пункт передбачає, що у вас уже встановлено certbot python3-certbot-nginx та уже добавлено
сертифкати на ваш сервер.

Додайте новий файл в папку /etc/cron.weekly/ з назвою, наприклад, certbot-renew:

```
sudo nano /etc/cron.weekly/certbot-renew
```

Додайте наступний скрипт у створений файл та збережіть його:

```
#!/bin/sh
/usr/bin/certbot renew --quiet --renew-hook "/usr/sbin/service nginx reload"
```

Цей скрипт автоматично виконує оновлення сертифікатів Certbot та перезавантажує сервер Nginx.

Зробіть файл виконуваним:

```
sudo chmod +x /etc/cron.weekly/certbot-renew
```

Тепер SSL-сертифікати будуть автоматично поновлюватись щотижня. Ви можете налаштувати більш часте оновлення, змінивши
час запуску скрипту у файлі /etc/crontab. Також, Certbot встановить повідомлення електронної пошти про будь-які проблеми
поновлення сертифікатів або про те, що SSL-сертифікат майже закінчується та його потрібно оновити вручну.

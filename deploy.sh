#!/bin/bash

COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="bms-monitor-ble"

if [ -f .env ]; then
    echo "ℹ️ Завантажуємо змінні оточення з .env"
    source .env
    
    export TELEGRAM_BOT_TOKEN
    export TELEGRAM_CHAT_ID
else
    echo "⚠️ Файл .env не знайдено. Перевіряємо змінні оточення."
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "❌ ПОМИЛКА: TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID не визначено."
fi

function send_telegram_notification() {
  local message_text=$1
  curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TELEGRAM_CHAT_ID" \
    -d "parse_mode=Markdown" \
    -d "text=$message_text" > /dev/null
}

function deploy() {
  local DEPLOY_START_TIME=$(date +%s)
  local DEPLOY_START_DATE=$(date +%d.%m.%Y\ %H:%M:%S)
  local START_MESSAGE="🚀 *[$PROJECT_NAME]* Починаємо автоматичне розгортання о $DEPLOY_START_DATE"
  send_telegram_notification "$START_MESSAGE"
  echo "⏳ ====> Починаємо оновлення проекту"

  echo "⏳ ====> Оновлюємо код з Git"
  git pull
  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час оновлення коду з Git"
    local ERROR_MSG="❌ *[$PROJECT_NAME]* ПОМИЛКА: Не вдалося оновити код з Git. Перевірте підключення."
    send_telegram_notification "$ERROR_MSG"
    echo "$ERROR_MSG"
    exit 1
  fi
  echo "✅ Код успішно оновлено з Git"

  echo "⏳ ====> Ребілдимо Докер-образи через Docker Compose"
  # On weak Raspberry Pi it is: Heavily loads the CPU, Uses all RAM + disk I/O
  # - Because of this, the Pi can:
  # - shut down
  # - freeze
  # - lose SSH
# - call OOM killer (kills one of the processes)
  # docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build --parallel

  # Solution: build sequentially, not in parallel
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build frontend
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME build python-app

  echo "====> Перезапускаємо Докер-контейнери"
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d

  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час ребілду та запуску контейнерів"
    local ERROR_MSG="❌ *[$PROJECT_NAME]* ПОМИЛКА: Не вдалося ребілднути та запустити контейнери. Перевірте log Compose."
    send_telegram_notification "$ERROR_MSG"
    echo "$ERROR_MSG"
    exit 1
  fi
  echo "✅ Контейнери успішно перезапущені"

    FRONTEND_CONTAINER=$(docker ps -q -f name="${PROJECT_NAME}-frontend")
  if [ -z "$FRONTEND_CONTAINER" ]; then
    echo "❌ Не вдалося знайти контейнер фронтенду"
    local ERROR_MSG="❌ *[$PROJECT_NAME]* ПОМИЛКА: Не вдалося знайти контейнер фронтенду."
    send_telegram_notification "$ERROR_MSG"
    echo "$ERROR_MSG"
    exit 1
  fi

  docker cp "$FRONTEND_CONTAINER":/usr/share/nginx/html /usr/share/nginx/
  if [ $? -ne 0 ]; then
    echo "❌ Помилка копіювання статичних файлів з контейнера"
    local ERROR_MSG="❌ *[$PROJECT_NAME]* ПОМИЛКА: Не вдалося скопіювати статичні файли з контейнера."
    send_telegram_notification "$ERROR_MSG"
    echo "$ERROR_MSG"
    exit 1
  fi
  echo "✅ Статичні файли успішно скопійовані"

  echo "⏳ ====> Видаляємо непотрібні  Докер-образи, контейнери, імеджі та мережі"
  # NOTE: no --volumes here: if a container is not running at this moment its volume
  # (sqlite_data = all history, passwords, devices) would be deleted.
  docker system prune --all --force
  # Очищає все непотрібне, включаючи:
  # - Зупинені контейнери.
  # - Невикористовувані образи (включаючи "dangling" і "непов'язані").
  # - Невикористовувані мережі.
  # - Неприв'язані томи (завдяки опції --volumes).

  # docker system prune -f # Видалення непотрібних контейнерів, образів та мереж
  # docker volume prune -f # Видалення неприєднаних томів (не зачіпає sqlite_data)
  # docker image prune -f

  # END
  local DEPLOY_END_TIME=$(date +%s)
  local DURATION=$((DEPLOY_END_TIME - DEPLOY_START_TIME))
  local SUCCESS_MESSAGE="✅ *[$PROJECT_NAME]* Успішне розгортання завершено! Тривалість: ${DURATION} секунд."
  send_telegram_notification "$SUCCESS_MESSAGE"
  echo "⏳ ====> Оновлення проекту завершено успішно"

  # echo "====> Перезапускаємо сервер Ubuntu..."
  # sudo reboot
}

function check_deploy() {
    changed=0
    git fetch && git status -uno | grep -q 'Your branch is behind' && changed=1

    if [ $changed = 1 ]; then
        deploy
        pm2 reset "⚙️ DEPLOY: [BLE] BMS Monitor!"
    else
        dt=$(date +%d.%m.%Y\ %H:%M:%S)
        echo "[$dt] Branch is up to date"
    fi
}

while [ 1 ]; do
    check_deploy 2>&1

    now=$(date +%s)
    target=$(date -d '04:00 next day' +%s)
    sleep_time=$(( target - now ))
    sleep_time=60 # TODO: hardcoded 1min
    sleep $sleep_time

    # sleep 300 # 5 min sleep
    # sleep 86400 # 24 hours sleep
done

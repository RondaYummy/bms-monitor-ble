#!/bin/bash

COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="bms-monitor-ble"

function deploy() {
  echo "====> Починаємо оновлення проекту"

  echo "====> Оновлюємо код з Git"
  git pull
  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час оновлення коду з Git"
    exit 1
  fi
  echo "✅ Код успішно оновлено з Git"

  echo "====> Ребілдимо паралельно Докер-образи через Docker Compose"
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
    exit 1
  fi
  echo "✅ Контейнери успішно перезапущені"

    FRONTEND_CONTAINER=$(docker ps -q -f name="${PROJECT_NAME}-frontend")
  if [ -z "$FRONTEND_CONTAINER" ]; then
    echo "❌ Не вдалося знайти контейнер фронтенду"
    exit 1
  fi

  docker cp "$FRONTEND_CONTAINER":/usr/share/nginx/html /usr/share/nginx/
  if [ $? -ne 0 ]; then
    echo "❌ Помилка копіювання статичних файлів з контейнера"
    exit 1
  fi
  echo "✅ Статичні файли успішно скопійовані"

  echo "====> Видаляємо непотрібні  Докер-образи, контейнери, імеджі та мережі"
  docker system prune --all --force --volumes
  # Очищає все непотрібне, включаючи:
  # - Зупинені контейнери.
  # - Невикористовувані образи (включаючи "dangling" і "непов'язані").
  # - Невикористовувані мережі.
  # - Неприв'язані томи (завдяки опції --volumes).

  # docker system prune -f # Видалення непотрібних контейнерів, образів та мереж
  # docker volume prune -f # Видалення неприєднаних томів (не зачіпає sqlite_data)
  # docker image prune -f

  # END
  echo "====> Оновлення проекту завершено успішно"

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
    sleep_time=30 # TODO: hardcoded
    sleep $sleep_time

    # sleep 300 # 5 min sleep
    # sleep 86400 # 24 hours sleep
done

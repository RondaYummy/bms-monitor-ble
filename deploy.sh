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

  echo "====> Ребілдимо Докер-образи через Docker Compose"
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down
  docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up --build -d
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

  # END
  echo "====> Оновлення проекту завершено успішно"
}

function check_deploy() {
    changed=0
    git fetch && git status -uno | grep -q 'Your branch is behind' && changed=1

    if [ $changed = 1 ]; then
        deploy
    else
        dt=$(date +%d.%m.%Y\ %H:%M:%S)
        echo "[$dt] Branch is up to date"
    fi
}

while [ 1 ]; do
    check_deploy 2>&1
    sleep 300 # 5 min sleep
    # sleep 86400 # 24 hours sleep
done

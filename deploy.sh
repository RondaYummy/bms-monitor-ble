#!/bin/bash

function deploy() {
  echo "====> Починаємо оновлення проекту"

  echo "====> Оновлюємо код з Git"
  git pull
  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час оновлення коду з Git"
    exit 1
  fi
  echo "✅ Код успішно оновлено з Git"

  echo "====> Ребілдимо Докер"
  docker build --no-cache -t bms-monitor-ble .
  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час ребілду докера"
    exit 1
  fi
  echo "✅ Докер перезібрався успішно"

  echo "====> Запускаємо проект"
  docker run --rm -it --privileged --name bms-monitor-ble --net=host     -v /var/run/dbus:/var/run/dbus     bms-monitor-ble
  if [ $? -ne 0 ]; then
    echo "❌ Помилка під час запуску проекта"
    exit 1
  fi
  echo "✅ Проект успішно запущено"


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
    sleep 60
done

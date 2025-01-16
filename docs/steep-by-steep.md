## Оновіть пакетну базу даних та оновіть пакети до останніх версій:

```
sudo apt update
sudo apt upgrade -y
```
## Встановіть необхідні залежності
```
sudo apt install -y curl ca-certificates gnupg lsb-release

```

## Додайте офіційний Docker GPG-ключ
```
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```

## Додайте Docker репозиторій
```
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

## Оновіть пакетну базу даних
```
sudo apt update
```

## Встановіть Docker Engine
```
sudo apt install -y docker-ce docker-ce-cli containerd.io
docker --version
```

## Додайте користувача в групу docker (опціонально)
```
sudo usermod -aG docker $USER
newgrp docker
```

## Встановіть NVM та PM2
```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install --lts
nvm alias default 22
npm install pm2 -g
pm2 start ecosystem.config.js
```

## Встановіть необхідні залежності
```

```

## Встановіть необхідні залежності
```

```

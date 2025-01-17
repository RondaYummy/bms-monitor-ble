FROM node:22

WORKDIR /app

COPY package.json yarn.lock ./

COPY . .

RUN yarn install

RUN yarn build

FROM nginx:stable-alpine

# Копіюємо статичні файли у папку nginx
COPY --from=0 /app/dist/pwa /usr/share/nginx/html

# Копіюємо кастомний конфіг для nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Вказуємо, що контейнер слухає порт 8444
EXPOSE 8444

CMD ["nginx", "-g", "daemon off;"]

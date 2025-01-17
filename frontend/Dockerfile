FROM node:22 as build-stage

WORKDIR /app

COPY package.json yarn.lock ./

RUN yarn install

COPY . .

RUN yarn build

RUN ls -l /app/dist

FROM nginx:stable-alpine

# Копіюємо статичні файли у папку nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

RUN ls -l /usr/share/nginx/html

# Копіюємо кастомний конфіг для nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8444
CMD ["nginx", "-g", "daemon off;"]

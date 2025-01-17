FROM node:22 as build-stage

WORKDIR /usr/src/app

COPY package.json package-lock.json ./

RUN npm install

COPY . .

RUN npm run build

FROM nginx:stable-alpine

# Копіюємо статичні файли у папку nginx
COPY --from=build-stage /usr/src/app/dist /usr/share/nginx/html

# Копіюємо кастомний конфіг для nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8444
CMD ["nginx", "-g", "daemon off;"]

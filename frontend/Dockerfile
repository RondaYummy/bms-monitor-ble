FROM node:22 as build-stage

WORKDIR /usr/src/app

COPY package.json package-lock.json ./

RUN npm install

COPY . .

RUN npm run build

FROM nginx:stable-alpine

RUN apk add --no-cache gettext

COPY --from=build-stage /usr/src/app/dist /usr/share/nginx/html

COPY nginx.conf.template /etc/nginx/conf.d/nginx.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8444
ENTRYPOINT ["/entrypoint.sh"]

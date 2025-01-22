FROM node:22

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

COPY . .

RUN yarn build

EXPOSE 3010

CMD ["yarn", "start:prod"]

FROM node:18-alpine

WORKDIR /usr/app

RUN npm install express async-barrier node-cron log-timestamp connect-timeout

COPY . .

EXPOSE 1968

ENTRYPOINT [ "node", "drr_server.js" ]

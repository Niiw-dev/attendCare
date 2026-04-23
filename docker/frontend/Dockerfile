FROM node:20

WORKDIR /app

COPY docker/frontend/package*.json ./

RUN npm install

COPY docker/frontend/ .

CMD ["npm", "run", "dev", "--", "--host"]
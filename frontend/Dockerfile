FROM node:24.14.1-bullseye
WORKDIR /app

COPY package*.json ./
RUN npm install

EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# Для сервисов с Prisma — генерация клиента
RUN npx prisma generate

EXPOSE 3002

CMD ["node", "src/index.js"]

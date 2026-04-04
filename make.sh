#!/bin/bash

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан файл .env из .env.example"
fi

# Функция для генерации случайной строки (32 символа)
generate_secret() {
    openssl rand -base64 24 | tr -d '/+=' # Чистая строка без спецсимволов
}

POSTGRES_PASSWORD=$(generate_secret)
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env

PREFIXAUTH=$(grep "AUTH_DATABASE_URL=" .env.example | cut -d '=' -f2 | cut -c 1-30)
POSTFIXAUTH=$(grep "AUTH_DATABASE_URL=" .env.example | cut -d '=' -f2 | cut -c 37-58)


AUTH_URL="${PREFIXAUTH}${POSTGRES_PASSWORD}${POSTFIXAUTH}"


sed -i "s|^AUTH_DATABASE_URL=.*|AUTH_DATABASE_URL=$AUTH_URL|" .env

PREFIXTASK=$(grep "TASK_DATABASE_URL=" .env.example | cut -d '=' -f2 | cut -c 1-30)
POSTFIXTASK=$(grep "TASK_DATABASE_URL=" .env.example | cut -d '=' -f2 | cut -c 37-58)

TASK_URL="${PREFIXTASK}${POSTGRES_PASSWORD}${POSTFIXTASK}"

sed -i "s|^TASK_DATABASE_URL=.*|TASK_DATABASE_URL=$TASK_URL|" .env


sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(generate_secret)|" .env

sed -i "s|^REFRESH_TOKEN_SECRET=.*|REFRESH_TOKEN_SECRET=$(generate_secret)|" .env

echo "Поля с паролями и ключами успешно заполнены."

docker-compose up

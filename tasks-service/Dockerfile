FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Миграции БД выполняются при старте через entrypoint или вручную
# RUN alembic upgrade head

EXPOSE 3002

CMD ["uvicorn", "cmd.main:app", "--host", "0.0.0.0", "--port", "3002"]

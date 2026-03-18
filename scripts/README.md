# Project Scripts

## `generate_env.py`

Генерирует `.env` файл из шаблона `.env.example` с безопасными случайными секретами.

### Использование

```bash
# Из корня проекта
python scripts/generate_env.py
```

### Что делает:

1. Копирует `.env.example` в `.env`
2. Генерирует случайные секреты:
   - `JWT_SECRET_KEY` (32 символа)
   - `REFRESH_TOKEN_SECRET` (32 символа)
   - `POSTGRES_PASSWORD` (16 символов)
3. Сохраняет в корень проекта

### Для production

В production используйте CI/CD secrets или environment variables:

```bash
# Пример с GitHub Actions
- name: Deploy
  run: docker-compose up -d
  env:
    JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

**Не используйте этот скрипт в production!**

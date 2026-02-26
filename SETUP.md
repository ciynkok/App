# Настройка окружения

Этот файл содержит подробную инструкцию по настройке проекта в новом окружении.

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd App

# 2. Создать .env из шаблона
cp .env.example .env

# 3. Заполнить .env (см. ниже)

# 4. Запустить весь стек
docker compose up --build
```

---

## 📝 Настройка .env файла

Скопируйте `.env.example` в `.env` и заполните переменные:

```bash
cp .env.example .env
```

---

### 🔐 Обязательные переменные

Эти переменные **нужно заполнить обязательно** для работы проекта:

| Переменная | Пример значения | Описание |
|------------|-----------------|----------|
| `POSTGRES_USER` | `postgres` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | `secret123` | Пароль PostgreSQL (придумайте свой) |
| `POSTGRES_DB` | `collab` | Имя базы данных |
| `DATABASE_URL` | `postgresql://postgres:secret123@postgres:5432/collab` | Connection string к БД |
| `REDIS_URL` | `redis://redis:6379` | Connection string к Redis |
| `JWT_SECRET` | `min-32-char-secret-key-here` | Секрет для JWT (мин. 32 символа) |
| `JWT_EXPIRES_IN` | `1h` | Время жизни access token |
| `REFRESH_TOKEN_SECRET` | `another-secret-key-32-chars` | Секрет для refresh token |
| `REFRESH_TOKEN_EXPIRES_IN` | `30d` | Время жизни refresh token |

---

### 🔑 OAuth переменные (опционально)

Заполняйте, если планируете использовать OAuth (Google/GitHub):

#### Google OAuth

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите **Google+ API**
4. Перейдите в **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Добавьте redirect URI: `http://localhost/auth/google/callback`

| Переменная | Описание |
|------------|----------|
| `GOOGLE_CLIENT_ID` | Client ID из Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Client Secret из Google Cloud Console |
| `GOOGLE_CALLBACK_URL` | `http://localhost/auth/google/callback` |

#### GitHub OAuth

1. Перейдите в [GitHub Settings](https://github.com/settings/developers)
2. **New OAuth App**
3. Добавьте:
   - **Homepage URL**: `http://localhost`
   - **Authorization callback URL**: `http://localhost/auth/github/callback`

| Переменная | Описание |
|------------|----------|
| `GITHUB_CLIENT_ID` | Client ID из GitHub OAuth App |
| `GITHUB_CLIENT_SECRET` | Client Secret из GitHub OAuth App |
| `GITHUB_CALLBACK_URL` | `http://localhost/auth/github/callback` |

---

### 🌐 Переменные сервисов

Эти переменные используются для внутренней коммуникации сервисов:

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `REALTIME_SERVICE_URL` | `http://realtime:3003` | URL real-time сервиса (внутренний) |
| `AUTH_SERVICE_URL` | `http://auth:3001` | URL auth сервиса (внутренний) |

---

### 🖥️ Frontend переменные

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `NEXT_PUBLIC_API_URL` | `http://localhost` | Публичный URL API (для браузера) |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost/ws` | Публичный URL WebSocket (для браузера) |

---

### ⚙️ Общие переменные

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `NODE_ENV` | `development` | Окружение (development/production) |

---

## 📋 Полный шаблон .env

```env
# ─── PostgreSQL ───────────────────────────────────────
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret123
POSTGRES_DB=collab
DATABASE_URL=postgresql://postgres:secret123@postgres:5432/collab

# ─── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ─── Auth Service ─────────────────────────────────────
JWT_SECRET=your-super-secret-jwt-key-min-32-chars-here
JWT_EXPIRES_IN=1h
REFRESH_TOKEN_SECRET=your-refresh-token-secret-key-32-chars
REFRESH_TOKEN_EXPIRES_IN=30d

# ─── OAuth Google ─────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALLBACK_URL=http://localhost/auth/google/callback

# ─── OAuth GitHub ─────────────────────────────────────
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_CALLBACK_URL=http://localhost/auth/github/callback

# ─── Task Service ─────────────────────────────────────
REALTIME_SERVICE_URL=http://realtime:3003

# ─── Real-time Service ────────────────────────────────
AUTH_SERVICE_URL=http://auth:3001

# ─── Frontend ─────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost
NEXT_PUBLIC_WS_URL=ws://localhost/ws

# ─── Общие ────────────────────────────────────────────
NODE_ENV=development
```

---

## 🔒 Генерация секретных ключей

### JWT_SECRET (мин. 32 символа)

```bash
# Linux/Mac
openssl rand -base64 32

# Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

**Пример:** `a3f8b2c1d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6`

---

## ✅ Проверка после настройки

### 1. Запустить стек
```bash
docker compose up --build
```

### 2. Проверить сервисы

| Сервис | Команда | Ожидаемый ответ |
|--------|---------|-----------------|
| Auth | `curl http://localhost/auth/health` | `{"status":"ok"}` |
| Task | `curl http://localhost/task/health` | `{"status":"ok"}` |
| Realtime | `curl http://localhost/realtime/health` | `{"status":"ok"}` |
| Frontend | Открыть http://localhost | Страница загрузки |

### 3. Проверить БД
```bash
docker compose exec postgres psql -U postgres -d collab -c "\dn"
```

Ожидаемый вывод:
```
  List of schemas
  Name  |       Owner
--------+-------------------
 auth   | postgres
 task   | postgres
 public | pg_database_owner
```

### 4. Проверить Redis
```bash
docker compose exec redis redis-cli ping
```

Ожидаемый ответ: `PONG`

---

## 🐛 Частые проблемы

### Ошибка: "Cannot connect to database"

**Причина:** Неправильный `DATABASE_URL` или БД ещё не готова.

**Решение:**
```bash
# Проверить логи PostgreSQL
docker compose logs postgres

# Перезапустить стек
docker compose down -v
docker compose up --build
```

---

### Ошибка: "JWT_SECRET is too short"

**Причина:** Секрет меньше 32 символов.

**Решение:** Сгенерируйте новый ключ (см. выше).

---

### Ошибка: "Port 5432 already in use"

**Причина:** PostgreSQL уже запущен на хост-машине.

**Решение:**
1. Остановить локальный PostgreSQL
2. Или изменить порт в `docker-compose.yml`

---

### Ошибка: "Cannot find module"

**Причина:** Зависимости не установлены.

**Решение:**
```bash
# Пересобрать образы
docker compose build --no-cache
docker compose up
```

---

## 📚 Дополнительные ресурсы

- [Docker Compose документация](https://docs.docker.com/compose/)
- [Prisma документация](https://www.prisma.io/docs)
- [Next.js документация](https://nextjs.org/docs)

---

## 🆘 Нужна помощь?

1. Проверьте логи: `docker compose logs`
2. Проверьте `.env` на опечатки
3. Убедитесь, что порты 5432, 6379, 3000-3003 свободны

# Real-Time Collaborative Dashboard

> Микросервисная платформа командной работы с Kanban-досками, real-time коллаборацией и встроенным чатом.

---

## Оглавление

1. [Структура проекта](#структура-проекта)
2. [Архитектура системы](#архитектура-системы)
3. [Сервисы и порты](#сервисы-и-порты)
4. [База данных](#база-данных)
5. [Redis — ключи и паттерны](#redis--ключи-и-паттерны)
6. [API-контракт](#api-контракт)
7. [WebSocket события](#websocket-события)
8. [Переменные окружения](#переменные-окружения)
9. [Docker — инструкции для агента](#docker--инструкции-для-агента)
10. [Запуск проекта](#запуск-проекта)
11. [Технологический стек](#технологический-стек)
12. [Правила интеграции между сервисами](#правила-интеграции-между-сервисами)

---

## Структура проекта

```
collab-dashboard/
├── docker-compose.yml                  # Главный файл запуска всего стека
├── docker-compose.override.yml         # Dev-переменные окружения (не в git)
├── docker-compose.monitoring.yml       # Опциональный мониторинг: Prometheus + Grafana
├── .env.example                        # Все переменные окружения — шаблон
│
├── nginx/
│   └── nginx.conf                      # Reverse proxy: роутинг на сервисы + SSL termination
│
├── auth-service/                       # Dev 1 — Auth Service (порт 3001)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                     # Точка входа: FastAPI app
│       ├── routes/
│       │   └── auth.py                 # /auth/* endpoints
│       ├── middleware/
│       │   └── auth.py                 # RBAC middleware
│       └── db/
│           ├── database.py             # SQLAlchemy подключение
│           └── models.py               # Модели: User, RefreshToken, OAuthAccount
│
├── task-service/                       # Dev 2 — Task Service (порт 3002)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── routes/
│       │   ├── boards.py               # /api/boards
│       │   └── tasks.py                # /api/tasks
│       └── db/
│           ├── database.py
│           └── models.py               # Модели: Board, Column, Task, Comment, BoardMember
│
├── realtime-service/                   # Dev 3 — Real-time Service (порт 3003)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                     # FastAPI + WebSocket endpoint
│       └── handlers/
│           └── events.py               # Обработка WebSocket событий
│
└── frontend/                           # Dev 3 — Next.js 15 (порт 3000)
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    └── src/
        └── app/                        # Next.js App Router
            ├── layout.js
            ├── page.js
            ├── auth/
            │   ├── login/page.js
            │   └── register/page.js
            └── dashboard/
                └── [boardId]/page.js
```

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────┐
│                     КЛИЕНТ                          │
│   Next.js 15 + React 19 + Tailwind + Framer Motion  │
│              Socket.io-client (WSS)                 │
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS / WSS
                        ▼
┌─────────────────────────────────────────────────────┐
│               API GATEWAY — Nginx                   │
│  /auth/*  →  auth-service:3001                      │
│  /api/*   →  task-service:3002                      │
│  /ws      →  realtime-service:3003                  │
│  /*       →  frontend:3000                          │
└──────┬──────────────────┬──────────────────┬────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌────────────┐   ┌──────────────┐   ┌────────────────┐
│AUTH SERVICE│   │ TASK SERVICE │   │REALTIME SERVICE│
│  порт 3001 │   │   порт 3002  │   │   порт 3003    │
│            │   │              │   │                │
│ JWT выдача │   │ CRUD Boards  │   │ WebSocket WS   │
│ OAuth2     │   │ CRUD Tasks   │   │ Redis Pub/Sub  │
│ Google     │   │ CRUD Columns │   │ Chat history   │
│ GitHub     │   │ Comments     │   │ Presence       │
│ RBAC roles │   │ Search/Filter│   │ Notifications  │
│ Refresh    │   │ Burn-down    │   │ Webhooks recv  │
│ tokens     │   │ Webhooks send│   │                │
└─────┬──────┘   └──────┬───────┘   └───────┬────────┘
      │                 │                   │
      └─────────────────┴───────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
   ┌─────────────────┐     ┌─────────────────┐
   │  PostgreSQL 16  │     │   Redis 7       │
   │    порт 5432    │     │   порт 6379     │
   │                 │     │                 │
   │ auth_db         │     │ Chat history    │
   │ task_db         │     │ Online users    │
   │                 │     │ Pub/Sub         │
   └─────────────────┘     └─────────────────┘
```

**Ключевые принципы:**
- Каждый сервис — отдельный Docker-контейнер со своим `Dockerfile`
- Сервисы общаются через **внутреннюю Docker-сеть** (не через Nginx)
- Task Service → Real-time Service: HTTP webhook на `http://realtime:3003/internal/events`
- Frontend → Auth Service: REST через Nginx (`/auth/*`)
- Frontend → Task Service: REST через Nginx (`/api/*`)
- Frontend → Real-time Service: WebSocket через Nginx (`/ws`)
- **Auth Service** использует свою БД: `auth_db`
- **Task Service** использует свою БД: `task_db`
- **Real-time Service** использует **Redis** (без PostgreSQL)

---

## Сервисы и порты

| Сервис | Контейнер | Внутренний порт | Внешний порт | Технологии |
|--------|-----------|-----------------|--------------|-----------|
| Frontend | `frontend` | 3000 | 3000 | Next.js 15, React 19 |
| Auth Service | `auth` | 3001 | 3001 | Python 3.12, FastAPI, SQLAlchemy |
| Task Service | `task` | 3002 | 3002 | Python 3.12, FastAPI, SQLAlchemy |
| Real-time Service | `realtime` | 3003 | 3003 | Python 3.12, FastAPI, websockets |
| Nginx | `nginx` | 80/443 | 80/443 | Nginx reverse proxy |
| PostgreSQL | `postgres` | 5432 | 5432 | PostgreSQL 16 |
| Redis | `redis` | 6379 | 6379 | Redis 7 Alpine |

**Зависимости запуска (depends_on):**
```
postgres, redis → auth → task, realtime → frontend → nginx
```

---

## База данных

Каждый сервис использует **отдельную базу данных** PostgreSQL. Прямые JOIN между сервисами невозможны — связь только через `user_id` (UUID).

### База данных `auth_db` (владелец: Auth Service)

```sql
-- Пользователи
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name        VARCHAR(255) NOT NULL,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### База данных `task_db` (владелец: Task Service)

```sql
-- Доски
CREATE TABLE boards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id    UUID NOT NULL,            -- ссылка на auth.users.id (без FK)
    color       VARCHAR(7) DEFAULT '#6366f1',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Задачи
CREATE TABLE tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id   UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    board_id    UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID,                     -- ссылка на auth.users.id
    priority    VARCHAR(10) DEFAULT 'medium',
    status      VARCHAR(20) DEFAULT 'todo',
    deadline    TIMESTAMPTZ,
    position    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Комментарии
CREATE TABLE comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Redis — ключи и паттерны

| Ключ | Тип | Владелец | TTL | Описание |
|------|-----|----------|-----|----------|
| `auth:blacklist:{jti}` | String | Auth Service | Время жизни токена | Отозванные JWT (значение: `'revoked'`) |
| `auth:refresh:{userId}` | String | Auth Service | 30 дней | Хэш активного refresh токена |
| `rt:chat:{boardId}` | List | Real-time Service | 24 часа | История сообщений чата доски (`LPUSH` / `LRANGE`) |
| `rt:online:{boardId}` | Set | Real-time Service | — | Множество активных `user_id` на доске |
| `rt:board:{boardId}:lock:{taskId}` | String | Real-time Service | 30 сек | Оптимистичная блокировка задачи (значение: `userId`) |

---

## API-контракт

### Auth Service — `/auth/*` (порт 3001)

| Метод | Endpoint | Описание | Авторизация |
|-------|----------|----------|-------------|
| `POST` | `/auth/register` | Регистрация пользователя | Public |
| `POST` | `/auth/login` | Логин, получение JWT | Public |
| `GET` | `/auth/me` | Данные текущего пользователя | JWT Required |
| `POST` | `/auth/refresh` | Обновление access token | Refresh Token |
| `POST` | `/auth/logout` | Выход, инвалидация токена | JWT Required |
| `GET` | `/auth/google` | OAuth2 redirect (Google) | Public |
| `GET` | `/auth/google/callback` | OAuth2 callback (Google) | Public |
| `GET` | `/auth/github` | OAuth2 redirect (GitHub) | Public |
| `GET` | `/auth/github/callback` | OAuth2 callback (GitHub) | Public |

**JWT payload (обязательный формат — все сервисы используют этот контракт):**
```json
{
  "sub": "uuid-v4-user-id",
  "role": "admin | editor | viewer",
  "email": "user@example.com",
  "iat": 1700000000,
  "exp": 1700003600
}
```

### Task Service — `/api/*` (порт 3002)

| Метод | Endpoint | Описание | Роль |
|-------|----------|----------|------|
| `GET` | `/api/boards` | Список досок пользователя | JWT Required |
| `POST` | `/api/boards` | Создать доску | editor / admin |
| `GET` | `/api/boards/:id` | Детали доски + колонки | JWT Required |
| `DELETE` | `/api/boards/:id` | Удалить доску | admin |
| `POST` | `/api/boards/:id/columns` | Добавить колонку | editor / admin |
| `GET` | `/api/tasks` | Список задач с фильтрами | JWT Required |
| `POST` | `/api/tasks` | Создать задачу | editor / admin |
| `PUT` | `/api/tasks/:id` | Обновить задачу | editor / admin |
| `PATCH` | `/api/tasks/:id/move` | Переместить в колонку | editor / admin |
| `DELETE` | `/api/tasks/:id` | Удалить задачу | admin |
| `GET` | `/api/tasks/:id/comments` | Комментарии к задаче | JWT Required |
| `POST` | `/api/tasks/:id/comments` | Добавить комментарий | JWT Required |
| `DELETE` | `/api/tasks/:id/comments/:cid` | Удалить комментарий | JWT Required |
| `GET` | `/api/boards/:id/stats` | Данные burn-down chart | JWT Required |
| `GET` | `/api/tasks?search=&status=&assignee=&priority=` | Поиск/фильтрация | JWT Required |

**Webhook от Task Service → Real-time Service (внутренний):**
```
POST http://realtime:3003/internal/events
Content-Type: application/json

{
  "event": "task:moved",
  "boardId": "uuid",
  "payload": { ... }
}
```

### Единый формат ошибок (все сервисы)

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Token is invalid or expired",
    "details": {}
  }
}
```

---

## WebSocket события

Real-time Service (порт 3003) использует **WebSocket endpoint на FastAPI** с комнатами по `boardId`.

### Клиент → Сервер

```js
socket.emit('join:board', { boardId, token })
socket.emit('leave:board', { boardId })
socket.emit('chat:message', { boardId, text })
```

### Сервер → Клиент (broadcast в комнату)

| Событие | Payload | Источник |
|---------|---------|---------|
| `task:moved` | `{ taskId, fromCol, toCol, userId }` | Task Service webhook |
| `task:created` | `{ task, boardId, userId }` | Task Service webhook |
| `task:updated` | `{ taskId, changes, userId }` | Task Service webhook |
| `task:deleted` | `{ taskId, boardId }` | Task Service webhook |
| `comment:added` | `{ taskId, comment, userId }` | Task Service webhook |
| `user:joined` | `{ userId, boardId, name }` | Real-time Service |
| `user:left` | `{ userId, boardId }` | Real-time Service |
| `chat:message` | `{ from, text, boardId, ts }` | Real-time Service |

---

## Переменные окружения

Все переменные хранятся в `.env` (на основе `.env.example`). Каждый сервис читает только свои переменные.

```dotenv
# ─── PostgreSQL ───────────────────────────────────────
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DB=collab
DATABASE_URL=postgresql://postgres:secret@postgres:5432/collab

# ─── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ─── Auth Service ─────────────────────────────────────
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
JWT_EXPIRES_IN=1h
REFRESH_TOKEN_SECRET=your-refresh-secret
REFRESH_TOKEN_EXPIRES_IN=30d

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALLBACK_URL=http://localhost/auth/google/callback

GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
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

## Docker — инструкции для агента

### Dockerfile шаблон (для auth-service, task-service, realtime-service)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE <PORT>

# Для сервисов с миграциями Alembic
# RUN alembic upgrade head

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "<PORT>"]
```

> Замени `<PORT>` на: `3001` (auth), `3002` (task), `3003` (realtime)

### Dockerfile для Frontend (Next.js)

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

> В `next.config.js` требуется `output: 'standalone'`

### docker-compose.yml (полная структура)

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  auth:
    build: ./auth-service
    ports:
      - "3001:3001"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  task:
    build: ./task-service
    ports:
      - "3002:3002"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      auth:
        condition: service_started
    restart: unless-stopped

  realtime:
    build: ./realtime-service
    ports:
      - "3003:3003"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      auth:
        condition: service_started
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file: .env
    depends_on:
      - auth
      - task
      - realtime
    restart: unless-stopped

  nginx:
    build: ./nginx
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - auth
      - task
      - realtime
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

### nginx/nginx.conf

```nginx
upstream frontend    { server frontend:3000; }
upstream auth        { server auth:3001; }
upstream task        { server task:3002; }
upstream realtime    { server realtime:3003; }

server {
    listen 80;

    location /auth/ {
        proxy_pass http://auth/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://task/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://realtime;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Dockerfile для Nginx

```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80 443
```

---

## Запуск проекта

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd collab-dashboard

# 2. Создать .env из шаблона
cp .env.example .env
# Заполнить значения в .env

# 3. Запустить весь стек
docker compose up --build

# 4. (Опционально) Запустить миграции Alembic вручную, если не автостарт
docker compose exec auth alembic upgrade head
docker compose exec task alembic upgrade head

# Остановка и удаление volumes
docker compose down -v
```

**Проверка работоспособности:**
- Frontend: http://localhost
- Auth API: http://localhost/auth/me
- Task API: http://localhost/api/boards
- Swagger docs: http://localhost/api/docs

---

## Технологический стек

| Технология | Версия | Назначение |
|-----------|--------|-----------|
| Next.js | 15 (App Router) | Frontend framework |
| React | 19 | UI, Concurrent rendering |
| Tailwind CSS | 3+ | Стилизация + тёмная тема (`dark:`) |
| Framer Motion | — | Анимации карточек и переходов |
| @dnd-kit/core | — | Drag-and-drop (accessibility-first) |
| Socket.io-client | — | WebSocket на клиенте |
| Recharts | — | Burn-down chart |
| Zustand | — | Глобальный стейт (user, board) |
| Python | 3.12 | Backend runtime |
| FastAPI | — | HTTP framework (все backend-сервисы) |
| SQLAlchemy | — | ORM для работы с PostgreSQL |
| Alembic | — | Миграции БД |
| python-jose | — | JWT выдача/валидация |
| passlib | — | Хэширование паролей |
| httpx | — | HTTP клиент для webhook и OAuth |
| websockets | — | WebSocket сервер |
| aiohttp | — | Асинхронный HTTP клиент/сервер |
| pydantic | — | Валидация входящих данных |
| pytest + httpx | — | Тестирование API |
| PostgreSQL | 16 | Основная БД |
| Redis | 7 Alpine | Кэш, Pub/Sub, чат, presence |
| Nginx | alpine | API Gateway, reverse proxy |
| Docker Compose | — | Оркестрация всего стека |

---

## Правила интеграции между сервисами

### 1. User ID
Везде используется **UUID v4**. Поле называется `userId` или `user_id` во всех сервисах и событиях.

### 2. Аутентификация запросов к Task/Realtime Service
Все защищённые запросы включают заголовок:
```
Authorization: Bearer <access_token>
```
Task Service и Real-time Service **валидируют JWT локально** через общий `JWT_SECRET`.

**JWT payload:**
```json
{
  "sub": "uuid-v4-user-id",
  "email": "user@example.com",
  "jti": "unique-token-id",
  "iat": 1700000000,
  "exp": 1700003600
}
```

**Важно:** Все сервисы используют **один `JWT_SECRET`** из корневого `.env` проекта.

### 3. Webhook от Task Service к Real-time Service
При любом CRUD-действии над задачей Task Service отправляет:
```
POST http://realtime:3003/internal/events
```
```json
{
  "event": "task:moved | task:created | task:updated | task:deleted | comment:added",
  "boardId": "uuid",
  "payload": { "taskId": "uuid", "...": "..." }
}
```
Этот endpoint **не требует JWT** (только внутренняя Docker-сеть).

### 4. Порядок инициализации команды
1. Dev 1 создаёт `docker-compose.yml` с postgres + redis (День 1–2)
2. Dev 1 публикует формат JWT payload
3. Dev 2 публикует Swagger spec (`/api/docs`)
4. Dev 3 публикует спецификацию WebSocket событий
5. Неделя 4 — интеграционное тестирование

---

*Real-Time Collaborative Dashboard | 2026 | Микросервисная архитектура*

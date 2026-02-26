# Real-Time Collaborative Dashboard

Микросервисная платформа командной работы с Kanban-досками, real-time коллаборацией и встроенным чатом.

## Структура проекта

```
App/
├── docker-compose.yml                  # Главный файл запуска всего стека
├── .env.example                        # Шаблон переменных окружения
├── .env                                # Переменные окружения (не в git)
│
├── nginx/                              # API Gateway (reverse proxy)
│   ├── Dockerfile
│   └── nginx.conf
│
├── auth-service/                       # Auth Service (порт 3001)
│   ├── Dockerfile
│   ├── package.json
│   ├── prisma/
│   │   └── schema.prisma
│   ├── init.sql
│   └── src/
│       ├── index.js
│       ├── routes/
│       │   └── auth.routes.js
│       └── middleware/
│           └── checkRole.js
│
├── tasks-service/                      # Task Service (порт 3002)
│   ├── Dockerfile
│   ├── package.json
│   ├── prisma/
│   │   └── schema.prisma
│   ├── init.sql
│   └── src/
│       ├── index.js
│       └── routes/
│           ├── boards.routes.js
│           └── tasks.routes.js
│
├── realtime-service/                   # Real-time Service (порт 3003)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.js
│       └── handlers/
│           └── events.handler.js
│
└── frontend/                           # Next.js 15 (порт 3000)
    ├── Dockerfile
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    └── src/
        └── app/
            ├── layout.js
            ├── page.js
            ├── globals.css
            ├── auth/
            │   ├── login/page.js
            │   └── register/page.js
            └── dashboard/
                └── [boardId]/page.js
```

## Быстрый старт

### 1. Создать .env из шаблона

```bash
cp .env.example .env
```

Заполните значения в `.env` (особенно секреты для JWT и OAuth).

### 2. Запустить весь стек

```bash
docker compose up --build
```

### 3. Проверка работоспособности

- Frontend: http://localhost
- Auth API: http://localhost/auth/me
- Task API: http://localhost/api/boards
- Real-time WS: ws://localhost/ws

### Остановка

```bash
docker compose down
```

Для удаления volumes:

```bash
docker compose down -v
```

## Сервисы и порты

| Сервис | Порт | Описание |
|--------|------|----------|
| Frontend | 3000 | Next.js 15 приложение |
| Auth Service | 3001 | Аутентификация, JWT, OAuth2 |
| Task Service | 3002 | CRUD досок, задач, колонок |
| Real-time Service | 3003 | WebSocket, Socket.io |
| Nginx | 80/443 | Reverse proxy |
| PostgreSQL | 5432 | База данных |
| Redis | 6379 | Кэш, Pub/Sub, чат |

## Технологический стек

См. `architecture_readme.md` для полного описания стека технологий.

**Кратко:**
- **Frontend:** Next.js 15, React 19, Tailwind CSS, Socket.io-client
- **Backend:** Node.js 22, Express.js, Prisma ORM
- **Database:** PostgreSQL 16, Redis 7
- **Auth:** Passport.js, jsonwebtoken, bcrypt
- **Real-time:** Socket.io, ioredis
- **Deployment:** Docker Compose, Nginx

## Документация

Полная документация находится в файле `architecture_readme.md`.

# Task Service

Сервис бизнес-логики. Отвечает за всё, что связано с досками, колонками, задачами и комментариями. Предоставляет REST API для Frontend, отправляет webhook-события в Real-time Service при каждом изменении данных.

---

## Содержание

1. [Обязанности сервиса](#обязанности-сервиса)
2. [Структура директорий](#структура-директорий)
3. [Dockerfile](#dockerfile)
4. [Переменные окружения](#переменные-окружения)
5. [База данных — схема `task`](#база-данных--схема-task)
6. [API endpoints](#api-endpoints)
7. [Webhook — отправка событий в Real-time Service](#webhook--отправка-событий-в-real-time-service)
8. [Валидация данных (Joi)](#валидация-данных-joi)
9. [Аутентификация и авторизация](#аутентификация-и-авторизация)
10. [Swagger / OpenAPI документация](#swagger--openapi-документация)
11. [Тестирование](#тестирование)
12. [Зависимости (npm)](#зависимости-npm)
13. [Взаимодействие с другими сервисами](#взаимодействие-с-другими-сервисами)

---

## Обязанности сервиса

- CRUD для Boards, Columns, Tasks, Comments
- Управление участниками доски (`board_members`)
- Перемещение задач между колонками (`PATCH /api/tasks/:id/move`)
- Поиск и фильтрация задач по статусу, исполнителю, приоритету, дедлайну
- Аналитические данные для burn-down chart
- Отправка HTTP webhook в Real-time Service при каждом CRUD-событии
- Swagger документация — контракт для Frontend разработчика

**Порт:** `3002`
**Внутренний хост в Docker-сети:** `task`

---

## Структура директорий

```
task-service/
├── Dockerfile
├── package.json
├── .env                              # не в git
├── prisma/
│   ├── schema.prisma                 # Модели: Board, Column, Task, Comment, BoardMember
│   └── migrations/                   # Автогенерируется Prisma
├── src/
│   ├── index.js                      # Точка входа: Express app, Swagger, порт 3002
│   ├── config/
│   │   └── swagger.js                # Настройка swagger-jsdoc
│   ├── routes/
│   │   ├── boards.routes.js          # /api/boards/*
│   │   └── tasks.routes.js           # /api/tasks/*
│   ├── controllers/
│   │   ├── boards.controller.js      # Логика для досок и колонок
│   │   └── tasks.controller.js       # Логика для задач и комментариев
│   ├── middleware/
│   │   ├── checkAuth.js              # Валидация JWT (копия из auth-service)
│   │   └── checkRole.js              # RBAC middleware (копия из auth-service)
│   ├── services/
│   │   ├── boards.service.js         # Prisma-запросы для досок
│   │   ├── tasks.service.js          # Prisma-запросы для задач
│   │   ├── stats.service.js          # Расчёт данных для burn-down chart
│   │   └── webhook.service.js        # HTTP-отправка событий в Real-time Service
│   ├── validators/
│   │   ├── board.validator.js        # Joi схемы для Board
│   │   └── task.validator.js         # Joi схемы для Task
│   ├── jobs/
│   │   └── deadline.job.js           # node-cron: напоминания о дедлайнах
│   └── utils/
│       └── errors.js                 # Стандартный формат ошибок
└── init.sql                          # DDL схемы task
```

---

## Dockerfile

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

RUN npx prisma generate

EXPOSE 3002

CMD ["node", "src/index.js"]
```

---

## Переменные окружения

```dotenv
# PostgreSQL
DATABASE_URL=postgresql://postgres:secret@postgres:5432/collab

# JWT (должен совпадать с JWT_SECRET в auth-service)
JWT_SECRET=your-super-secret-jwt-key-min-32-chars

# Real-time Service — URL для отправки webhook-событий
REALTIME_SERVICE_URL=http://realtime:3003

# Общие
NODE_ENV=development
PORT=3002
```

---

## База данных — схема `task`

Task Service использует **схему `task`** внутри общей PostgreSQL базы. Прямые JOIN с таблицами схемы `auth` запрещены — связь только через `user_id` (UUID).

### Prisma schema

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Board {
  id          String        @id @default(uuid()) @db.Uuid
  title       String
  description String?
  ownerId     String        @map("owner_id") @db.Uuid   // UUID из auth.users — без FK
  color       String        @default("#6366f1")
  createdAt   DateTime      @default(now()) @map("created_at")

  columns     Column[]
  tasks       Task[]
  members     BoardMember[]

  @@map("boards")
  @@schema("task")
}

model BoardMember {
  boardId  String @map("board_id") @db.Uuid
  userId   String @map("user_id") @db.Uuid              // UUID из auth.users — без FK
  role     String @default("viewer")                    // admin | editor | viewer

  board    Board  @relation(fields: [boardId], references: [id], onDelete: Cascade)

  @@id([boardId, userId])
  @@map("board_members")
  @@schema("task")
}

model Column {
  id        String   @id @default(uuid()) @db.Uuid
  boardId   String   @map("board_id") @db.Uuid
  title     String
  position  Int      @default(0)
  createdAt DateTime @default(now()) @map("created_at")

  board     Board    @relation(fields: [boardId], references: [id], onDelete: Cascade)
  tasks     Task[]

  @@map("columns")
  @@schema("task")
}

model Task {
  id          String    @id @default(uuid()) @db.Uuid
  columnId    String    @map("column_id") @db.Uuid
  boardId     String    @map("board_id") @db.Uuid
  title       String
  description String?
  assigneeId  String?   @map("assignee_id") @db.Uuid   // UUID из auth.users — без FK
  priority    Priority  @default(medium)
  status      String    @default("todo")
  deadline    DateTime?
  position    Int       @default(0)
  createdAt   DateTime  @default(now()) @map("created_at")

  column      Column    @relation(fields: [columnId], references: [id], onDelete: Cascade)
  board       Board     @relation(fields: [boardId], references: [id], onDelete: Cascade)
  comments    Comment[]

  @@map("tasks")
  @@schema("task")
}

model Comment {
  id        String   @id @default(uuid()) @db.Uuid
  taskId    String   @map("task_id") @db.Uuid
  authorId  String   @map("author_id") @db.Uuid         // UUID из auth.users — без FK
  content   String
  createdAt DateTime @default(now()) @map("created_at")

  task      Task     @relation(fields: [taskId], references: [id], onDelete: Cascade)

  @@map("comments")
  @@schema("task")
}

enum Priority {
  low
  medium
  high
  urgent

  @@schema("task")
}
```

### init.sql (DDL)

```sql
CREATE SCHEMA IF NOT EXISTS task;

CREATE TYPE task.priority_enum AS ENUM ('low', 'medium', 'high', 'urgent');

CREATE TABLE task.boards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id    UUID NOT NULL,
    color       VARCHAR(7) DEFAULT '#6366f1',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE task.board_members (
    board_id  UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL,
    role      VARCHAR(20) NOT NULL DEFAULT 'viewer'
              CHECK (role IN ('admin', 'editor', 'viewer')),
    PRIMARY KEY (board_id, user_id)
);

CREATE TABLE task.columns (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id  UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    title     VARCHAR(255) NOT NULL,
    position  INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE task.tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id   UUID NOT NULL REFERENCES task.columns(id) ON DELETE CASCADE,
    board_id    UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID,
    priority    task.priority_enum NOT NULL DEFAULT 'medium',
    status      VARCHAR(50) NOT NULL DEFAULT 'todo',
    deadline    TIMESTAMPTZ,
    position    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON task.tasks(board_id);
CREATE INDEX ON task.tasks(column_id);
CREATE INDEX ON task.tasks(assignee_id);

CREATE TABLE task.comments (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id   UUID NOT NULL REFERENCES task.tasks(id) ON DELETE CASCADE,
    author_id UUID NOT NULL,
    content   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON task.comments(task_id);
```

---

## API endpoints

Базовый URL: `http://task:3002` (внутри Docker) или `http://localhost/api` (через Nginx).

Все endpoints (кроме Swagger docs) требуют заголовок:
```
Authorization: Bearer <access_token>
```

---

### Boards

#### `GET /api/boards`
Список досок, где пользователь является участником (`board_members.user_id = req.user.sub`).

**Response 200:**
```json
[
  {
    "id": "uuid",
    "title": "My Project",
    "description": "...",
    "color": "#6366f1",
    "role": "editor",
    "createdAt": "2026-01-01T00:00:00Z"
  }
]
```

---

#### `POST /api/boards`
Создать новую доску. Требует роль `editor` или `admin`.

**Body:**
```json
{
  "title": "My Project",
  "description": "Optional description",
  "color": "#6366f1"
}
```
**Response 201:** созданный объект Board. Создатель автоматически добавляется в `board_members` с ролью `admin`.

---

#### `GET /api/boards/:id`
Полные данные доски: колонки и задачи внутри каждой колонки. Доступно только участникам доски.

**Response 200:**
```json
{
  "id": "uuid",
  "title": "My Project",
  "color": "#6366f1",
  "columns": [
    {
      "id": "uuid",
      "title": "To Do",
      "position": 0,
      "tasks": [
        {
          "id": "uuid",
          "title": "Fix login bug",
          "priority": "high",
          "status": "todo",
          "assigneeId": "uuid",
          "deadline": "2026-02-01T00:00:00Z",
          "position": 0
        }
      ]
    }
  ]
}
```

---

#### `DELETE /api/boards/:id`
Удалить доску. Требует роль `admin`.

**Response 204:** No Content

---

#### `POST /api/boards/:id/columns`
Добавить колонку в доску. Требует роль `editor` или `admin`.

**Body:**
```json
{
  "title": "In Progress",
  "position": 1
}
```
**Response 201:** созданный объект Column

---

#### `DELETE /api/boards/:boardId/columns/:columnId`
Удалить колонку (и все задачи в ней через CASCADE). Требует роль `admin`.

**Response 204:** No Content

---

### Tasks

#### `GET /api/tasks`
Список задач с фильтрацией. Возвращает только задачи досок, участником которых является пользователь.

**Query params:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `boardId` | UUID | Фильтр по доске (обязательный или опциональный) |
| `search` | string | Поиск по полю `title` (ILIKE) |
| `status` | string | Фильтр по статусу (`todo`, `in_progress`, `done`) |
| `assignee` | UUID | Фильтр по `assignee_id` |
| `priority` | string | Фильтр по приоритету (`low`, `medium`, `high`, `urgent`) |
| `deadline` | ISO date | Задачи с дедлайном до указанной даты |

**Пример:** `GET /api/tasks?boardId=uuid&status=todo&priority=high`

**Response 200:** массив объектов Task

---

#### `POST /api/tasks`
Создать задачу. Требует роль `editor` или `admin`.

**Body:**
```json
{
  "columnId": "uuid",
  "boardId": "uuid",
  "title": "Fix login bug",
  "description": "Users can't log in with Google",
  "assigneeId": "uuid",
  "priority": "high",
  "deadline": "2026-02-01T00:00:00Z"
}
```
**Response 201:** созданный объект Task

После создания — отправить webhook `task:created` в Real-time Service.

---

#### `PUT /api/tasks/:id`
Обновить поля задачи. Требует роль `editor` или `admin`.

**Body** (все поля опциональны):
```json
{
  "title": "Updated title",
  "description": "...",
  "assigneeId": "uuid",
  "priority": "urgent",
  "status": "in_progress",
  "deadline": "2026-03-01T00:00:00Z"
}
```
**Response 200:** обновлённый объект Task

После обновления — отправить webhook `task:updated` в Real-time Service.

---

#### `PATCH /api/tasks/:id/move`
Переместить задачу в другую колонку (drag-and-drop). Требует роль `editor` или `admin`.

**Body:**
```json
{
  "columnId": "uuid-целевой-колонки",
  "position": 2
}
```
**Response 200:**
```json
{
  "id": "uuid",
  "columnId": "uuid-целевой-колонки",
  "position": 2
}
```

После перемещения — отправить webhook `task:moved` в Real-time Service.

---

#### `DELETE /api/tasks/:id`
Удалить задачу. Требует роль `admin`.

**Response 204:** No Content

После удаления — отправить webhook `task:deleted` в Real-time Service.

---

### Comments

#### `GET /api/tasks/:id/comments`
Список комментариев к задаче, сортировка по `created_at ASC`.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "content": "This is a comment",
    "authorId": "uuid",
    "createdAt": "2026-01-01T12:00:00Z"
  }
]
```

---

#### `POST /api/tasks/:id/comments`
Добавить комментарий к задаче.

**Body:**
```json
{
  "content": "This is a comment"
}
```
**Response 201:** созданный объект Comment

После создания — отправить webhook `comment:added` в Real-time Service.

---

#### `DELETE /api/tasks/:taskId/comments/:commentId`
Удалить комментарий. Доступно автору комментария или `admin`.

**Response 204:** No Content

---

### Stats (Burn-down Chart)

#### `GET /api/boards/:id/stats`
Аналитические данные для построения burn-down chart на Frontend.

**Response 200:**
```json
{
  "boardId": "uuid",
  "totalTasks": 24,
  "completedTasks": 10,
  "tasksByStatus": {
    "todo": 8,
    "in_progress": 6,
    "done": 10
  },
  "tasksByPriority": {
    "low": 4,
    "medium": 10,
    "high": 7,
    "urgent": 3
  },
  "burndown": [
    { "date": "2026-01-01", "remaining": 24 },
    { "date": "2026-01-02", "remaining": 22 },
    { "date": "2026-01-03", "remaining": 19 }
  ]
}
```

---

### Swagger Docs

#### `GET /api/docs`
Swagger UI — интерактивная документация всех endpoints.
Доступна без авторизации. Используется Frontend разработчиком как контракт.

---

### Формат ошибок

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Board not found",
    "details": {}
  }
}
```

| Код ошибки | HTTP статус | Описание |
|-----------|-------------|----------|
| `VALIDATION_ERROR` | 400 | Неверный формат входных данных (Joi) |
| `UNAUTHORIZED` | 401 | Токен отсутствует или невалиден |
| `FORBIDDEN` | 403 | Нет прав доступа к ресурсу или роль недостаточна |
| `NOT_FOUND` | 404 | Ресурс не найден |
| `CONFLICT` | 409 | Конфликт данных |
| `INTERNAL_ERROR` | 500 | Внутренняя ошибка сервера |

---

## Webhook — отправка событий в Real-time Service

После **каждого** успешного CRUD-действия Task Service отправляет HTTP POST на внутренний endpoint Real-time Service. Frontend не участвует — он получает событие через WebSocket от Real-time Service.

**Endpoint:** `POST http://realtime:3003/internal/events`
**Авторизация:** не требуется (только внутренняя Docker-сеть)

### Реализация `webhook.service.js`

```js
const axios = require('axios')

const REALTIME_URL = process.env.REALTIME_SERVICE_URL // http://realtime:3003

async function sendWebhook(event, boardId, payload) {
  try {
    await axios.post(`${REALTIME_URL}/internal/events`, {
      event,
      boardId,
      payload,
    })
  } catch (err) {
    // Не бросаем ошибку — webhook не должен ломать основной запрос
    console.error(`[webhook] Failed to send ${event}:`, err.message)
  }
}

module.exports = { sendWebhook }
```

### Таблица событий

| Событие | Когда отправлять | Payload |
|---------|-----------------|---------|
| `task:created` | `POST /api/tasks` — успешный 201 | `{ task, boardId, userId }` |
| `task:updated` | `PUT /api/tasks/:id` — успешный 200 | `{ taskId, changes, userId }` |
| `task:moved` | `PATCH /api/tasks/:id/move` — успешный 200 | `{ taskId, fromCol, toCol, position, userId }` |
| `task:deleted` | `DELETE /api/tasks/:id` — успешный 204 | `{ taskId, boardId }` |
| `comment:added` | `POST /api/tasks/:id/comments` — успешный 201 | `{ taskId, comment, userId }` |

### Пример вызова в контроллере

```js
// tasks.controller.js
const { sendWebhook } = require('../services/webhook.service')

async function moveTask(req, res) {
  const { id } = req.params
  const { columnId, position } = req.body
  const userId = req.user.sub

  const task = await tasksService.moveTask(id, columnId, position)

  // Сначала ответить клиенту, потом отправить webhook
  res.json(task)

  await sendWebhook('task:moved', task.boardId, {
    taskId: id,
    fromCol: task.previousColumnId,
    toCol: columnId,
    position,
    userId,
  })
}
```

---

## Валидация данных (Joi)

```js
// src/validators/task.validator.js
const Joi = require('joi')

const createTaskSchema = Joi.object({
  columnId:    Joi.string().uuid().required(),
  boardId:     Joi.string().uuid().required(),
  title:       Joi.string().min(1).max(255).required(),
  description: Joi.string().max(5000).optional().allow(''),
  assigneeId:  Joi.string().uuid().optional(),
  priority:    Joi.string().valid('low', 'medium', 'high', 'urgent').default('medium'),
  deadline:    Joi.date().iso().optional(),
})

const updateTaskSchema = Joi.object({
  title:       Joi.string().min(1).max(255),
  description: Joi.string().max(5000).allow(''),
  assigneeId:  Joi.string().uuid().allow(null),
  priority:    Joi.string().valid('low', 'medium', 'high', 'urgent'),
  status:      Joi.string().valid('todo', 'in_progress', 'done'),
  deadline:    Joi.date().iso().allow(null),
}).min(1) // хотя бы одно поле

const moveTaskSchema = Joi.object({
  columnId: Joi.string().uuid().required(),
  position: Joi.number().integer().min(0).required(),
})

module.exports = { createTaskSchema, updateTaskSchema, moveTaskSchema }
```

---

## Аутентификация и авторизация

Task Service **самостоятельно валидирует JWT** — без запросов к Auth Service.

```js
// src/middleware/checkAuth.js
const jwt = require('jsonwebtoken')

function checkAuth(req, res, next) {
  const authHeader = req.headers.authorization
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({
      error: { code: 'UNAUTHORIZED', message: 'Authorization header missing' }
    })
  }

  const token = authHeader.split(' ')[1]

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET)
    req.user = payload  // { sub, role, email, jti, iat, exp }
    next()
  } catch (err) {
    return res.status(401).json({
      error: { code: 'UNAUTHORIZED', message: 'Token is invalid or expired' }
    })
  }
}

module.exports = { checkAuth }
```

**Важно:** Task Service не проверяет Redis blacklist — это зона ответственности Auth Service. При `logout` старые токены технически валидны до истечения TTL (1 час). Для критичных операций можно добавить проверку blacklist.

---

## Swagger / OpenAPI документация

```js
// src/config/swagger.js
const swaggerJsdoc = require('swagger-jsdoc')

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Task Service API',
      version: '1.0.0',
      description: 'REST API для управления досками, задачами и комментариями',
    },
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        }
      }
    },
    security: [{ bearerAuth: [] }],
  },
  apis: ['./src/routes/*.js'],  // JSDoc аннотации в файлах роутов
}

module.exports = swaggerJsdoc(options)
```

Swagger UI доступен на `GET /api/docs` — является **официальным контрактом** для Frontend разработчика.

---

## Тестирование

```
task-service/
└── src/
    └── __tests__/
        ├── boards.test.js     # Integration тесты для /api/boards
        ├── tasks.test.js      # Integration тесты для /api/tasks
        └── stats.test.js      # Unit тесты для stats.service.js
```

```bash
# Запуск тестов
npm test

# С отчётом покрытия (цель: > 70%)
npm run test:coverage
```

**Stack:** Jest + Supertest. Тесты используют отдельную тестовую БД или мокируют Prisma Client.

---

## Зависимости (npm)

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "@prisma/client": "^5.0.0",
    "jsonwebtoken": "^9.0.0",
    "joi": "^17.9.0",
    "axios": "^1.6.0",
    "swagger-jsdoc": "^6.2.0",
    "swagger-ui-express": "^5.0.0",
    "node-cron": "^3.0.0",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "dotenv": "^16.0.0"
  },
  "devDependencies": {
    "prisma": "^5.0.0",
    "jest": "^29.0.0",
    "supertest": "^6.3.0",
    "nodemon": "^3.0.0"
  }
}
```

---

## Взаимодействие с другими сервисами

```
                    ┌─────────────────────────────┐
                    │        TASK SERVICE          │
                    │          порт 3002           │
                    └──────┬──────────────┬────────┘
                           │              │
          Валидирует JWT    │              │  HTTP POST webhook
          самостоятельно   │              │  /internal/events
          (JWT_SECRET)      │              │
                           ▼              ▼
              ┌──────────────────┐   ┌────────────────────┐
              │   Auth Service   │   │  Realtime Service  │
              │   (не вызывает)  │   │     порт 3003      │
              └──────────────────┘   └────────────────────┘
                           ▲
                           │  REST API: /api/*
                           │  Authorization: Bearer <token>
                    ┌──────┴──────────────────────┐
                    │         FRONTEND             │
                    │  GET /api/boards             │
                    │  POST /api/tasks             │
                    │  PATCH /api/tasks/:id/move   │
                    └─────────────────────────────┘
```

**Task Service НЕ обращается к Auth Service в рантайме.**
JWT валидируется локально через `JWT_SECRET`.

**Task Service ВСЕГДА уведомляет Real-time Service** через webhook после успешного изменения данных. Если Real-time Service недоступен — ошибка логируется, основной запрос завершается успешно.

---

*Task Service | Real-Time Collaborative Dashboard | 2026*

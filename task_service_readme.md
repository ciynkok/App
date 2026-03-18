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
├── requirements.txt
├── .env                              # не в git
├── src/
│   ├── main.py                       # Точка входа: FastAPI app, Swagger, порт 3002
│   ├── config/
│   │   ├── database.py               # SQLAlchemy подключение
│   │   └── swagger.py                # Настройка OpenAPI
│   ├── routes/
│   │   ├── boards.py                 # /api/boards/*
│   │   └── tasks.py                  # /api/tasks/*
│   ├── middleware/
│   │   └── auth.py                   # JWT валидация и RBAC
│   ├── services/
│   │   ├── boards.py                 # SQLAlchemy запросы для досок
│   │   ├── tasks.py                  # SQLAlchemy запросы для задач
│   │   ├── stats.py                  # Расчёт данных для burn-down chart
│   │   └── webhook.py                # HTTP-отправка событий в Real-time Service
│   ├── schemas/
│   │   ├── board.py                  # Pydantic схемы для Board
│   │   └── task.py                   # Pydantic схемы для Task
│   ├── models/
│   │   └── task.py                   # SQLAlchemy модели: Board, Column, Task, Comment, BoardMember
│   └── jobs/
│       └── deadline.py               # APScheduler: напоминания о дедлайнах
└── alembic/                          # Миграции БД
    ├── env.py
    └── versions/
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Миграции БД выполняются при старте контейнера
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3002"]
```

> Миграции Alembic можно запускать через entrypoint-скрипт или вручную:
> `docker compose exec task alembic upgrade head`

---

## Переменные окружения

```dotenv
# PostgreSQL
DATABASE_URL=postgresql://postgres:secret@postgres:5432/collab

# JWT (должен совпадать с JWT_SECRET_KEY в auth-service)
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars

# Real-time Service — URL для отправки webhook-событий
REALTIME_SERVICE_URL=http://realtime:3003

# Общие
NODE_ENV=development
PORT=3002
```

---

## База данных — схема `task`

Task Service использует **схему `task`** внутри общей PostgreSQL базы. Прямые JOIN с таблицами схемы `auth` запрещены — связь только через `user_id` (UUID).

### SQLAlchemy модели

```python
# src/models/task.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()

class Priority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class Board(Base):
    __tablename__ = "boards"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)  # UUID из auth.users — без FK
    color = Column(String(7), default="#6366f1")
    created_at = Column(DateTime, default=func.now())

    columns = relationship("Column", back_populates="board", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="board", cascade="all, delete-orphan")
    members = relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")

class BoardMember(Base):
    __tablename__ = "board_members"
    __table_args__ = (
        PrimaryKeyConstraint("board_id", "user_id"),
        {"schema": "task"}
    )

    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # UUID из auth.users — без FK
    role = Column(String(20), default="viewer")  # admin | editor | viewer

    board = relationship("Board", back_populates="members")

class Column(Base):
    __tablename__ = "columns"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    column_id = Column(UUID(as_uuid=True), ForeignKey("task.columns.id", ondelete="CASCADE"), nullable=False)
    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(UUID(as_uuid=True), nullable=True)  # UUID из auth.users — без FK
    priority = Column(Enum(Priority), default=Priority.medium)
    status = Column(String(50), default="todo")
    deadline = Column(DateTime, nullable=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    column = relationship("Column", back_populates="tasks")
    board = relationship("Board", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    task_id = Column(UUID(as_uuid=True), ForeignKey("task.tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False)  # UUID из auth.users — без FK
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    task = relationship("Task", back_populates="comments")
```
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

## Валидация данных (Pydantic)

```python
# src/schemas/task.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

class TaskCreate(BaseModel):
    column_id: UUID
    board_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    assignee_id: Optional[UUID] = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    deadline: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    assignee_id: Optional[UUID] = None
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = None
    status: Optional[Literal["todo", "in_progress", "done"]] = None
    deadline: Optional[datetime] = None

class TaskMove(BaseModel):
    column_id: UUID
    position: int = Field(..., ge=0)

class BoardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")

class ColumnCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    position: int = Field(default=0, ge=0)
```

---

## Аутентификация и авторизация

Task Service **валидирует JWT через Auth Service** — делает HTTP-запрос на endpoint `/auth/verify` для каждого запроса.

```python
# src/middleware.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from src.config import settings

security = HTTPBearer()

async def verify_jwt_with_auth_service(token: str) -> dict:
    """
    Проверка JWT токена через Auth Service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.auth_service_url}{settings.auth_service_verify_endpoint}",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == status.HTTP_200_OK:
                return response.json()
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Auth service unavailable"}}
                )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Failed to connect to Auth Service"}}
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    user_info = await verify_jwt_with_auth_service(token)

    if not user_info or "user_id" not in user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid token payload"}}
        )

    return user_info
```

**Преимущества централизованной валидации:**
- ✅ Auth Service проверяет **Redis blacklist** — токены отозванные при logout сразу становятся невалидными
- ✅ Централизованное управление сессиями
- ✅ Единая точка для обновления алгоритмов валидации

**Недостатки:**
- ⚠️ Дополнительный сетевой вызов на каждый запрос (небольшая задержка)
- ⚠️ Нагрузка на Auth Service

---

## Swagger / OpenAPI документация

FastAPI автоматически генерирует OpenAPI документацию и Swagger UI.

```python
# src/main.py
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    title="Task Service API",
    description="REST API для управления досками, задачами и комментариями",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)

# Все роутеры автоматически включаются в документацию
# благодаря аннотациям Pydantic и FastAPI Depends
```

Swagger UI доступен на `GET /api/docs` — является **официальным контрактом** для Frontend разработчика.

---

## Тестирование

```
task-service/
└── tests/
    ├── test_boards.py         # Integration тесты для /api/boards
    ├── test_tasks.py          # Integration тесты для /api/tasks
    └── test_stats.py          # Unit тесты для stats.py
```

```bash
# Запуск тестов
pytest

# С отчётом покрытия (цель: > 70%)
pytest --cov=src --cov-report=html
```

**Stack:** pytest + httpx. Тесты используют отдельную тестовую БД или мокируют SQLAlchemy сессии.

---

## Зависимости (requirements.txt)

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.26.0
aioredis==2.0.1
apscheduler==3.10.4
python-multipart==0.0.6
```

---

## Взаимодействие с другими сервисами

```
                    ┌─────────────────────────────┐
                    │        TASK SERVICE          │
                    │          порт 3002           │
                    └──────┬──────────────┬────────┘
                           │              │
          HTTP POST        │              │  HTTP POST webhook
          /auth/verify     │              │  /internal/events
          (валидация JWT)  │              │
                           ▼              ▼
              ┌──────────────────┐   ┌────────────────────┐
              │   Auth Service   │   │  Realtime Service  │
              │   порт 3001      │   │     порт 3003      │
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

**Task Service обращается к Auth Service для валидации JWT:**
- Каждый запрос с JWT проверяется через `POST /auth/verify`
- Auth Service проверяет токен и Redis blacklist
- При logout токены сразу становятся невалидными

**Task Service ВСЕГДА уведомляет Real-time Service** через webhook после успешного изменения данных. Если Real-time Service недоступен — ошибка логируется, основной запрос завершается успешно.

---

*Task Service | Real-Time Collaborative Dashboard | 2026*

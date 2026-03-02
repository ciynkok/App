# Realtime Service

Сервис real-time коммуникации. Управляет WebSocket-соединениями через FastAPI WebSocket, транслирует события между участниками досок, хранит историю чата и присутствие пользователей в Redis. Принимает HTTP webhook от Task Service и рассылает события всем подключённым клиентам нужной доски.

---

## Содержание

1. [Обязанности сервиса](#обязанности-сервиса)
2. [Структура директорий](#структура-директорий)
3. [Dockerfile](#dockerfile)
4. [Переменные окружения](#переменные-окружения)
5. [Redis — ключи и паттерны](#redis--ключи-и-паттерны)
6. [Socket.io — комнаты и подключение](#socketio--комнаты-и-подключение)
7. [WebSocket события](#websocket-события)
8. [Internal HTTP API — приём webhook от Task Service](#internal-http-api--приём-webhook-от-task-service)
9. [Аутентификация WebSocket соединений](#аутентификация-websocket-соединений)
10. [Redis Pub/Sub — горизонтальное масштабирование](#redis-pubsub--горизонтальное-масштабирование)
11. [Встроенный чат](#встроенный-чат)
12. [Presence — индикаторы присутствия](#presence--индикаторы-присутствия)
13. [Оптимистичная блокировка задач](#оптимистичная-блокировка-задач)
14. [Зависимости (npm)](#зависимости-npm)
15. [Взаимодействие с другими сервисами](#взаимодействие-с-другими-сервисами)

---

## Обязанности сервиса

- Принимать WebSocket-соединения от Frontend клиентов
- Аутентифицировать подключения по JWT (без запросов к Auth Service)
- Организовывать клиентов в **комнаты по `boardId`** (WebSocket rooms)
- Принимать HTTP webhook от Task Service и **транслировать события** всем клиентам комнаты
- Обеспечивать **встроенный чат** — хранение истории в Redis, рассылка сообщений
- Отслеживать **присутствие пользователей** на доске (online/offline)
- Поддерживать **оптимистичную блокировку задач** (кто сейчас редактирует)
- Синхронизировать несколько инстанций сервиса через **Redis Pub/Sub**

**Порт:** `3003`
**Внутренний хост в Docker-сети:** `realtime`

---

## Структура директорий

```
realtime-service/
├── Dockerfile
├── requirements.txt
├── .env                                  # не в git
└── src/
    ├── main.py                           # Точка входа: FastAPI + WebSocket, порт 3003
    ├── config/
    │   └── redis.py                      # Redis подключение
    ├── middleware/
    │   └── ws_auth.py                    # JWT-аутентификация WebSocket
    ├── handlers/
    │   ├── websocket.py                  # Обработка WebSocket подключений
    │   ├── board.py                      # join:board, leave:board
    │   ├── chat.py                       # chat:message — приём и рассылка
    │   └── task.py                       # Обработка task:* событий
    ├── services/
    │   ├── chat.py                       # Сохранение/получение истории чата из Redis
    │   ├── presence.py                   # Управление online-статусом в Redis Sets
    │   ├── lock.py                       # Оптимистичная блокировка задач в Redis
    │   └── pubsub.py                     # Redis Pub/Sub: publish + subscribe
    └── routes/
        └── internal.py                   # POST /internal/events — webhook от Task Service
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

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3003"]
```

---

## Переменные окружения

```dotenv
# Redis
REDIS_URL=redis://redis:6379

# JWT (должен совпадать с JWT_SECRET в auth-service и task-service)
JWT_SECRET=your-super-secret-jwt-key-min-32-chars

# Общие
NODE_ENV=development
PORT=3003

# Настройки чата
CHAT_HISTORY_TTL=86400       # TTL истории чата в секундах (24 часа)
CHAT_HISTORY_MAX_MESSAGES=100  # Максимум сообщений в истории доски

# Настройки блокировки
TASK_LOCK_TTL=30             # TTL блокировки задачи в секундах
```

---

## Redis — ключи и паттерны

Realtime Service использует **префикс `rt:`** для всех ключей.

| Ключ | Тип Redis | TTL | Описание |
|------|-----------|-----|----------|
| `rt:chat:{boardId}` | List | 24 часа | История сообщений чата. Каждый элемент — JSON строка сообщения |
| `rt:online:{boardId}` | Set | — | Множество `userId` активных участников доски |
| `rt:board:{boardId}:lock:{taskId}` | String | 30 сек | Кто сейчас редактирует задачу. Значение: `userId` |
| `rt:pubsub:board:{boardId}` | Channel | — | Pub/Sub канал для синхронизации нескольких инстанций |

```js
// Примеры операций с Redis

// Добавить сообщение в историю чата
await redis.lpush(`rt:chat:${boardId}`, JSON.stringify(message))
await redis.expire(`rt:chat:${boardId}`, CHAT_HISTORY_TTL)
// Обрезать список до MAX сообщений
await redis.ltrim(`rt:chat:${boardId}`, 0, CHAT_HISTORY_MAX_MESSAGES - 1)

// Получить историю чата (последние N сообщений, от новых к старым)
const messages = await redis.lrange(`rt:chat:${boardId}`, 0, 49)

// Добавить пользователя в online Set
await redis.sadd(`rt:online:${boardId}`, userId)

// Удалить пользователя из online Set
await redis.srem(`rt:online:${boardId}`, userId)

// Получить всех online пользователей
const onlineUsers = await redis.smembers(`rt:online:${boardId}`)

// Установить блокировку задачи (NX — только если не занято)
const locked = await redis.set(
  `rt:board:${boardId}:lock:${taskId}`,
  userId,
  'EX', TASK_LOCK_TTL,
  'NX'
)

// Снять блокировку
await redis.del(`rt:board:${boardId}:lock:${taskId}`)
```

---

## WebSocket — подключение

Каждая доска — отдельная **комната** с именем `board:{boardId}`. Это позволяет транслировать события только участникам конкретной доски.

### Точка входа `src/main.py`

```python
# src/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
import jwt
from redis import asyncio as aioredis

from .handlers import websocket, board, chat, task
from .routes import internal
from .config import redis, settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение HTTP роутов
app.include_router(internal.router, prefix="/internal")

# Хранилище активных подключений по комнатам
connection_manager = websocket.ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.accept(websocket)
    
    # JWT-аутентификация при подключении
    try:
        token = websocket.query_params.get("token")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        websocket.user = {
            "id": payload["sub"],
            "role": payload["role"],
            "email": payload["email"],
        }
    except (jwt.JWTError, KeyError):
        await websocket.close(code=4001)
        return
    
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            payload = data.get("payload", {})
            
            # Маршрутизация событий
            if event_type == "join:board":
                await board.handle_join(websocket, payload, connection_manager)
            elif event_type == "leave:board":
                await board.handle_leave(websocket, payload, connection_manager)
            elif event_type == "chat:message":
                await chat.handle_message(websocket, payload, connection_manager)
            elif event_type == "task:lock":
                await task.handle_lock(websocket, payload, connection_manager)
            elif event_type == "task:unlock":
                await task.handle_unlock(websocket, payload, connection_manager)
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
```

---

## WebSocket события

### Клиент → Сервер (emit от Frontend)

| Событие | Payload | Описание |
|---------|---------|----------|
| `join:board` | `{ boardId: string }` | Войти в комнату доски. Сервер добавляет socket в room `board:{boardId}` и userId в Redis Set |
| `leave:board` | `{ boardId: string }` | Покинуть комнату. Сервер удаляет из room и Redis Set |
| `chat:message` | `{ boardId: string, text: string }` | Отправить сообщение в чат доски |
| `task:lock` | `{ boardId: string, taskId: string }` | Заблокировать задачу для редактирования |
| `task:unlock` | `{ boardId: string, taskId: string }` | Снять блокировку задачи |

### Сервер → Клиент (broadcast в комнату `board:{boardId}`)

| Событие | Payload | Источник | Описание |
|---------|---------|---------|----------|
| `task:created` | `{ task, boardId, userId }` | Task Service webhook | Новая задача добавлена на доску |
| `task:updated` | `{ taskId, changes, userId }` | Task Service webhook | Задача обновлена |
| `task:moved` | `{ taskId, fromCol, toCol, position, userId }` | Task Service webhook | Задача перемещена в другую колонку |
| `task:deleted` | `{ taskId, boardId }` | Task Service webhook | Задача удалена |
| `comment:added` | `{ taskId, comment, userId }` | Task Service webhook | Добавлен комментарий |
| `user:joined` | `{ userId, boardId, name }` | Realtime Service | Пользователь открыл доску |
| `user:left` | `{ userId, boardId }` | Realtime Service | Пользователь покинул доску |
| `user:online` | `{ boardId, users: string[] }` | Realtime Service | Список онлайн-пользователей при входе |
| `chat:message` | `{ from, text, boardId, ts }` | Realtime Service | Сообщение в чате |
| `chat:history` | `{ boardId, messages: [] }` | Realtime Service | История чата при входе на доску |
| `task:locked` | `{ taskId, boardId, userId }` | Realtime Service | Задача заблокирована кем-то |
| `task:unlocked` | `{ taskId, boardId }` | Realtime Service | Задача разблокирована |

---

## Internal HTTP API — приём webhook от Task Service

Task Service отправляет HTTP POST на `/internal/events`. Этот endpoint **не требует JWT** — доступен только внутри Docker-сети.

### `POST /internal/events`

**Body:**
```json
{
  "event": "task:moved",
  "boardId": "uuid",
  "payload": {
    "taskId": "uuid",
    "fromCol": "uuid",
    "toCol": "uuid",
    "position": 2,
    "userId": "uuid"
  }
}
```

**Response 200:**
```json
{ "ok": true }
```

### Реализация `src/routes/internal.routes.js`

```js
const { Router } = require('express')
const router = Router()

// Список допустимых событий
const ALLOWED_EVENTS = [
  'task:created',
  'task:updated',
  'task:moved',
  'task:deleted',
  'comment:added',
]

router.post('/events', (req, res) => {
  const { event, boardId, payload } = req.body

  if (!event || !boardId || !payload) {
    return res.status(400).json({ error: 'Missing required fields' })
  }

  if (!ALLOWED_EVENTS.includes(event)) {
    return res.status(400).json({ error: `Unknown event: ${event}` })
  }

  // Получить Socket.io инстанцию из Express app
  const io = req.app.get('io')

  // Broadcast в комнату доски
  io.to(`board:${boardId}`).emit(event, payload)

  res.json({ ok: true })
})

module.exports = router
```

---

## Аутентификация WebSocket соединений

JWT передаётся при подключении через `auth` объект Socket.io (не через заголовки — WebSocket не поддерживает кастомные заголовки).

### Frontend — подключение с токеном

```js
// На клиенте (Frontend)
import { io } from 'socket.io-client'

const socket = io('ws://localhost/ws', {
  auth: {
    token: localStorage.getItem('accessToken')  // или из cookie
  }
})
```

### `src/middleware/socketAuth.js`

```js
const jwt = require('jsonwebtoken')

function socketAuth(socket, next) {
  const token = socket.handshake.auth?.token

  if (!token) {
    return next(new Error('UNAUTHORIZED: Token missing'))
  }

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET)
    // Прикрепить данные пользователя к socket — доступны в handlers
    socket.user = {
      id: payload.sub,
      role: payload.role,
      email: payload.email,
    }
    next()
  } catch (err) {
    next(new Error('UNAUTHORIZED: Token invalid or expired'))
  }
}

module.exports = { socketAuth }
```

---

## Redis Pub/Sub — горизонтальное масштабирование

При запуске нескольких инстанций Realtime Service каждая инстанция имеет своих подключённых клиентов. Без синхронизации событие, пришедшее в одну инстанцию через webhook, не попадёт к клиентам другой. Pub/Sub решает эту проблему.

```
Task Service
     │ POST /internal/events
     ▼
Realtime Instance 1        Realtime Instance 2
  └─ PUBLISH rt:pubsub:board:{boardId}  ──→  SUBSCRIBE rt:pubsub:board:{boardId}
  └─ emit to own clients                     └─ emit to own clients
```

### `src/services/pubsub.service.js`

```js
const Redis = require('ioredis')

// Два отдельных клиента: subscriber не может выполнять обычные команды
const publisher  = new Redis(process.env.REDIS_URL)
const subscriber = new Redis(process.env.REDIS_URL)

const CHANNEL_PREFIX = 'rt:pubsub:board:'

// Публикация события в канал доски
async function publishBoardEvent(boardId, event, payload) {
  const channel = `${CHANNEL_PREFIX}${boardId}`
  await publisher.publish(channel, JSON.stringify({ event, payload }))
}

// Подписка — вызывается при старте сервиса
function subscribeToBoardEvents(io) {
  subscriber.psubscribe(`${CHANNEL_PREFIX}*`)  // подписка на все каналы досок

  subscriber.on('pmessage', (pattern, channel, message) => {
    const boardId = channel.replace(CHANNEL_PREFIX, '')
    const { event, payload } = JSON.parse(message)

    // Broadcast клиентам этой инстанции
    io.to(`board:${boardId}`).emit(event, payload)
  })
}

module.exports = { publishBoardEvent, subscribeToBoardEvents }
```

> В текущей конфигурации `docker-compose.yml` запускается **одна инстанция** Realtime Service, поэтому Pub/Sub используется опционально. Реализация закладывается для масштабируемости.

---

## Встроенный чат

Чат реализован поверх WebSocket-комнат. История хранится в Redis List с TTL 24 часа.

### `src/handlers/chat.handler.js`

```js
const { saveChatMessage, getChatHistory } = require('../services/chat.service')
const { publishBoardEvent } = require('../services/pubsub.service')

function registerChatHandler(io, socket) {
  socket.on('chat:message', async ({ boardId, text }) => {
    if (!boardId || !text?.trim()) return

    const message = {
      from: socket.user.id,
      name: socket.user.email,
      text: text.trim(),
      boardId,
      ts: new Date().toISOString(),
    }

    // Сохранить в Redis
    await saveChatMessage(boardId, message)

    // Broadcast всем в комнате (включая отправителя)
    io.to(`board:${boardId}`).emit('chat:message', message)

    // Синхронизация с другими инстанциями (Pub/Sub)
    await publishBoardEvent(boardId, 'chat:message', message)
  })
}

module.exports = { registerChatHandler }
```

### `src/services/chat.service.js`

```js
const redis = require('../config/redis').client
const MAX_MESSAGES = parseInt(process.env.CHAT_HISTORY_MAX_MESSAGES) || 100
const CHAT_TTL    = parseInt(process.env.CHAT_HISTORY_TTL) || 86400

async function saveChatMessage(boardId, message) {
  const key = `rt:chat:${boardId}`
  await redis.lpush(key, JSON.stringify(message))
  await redis.ltrim(key, 0, MAX_MESSAGES - 1)
  await redis.expire(key, CHAT_TTL)
}

async function getChatHistory(boardId, limit = 50) {
  const key = `rt:chat:${boardId}`
  const messages = await redis.lrange(key, 0, limit - 1)
  return messages.map(JSON.parse).reverse()  // от старых к новым
}

module.exports = { saveChatMessage, getChatHistory }
```

---

## Presence — индикаторы присутствия

Отслеживание кто сейчас находится на доске. Используется Frontend для отображения аватаров участников.

### `src/handlers/board.handler.js`

```js
const { addUserToBoard, removeUserFromBoard, getOnlineUsers } = require('../services/presence.service')
const { registerChatHandler } = require('./chat.handler')

function registerBoardHandler(io, socket) {
  socket.on('join:board', async ({ boardId }) => {
    // Войти в Socket.io комнату
    socket.join(`board:${boardId}`)
    socket.currentBoardId = boardId

    // Добавить в Redis Set online-пользователей
    await addUserToBoard(boardId, socket.user.id)

    // Отправить историю чата только подключившемуся клиенту
    const { getChatHistory } = require('../services/chat.service')
    const history = await getChatHistory(boardId)
    socket.emit('chat:history', { boardId, messages: history })

    // Отправить список online-пользователей только подключившемуся
    const onlineUsers = await getOnlineUsers(boardId)
    socket.emit('user:online', { boardId, users: onlineUsers })

    // Уведомить остальных о новом участнике
    socket.to(`board:${boardId}`).emit('user:joined', {
      userId: socket.user.id,
      boardId,
      name: socket.user.email,
    })
  })

  socket.on('leave:board', async ({ boardId }) => {
    socket.leave(`board:${boardId}`)
    await removeUserFromBoard(boardId, socket.user.id)

    io.to(`board:${boardId}`).emit('user:left', {
      userId: socket.user.id,
      boardId,
    })
  })

  // Регистрация обработчика чата
  registerChatHandler(io, socket)
}

module.exports = { registerBoardHandler }
```

### `src/services/presence.service.js`

```js
const redis = require('../config/redis').client

async function addUserToBoard(boardId, userId) {
  await redis.sadd(`rt:online:${boardId}`, userId)
}

async function removeUserFromBoard(boardId, userId) {
  await redis.srem(`rt:online:${boardId}`, userId)
}

async function getOnlineUsers(boardId) {
  return redis.smembers(`rt:online:${boardId}`)
}

module.exports = { addUserToBoard, removeUserFromBoard, getOnlineUsers }
```

---

## Оптимистичная блокировка задач

Позволяет показывать другим пользователям, что задача в данный момент редактируется. Блокировка автоматически снимается через TTL (30 сек).

### `src/services/lock.service.js`

```js
const redis = require('../config/redis').client
const LOCK_TTL = parseInt(process.env.TASK_LOCK_TTL) || 30

// Установить блокировку (NX — только если ключ не существует)
async function lockTask(boardId, taskId, userId) {
  const key = `rt:board:${boardId}:lock:${taskId}`
  const result = await redis.set(key, userId, 'EX', LOCK_TTL, 'NX')
  return result === 'OK'  // true — блокировка получена, false — уже заблокировано
}

// Снять блокировку (только владелец блокировки может снять)
async function unlockTask(boardId, taskId, userId) {
  const key = `rt:board:${boardId}:lock:${taskId}`
  const owner = await redis.get(key)
  if (owner === userId) {
    await redis.del(key)
    return true
  }
  return false
}

// Получить текущего владельца блокировки
async function getLockOwner(boardId, taskId) {
  return redis.get(`rt:board:${boardId}:lock:${taskId}`)
}

module.exports = { lockTask, unlockTask, getLockOwner }
```

### Обработчик в `src/handlers/task.handler.js`

```js
const { lockTask, unlockTask } = require('../services/lock.service')

function registerTaskHandler(io, socket) {
  socket.on('task:lock', async ({ boardId, taskId }) => {
    const acquired = await lockTask(boardId, taskId, socket.user.id)
    if (acquired) {
      io.to(`board:${boardId}`).emit('task:locked', {
        taskId, boardId, userId: socket.user.id
      })
    }
  })

  socket.on('task:unlock', async ({ boardId, taskId }) => {
    const released = await unlockTask(boardId, taskId, socket.user.id)
    if (released) {
      io.to(`board:${boardId}`).emit('task:unlocked', { taskId, boardId })
    }
  })
}

module.exports = { registerTaskHandler }
```

---

## Зависимости (requirements.txt)

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
python-jose[cryptography]==3.3.0
aioredis==2.0.1
httpx==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
```

---

## Взаимодействие с другими сервисами

```
┌──────────────────────────────────────────────────────────┐
│                    REALTIME SERVICE                      │
│                       порт 3003                          │
└──────┬───────────────────┬──────────────────┬────────────┘
       │                   │                  │
       │ JWT валидация      │ HTTP POST        │ WebSocket
       │ (самостоятельно,   │ /internal/events │ emit/broadcast
       │  JWT_SECRET)       │                  │
       │                   │                  │
       ▼                   ▼                  ▼
┌────────────┐   ┌──────────────────┐   ┌────────────────────┐
│Auth Service│   │  Task Service    │   │     Frontend       │
│(не вызывает│   │  (отправляет     │   │  WebSocket         │
│ в рантайме)│   │  webhooks при    │   │  join:board        │
└────────────┘   │  CRUD событиях)  │   │  chat:message      │
                 └──────────────────┘   │  task:lock / unlock│
                                        └────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Redis 7    │
                    │             │
                    │ rt:chat:*   │
                    │ rt:online:* │
                    │ rt:board:*  │
                    │ rt:pubsub:* │
                    └─────────────┘
```

**Realtime Service НЕ обращается к Auth Service и Task Service** — он только принимает входящие соединения и события.

**Единственный входящий HTTP вызов** — от Task Service на `POST /internal/events`. Все остальные взаимодействия — через WebSocket от Frontend.

---

*Realtime Service | Real-Time Collaborative Dashboard | 2026*

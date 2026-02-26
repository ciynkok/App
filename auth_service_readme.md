# Auth Service

Сервис аутентификации и авторизации. Отвечает за регистрацию, логин, OAuth2, выдачу JWT-токенов и управление ролями пользователей.

---

## Содержание

1. [Обязанности сервиса](#обязанности-сервиса)
2. [Структура директорий](#структура-директорий)
3. [Dockerfile](#dockerfile)
4. [Переменные окружения](#переменные-окружения)
5. [База данных — схема `auth`](#база-данных--схема-auth)
6. [Redis — ключи](#redis--ключи)
7. [API endpoints](#api-endpoints)
8. [JWT — формат токена](#jwt--формат-токена)
9. [RBAC — система ролей](#rbac--система-ролей)
10. [OAuth2 — Google и GitHub](#oauth2--google-и-github)
11. [Зависимости (npm)](#зависимости-npm)
12. [Взаимодействие с другими сервисами](#взаимодействие-с-другими-сервисами)

---

## Обязанности сервиса

- Регистрация и логин пользователей (email + password)
- OAuth2 через Google и GitHub (Passport.js)
- Выдача `access_token` (JWT, TTL: 1h) и `refresh_token` (TTL: 30d)
- Валидация и инвалидация токенов (Redis blacklist)
- Хранение и управление ролями: `admin`, `editor`, `viewer`
- Middleware `checkRole()` — используется как npm-пакет или копируется в другие сервисы

**Порт:** `3001`
**Внутренний хост в Docker-сети:** `auth`

---

## Структура директорий

```
auth-service/
├── Dockerfile
├── package.json
├── .env                          # не в git
├── prisma/
│   ├── schema.prisma             # Модели: User, RefreshToken, OAuthAccount
│   └── migrations/               # Автогенерируется Prisma
├── src/
│   ├── index.js                  # Точка входа: Express app, порт 3001
│   ├── config/
│   │   ├── passport.js           # Настройка Passport.js стратегий (Google, GitHub)
│   │   └── redis.js              # Подключение ioredis
│   ├── routes/
│   │   └── auth.routes.js        # Все /auth/* маршруты
│   ├── controllers/
│   │   └── auth.controller.js    # Логика обработчиков
│   ├── middleware/
│   │   ├── checkAuth.js          # Проверка JWT из Authorization header
│   │   └── checkRole.js          # RBAC: checkRole('admin'), checkRole('editor')
│   ├── services/
│   │   ├── token.service.js      # Генерация/валидация JWT и refresh токенов
│   │   └── user.service.js       # Работа с пользователями через Prisma
│   └── utils/
│       └── errors.js             # Стандартный формат ошибок { error: { code, message } }
└── init.sql                      # DDL схемы auth (запускается при старте postgres)
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

EXPOSE 3001

CMD ["node", "src/index.js"]
```

> Prisma generate нужен на этапе сборки, чтобы сгенерировать клиент под Alpine Linux.
> Миграции (`prisma migrate deploy`) запускать отдельно или через entrypoint-скрипт.

---

## Переменные окружения

```dotenv
# PostgreSQL
DATABASE_URL=postgresql://postgres:secret@postgres:5432/collab

# Redis
REDIS_URL=redis://redis:6379

# JWT
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
JWT_EXPIRES_IN=1h

# Refresh Token
REFRESH_TOKEN_SECRET=your-refresh-secret-min-32-chars
REFRESH_TOKEN_EXPIRES_IN=30d

# OAuth2 — Google
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALLBACK_URL=http://localhost/auth/google/callback

# OAuth2 — GitHub
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_CALLBACK_URL=http://localhost/auth/github/callback

# Общие
NODE_ENV=development
PORT=3001
```

---

## База данных — схема `auth`

Auth Service использует **схему `auth`** внутри общей PostgreSQL базы. Прямые JOIN с таблицами схемы `task` запрещены.

### Prisma schema

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String         @id @default(uuid()) @db.Uuid
  email         String         @unique
  passwordHash  String?        @map("password_hash")
  name          String
  avatarUrl     String?        @map("avatar_url")
  role          Role           @default(viewer)
  createdAt     DateTime       @default(now()) @map("created_at")
  updatedAt     DateTime       @updatedAt @map("updated_at")

  refreshTokens RefreshToken[]
  oauthAccounts OAuthAccount[]

  @@map("users")
  @@schema("auth")
}

model RefreshToken {
  id         String   @id @default(uuid()) @db.Uuid
  userId     String   @map("user_id") @db.Uuid
  tokenHash  String   @map("token_hash")
  expiresAt  DateTime @map("expires_at")
  revoked    Boolean  @default(false)
  createdAt  DateTime @default(now()) @map("created_at")

  user       User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@map("refresh_tokens")
  @@schema("auth")
}

model OAuthAccount {
  id          String   @id @default(uuid()) @db.Uuid
  userId      String   @map("user_id") @db.Uuid
  provider    Provider
  providerId  String   @map("provider_id")
  accessToken String?  @map("access_token")

  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([provider, providerId])
  @@map("oauth_accounts")
  @@schema("auth")
}

enum Role {
  admin
  editor
  viewer

  @@schema("auth")
}

enum Provider {
  google
  github

  @@schema("auth")
}
```

### init.sql (DDL — альтернатива Prisma migrations)

```sql
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TYPE auth.role_enum AS ENUM ('admin', 'editor', 'viewer');
CREATE TYPE auth.provider_enum AS ENUM ('google', 'github');

CREATE TABLE auth.users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name          VARCHAR(255) NOT NULL,
    avatar_url    TEXT,
    role          auth.role_enum NOT NULL DEFAULT 'viewer',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX ON auth.users(email);

CREATE TABLE auth.refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth.oauth_accounts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider     auth.provider_enum NOT NULL,
    provider_id  VARCHAR(255) NOT NULL,
    access_token TEXT
);
CREATE UNIQUE INDEX ON auth.oauth_accounts(provider, provider_id);
```

---

## Redis — ключи

Auth Service использует **префикс `auth:`** для всех ключей.

| Ключ | Тип Redis | TTL | Значение | Описание |
|------|-----------|-----|----------|----------|
| `auth:blacklist:{jti}` | String | Время жизни токена | `'revoked'` | Инвалидированные JWT. `jti` — уникальный ID из payload токена |
| `auth:refresh:{userId}` | String | 30 дней | `token_hash` | Хэш активного refresh токена пользователя |

```js
// Занести токен в blacklist (при logout)
await redis.set(`auth:blacklist:${jti}`, 'revoked', 'EX', remainingTtl)

// Сохранить refresh token
await redis.set(`auth:refresh:${userId}`, tokenHash, 'EX', 60 * 60 * 24 * 30)

// Проверить blacklist
const isRevoked = await redis.get(`auth:blacklist:${jti}`)
```

---

## API endpoints

Базовый URL: `http://auth:3001` (внутри Docker) или `http://localhost/auth` (через Nginx)

### `POST /auth/register`
Регистрация нового пользователя.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!",
  "name": "Ivan Petrov"
}
```
**Response 201:**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "user": {
    "id": "uuid-v4",
    "email": "user@example.com",
    "name": "Ivan Petrov",
    "role": "viewer"
  }
}
```

---

### `POST /auth/login`
Логин по email + password.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```
**Response 200:** аналогично `/register`

---

### `GET /auth/me`
Получить данные текущего пользователя по JWT.

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:**
```json
{
  "id": "uuid-v4",
  "email": "user@example.com",
  "name": "Ivan Petrov",
  "avatarUrl": null,
  "role": "editor"
}
```

---

### `POST /auth/refresh`
Обновить access token по refresh token.

**Body:**
```json
{
  "refreshToken": "eyJ..."
}
```
**Response 200:**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ..."
}
```

---

### `POST /auth/logout`
Инвалидировать текущий access token (занести в blacklist) и удалить refresh token.

**Headers:** `Authorization: Bearer <access_token>`

**Response 204:** No Content

---

### `GET /auth/google`
Редирект на Google OAuth2 consent screen.

---

### `GET /auth/google/callback`
Callback после авторизации через Google. Создаёт или находит пользователя, возвращает токены.

**Response:** редирект на frontend с токенами в query params или cookie.

---

### `GET /auth/github`
Редирект на GitHub OAuth2.

---

### `GET /auth/github/callback`
Callback после авторизации через GitHub.

---

### Формат ошибок

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect",
    "details": {}
  }
}
```

| Код ошибки | HTTP статус | Описание |
|-----------|-------------|----------|
| `VALIDATION_ERROR` | 400 | Неверный формат данных |
| `EMAIL_TAKEN` | 409 | Email уже зарегистрирован |
| `INVALID_CREDENTIALS` | 401 | Неверный email или пароль |
| `UNAUTHORIZED` | 401 | Токен отсутствует, невалиден или истёк |
| `TOKEN_REVOKED` | 401 | Токен в blacklist |
| `FORBIDDEN` | 403 | Недостаточно прав (роль) |
| `INTERNAL_ERROR` | 500 | Внутренняя ошибка сервера |

---

## JWT — формат токена

Все сервисы используют **единый формат payload**. Изменение структуры требует согласования с Task Service и Real-time Service.

```json
{
  "sub": "uuid-v4-user-id",
  "role": "admin | editor | viewer",
  "email": "user@example.com",
  "jti": "unique-token-id-uuid",
  "iat": 1700000000,
  "exp": 1700003600
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `sub` | UUID v4 | ID пользователя — используется как `userId` во всех сервисах |
| `role` | enum | Роль пользователя |
| `email` | string | Email (для логов и отображения) |
| `jti` | UUID v4 | Уникальный ID токена — ключ в Redis blacklist |
| `iat` | timestamp | Время выдачи |
| `exp` | timestamp | Время истечения (iat + 1h) |

**Подпись:** `HS256` с `JWT_SECRET`

---

## RBAC — система ролей

```
admin   — полный доступ: CRUD + удаление досок и задач, управление участниками
editor  — создание и редактирование досок, колонок, задач, комментариев
viewer  — только чтение: просмотр досок и задач, без изменений
```

### Middleware `checkRole.js`

```js
// src/middleware/checkRole.js

const checkRole = (...allowedRoles) => (req, res, next) => {
  const user = req.user  // устанавливается middleware checkAuth.js

  if (!user) {
    return res.status(401).json({
      error: { code: 'UNAUTHORIZED', message: 'Authentication required' }
    })
  }

  if (!allowedRoles.includes(user.role)) {
    return res.status(403).json({
      error: { code: 'FORBIDDEN', message: 'Insufficient permissions' }
    })
  }

  next()
}

module.exports = { checkRole }
```

**Использование:**
```js
// Только admin и editor могут создавать задачи
router.post('/api/tasks', checkAuth, checkRole('admin', 'editor'), createTask)

// Только admin может удалять
router.delete('/api/tasks/:id', checkAuth, checkRole('admin'), deleteTask)
```

> Task Service и Real-time Service **копируют** `checkAuth.js` и `checkRole.js` к себе.
> Они валидируют JWT самостоятельно через `JWT_SECRET` из своего `.env` — без запросов к Auth Service.

---

## OAuth2 — Google и GitHub

### Passport.js конфигурация (src/config/passport.js)

```js
const passport = require('passport')
const { Strategy: GoogleStrategy } = require('passport-google-oauth20')
const { Strategy: GitHubStrategy } = require('passport-github2')

// Общая логика: найти или создать пользователя по OAuth профилю
async function findOrCreateOAuthUser(profile, provider) {
  // 1. Найти в oauth_accounts по provider + provider_id
  // 2. Если найден — вернуть user
  // 3. Если нет — создать User + OAuthAccount
  // 4. Вернуть user
}

passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  callbackURL: process.env.GOOGLE_CALLBACK_URL,
}, async (accessToken, refreshToken, profile, done) => {
  try {
    const user = await findOrCreateOAuthUser(profile, 'google')
    done(null, user)
  } catch (err) {
    done(err)
  }
}))

passport.use(new GitHubStrategy({
  clientID: process.env.GITHUB_CLIENT_ID,
  clientSecret: process.env.GITHUB_CLIENT_SECRET,
  callbackURL: process.env.GITHUB_CALLBACK_URL,
}, async (accessToken, refreshToken, profile, done) => {
  try {
    const user = await findOrCreateOAuthUser(profile, 'github')
    done(null, user)
  } catch (err) {
    done(err)
  }
}))
```

---

## Зависимости (npm)

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "passport": "^0.7.0",
    "passport-google-oauth20": "^2.0.0",
    "passport-github2": "^0.1.12",
    "jsonwebtoken": "^9.0.0",
    "bcrypt": "^5.1.0",
    "@prisma/client": "^5.0.0",
    "ioredis": "^5.3.0",
    "joi": "^17.9.0",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "express-rate-limit": "^7.0.0",
    "uuid": "^9.0.0",
    "dotenv": "^16.0.0"
  },
  "devDependencies": {
    "prisma": "^5.0.0",
    "nodemon": "^3.0.0",
    "jest": "^29.0.0",
    "supertest": "^6.3.0"
  }
}
```

---

## Взаимодействие с другими сервисами

```
Auth Service  ─────────────────────────────────────────────────────────
     │
     │  Выдаёт JWT с payload: { sub, role, email, jti }
     │
     ▼
Task Service (порт 3002)        — валидирует JWT самостоятельно через JWT_SECRET
Real-time Service (порт 3003)   — валидирует JWT самостоятельно через JWT_SECRET
Frontend (порт 3000)            — получает токены, хранит в httpOnly cookie или localStorage
```

**Auth Service НЕ получает запросы от других сервисов в рантайме.**
Остальные сервисы валидируют токены локально, используя общий `JWT_SECRET`.

Единственная зависимость: все сервисы должны иметь **одинаковое значение `JWT_SECRET`** в своих `.env`.

---

*Auth Service | Real-Time Collaborative Dashboard | 2026*

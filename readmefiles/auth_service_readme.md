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
- OAuth2 через Google и GitHub
- Выдача `access_token` (JWT, TTL: 1h) и `refresh_token` (TTL: 30d)
- Валидация и инвалидация токенов (Redis blacklist)
- Хранение пользователей

**Порт:** `3001`
**Внутренний хост в Docker-сети:** `auth`

> **Важно:** Task Service и Real-time Service валидируют JWT **локально** через общий `JWT_SECRET_KEY`. Auth Service не участвует в проверке токенов на каждый запрос.

---

## Структура директорий

```
auth-service/
├── Dockerfile
├── requirements.txt
├── .env                          # не в git
├── src/
│   ├── main.py                   # Точка входа: FastAPI app, порт 3001
│   ├── config/
│   │   ├── database.py           # SQLAlchemy подключение
│   │   └── redis.py              # Подключение aioredis
│   ├── routes/
│   │   └── auth.py               # Все /auth/* маршруты
│   ├── middleware/
│   │   └── auth.py               # RBAC middleware
│   ├── services/
│   │   ├── token.py              # Генерация/валидация JWT и refresh токенов
│   │   └── user.py               # Работа с пользователями через SQLAlchemy
│   ├── models/
│   │   └── user.py               # Модели: User, RefreshToken, OAuthAccount
│   └── schemas/
│       └── auth.py               # Pydantic схемы для валидации
└── alembic/                      # Миграции БД
    ├── env.py
    └── versions/                 # Автогенерируется Alembic
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
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3001"]
```

> Миграции Alembic можно запускать через entrypoint-скрипт или вручную:
> `docker compose exec auth alembic upgrade head`

---

## Переменные окружения

```dotenv
# PostgreSQL
DATABASE_URL=postgresql://postgres:secret@postgres:5432/collab

# Redis
REDIS_URL=redis://redis:6379

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
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

### SQLAlchemy модели

```python
# src/models/user.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum

Base = declarative_base()

class Role(enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"

class Provider(enum.Enum):
    google = "google"
    github = "github"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(Enum(Role), nullable=False, default=Role.viewer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="refresh_tokens")

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = {"schema": "auth"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Enum(Provider), nullable=False)
    provider_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=True)

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_provider_provider_id"),
        {"schema": "auth"}
    )
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

**Подпись:** `HS256` с `JWT_SECRET_KEY`

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
> Они валидируют JWT самостоятельно через `JWT_SECRET_KEY` из своего `.env` — без запросов к Auth Service.

---

## OAuth2 — Google и GitHub

### Authlib конфигурация (src/config/oauth.py)

```python
# src/config/oauth.py
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

def configure_oauth(app):
    # Google OAuth2
    oauth.register(
        name="google",
        client_id=app.settings.GOOGLE_CLIENT_ID,
        client_secret=app.settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            "scope": "openid email profile",
        },
    )

    # GitHub OAuth2
    oauth.register(
        name="github",
        client_id=app.settings.GITHUB_CLIENT_ID,
        client_secret=app.settings.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={
            "scope": "user:email",
        },
    )
```

### Обработчик OAuth callback (src/routes/auth.py)

```python
@router.get("/google/callback")
async def google_callback(request: Request):
    code = request.query_params.get("code")
    tokens = await oauth.google.authorize_access_token(request)
    user_info = tokens.get("userinfo")
    
    # Найти или создать пользователя по OAuth профилю
    db_user = await find_or_create_oauth_user(
        provider="google",
        provider_id=user_info["sub"],
        email=user_info["email"],
        name=user_info["name"],
        avatar_url=user_info.get("picture"),
    )
    
    # Сгенерировать JWT токены
    access_token = create_access_token(db_user)
    refresh_token = create_refresh_token(db_user)
    
    # Редирект на frontend с токенами
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={access_token}&refreshToken={refresh_token}"
    return RedirectResponse(url=redirect_url)

@router.get("/github/callback")
async def github_callback(request: Request):
    code = request.query_params.get("code")
    tokens = await oauth.github.authorize_access_token(request)
    user_info = tokens.get("userinfo")
    
    db_user = await find_or_create_oauth_user(
        provider="github",
        provider_id=str(user_info["id"]),
        email=user_info["email"],
        name=user_info["name"],
        avatar_url=user_info.get("avatar_url"),
    )
    
    access_token = create_access_token(db_user)
    refresh_token = create_refresh_token(db_user)
    
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={access_token}&refreshToken={refresh_token}"
    return RedirectResponse(url=redirect_url)
```

---

## Зависимости (requirements.txt)

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aioredis==2.0.1
httpx==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6
authlib==1.3.0
```

---

## Взаимодействие с другими сервисами

```
Auth Service  ─────────────────────────────────────────────────────────
     │
     │  Выдаёт JWT с payload: { sub, email, jti }
     │
     ▼
Task Service (порт 3002)        — валидирует JWT самостоятельно через JWT_SECRET_KEY
Real-time Service (порт 3003)   — валидирует JWT самостоятельно через JWT_SECRET_KEY
Frontend (порт 3000)            — получает токены, хранит в cookie или localStorage
```

**Auth Service НЕ получает запросы от других сервисов в рантайме.**
Остальные сервисы валидируют токены локально, используя общий `JWT_SECRET_KEY`.

**Важно:** Все сервисы должны иметь **одинаковое значение `JWT_SECRET_KEY`** в своих `.env` (берётся из корневого `.env` проекта).

---

*Auth Service | Real-Time Collaborative Dashboard | 2026*

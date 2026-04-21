# 📊 Real-Time Collaborative Dashboard

Микросервисная веб-платформа для командной работы с Kanban-досками, real-time синхронизацией, встроенным чатом и аналитикой прогресса.

---

## ✨ Возможности
- 🗂 **Kanban-доски** с drag-and-drop перемещением задач (`@dnd-kit`)
- ⚡ **Real-time обновления** состояния доски и уведомлений через WebSocket
- 💬 **Встроенный чат** с историей сообщений и индикаторами присутствия
- 📊 **Burn-down chart** для отслеживания скорости закрытия задач
- 🔐 **Аутентификация & RBAC**: Email/Password + OAuth2 (Google, GitHub), роли `admin`, `editor`, `viewer`
- 🌙 **Тёмная/Светлая тема** с плавными анимациями (`Framer Motion`)
- 🔄 **Бесшовный refresh JWT** без разрыва сессии и потери данных
- 🧩 **Изолированная архитектура**: каждый сервис в отдельном контейнере, общая точка входа через Nginx

---

## 🏗 Архитектура

```text
Клиент (Next.js 15)
   │
   ├─ REST ──→ Nginx (80/443) ──→ /auth/* → Auth Service (3001)
   ├─ REST ──→ Nginx (80/443) ──→ /api/*  → Task Service (3002)
   └─ WSS  ──→ Nginx (80/443) ──→ /ws     → Realtime Service (3003)
                        │
Task Service ──(HTTP Webhook)──▶ Realtime Service (POST /internal/events)
                        │
PostgreSQL ◀──── Auth & Task Services (изолированные схемы: auth / task)
Redis      ◀──── Auth & Realtime Services (blacklist JWT, чат, presence, Pub/Sub)
```

**Ключевые принципы:**
- 🔐 **Локальная валидация JWT**: Task и Realtime Service проверяют токены самостоятельно через общий `JWT_SECRET_KEY`.
- 🔄 **Webhook-уведомления**: Task Service отправляет события в Realtime Service, который транслирует их подключённым клиентам.
- 🗄 **Изоляция данных**: Прямые `JOIN` между схемами запрещены. Связь только через `user_id` (UUID v4).

---

## 🛠 Технологический стек
| Компонент | Технологии |
|-----------|------------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Zustand, `@dnd-kit`, Socket.io-client, Recharts, Framer Motion |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn, python-jose, Authlib |
| **БД & Кэш** | PostgreSQL 16 (схемы `auth`/`task`), Redis 7 (чаты, presence, Pub/Sub, blacklist JWT) |
| **Инфраструктура** | Docker Compose, Nginx (API Gateway, SSL termination, WS proxy) |

---

## 🚀 Быстрый старт

### 📋 Требования
- Docker & Docker Compose v2+
- 4+ GB RAM
- Git

### ⚙️ Установка и запуск
```
# 1. Клонировать репозиторий
git clone https://github.com/ciynkok/App.git

# 2 Запустить Docker Desktop (для Windows)

# 3. Создать .env и запустить проект
cd App

Для Linux:
./make.sh

Для Windows
./Make.ps1


# 4 Зайти на сайт
В браузере перейти по адресу localhost

## 📜 Лицензия

Этот проект распространяется под лицензией [MIT](LICENSE).

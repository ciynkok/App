# Архитектура Task Service

## 1. Назначение сервиса
Task Service отвечает за бизнес-логику управления досками, задачами, колонками и комментариями. Сервис реализует REST API для CRUD-операций, поддерживает фильтрацию, поиск, аналитику (burn-down chart) и взаимодействует с Real-time сервисом через webhooks.

## 2. Технологический стек
- **Python 3.12 + FastAPI** — HTTP сервер и роутинг
- **SQLAlchemy 2.0 (async)** — работа с PostgreSQL (схема task)
- **PostgreSQL 16** — основная БД (схема task)
- **Pydantic** — валидация входящих данных
- **pytest + pytest-asyncio** — тестирование (unit + integration)
- **FastAPI встроенный OpenAPI/Swagger** — автогенерация API документации
- **APScheduler** — планировщик задач (напоминания о дедлайнах)
- **httpx** — HTTP-клиент для отправки webhooks в Real-time Service

## 3. Архитектура и компоненты

### 3.1 Структура базы данных (PostgreSQL, схема task)
- **task.boards**: id (UUID), title, description, owner_id, color, created_at
- **task.board_members**: board_id, user_id, role (admin|editor|viewer)
- **task.columns**: id, board_id, title, position, created_at
- **task.tasks**: id, column_id, board_id, title, description, assignee_id, priority, status, deadline, position, created_at
- **task.comments**: id, task_id, author_id, content, created_at

### 3.2 Основные REST endpoints
- **/api/boards** — CRUD досок
- **/api/boards/:id/columns** — добавление колонок
- **/api/tasks** — CRUD задач, фильтрация, поиск
- **/api/tasks/:id/move** — перемещение задач между колонками
- **/api/tasks/:id/comments** — работа с комментариями
- **/api/boards/:id/stats** — аналитика для burn-down chart

### 3.3 Аутентификация и авторизация
- JWT-токены, выданные Auth Service (Dev 1)
- Проверка токена на каждом защищённом endpoint
- RBAC: роли admin/editor/viewer (роль хранится в board_members)

### 3.4 Интеграция с другими сервисами
- **Auth Service**: валидация JWT, получение userId
- **Real-time Service**: отправка webhooks на внутренний endpoint при изменениях задач/комментариев

### 3.5 Валидация и обработка ошибок
- Pydantic-схемы для проверки входящих данных
- Единый формат ошибок: { error: { code, message, details } }

### 3.6 Документация и тестирование
- Swagger/OpenAPI спецификация для всех endpoint
- Покрытие тестами > 70% (pytest + pytest-asyncio)

## 4. Потоки данных
1. **Пользователь** → **API Gateway (Nginx)** → **Task Service**
2. **Task Service** ←→ **PostgreSQL** (чтение/запись)
3. **Task Service** → **Real-time Service** (webhook при изменениях)
4. **Task Service** ← **Auth Service** (валидация JWT)

## 5. Безопасность
- Проверка JWT на каждом запросе
- Ограничение доступа по ролям (RBAC)
- Валидация данных на входе

## 6. Масштабируемость и отказоустойчивость
- Stateless сервис, масштабируется горизонтально
- Все состояния — в PostgreSQL
- Взаимодействие с Real-time сервисом через внутреннюю сеть Docker

## 7. Запуск и окружение
- Сервис запускается через Docker Compose
- Все переменные окружения описаны в .env.example
- Зависимости: PostgreSQL, Auth Service

---

**Task Service** — это изолированный микросервис, реализующий всю бизнес-логику задач и досок, с чёткими точками интеграции и строгим разграничением ответственности.
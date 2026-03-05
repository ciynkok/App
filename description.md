Real-Time Collaborative Dashboard
Проект №2 — Архитектура и распределение задач


Улучшенная платформа командной работы с акцентом на real-time коллаборацию

👥 Команда
🏗️ Архитектура
⏱️ Срок
3 разработчика
Микросервисы
4 недели



1. Архитектурное решение
Для данного проекта выбрана микросервисная архитектура. Это решение позволяет трём разработчикам работать полностью независимо — каждый сервис имеет свой репозиторий (или директорию), свой Dockerfile и свою зону ответственности. Изменения в одном сервисе не затрагивают код другого.

1.1 Почему микросервисы, а не монолит?

✅ Преимущества микросервисного подхода для команды из 3 человек
• Нулевое пересечение кода — каждый разработчик владеет своим сервисом полностью
• Независимый деплой — можно обновить Auth Service не трогая остальные
• Разные технологии при необходимости — сервисы общаются через REST/Events
• Параллельная разработка с первого дня — не нужно ждать друг друга
• Реальный опыт — работодатели ценят знание микросервисной архитектуры
• Docker Compose объединяет всё в один запуск: docker compose up


1.2 Схема архитектуры

АРХИТЕКТУРА СИСТЕМЫ (МИКРОСЕРВИСЫ)
[ КЛИЕНТ ]
Next.js 15 + React 19 + Tailwind CSS + Framer Motion + Socket.io-client
▼  HTTPS / WSS
[ API GATEWAY ]  Nginx Reverse Proxy
Роутинг запросов: /auth → Auth Service | /api → Task Service | /ws → Real-time Service
▼  Internal Docker Network


AUTH SERVICE
TASK SERVICE
REALTIME SERVICE
Node.js 22 + Express
Порт: 3001

JWT выдача/валидация
OAuth2 (Google/GitHub)
Роли: admin/editor/viewer
Refresh tokens
Rate limiting
Node.js 22 + Express
Порт: 3002

CRUD Boards/Tasks/Columns
Комментарии к задачам
Поиск и фильтрация
Burn-down chart данные
PostgreSQL + Prisma ORM
Node.js 22 + Socket.io
Порт: 3003

WebSocket connections
Broadcast task moves
Встроенный чат
Push-уведомления
Redis Pub/Sub
PostgreSQL (порт 5432)  |  Redis (порт 6379)



2. Распределение задач по разработчикам
Ключевой принцип: каждый разработчик владеет одним микросервисом полностью — от базы данных до API. Пересечений нет. Точки интеграции прописаны в общем API-контракте (OpenAPI/Swagger) до начала разработки.

РАЗРАБОТЧИК 1 — DevOps Engineer + Auth Service


Разработчик 1 — это «фундамент» всего проекта. Он первым поднимает инфраструктуру, настраивает Docker Compose с нуля и создаёт сервис аутентификации, которым пользуются оба других разработчика.

Задача
Срок (недели)
Deliverable
Настройка Docker Compose (все сервисы)
Нед. 1
docker-compose.yml, .env.example
Dockerfile для каждого сервиса
Нед. 1
4 × Dockerfile (auth, task, rt, nginx)
PostgreSQL + Redis setup + схема Users
Нед. 1
init.sql, prisma/schema.prisma (users)
Auth Service: регистрация/логин + JWT
Нед. 2
POST /auth/register, POST /auth/login
OAuth2: Google + GitHub
Нед. 2
GET /auth/google, GET /auth/github/callback
Система ролей (admin/editor/viewer)
Нед. 2
Middleware checkRole(), RBAC таблица
Nginx API Gateway конфигурация
Нед. 3
nginx.conf с роутингом на все сервисы
Rate limiting + токены обновления
Нед. 3
Защита от брутфорса, refresh token endpoint
Postman коллекция + README проекта
Нед. 4
collab-dashboard.postman_collection.json
Мониторинг: Prometheus + Grafana (опц.)
Нед. 4
docker-compose.monitoring.yml


🔑 Технологии Dev 1
• Node.js 22 LTS + Express.js — Auth Service (порт 3001)
• Passport.js — OAuth2 стратегии (google, github)
• jsonwebtoken + bcrypt — JWT и хэширование паролей
• Prisma ORM — работа с PostgreSQL (таблицы: users, roles, refresh_tokens)
• ioredis — хранение черных списков токенов в Redis
• Nginx — reverse proxy + SSL termination
• Docker + Docker Compose — оркестрация всего стека


РАЗРАБОТЧИК 2 — Backend Engineer — Task & Board Service


Разработчик 2 — «мозг» бизнес-логики. Он создаёт весь REST API для работы с досками, задачами и комментариями. Использует JWT-токены от сервиса Dev 1 для проверки доступа, но не вмешивается в их генерацию.

Задача
Срок (недели)
Deliverable
PostgreSQL схема: boards, tasks, columns, comments
Нед. 1
Prisma migrations, init.sql для Task Service
CRUD API: Boards (создание, список, удаление)
Нед. 2
GET/POST/PUT/DELETE /api/boards
CRUD API: Columns и перемещение задач
Нед. 2
POST /api/columns, PATCH /api/tasks/:id/move
CRUD API: Tasks с приоритетом и дедлайном
Нед. 2
CRUD /api/tasks с полной моделью данных
Комментарии к задачам
Нед. 3
GET/POST/DELETE /api/tasks/:id/comments
Поиск и фильтрация задач
Нед. 3
GET /api/tasks?search=&status=&assignee=
Данные для burn-down chart
Нед. 3
GET /api/boards/:id/stats — аналитика
WebHook-события для Real-time сервиса
Нед. 3
POST на внутренний endpoint RT Service при CRUD
Swagger/OpenAPI документация
Нед. 4
swagger.json — контракт для Frontend Dev
Тестирование: Jest + Supertest
Нед. 4
Unit + integration тесты, coverage > 70%


⚙️ Технологии Dev 2
• Node.js 22 LTS + Express.js — Task Service (порт 3002)
• Prisma ORM — PostgreSQL: boards, tasks, columns, comments, task_assignments
• Joi — валидация входящих данных (schemas)
• Jest + Supertest — юнит и интеграционные тесты
• swagger-jsdoc + swagger-ui-express — автогенерация API документации
• node-cron — scheduled jobs (напоминания о дедлайнах)
• axios — HTTP вызовы к Real-time Service для уведомлений



РАЗРАБОТЧИК 3 — Frontend Engineer + Real-time Service


Разработчик 3 — «лицо» продукта. Он создаёт всё, что видит пользователь, и отдельный сервис для WebSocket-коммуникации. Потребляет REST API Dev 2 и JWT-токены Dev 1, но самостоятельно строит весь UI и real-time слой.

Задача
Срок (недели)
Deliverable
Next.js 15 scaffold, роутинг, layout, компоненты
Нед. 1
src/app структура, tailwind.config, globals.css
Страницы: Login/Register + OAuth кнопки
Нед. 2
auth/login, auth/register с OAuth buttons
Kanban Board UI — колонки, карточки задач
Нед. 2
Компонент Board, TaskCard, Column
Drag-and-drop (dnd-kit)
Нед. 2
Плавное перемещение задач между колонками
Real-time Service — Socket.io сервер
Нед. 3
Node.js сервис (порт 3003) с WS комнатами
Broadcast: перемещение задач всем в доске
Нед. 3
socket.emit('task:moved') → всем участникам
Встроенный чат между участниками
Нед. 3
Chat sidebar, история сообщений в Redis
Тёмная тема + кастомизация (Tailwind)
Нед. 3
dark: классы, localStorage preference
Страница поиска и фильтрации задач
Нед. 4
Фильтры: status, assignee, priority, deadline
Burn-down chart (Recharts)
Нед. 4
Компонент BurndownChart с данными из Dev 2 API
Framer Motion анимации
Нед. 4
AnimatePresence на добавление/удаление карточек


🎨 Технологии Dev 3
• Next.js 15 (App Router) + React 19 — Frontend (порт 3000)
• Tailwind CSS — стилизация, тёмная тема через dark: prefix
• Framer Motion — анимации карточек и переходов
• @dnd-kit/core + @dnd-kit/sortable — drag-and-drop без jQuery
• Socket.io-client — подключение к Real-time Service
• Socket.io (сервер) + Node.js — Real-time Service (порт 3003)
• Redis Pub/Sub — синхронизация нескольких WS-инстанций
• Recharts — burn-down chart и графики прогресса
• Zustand или React Context — глобальный стейт (user, board)



3. Временная шкала (4 недели)
Параллельная работа с первого дня. Единственное последовательное требование: Dev 1 должен поднять docker-compose с PostgreSQL и Redis к концу Недели 1, чтобы Dev 2 и Dev 3 могли разрабатывать локально.

Период
Dev 1 (DevOps + Auth)
Dev 2 (Backend Tasks)
Dev 3 (Frontend + RT)
Неделя 1
Среда разработки, Docker compose, Auth DB schema
БД схема (boards, tasks, columns, comments), Prisma ORM
Wireframes + Next.js 15 scaffold, роутинг, layout
Неделя 2
JWT + OAuth2 Google/GitHub, роли
CRUD API: Boards, Columns, Tasks
Kanban UI + drag-and-drop (dnd-kit), Auth UI
Неделя 3
Rate limiting, API Gateway Nginx, тестирование Auth
Comments API, Search/Filter, Burn-down данные
Socket.io real-time service + frontend, Чат, темная тема
Неделя 4
Финальная интеграция, Postman коллекция, README
Тестирование API, документация, финальная интеграция
Burn-down chart (Recharts), Framer Motion анимации, полировка UI


4. API-контракт (точки интеграции)
Этот контракт — единственный документ, который читают все три разработчика. Dev 1 реализует /auth/*, Dev 2 реализует /api/*, Dev 3 потребляет оба. Real-time Service (Dev 3) получает события от Task Service (Dev 2) через внутренние HTTP webhooks.

4.1 Auth Service (Dev 1) — порт 3001

Метод
Endpoint
Описание
Роль
Владелец
POST
/auth/register
Регистрация пользователя
Public
Dev 1
POST
/auth/login
Логин, получение JWT
Public
Dev 1
GET
/auth/me
Данные текущего пользователя
JWT Required
Dev 1
POST
/auth/refresh
Обновление access token
Refresh Token
Dev 1
POST
/auth/logout
Выход, инвалидация токена
JWT Required
Dev 1
GET
/auth/google
OAuth2 redirect
Public
Dev 1
GET
/auth/github
OAuth2 redirect
Public
Dev 1


4.2 Task Service (Dev 2) — порт 3002

Метод
Endpoint
Описание
Роль
Владелец
GET
/api/boards
Список досок пользователя
JWT Required
Dev 2
POST
/api/boards
Создать доску
editor/admin
Dev 2
GET
/api/boards/:id
Детали доски + колонки
JWT Required
Dev 2
POST
/api/boards/:id/columns
Добавить колонку
editor/admin
Dev 2
GET
/api/tasks
Список задач (с фильтрами)
JWT Required
Dev 2
POST
/api/tasks
Создать задачу
editor/admin
Dev 2
PUT
/api/tasks/:id
Обновить задачу
editor/admin
Dev 2
PATCH
/api/tasks/:id/move
Переместить в колонку
editor/admin
Dev 2
DELETE
/api/tasks/:id
Удалить задачу
admin
Dev 2
GET
/api/tasks/:id/comments
Комментарии к задаче
JWT Required
Dev 2
POST
/api/tasks/:id/comments
Добавить комментарий
JWT Required
Dev 2
GET
/api/boards/:id/stats
Данные burn-down chart
JWT Required
Dev 2


4.3 Real-time Events (Dev 3) — WebSocket Events

Событие (emit)
Данные (payload)
Описание
task:moved
{ taskId, fromCol, toCol, userId }
Задача перемещена в другую колонку
task:created
{ task, boardId, userId }
Новая задача создана на доске
task:updated
{ taskId, changes, userId }
Задача обновлена
task:deleted
{ taskId, boardId }
Задача удалена
comment:added
{ taskId, comment, userId }
Добавлен комментарий
user:joined
{ userId, boardId, name }
Пользователь открыл доску
user:left
{ userId, boardId }
Пользователь покинул доску
chat:message
{ from, text, boardId, ts }
Сообщение в чате доски



5. Схема базы данных
PostgreSQL — единая БД с разными схемами для каждого сервиса. Auth Service владеет схемой auth, Task Service — схемой task. Это предотвращает случайные JOIN-запросы между сервисами.

5.1 Auth Schema (Dev 1)

Таблицы: auth.users, auth.refresh_tokens, auth.oauth_accounts
auth.users: id (UUID), email, password_hash, name, avatar_url, role (ENUM), created_at, updated_at
auth.refresh_tokens: id, user_id (FK), token_hash, expires_at, revoked, created_at
auth.oauth_accounts: id, user_id (FK), provider (google|github), provider_id, access_token


Роль ENUM: 'admin', 'editor', 'viewer'
Индексы: users.email (UNIQUE), oauth_accounts(provider, provider_id) (UNIQUE)


5.2 Task Schema (Dev 2)

Таблицы: task.boards, task.columns, task.tasks, task.comments, task.board_members
task.boards: id (UUID), title, description, owner_id (UUID), color, created_at
task.board_members: board_id, user_id, role (admin|editor|viewer)
task.columns: id, board_id (FK), title, position (INT), created_at
task.tasks: id, column_id (FK), board_id (FK), title, description, assignee_id,
           priority (low|medium|high|urgent), status, deadline, position, created_at
task.comments: id, task_id (FK), author_id (UUID), content, created_at


Индексы: tasks(board_id), tasks(column_id), tasks(assignee_id), comments(task_id)


5.3 Redis (общий)

Redis Key Patterns — Dev 1 и Dev 3 используют разные prefixes
auth:blacklist:{jti} → 'revoked' — чёрный список JWT (Dev 1)
auth:refresh:{userId} → token_hash — активные refresh токены (Dev 1)
rt:chat:{boardId} → List (LPUSH/LRANGE) — история чата, TTL 24h (Dev 3)
rt:online:{boardId} → Set — множество активных user_id в доске (Dev 3)
rt:board:{boardId}:lock:{taskId} → userId — оптимистичная блокировка (Dev 3)



6. Технологический стек с обоснованием

Технология
Назначение
Обоснование
Next.js 15
Frontend framework
App Router, SSR/SSG, оптимизированный бандл
React 19
UI библиотека
Concurrent rendering, Server Components
Tailwind CSS
Стилизация
Utility-first, встроенная тёмная тема
Framer Motion
Анимации
Declarative API, GPU-ускоренные анимации
dnd-kit
Drag-and-drop
Accessibility-first, без jQuery/HTML5 DnD
Socket.io
WebSockets
Автоматический fallback на polling, комнаты
Node.js 22 LTS
Backend runtime
LTS до 2027, native fetch, improved perf
Express.js
HTTP framework
Минималистичный, огромная экосистема
Prisma ORM
ORM для PostgreSQL
Type-safe запросы, автомиграции
PostgreSQL 16
Основная БД
ACID, JSON support, надёжность
Redis 7
Кэш + Pub/Sub
in-memory, WebSocket синхронизация
JWT + Passport.js
Аутентификация
Stateless, OAuth2 стратегии
Nginx
API Gateway
Reverse proxy, SSL, балансировка нагрузки
Docker Compose
Оркестрация
Единая команда запуска всего стека
Recharts
Графики
React-native, SVG, responsive


7. Docker Compose структура

Файловая структура репозитория
collab-dashboard/
├── docker-compose.yml          ← главный файл запуска
├── docker-compose.override.yml ← dev-переменные
├── .env.example               ← все переменные окружения
├── nginx/nginx.conf           ← конфигурация API Gateway
│
├── auth-service/              ← Dev 1
│   ├── Dockerfile
│   ├── src/
│   └── package.json
│
├── task-service/              ← Dev 2
│   ├── Dockerfile
│   ├── src/
│   ├── prisma/schema.prisma
│   └── package.json
│
├── realtime-service/          ← Dev 3
│   ├── Dockerfile
│   ├── src/
│   └── package.json
│
└── frontend/                  ← Dev 3
    ├── Dockerfile
    ├── src/app/
    └── package.json


Сервисы docker-compose.yml (Dev 1 настраивает)
postgres   → image: postgres:16    порт 5432   volume: pgdata
redis      → image: redis:7-alpine порт 6379   volume: redisdata
auth       → build: ./auth-service порт 3001   depends_on: postgres, redis
task       → build: ./task-service порт 3002   depends_on: postgres, auth
realtime   → build: ./realtime-ser  порт 3003  depends_on: redis, auth
frontend   → build: ./frontend     порт 3000   depends_on: auth, task, realtime
nginx      → build: ./nginx        порт 80/443 depends_on: все сервисы


Запуск: docker compose up --build
Остановка: docker compose down -v



8. Правила работы в команде

8.1 Git Flow
main — только stable, merge через Pull Request с ревью
develop — ветка интеграции
feature/auth-jwt (Dev 1), feature/task-crud (Dev 2), feature/frontend-kanban (Dev 3)
Коммиты по Conventional Commits: feat:, fix:, chore:, docs:

8.2 Точки синхронизации

Когда разработчики должны договориться ДО начала работы
1. JWT структура — Dev 1 публикует payload формат: { sub, role, email, iat, exp }
2. User ID формат — UUID v4 во всех сервисах, одно и то же поле userId
3. WebHook format — Dev 2 → Dev 3: POST http://realtime:3003/internal/events
   { event: 'task:moved', boardId, payload: {...} }
4. Error format — единый формат ошибок: { error: { code, message, details } }
5. .env.example — Dev 1 создаёт, все добавляют свои переменные туда же


8.3 Порядок запуска разработки
Dev 1: создаёт docker-compose.yml с postgres + redis + nginx skeleton (День 1-2)
Все: клонируют репо, запускают docker compose up, убеждаются что БД работает
Dev 1 + Dev 2: договариваются о JWT payload и user_id формате (30 мин встреча)
Dev 2 публикует Swagger spec /api/docs — Dev 3 начинает писать API клиент
Dev 3 публикует WebSocket events spec — Dev 2 знает куда слать webhook-и
Неделя 4: интеграционное тестирование, запись видео-демонстрации, финал

9. Чеклист сдачи проекта

✅ Обязательные требования (must-have)
□ docker compose up запускает всё за одну команду
□ Регистрация и логин работают (email + Google/GitHub OAuth2)
□ Роли: admin видит кнопки удаления, viewer — только просмотр
□ Kanban доска: создание/редактирование/удаление задач
□ Drag-and-drop: перемещение задач между колонками
□ Real-time: открыть два браузера, переместить задачу — видно в обоих
□ Комментарии к задачам работают
□ Поиск задач по названию/статусу/исполнителю
□ README.md с инструкцией запуска и бейджами
□ Postman коллекция с примерами всех запросов


🔥 WOW-фичи (для высокой оценки)
□ Встроенный чат в боковой панели доски
□ Burn-down chart на странице доски (Recharts)
□ Тёмная тема с переключателем (Tailwind dark:)
□ Индикаторы присутствия (avatars пользователей в доске)
□ Уведомления в реальном времени (toast при событиях)
□ Prometheus + Grafana мониторинг (docker-compose.monitoring.yml)




"Деплой — это половина успеха. Если проект не запускается одной командой, его не существует."
Real-Time Collaborative Dashboard | Проект №2 | 2026

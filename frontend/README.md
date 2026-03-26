# Real-Time Collaborative Dashboard — Фронтенд

Современная Kanban-доска с возможностью совместной работы в реальном времени, построенная на Next.js 15, React 19.

## Технологический стек

- **Next.js 15** (App Router)
- **React 19**
- **Tailwind CSS** (с поддержкой тёмной темы)
- **Framer Motion** (анимации)
- **@dnd-kit** (drag-and-drop)
- **Socket.io-client** (WebSocket для связи в реальном времени)
- **Recharts** (графики и статистика)
- **Zustand** (управление состоянием)
- **React Hook Form** (работа с формами)
- **date-fns** (форматирование дат)
- **react-hot-toast** (уведомления)
- **lucide-react** (иконки)

## Структура проекта

```
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── layout.js
│   │   ├── page.js
│   │   ├── auth/
│   │   │   ├── login/page.js
│   │   │   └── register/page.js
│   │   └── dashboard/
│   │       └── [boardId]/page.js
│   ├── components/
│   │   ├── ui/
│   │   ├── board/
│   │   ├── chat/
│   │   ├── charts/
│   │   └── modals/
│   ├── hooks/
│   ├── lib/
│   │   ├── api/
│   │   └── socket.js
│   ├── store/
│   └── styles/
├── .env.local.example
├── next.config.js
├── tailwind.config.js
├── Dockerfile
└── package.json
```

## Быстрый старт

### Требования

- Node.js 18+
- npm или yarn

### Установка

1. **Установите зависимости:**
   ```bash
   cd frontend
   npm install
   ```

2. **Настройте переменные окружения:**
   ```bash
   cp .env.local.example .env.local
   ```
   
   Отредактируйте `.env.local`, указав URL вашего бэкенда:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:3001
   NEXT_PUBLIC_WS_URL=ws://localhost:3001
   ```

3. **Запустите сервер разработки:**
   ```bash
   npm run dev
   ```

4. **Откройте [http://localhost:3000](http://localhost:3000)** в браузере.

## Возможности

### 🔐 Аутентификация
- Вход и регистрация по email/паролю
- JWT-токены для авторизации
- Защита маршрутов через middleware
- Сохранение сессии через Zustand persist

### 📋 Доски
- Создание, просмотр и удаление досок
- Выбор цвета доски
- Описание досок
- Отображение количества участников

### 🎯 Kanban-доска
- Несколько колонок (Нужно сделать, В процессе, Готово и т.д.)
- Drag-and-drop задач между колонками
- Приоритеты задач (Низкий, Средний, Высокий)
- Дедлайны задач
- Назначение исполнителей
- Оптимистичные обновления с откатом при ошибке

### 📝 Задачи
- Создание, редактирование и удаление задач
- Модальное окно с деталями задачи
- Комментарии к задачам
- Обновление комментариев в реальном времени
- Бейджи приоритетов
- Отслеживание дедлайнов

### 🌐 Real-time функции
- Обновление задач через WebSocket
- Комментарии в реальном времени
- Чат доски
- Индикатор онлайн-пользователей
- Уведомления о присоединении/выходе пользователей

### 🎨 UI/UX
- Тёмная тема (сохраняется в localStorage)
- Адаптивный дизайн (mobile-first)
- Плавные анимации через Framer Motion
- Toast-уведомления
- Индикаторы загрузки
- Обработка ошибок

### 📊 Статистика
- Burn-down диаграммы
- Отслеживание выполнения задач

## Docker развёртывание

### Сборка и запуск в Docker

```bash
# Сборка Docker-образа
docker build -t dashboard-frontend .

# Запуск контейнера
docker run -p 3000:3000 --env-file .env.local dashboard-frontend
```

### Docker Compose (вместе с бэкендом)

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:3001
      - NEXT_PUBLIC_WS_URL=ws://backend:3001
    depends_on:
      - backend
  
  backend:
    build: ./backend
    ports:
      - "3001:3001"
```

## Интеграция с API

Фронтенд ожидает бэкенд со следующими эндпоинтами:

### Аутентификация
- `POST /auth/login` — Вход пользователя
- `POST /auth/register` — Регистрация пользователя
- `GET /auth/me` — Получение текущего пользователя
- `POST /auth/logout` — Выход пользователя

### Доски
- `GET /api/boards` — Список всех досок
- `GET /api/boards/:id` — Детали доски
- `POST /api/boards` — Создать доску
- `PUT /api/boards/:id` — Обновить доску
- `DELETE /api/boards/:id` — Удалить доску
- `GET /api/boards/:id/stats` — Статистика доски

### Задачи
- `GET /api/tasks?boardId=:id` — Список задач
- `GET /api/tasks/:id` — Детали задачи
- `POST /api/tasks` — Создать задачу
- `PUT /api/tasks/:id` — Обновить задачу
- `PATCH /api/tasks/:id/move` — Переместить задачу
- `DELETE /api/tasks/:id` — Удалить задачу

### Комментарии
- `GET /api/tasks/:id/comments` — Список комментариев
- `POST /api/tasks/:id/comments` — Добавить комментарий
- `DELETE /api/tasks/:id/comments/:cid` — Удалить комментарий

### WebSocket события
- `join:board` — Присоединиться к комнате доски
- `leave:board` — Покинуть комнату доски
- `chat:message` — Отправить/получить сообщение чата
- `task:created` — Задача создана
- `task:updated` — Задача обновлена
- `task:moved` — Задача перемещена
- `task:deleted` — Задача удалена
- `comment:added` — Комментарий добавлен
- `user:joined` — Пользователь присоединился
- `user:left` — Пользователь покинул
- `online:users` — Список онлайн-пользователей

## Скрипты

| Команда | Описание |
|---------|----------|
| `npm run dev` | Запуск сервера разработки |
| `npm run build` | Сборка для продакшена |
| `npm run start` | Запуск продакшен-сервера |
| `npm run lint` | Проверка ESLint |

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `NEXT_PUBLIC_API_URL` | URL REST API бэкенда | `http://localhost:3001` |
| `NEXT_PUBLIC_WS_URL` | URL WebSocket бэкенда | `ws://localhost:3001` |

## Поддерживаемые браузеры

- Chrome (последняя версия)
- Firefox (последняя версия)
- Safari (последняя версия)
- Edge (последняя версия)

## Решение проблем

### Ошибка подключения к WebSocket
Убедитесь, что бэкенд запущен и `NEXT_PUBLIC_WS_URL` настроен правильно.

### Проблемы с авторизацией
Проверьте, что токен сохраняется в cookies/localStorage и `NEXT_PUBLIC_API_URL` указан верно.

### Ошибки сборки в Docker
Убедитесь, что все зависимости установлены и нет конфликтов версий.

## Лицензия

MIT

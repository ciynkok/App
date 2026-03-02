# Frontend

Next.js 15 приложение — клиентская часть платформы. Реализует Kanban-интерфейс с drag-and-drop, real-time обновлениями через WebSocket, встроенным чатом, тёмной темой и burn-down chart. Потребляет REST API FastAPI сервисов (Auth Service, Task Service), подключается к Realtime Service по WebSocket.

---

## Содержание

1. [Обязанности сервиса](#обязанности-сервиса)
2. [Структура директорий](#структура-директорий)
3. [Dockerfile](#dockerfile)
4. [Переменные окружения](#переменные-окружения)
5. [Роутинг — App Router](#роутинг--app-router)
6. [Компоненты](#компоненты)
7. [Глобальный стейт (Zustand)](#глобальный-стейт-zustand)
8. [API-клиент — запросы к сервисам](#api-клиент--запросы-к-сервисам)
9. [WebSocket — подключение к Realtime Service](#websocket--подключение-к-realtime-service)
10. [Drag-and-Drop (dnd-kit)](#drag-and-drop-dnd-kit)
11. [Аутентификация — токены и OAuth2](#аутентификация--токены-и-oauth2)
12. [Тёмная тема (Tailwind)](#тёмная-тема-tailwind)
13. [Анимации (Framer Motion)](#анимации-framer-motion)
14. [Burn-down Chart (Recharts)](#burn-down-chart-recharts)
15. [Зависимости (npm)](#зависимости-npm)
16. [Взаимодействие с другими сервисами](#взаимодействие-с-другими-сервисами)

---

## Обязанности сервиса

- Страницы логина и регистрации с OAuth2 кнопками (Google, GitHub)
- Kanban-доска с колонками и карточками задач
- Drag-and-drop перемещение задач между колонками (`@dnd-kit`)
- Real-time синхронизация состояния доски через WebSocket
- Встроенный чат в боковой панели
- Индикаторы присутствия — аватары онлайн-участников
- Поиск и фильтрация задач
- Burn-down chart (Recharts)
- Тёмная тема с переключателем

**Порт:** `3000`
**Внутренний хост в Docker-сети:** `frontend`
**Framework:** Next.js 15, App Router, `output: 'standalone'`

---

## Структура директорий

```
frontend/
├── Dockerfile
├── package.json
├── next.config.js                        # output: 'standalone', env vars
├── tailwind.config.js                    # darkMode: 'class', кастомные цвета
├── .env.local                            # не в git
└── src/
    ├── app/                              # Next.js App Router
    │   ├── layout.js                     # Root layout: ThemeProvider, AuthGuard, Zustand
    │   ├── page.js                       # Redirect: / → /dashboard или /auth/login
    │   ├── globals.css                   # Tailwind directives, CSS переменные
    │   │
    │   ├── auth/
    │   │   ├── login/
    │   │   │   └── page.js               # Страница логина
    │   │   └── register/
    │   │       └── page.js               # Страница регистрации
    │   │
    │   └── dashboard/
    │       ├── page.js                   # Список досок пользователя
    │       └── [boardId]/
    │           └── page.js               # Kanban-доска конкретного проекта
    │
    ├── components/
    │   ├── auth/
    │   │   ├── LoginForm.jsx             # Форма логина + OAuth кнопки
    │   │   ├── RegisterForm.jsx          # Форма регистрации
    │   │   └── OAuthButtons.jsx          # Кнопки Google / GitHub
    │   │
    │   ├── board/
    │   │   ├── BoardView.jsx             # Корневой компонент доски (DnD контекст)
    │   │   ├── Column.jsx                # Колонка с задачами (droppable)
    │   │   ├── TaskCard.jsx              # Карточка задачи (draggable)
    │   │   ├── TaskModal.jsx             # Модальное окно задачи — детали, редактирование
    │   │   ├── AddTaskForm.jsx           # Инлайн-форма создания задачи
    │   │   ├── AddColumnForm.jsx         # Форма создания колонки
    │   │   └── BoardHeader.jsx           # Заголовок доски: название, участники, фильтры
    │   │
    │   ├── chat/
    │   │   ├── ChatSidebar.jsx           # Боковая панель чата
    │   │   ├── ChatMessage.jsx           # Отдельное сообщение
    │   │   └── ChatInput.jsx             # Поле ввода сообщения
    │   │
    │   ├── dashboard/
    │   │   ├── BoardCard.jsx             # Карточка доски в списке
    │   │   └── CreateBoardModal.jsx      # Модальное окно создания доски
    │   │
    │   ├── stats/
    │   │   └── BurndownChart.jsx         # Recharts burn-down chart
    │   │
    │   └── ui/
    │       ├── ThemeToggle.jsx           # Переключатель тёмной темы
    │       ├── PresenceAvatars.jsx       # Аватары онлайн-участников
    │       ├── PriorityBadge.jsx         # Бейдж приоритета задачи
    │       ├── SearchBar.jsx             # Поиск и фильтры задач
    │       └── Toast.jsx                 # Push-уведомления о событиях
    │
    ├── store/
    │   ├── authStore.js                  # Zustand: user, tokens, login/logout actions
    │   ├── boardStore.js                 # Zustand: boards, columns, tasks, optimistic updates
    │   └── uiStore.js                    # Zustand: тема, открытые модалки, сайдбар
    │
    ├── hooks/
    │   ├── useSocket.js                  # Хук подключения к Realtime Service
    │   ├── useBoardSocket.js             # Хук подписки на события конкретной доски
    │   └── useAuth.js                    # Хук получения текущего пользователя
    │
    ├── lib/
    │   ├── api.js                        # Axios инстанция с interceptors (авто-refresh)
    │   ├── auth.api.js                   # Запросы к Auth Service
    │   ├── boards.api.js                 # Запросы к Task Service: boards
    │   └── tasks.api.js                  # Запросы к Task Service: tasks, comments
    │
    └── utils/
        ├── cn.js                         # Утилита объединения Tailwind классов (clsx + twMerge)
        └── formatDate.js                 # Форматирование дат
```

---

## Dockerfile

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

### next.config.js

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',  // обязательно для Docker multi-stage build
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL,
  },
}

module.exports = nextConfig
```

---

## Переменные окружения

```dotenv
# URL API Gateway (Nginx) — используется для REST запросов
NEXT_PUBLIC_API_URL=http://localhost

# URL WebSocket — используется для Socket.io подключения
NEXT_PUBLIC_WS_URL=ws://localhost/ws
```

> Префикс `NEXT_PUBLIC_` обязателен — иначе переменные недоступны в браузере.

---

## Роутинг — App Router

| Путь | Компонент | Описание | Защита |
|------|-----------|----------|--------|
| `/` | `app/page.js` | Редирект на `/dashboard` или `/auth/login` | — |
| `/auth/login` | `app/auth/login/page.js` | Страница логина | Публичная |
| `/auth/register` | `app/auth/register/page.js` | Страница регистрации | Публичная |
| `/dashboard` | `app/dashboard/page.js` | Список досок пользователя | JWT Required |
| `/dashboard/[boardId]` | `app/dashboard/[boardId]/page.js` | Kanban-доска | JWT Required |

### Root layout с AuthGuard

```jsx
// src/app/layout.js
import { AuthGuard } from '@/components/AuthGuard'
import { ThemeProvider } from '@/components/ThemeProvider'
import './globals.css'

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthGuard>
            {children}
          </AuthGuard>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

---

## Компоненты

### BoardView — корневой компонент доски

```jsx
// src/components/board/BoardView.jsx
'use client'

import { useEffect } from 'react'
import { DndContext, closestCorners, DragOverlay } from '@dnd-kit/core'
import { useBoardSocket } from '@/hooks/useBoardSocket'
import { useBoardStore } from '@/store/boardStore'
import Column from './Column'
import TaskCard from './TaskCard'
import ChatSidebar from '../chat/ChatSidebar'
import PresenceAvatars from '../ui/PresenceAvatars'
import BurndownChart from '../stats/BurndownChart'

export default function BoardView({ boardId }) {
  const { board, columns, handleDragEnd, activeTask } = useBoardStore()
  const { onlineUsers } = useBoardSocket(boardId)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Основная область доски */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <BoardHeader board={board} onlineUsers={onlineUsers} />

        <DndContext
          collisionDetection={closestCorners}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 p-4 overflow-x-auto flex-1">
            {columns.map(column => (
              <Column key={column.id} column={column} />
            ))}
          </div>

          <DragOverlay>
            {activeTask && <TaskCard task={activeTask} isDragging />}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Боковая панель чата */}
      <ChatSidebar boardId={boardId} />
    </div>
  )
}
```

### TaskCard — карточка задачи (draggable)

```jsx
// src/components/board/TaskCard.jsx
'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { motion } from 'framer-motion'
import PriorityBadge from '../ui/PriorityBadge'

export default function TaskCard({ task, isDragging = false }) {
  const {
    attributes, listeners, setNodeRef,
    transform, transition, isDragging: isSortableDragging,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.4 : 1,
  }

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`
        bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm
        border border-gray-200 dark:border-gray-700
        cursor-grab active:cursor-grabbing
        hover:shadow-md transition-shadow
        ${isDragging ? 'shadow-xl rotate-2' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {task.title}
        </p>
        <PriorityBadge priority={task.priority} />
      </div>

      {task.deadline && (
        <p className="text-xs text-gray-500 mt-2">
          📅 {new Date(task.deadline).toLocaleDateString()}
        </p>
      )}
    </motion.div>
  )
}
```

---

## Глобальный стейт (Zustand)

### authStore

```js
// src/store/authStore.js
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,          // { id, email, name, role, avatarUrl }
      accessToken: null,
      refreshToken: null,

      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken }),

      logout: () =>
        set({ user: null, accessToken: null, refreshToken: null }),

      isAuthenticated: () => !!get().accessToken,
    }),
    {
      name: 'auth-storage',  // ключ в localStorage
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
```

### boardStore

```js
// src/store/boardStore.js
import { create } from 'zustand'

export const useBoardStore = create((set, get) => ({
  board: null,
  columns: [],          // [{ id, title, position, tasks: [] }]
  activeTask: null,     // задача, которая сейчас перетаскивается

  setBoard: (board) => set({ board }),
  setColumns: (columns) => set({ columns }),

  // Оптимистичное обновление при drag-and-drop
  moveTask: (taskId, fromColId, toColId, newPosition) => {
    set((state) => {
      const columns = state.columns.map(col => ({ ...col, tasks: [...col.tasks] }))
      const fromCol = columns.find(c => c.id === fromColId)
      const toCol   = columns.find(c => c.id === toColId)
      if (!fromCol || !toCol) return state

      const taskIndex = fromCol.tasks.findIndex(t => t.id === taskId)
      const [task] = fromCol.tasks.splice(taskIndex, 1)
      toCol.tasks.splice(newPosition, 0, { ...task, columnId: toColId })

      return { columns }
    })
  },

  // Обработчик dnd-kit onDragEnd
  handleDragEnd: (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    // определить fromColId и toColId из данных active/over
    // вызвать moveTask для оптимистичного обновления
    // вызвать API tasksApi.moveTask(taskId, toColId, position)
  },

  // Добавить задачу (из WebSocket события task:created)
  addTask: (task) => {
    set((state) => ({
      columns: state.columns.map(col =>
        col.id === task.columnId
          ? { ...col, tasks: [...col.tasks, task] }
          : col
      )
    }))
  },

  // Обновить задачу (из WebSocket события task:updated)
  updateTask: (taskId, changes) => {
    set((state) => ({
      columns: state.columns.map(col => ({
        ...col,
        tasks: col.tasks.map(t => t.id === taskId ? { ...t, ...changes } : t)
      }))
    }))
  },

  // Удалить задачу (из WebSocket события task:deleted)
  removeTask: (taskId) => {
    set((state) => ({
      columns: state.columns.map(col => ({
        ...col,
        tasks: col.tasks.filter(t => t.id !== taskId)
      }))
    }))
  },
}))
```

---

## API-клиент — запросы к сервисам

### Axios инстанция с авто-refresh

```js
// src/lib/api.js
import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
})

// Request interceptor — добавить access token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — авто-refresh при 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      const { refreshToken, setAuth, logout } = useAuthStore.getState()

      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
          { refreshToken }
        )
        setAuth(useAuthStore.getState().user, data.accessToken, data.refreshToken)
        original.headers.Authorization = `Bearer ${data.accessToken}`
        return api(original)
      } catch {
        logout()
        window.location.href = '/auth/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api
```

### Auth API

```js
// src/lib/auth.api.js
import api from './api'

export const authApi = {
  register: (data)        => api.post('/auth/register', data),
  login: (data)           => api.post('/auth/login', data),
  me: ()                  => api.get('/auth/me'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refreshToken }),
  logout: ()              => api.post('/auth/logout'),
}
```

### Boards & Tasks API

```js
// src/lib/boards.api.js
import api from './api'

export const boardsApi = {
  getAll: ()              => api.get('/api/boards'),
  getById: (id)           => api.get(`/api/boards/${id}`),
  create: (data)          => api.post('/api/boards', data),
  delete: (id)            => api.delete(`/api/boards/${id}`),
  addColumn: (id, data)   => api.post(`/api/boards/${id}/columns`, data),
  getStats: (id)          => api.get(`/api/boards/${id}/stats`),
}
```

```js
// src/lib/tasks.api.js
import api from './api'

export const tasksApi = {
  getAll: (params)           => api.get('/api/tasks', { params }),
  create: (data)             => api.post('/api/tasks', data),
  update: (id, data)         => api.put(`/api/tasks/${id}`, data),
  move: (id, data)           => api.patch(`/api/tasks/${id}/move`, data),
  delete: (id)               => api.delete(`/api/tasks/${id}`),
  getComments: (id)          => api.get(`/api/tasks/${id}/comments`),
  addComment: (id, data)     => api.post(`/api/tasks/${id}/comments`, data),
  deleteComment: (id, cid)   => api.delete(`/api/tasks/${id}/comments/${cid}`),
}
```

---

## WebSocket — подключение к Realtime Service

### useSocket — базовый хук

```js
// src/hooks/useSocket.js
import { useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import { useAuthStore } from '@/store/authStore'

let socketInstance = null  // синглтон

export function useSocket() {
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    if (!accessToken || socketInstance?.connected) return

    socketInstance = io(process.env.NEXT_PUBLIC_WS_URL, {
      auth: { token: accessToken },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    })

    socketInstance.on('connect_error', (err) => {
      console.error('[socket] Connection error:', err.message)
    })

    return () => {
      // НЕ дисконнектимся при размонтировании компонента — соединение общее
    }
  }, [accessToken])

  return socketInstance
}
```

### useBoardSocket — события конкретной доски

```js
// src/hooks/useBoardSocket.js
import { useEffect, useState } from 'react'
import { useSocket } from './useSocket'
import { useBoardStore } from '@/store/boardStore'
import { toast } from '@/components/ui/Toast'

export function useBoardSocket(boardId) {
  const socket = useSocket()
  const { addTask, updateTask, removeTask, moveTask } = useBoardStore()
  const [onlineUsers, setOnlineUsers] = useState([])

  useEffect(() => {
    if (!socket || !boardId) return

    // Войти в комнату доски
    socket.emit('join:board', { boardId })

    // ─── Обработчики task событий ───────────────────────────────
    socket.on('task:created', ({ task }) => {
      addTask(task)
      toast.info(`Новая задача: ${task.title}`)
    })

    socket.on('task:updated', ({ taskId, changes }) => {
      updateTask(taskId, changes)
    })

    socket.on('task:moved', ({ taskId, fromCol, toCol, position }) => {
      moveTask(taskId, fromCol, toCol, position)
    })

    socket.on('task:deleted', ({ taskId }) => {
      removeTask(taskId)
    })

    // ─── Presence события ───────────────────────────────────────
    socket.on('user:online', ({ users }) => {
      setOnlineUsers(users)
    })

    socket.on('user:joined', ({ userId }) => {
      setOnlineUsers(prev => [...new Set([...prev, userId])])
    })

    socket.on('user:left', ({ userId }) => {
      setOnlineUsers(prev => prev.filter(id => id !== userId))
    })

    return () => {
      socket.emit('leave:board', { boardId })
      socket.off('task:created')
      socket.off('task:updated')
      socket.off('task:moved')
      socket.off('task:deleted')
      socket.off('user:online')
      socket.off('user:joined')
      socket.off('user:left')
    }
  }, [socket, boardId])

  return { onlineUsers }
}
```

---

## Drag-and-Drop (dnd-kit)

Используется `@dnd-kit/core` + `@dnd-kit/sortable`. Задачи — draggable элементы, колонки — droppable контейнеры.

```jsx
// Структура DnD в BoardView.jsx
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'

// В Column.jsx — droppable контейнер
import { useDroppable } from '@dnd-kit/core'

export default function Column({ column }) {
  const { setNodeRef } = useDroppable({ id: column.id })

  return (
    <div ref={setNodeRef} className="...">
      <SortableContext
        items={column.tasks.map(t => t.id)}
        strategy={verticalListSortingStrategy}
      >
        {column.tasks.map(task => (
          <TaskCard key={task.id} task={task} />
        ))}
      </SortableContext>
    </div>
  )
}
```

**Логика `handleDragEnd` в boardStore:**
1. Определить `fromColId` — колонка, откуда взяли задачу
2. Определить `toColId` — колонка, куда бросили
3. Вычислить новый `position` по индексу в массиве
4. Оптимистично обновить стейт (`moveTask`)
5. Вызвать `tasksApi.move(taskId, { columnId: toColId, position })`
6. При ошибке API — откатить стейт к предыдущему состоянию

---

## Аутентификация — токены и OAuth2

### Поток email/password

```
Пользователь → POST /auth/login → accessToken + refreshToken
                                         ↓
                               сохранить в Zustand (persist → localStorage)
                                         ↓
                               Axios interceptor добавляет Bearer в каждый запрос
                                         ↓
                               При 401 → авто-refresh через POST /auth/refresh
```

### Поток OAuth2

```
Пользователь нажимает "Войти через Google"
        ↓
Редирект на GET /auth/google (через Nginx → Auth Service)
        ↓
Google OAuth2 consent screen
        ↓
Callback: GET /auth/google/callback → Auth Service выдаёт токены
        ↓
Редирект на Frontend: /auth/callback?token=...&refreshToken=...
        ↓
Frontend читает токены из URL, сохраняет в Zustand, редирект на /dashboard
```

### OAuthButtons компонент

```jsx
// src/components/auth/OAuthButtons.jsx
export default function OAuthButtons() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL

  return (
    <div className="flex flex-col gap-2">
      <a
        href={`${apiUrl}/auth/google`}
        className="flex items-center justify-center gap-2 w-full py-2 px-4
                   border border-gray-300 dark:border-gray-600 rounded-lg
                   hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        {/* Google SVG icon */}
        <span className="text-sm font-medium">Войти через Google</span>
      </a>

      <a
        href={`${apiUrl}/auth/github`}
        className="flex items-center justify-center gap-2 w-full py-2 px-4
                   bg-gray-900 dark:bg-gray-700 text-white rounded-lg
                   hover:bg-gray-800 transition-colors"
      >
        {/* GitHub SVG icon */}
        <span className="text-sm font-medium">Войти через GitHub</span>
      </a>
    </div>
  )
}
```

---

## Тёмная тема (Tailwind)

Tailwind настроен на режим `class` — тема переключается добавлением класса `dark` на `<html>`.

### tailwind.config.js

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#eef2ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        }
      }
    }
  },
  plugins: [],
}
```

### ThemeProvider

```jsx
// src/components/ThemeProvider.jsx
'use client'

import { createContext, useContext, useEffect } from 'react'
import { useUIStore } from '@/store/uiStore'

const ThemeContext = createContext({})

export function ThemeProvider({ children }) {
  const { theme, setTheme } = useUIStore()

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

### ThemeToggle

```jsx
// src/components/ui/ThemeToggle.jsx
'use client'

import { useUIStore } from '@/store/uiStore'

export default function ThemeToggle() {
  const { theme, setTheme } = useUIStore()

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800
                 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}
```

---

## Анимации (Framer Motion)

```jsx
// Появление и исчезновение карточек задач — AnimatePresence
import { AnimatePresence, motion } from 'framer-motion'

// В Column.jsx — обернуть список задач
<AnimatePresence>
  {column.tasks.map(task => (
    <motion.div
      key={task.id}
      initial={{ opacity: 0, height: 0, y: -10 }}
      animate={{ opacity: 1, height: 'auto', y: 0 }}
      exit={{ opacity: 0, height: 0, scale: 0.95 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <TaskCard task={task} />
    </motion.div>
  ))}
</AnimatePresence>

// Появление модального окна
const modalVariants = {
  hidden:  { opacity: 0, scale: 0.95, y: 20 },
  visible: { opacity: 1, scale: 1,    y: 0   },
  exit:    { opacity: 0, scale: 0.95, y: 20  },
}

<motion.div
  variants={modalVariants}
  initial="hidden"
  animate="visible"
  exit="exit"
  transition={{ duration: 0.2 }}
>
  <TaskModal task={task} />
</motion.div>
```

---

## Burn-down Chart (Recharts)

```jsx
// src/components/stats/BurndownChart.jsx
'use client'

import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { boardsApi } from '@/lib/boards.api'

export default function BurndownChart({ boardId }) {
  const [data, setData] = useState([])

  useEffect(() => {
    boardsApi.getStats(boardId).then(({ data }) => {
      setData(data.burndown)
    })
  }, [boardId])

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
        Burn-down Chart
      </h3>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#9ca3af' }}
          />
          <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: 'none',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="remaining"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ fill: '#6366f1' }}
            name="Оставшиеся задачи"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

---

## Зависимости (npm)

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "axios": "^1.6.0",
    "socket.io-client": "^4.7.0",
    "zustand": "^4.5.0",
    "@dnd-kit/core": "^6.1.0",
    "@dnd-kit/sortable": "^8.0.0",
    "@dnd-kit/utilities": "^3.2.0",
    "framer-motion": "^11.0.0",
    "recharts": "^2.10.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "@types/node": "^20.0.0"
  }
}
```

---

## Взаимодействие с другими сервисами

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                Next.js 15 — порт 3000                            │
└────────┬────────────────────┬─────────────────────┬─────────────┘
         │                    │                     │
         │ REST (через Nginx)  │ REST (через Nginx)  │ WebSocket
         │ /auth/*             │ /api/*              │ /ws
         │ Authorization:      │ Authorization:      │ auth.token
         │ Bearer <token>      │ Bearer <token>      │ (JWT)
         ▼                    ▼                     ▼
┌──────────────┐   ┌──────────────────┐   ┌────────────────────┐
│ Auth Service │   │  Task Service    │   │ Realtime Service   │
│  порт 3001   │   │   порт 3002      │   │    порт 3003       │
│              │   │                  │   │                    │
│ /auth/login  │   │ /api/boards      │   │ join:board         │
│ /auth/me     │   │ /api/tasks       │   │ task:moved         │
│ /auth/google │   │ /api/tasks/move  │   │ task:created       │
│ /auth/refresh│   │ /api/.../stats   │   │ chat:message       │
└──────────────┘   └──────────────────┘   └────────────────────┘
```

**Все REST запросы** идут через Nginx API Gateway — Frontend никогда не обращается напрямую к сервисам по портам 3001/3002/3003.

**WebSocket** подключается через Nginx (`/ws` → `realtime:3003`) — аутентификация через `auth.token` в handshake.

**Авто-refresh токенов** — Axios interceptor автоматически обновляет `accessToken` при получении 401, без участия пользователя.

---

*Frontend | Real-Time Collaborative Dashboard | 2026*

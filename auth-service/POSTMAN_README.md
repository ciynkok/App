# Postman Collection для Auth Service API

## 📋 Обзор

Коллекция содержит все endpoints для тестирования Auth Service API:

- **Authentication** — регистрация, логин, обновление токенов, logout
- **OAuth2** — авторизация через Google и GitHub
- **Inter-Service** — валидация токенов для межсервисного общения
- **Health Check** — проверка статуса сервиса
- **Test Scenarios** — негативные тесты для проверки валидации

## 🚀 Установка

### Импорт коллекции в Postman

1. Откройте **Postman**
2. Нажмите **Import** (левый верхний угол)
3. Выберите файл `postman_collection.json`
4. Коллекция появится в списке

### Настройка переменных

После импорта настройте переменные коллекции:

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `base_url` | `http://localhost:3001` | URL auth-service |
| `user_email` | `test@example.com` | Email для тестов |
| `user_password` | `TestPassword123!` | Пароль для тестов |
| `user_name` | `Test User` | Имя пользователя |
| `service_api_key` | ваш API ключ | Ключ для межсервисного общения |

> **Примечание:** `access_token`, `refresh_token`, `user_id` устанавливаются автоматически после успешной регистрации/логина.

## 📝 Использование

### Быстрый старт

1. **Запустите сервисы:**
   ```bash
   docker-compose up -d
   ```

2. **Проверьте health:**
   - Запрос: `Health Check`
   - Ожидаемый ответ: `{"status": "healthy", "service": "auth"}`

3. **Зарегистрируйте пользователя:**
   - Запрос: `Authentication → Register`
   - Токены сохранятся в переменные автоматически

4. **Получите данные пользователя:**
   - Запрос: `Authentication → Get Current User (Me)`

### Основные сценарии

#### Регистрация и логин
```
Register → Login → Get Me → Refresh Token → Logout
```

#### OAuth2 (требует настройки в .env)
```
Google Login → (авторизация в браузере) → Callback
GitHub Login → (авторизация в браузере) → Callback
```

#### Межсервисное взаимодействие
```
Validate Token (с Authorization + X-API-Key заголовками)
```

## 🧪 Тестовые сценарии

Коллекция включает негативные тесты в папке **Test Scenarios**:

| Запрос | Описание | Ожидаемый статус |
|--------|----------|------------------|
| Register with weak password | Пароль < 8 символов | 422 |
| Register with invalid email | Некорректный email | 422 |
| Login with wrong password | Неверный пароль | 401 |
| Register duplicate email | Email уже существует | 409 |
| Get Me without token | Без Authorization | 401 |
| Validate Token without API Key | Без X-API-Key | 403 |
| Refresh with invalid token | Неверный refresh | 401 |

## 🔑 OAuth2 Настройка

Для тестирования Google/GitHub OAuth добавьте в `.env` auth-service:

```env
# Google
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CALLBACK_URL=http://localhost/auth/google/callback

# GitHub
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_CALLBACK_URL=http://localhost/auth/github/callback
```

## 📊 Структура коллекции

```
Auth Service API
├── Authentication
│   ├── Register
│   ├── Login
│   ├── Refresh Token
│   ├── Logout
│   └── Get Current User (Me)
├── OAuth2
│   ├── Google Login (Redirect)
│   ├── Google Callback
│   ├── GitHub Login (Redirect)
│   └── GitHub Callback
├── Inter-Service
│   └── Validate Token
├── Health Check
└── Test Scenarios
    ├── Register with weak password (should fail)
    ├── Register with invalid email (should fail)
    ├── Login with wrong password (should fail)
    ├── Register duplicate email (should fail)
    ├── Get Me without token (should fail)
    ├── Validate Token without API Key (should fail)
    └── Refresh with invalid token (should fail)
```

## 💡 Советы

- **Автоматическое сохранение токенов:** После Register/Login токены сохраняются в переменные коллекции
- **Использование токена:** В запросах с авторизацией используется `{{access_token}}`
- **Сброс токенов:** Очистите переменные `access_token` и `refresh_token` для тестирования без авторизации

## 🔗 API Endpoints

| Метод | Endpoint | Описание | Auth |
|-------|----------|----------|------|
| POST | `/auth/register` | Регистрация нового пользователя | ❌ |
| POST | `/auth/login` | Логин по email и паролю | ❌ |
| POST | `/auth/refresh` | Обновление access токена | ❌ |
| POST | `/auth/logout` | Выход из системы | ✅ |
| GET | `/auth/me` | Данные текущего пользователя | ✅ |
| GET | `/auth/google` | Редирект на Google OAuth | ❌ |
| GET | `/auth/google/callback` | Callback Google OAuth | ❌ |
| GET | `/auth/github` | Редирект на GitHub OAuth | ❌ |
| GET | `/auth/github/callback` | Callback GitHub OAuth | ❌ |
| POST | `/auth/validate` | Валидация токена (inter-service) | API Key |
| GET | `/health` | Проверка статуса сервиса | ❌ |

## ⚠️ Важно

- Не коммитьте `.env` файлы с реальными секретами
- Для production используйте CI/CD secrets manager
- collection.json можно коммитить (не содержит секретов)

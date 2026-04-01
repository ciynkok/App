-- Auth Schema Initialization
-- Схема для сервиса аутентификации

-- Подключение к базе данных auth_db
\c auth_db

CREATE SCHEMA IF NOT EXISTS auth;

-- Пользователи
CREATE TABLE IF NOT EXISTS auth.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name        VARCHAR(255) NOT NULL,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_idx ON auth.users(email);

-- Refresh токены
CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- OAuth аккаунты
CREATE TABLE IF NOT EXISTS auth.oauth_accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider    VARCHAR(20) NOT NULL CHECK (provider IN ('google', 'github')),
    provider_id VARCHAR(255) NOT NULL,
    access_token TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS oauth_accounts_provider_idx ON auth.oauth_accounts(provider, provider_id);

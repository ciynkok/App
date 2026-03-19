import os
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


# Поиск .env файла: сначала в корневой директории проекта, затем в директории сервиса
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # auth-service/
ROOT_DIR = BASE_DIR.parent  # проект App/
ROOT_ENV = ROOT_DIR / ".env"
SERVICE_ENV = BASE_DIR / ".env"


class Settings(BaseSettings):
    # PostgreSQL
    AUTH_DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_EXPIRES_IN: str = "1h"
    JWT_ALGORITHM: str = "HS256"

    # Refresh Token
    REFRESH_TOKEN_SECRET: str
    REFRESH_TOKEN_EXPIRES_IN: str = "30d"

    # OAuth2 - Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALLBACK_URL: str = "http://localhost/auth/google/callback"

    # OAuth2 - GitHub
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_CALLBACK_URL: str = "http://localhost/auth/github/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Inter-service communication
    SERVICE_API_KEY: Optional[str] = None

    # Common
    NODE_ENV: str = "development"
    PORT: int = 3001

    class Config:
        # Читаем оба файла: локальный переопределяет корневой
        # Приоритет: env vars > service .env > root .env > defaults
        env_file = [
            str(ROOT_ENV),     # Сначала корневой (общие настройки)
            str(SERVICE_ENV),  # Потом локальный (переопределяет auth-specific)
        ]
        case_sensitive = True


settings = Settings()

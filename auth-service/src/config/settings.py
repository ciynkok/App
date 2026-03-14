import os
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


# Поиск .env файла: сначала в корневой директории проекта, затем в директории сервиса
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # auth-service/
ROOT_DIR = BASE_DIR.parent  # проект App/
ROOT_ENV = ROOT_DIR / ".env"
SERVICE_ENV = BASE_DIR / ".env"

# Используем корневой .env если он существует
env_file = str(ROOT_ENV if ROOT_ENV.exists() else SERVICE_ENV)


class Settings(BaseSettings):
    # PostgreSQL
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET: str
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

    # Common
    NODE_ENV: str = "development"
    PORT: int = 3001

    class Config:
        env_file = env_file
        case_sensitive = True


settings = Settings()

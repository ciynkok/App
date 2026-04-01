"""
Configuration module for Realtime Service.
Loads environment variables and provides application settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Realtime Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 3003

    # Redis
    redis_url: str = "redis://redis:6379"

    # JWT (общий с auth-service и task-service)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # CORS
    frontend_url: str = "http://localhost:3000"
    
    @property
    def cors_origins(self) -> list:
        """List of allowed CORS origins."""
        return [self.frontend_url]

    # Настройки чата
    chat_history_ttl: int = 86400  # 24 часа
    chat_history_max_messages: int = 100

    # Настройки блокировки
    task_lock_ttl: int = 30

    # Inter-service API Key (для внутренних webhook)
    service_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

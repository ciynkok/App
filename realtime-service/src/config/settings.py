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
    debug: bool = True

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
    frontend_url_alt: str = "http://localhost"
    cors_origins_raw: Optional[str] = None

    @property
    def cors_origins(self):
        """Allowed CORS origins for Socket.IO.

        Returns "*" (wildcard) if CORS_ORIGINS_RAW=="*" — useful for LAN testing
        where the browser reaches nginx by the host IP. Otherwise returns a list.
        """
        if self.cors_origins_raw:
            raw = self.cors_origins_raw.strip()
            if raw == "*":
                return "*"
            origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        else:
            origins = [
                self.frontend_url,
                self.frontend_url_alt,
                "http://127.0.0.1:3000",
                "http://127.0.0.1",
            ]

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(origins))

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

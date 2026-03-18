"""
Configuration module for Task Service.
Loads environment variables and provides application settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Task Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 3002

    # Database
    task_database_url: str

    # Auth Service
    auth_service_url: str = "http://auth-service:3001"
    auth_service_verify_endpoint: str = "/auth/verify"

    # Real-time Service
    realtime_service_url: str = "http://realtime-service:3003"
    realtime_webhook_endpoint: str = "/api/webhooks/task-events"

    # JWT (общий с auth-service)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Scheduler
    scheduler_enabled: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

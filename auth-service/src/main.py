from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.database import engine, Base
#from src.config.oauth import configure_oauth
from src.routes import auth
from src.config.settings import settings


async def create_tables():
    """Создание таблиц в БД"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_app() -> FastAPI:
    """Создание и настройка FastAPI приложения"""

    app = FastAPI(
        title="Auth Service",
        description="Сервис аутентификации и авторизации",
        version="1.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:80",
            "http://localhost",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Настройка OAuth
    #configure_oauth()

    # Создание таблиц при старте
    @app.on_event("startup")
    async def on_startup():
        await create_tables()

    # Регистрация роутов
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "auth"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)

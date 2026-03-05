"""
Main application entry point for Task Service.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database import init_db, close_db
from src.scheduler import deadline_scheduler
from src.routers import boards, columns, tasks, comments, analytics


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Task Service...")
    await init_db()
    deadline_scheduler.start()
    logger.info("Task Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Task Service...")
    deadline_scheduler.stop()
    await close_db()
    logger.info("Task Service shut down successfully")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Task Service - Manages boards, tasks, columns, and comments",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(boards.router)
app.include_router(columns.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cmd.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

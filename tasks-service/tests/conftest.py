"""
Pytest configuration and fixtures for Task Service tests.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from cmd.main import app
from src.models import Base
from src.database import get_db


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)


# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.
    
    Yields:
        AsyncSession: Test database session
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test HTTP client.
    
    Args:
        db_session: Test database session
        
    Yields:
        AsyncClient: Test HTTP client
    """
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user_id() -> str:
    """
    Mock user ID for testing.
    
    Returns:
        str: Mock user ID
    """
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_board_id() -> str:
    """
    Mock board ID for testing.
    
    Returns:
        str: Mock board ID
    """
    return "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def mock_task_id() -> str:
    """
    Mock task ID for testing.
    
    Returns:
        str: Mock task ID
    """
    return "00000000-0000-0000-0000-000000000003"

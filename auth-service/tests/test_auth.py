"""
Tests for Auth API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "auth"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session):
    """Test user registration."""
    user_data = {
        "email": "test@example.com",
        "password": "TestPass123!",
        "name": "Test User"
    }

    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert "user" in data
    assert data["user"]["email"] == user_data["email"]
    assert data["user"]["name"] == user_data["name"]
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session):
    """Test registration with duplicate email."""
    user_data = {
        "email": "test@example.com",
        "password": "TestPass123!",
        "name": "Test User"
    }

    # First registration
    response1 = await client.post("/auth/register", json=user_data)
    assert response1.status_code == 201

    # Duplicate registration
    response2 = await client.post("/auth/register", json=user_data)
    assert response2.status_code == 409

    data = response2.json()
    assert data["detail"]["error"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email."""
    user_data = {
        "email": "invalid-email",
        "password": "TestPass123!",
        "name": "Test User"
    }

    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration with short password."""
    user_data = {
        "email": "test@example.com",
        "password": "short",
        "name": "Test User"
    }

    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, db_session):
    """Test user login."""
    # First register
    register_data = {
        "email": "login@example.com",
        "password": "TestPass123!",
        "name": "Login User"
    }
    await client.post("/auth/register", json=register_data)

    # Then login
    login_data = {
        "email": "login@example.com",
        "password": "TestPass123!"
    }

    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["user"]["email"] == login_data["email"]


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, db_session):
    """Test login with invalid credentials."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "WrongPass123!"
    }

    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 401

    data = response.json()
    assert data["detail"]["error"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session):
    """Test login with wrong password."""
    # First register
    register_data = {
        "email": "test2@example.com",
        "password": "TestPass123!",
        "name": "Test User"
    }
    await client.post("/auth/register", json=register_data)

    # Login with wrong password
    login_data = {
        "email": "test2@example.com",
        "password": "WrongPassword!"
    }

    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session):
    """Test token refresh."""
    # Register and get tokens
    register_data = {
        "email": "refresh@example.com",
        "password": "TestPass123!",
        "name": "Refresh User"
    }
    register_response = await client.post("/auth/register", json=register_data)
    refresh_token = register_response.json()["refreshToken"]

    # Refresh access token
    refresh_data = {
        "refreshToken": refresh_token
    }

    response = await client.post("/auth/refresh", json=refresh_data)
    assert response.status_code == 200

    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Test refresh with invalid token."""
    refresh_data = {
        "refreshToken": "invalid-token"
    }

    response = await client.post("/auth/refresh", json=refresh_data)
    assert response.status_code == 401

    data = response.json()
    assert data["detail"]["error"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Test get me without authentication."""
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db_session):
    """Test user logout."""
    # Register and get access token
    register_data = {
        "email": "logout@example.com",
        "password": "TestPass123!",
        "name": "Logout User"
    }
    register_response = await client.post("/auth/register", json=register_data)
    access_token = register_response.json()["accessToken"]

    # Logout
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/auth/logout", headers=headers)
    assert response.status_code == 204

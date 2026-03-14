from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from src.config.database import get_db
from src.config.oauth import oauth
from src.services.token import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    hash_token,
)
from src.services.user import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    find_or_create_oauth_user,
)
from src.models.user import Provider, Role
from src.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    AuthResponse,
    UserResponse,
    TokenResponse,
)
from src.middleware.auth import check_auth
from src.config.redis import redis_client
from src.config.settings import settings
from datetime import datetime, timedelta

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(password, hashed_password)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверка существующего пользователя
    existing_user = await get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "EMAIL_TAKEN",
                "message": "Email is already registered",
            },
        )

    # Создание пользователя
    password_hash = hash_password(request.password)
    user = await create_user(
        db,
        email=request.email,
        password_hash=password_hash,
        name=request.name,
    )

    # Генерация токенов
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Сохранение refresh токена в Redis
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    await redis_client.setex(
        f"auth:refresh:{str(user.id)}",
        int((expires_at - datetime.utcnow()).total_seconds()),
        token_hash,
    )

    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Логин по email и паролю"""
    user = await get_user_by_email(db, request.email)

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_CREDENTIALS",
                "message": "Email or password is incorrect",
            },
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_CREDENTIALS",
                "message": "Email or password is incorrect",
            },
        )

    # Генерация токенов
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Сохранение refresh токена в Redis
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    await redis_client.setex(
        f"auth:refresh:{str(user.id)}",
        int((expires_at - datetime.utcnow()).total_seconds()),
        token_hash,
    )

    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    request: Request,
    user: dict = Depends(check_auth),
    db: AsyncSession = Depends(get_db),
):
    """Получение данных текущего пользователя"""
    db_user = await get_user_by_id(db, user["sub"])

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "USER_NOT_FOUND", "message": "User not found"},
        )

    return UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        name=db_user.name,
        avatar_url=db_user.avatar_url,
        role=db_user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Обновление access токена по refresh токену"""
    payload = verify_refresh_token(request.refreshToken)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid or expired refresh token",
            },
        )

    user_id = payload.get("sub")
    db_user = await get_user_by_id(db, user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "User not found",
            },
        )

    # Проверка refresh токена в Redis
    stored_hash = await redis_client.get(f"auth:refresh:{user_id}")
    if not stored_hash or stored_hash != hash_token(request.refreshToken):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Refresh token is invalid",
            },
        )

    # Генерация новых токенов
    new_access_token = create_access_token(db_user)
    new_refresh_token = create_refresh_token(db_user)

    # Обновление refresh токена в Redis
    new_token_hash = hash_token(new_refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    await redis_client.setex(
        f"auth:refresh:{user_id}",
        int((expires_at - datetime.utcnow()).total_seconds()),
        new_token_hash,
    )

    return TokenResponse(
        accessToken=new_access_token,
        refreshToken=new_refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    user: dict = Depends(check_auth),
    db: AsyncSession = Depends(get_db),
):
    """Выход из системы (инвалидация токенов)"""
    jti = user.get("jti")

    # Добавление access токена в blacklist
    if jti:
        # Получаем оставшееся время жизни токена
        exp = user.get("exp")
        if exp:
            ttl = max(0, exp - int(datetime.utcnow().timestamp()))
            await redis_client.setex(f"auth:blacklist:{jti}", ttl, "revoked")

    # Удаление refresh токена из Redis
    user_id = user.get("sub")
    await redis_client.delete(f"auth:refresh:{user_id}")

    return None


# OAuth2 endpoints
@router.get("/google")
async def google_login(request: Request):
    """Редирект на Google OAuth2"""
    google_oauth = oauth.create_client("google")
    if not google_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_NOT_CONFIGURED", "message": "Google OAuth is not configured"},
        )

    return await google_oauth.authorize_redirect(
        request, settings.GOOGLE_CALLBACK_URL
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Callback после авторизации через Google"""
    google_oauth = oauth.create_client("google")
    if not google_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_NOT_CONFIGURED", "message": "Google OAuth is not configured"},
        )

    token = await google_oauth.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_FAILED", "message": "Failed to get user info"},
        )

    # Находим или создаём пользователя
    db_user = await find_or_create_oauth_user(
        db,
        provider=Provider.google,
        provider_id=user_info.get("sub"),
        email=user_info.get("email"),
        name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )

    # Генерация токенов
    access_token = create_access_token(db_user)
    refresh_token = create_refresh_token(db_user)

    # Сохранение refresh токена в Redis
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    await redis_client.setex(
        f"auth:refresh:{str(db_user.id)}",
        int((expires_at - datetime.utcnow()).total_seconds()),
        token_hash,
    )

    # Редирект на frontend с токенами
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}&refreshToken={refresh_token}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


@router.get("/github")
async def github_login(request: Request):
    """Редирект на GitHub OAuth2"""
    github_oauth = oauth.create_client("github")
    if not github_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_NOT_CONFIGURED", "message": "GitHub OAuth is not configured"},
        )

    return await github_oauth.authorize_redirect(
        request, settings.GITHUB_CALLBACK_URL
    )


@router.get("/github/callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Callback после авторизации через GitHub"""
    github_oauth = oauth.create_client("github")
    if not github_oauth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_NOT_CONFIGURED", "message": "GitHub OAuth is not configured"},
        )

    token = await github_oauth.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "OAUTH_FAILED", "message": "Failed to get user info"},
        )

    # Находим или создаём пользователя
    db_user = await find_or_create_oauth_user(
        db,
        provider=Provider.github,
        provider_id=str(user_info.get("id")),
        email=user_info.get("email"),
        name=user_info.get("name"),
        avatar_url=user_info.get("avatar_url"),
    )

    # Генерация токенов
    access_token = create_access_token(db_user)
    refresh_token = create_refresh_token(db_user)

    # Сохранение refresh токена в Redis
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=30)
    await redis_client.setex(
        f"auth:refresh:{str(db_user.id)}",
        int((expires_at - datetime.utcnow()).total_seconds()),
        token_hash,
    )

    # Редирект на frontend с токенами
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}&refreshToken={refresh_token}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)

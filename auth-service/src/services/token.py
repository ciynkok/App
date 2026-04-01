import uuid
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.config.settings import settings
from src.models.user import User


def create_access_token(user: User) -> str:
    """Создание JWT access токена"""
    jti = str(uuid.uuid4())
    expires_delta = parse_timedelta(settings.JWT_EXPIRES_IN)
    now = datetime.utcnow()

    payload = {
        "sub": str(user.id),
        "email": user.email,

        "role": getattr(user, 'role', 'user'),  # Добавить role

        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user: User) -> str:
    """Создание JWT refresh токена"""
    jti = str(uuid.uuid4())
    expires_delta = parse_timedelta(settings.REFRESH_TOKEN_EXPIRES_IN)
    now = datetime.utcnow()

    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Проверка JWT access токена"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict:
    """Проверка JWT refresh токена"""
    try:
        payload = jwt.decode(
            token, settings.REFRESH_TOKEN_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Хеширование токена для безопасного хранения"""
    return hashlib.sha256(token.encode()).hexdigest()


def parse_timedelta(delta_str: str) -> timedelta:
    """Парсинг строки времени (например, '1h', '30d') в timedelta"""
    unit = delta_str[-1].lower()
    value = int(delta_str[:-1])

    units = {
        "s": timedelta(seconds=value),
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
    }

    return units.get(unit, timedelta(hours=1))

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.token import verify_access_token
from src.config.redis import redis_client


security = HTTPBearer(auto_error=False)


async def check_auth(
    request: Request, credentials: HTTPAuthorizationCredentials = security
) -> dict:
    """
    Middleware для проверки JWT токена.
    Устанавливает user в request.state при успешной проверке.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required"},
        )

    token = credentials.credentials
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid or expired token",
            },
        )

    # Проверка blacklist
    jti = payload.get("jti")
    if jti:
        is_revoked = await redis_client.get(f"auth:blacklist:{jti}")
        if is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TOKEN_REVOKED",
                    "message": "Token has been revoked",
                },
            )

    request.state.user = payload
    return payload

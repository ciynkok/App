"""
WebSocket authentication middleware.
Validates JWT token from WebSocket connection.
"""
import jwt
from fastapi import WebSocket
from src.config.settings import settings


class WebSocketAuthenticationError(Exception):
    """Raised when WebSocket authentication fails."""

    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        super().__init__(self.message)


async def authenticate_websocket(websocket: WebSocket) -> dict:
    """
    Authenticate WebSocket connection using JWT token.

    Token is expected in query params: ?token=<jwt_token>

    Args:
        websocket: WebSocket connection

    Returns:
        dict: User payload with id, role, email

    Raises:
        WebSocketAuthenticationError: If authentication fails
    """
    token = websocket.query_params.get("token")

    if not token:
        raise WebSocketAuthenticationError("Token missing")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Validate required fields
        if "sub" not in payload or "role" not in payload:
            raise WebSocketAuthenticationError("Invalid token payload")

        return {
            "id": payload["sub"],
            "role": payload["role"],
            "email": payload.get("email", ""),
        }

    except jwt.ExpiredSignatureError:
        raise WebSocketAuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise WebSocketAuthenticationError("Invalid token")
    except KeyError:
        raise WebSocketAuthenticationError("Invalid token payload")

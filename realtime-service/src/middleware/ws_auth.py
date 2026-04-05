"""
Socket.IO authentication middleware.
Validates JWT token from Socket.IO connection.
"""
import jwt
from urllib.parse import parse_qs

from src.config.settings import settings


class SocketAuthenticationError(Exception):
    """Raised when Socket.IO authentication fails."""

    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        super().__init__(self.message)


def _extract_token(environ: dict, auth: dict | None) -> str | None:
    """
    Extract JWT token from Socket.IO connection.

    Token can come from:
    - auth dict: { token: "<jwt_token>" } (client auth option)
    - query string: ?token=<jwt_token> (WebSocket transport)
    """
    # 1. Check auth dict first
    if auth and isinstance(auth, dict):
        token = auth.get("token")
        if token:
            return token

    # 2. Parse from query string (ASGI environ)
    # In ASGI, query_string is bytes under key "query_string"
    qs_bytes = environ.get("QUERY_STRING", b"")
    if isinstance(qs_bytes, bytes):
        qs_str = qs_bytes.decode("utf-8")
    else:
        qs_str = str(qs_bytes)

    if qs_str:
        parsed = parse_qs(qs_str)
        token_list = parsed.get("token")
        if token_list:
            return token_list[0]

    return None


async def authenticate_socket(environ: dict, auth: dict | None) -> dict | None:
    """
    Authenticate Socket.IO connection using JWT token.

    Args:
        environ: ASGI scope dict (contains query_string)
        auth: Optional auth dict from Socket.IO client

    Returns:
        dict: User payload with id, role, email — or None if auth fails
    """
    import logging
    logger = logging.getLogger(__name__)

    token = _extract_token(environ, auth)
    logger.warning(f"Auth debug: token={'present' if token else 'MISSING'}, auth={auth}")

    if not token:
        logger.warning(f"Auth debug: No token found. environ keys={list(environ.keys())}")
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        logger.warning(f"Auth debug: JWT decoded OK, sub={payload.get('sub')}")

        # Validate required fields
        if "sub" not in payload or "role" not in payload:
            logger.warning(f"Auth debug: Missing fields in payload: {payload.keys()}")
            return None

        return {
            "id": payload["sub"],
            "role": payload["role"],
            "email": payload.get("email", ""),
        }

    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Auth debug: Token expired: {e}")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Auth debug: Invalid token: {e}")
        return None
    except KeyError as e:
        logger.warning(f"Auth debug: KeyError: {e}")
        return None

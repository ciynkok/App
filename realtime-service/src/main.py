"""
Realtime Service - Socket.IO server.
Manages WebSocket connections via Socket.IO, broadcasts task events, chat, and presence.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI

from src.config.settings import settings
from src.config.redis import redis_client
from src.middleware.ws_auth import authenticate_socket
from src.routes import internal
from src.services.pubsub import pubsub_service

# Create Socket.IO server instance
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.cors_origins,
    logger=settings.debug,
    engineio_logger=True,
)

# Socket.IO ASGI app
socketio_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=None,  # We'll mount FastAPI routes separately
)


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def emit_board_sync(sid: str, board_id: str):
    """Send chat history and presence snapshot to one socket."""
    from src.services.chat import get_chat_history
    from src.services.presence import get_online_users

    history = await get_chat_history(board_id)
    await sio.emit("chat:history", {
        "boardId": board_id,
        "messages": history,
    }, room=sid)

    online_users = await get_online_users(board_id)
    await sio.emit("user:online", {
        "boardId": board_id,
        "users": list(online_users),
    }, room=sid)


# ─── Socket.IO Event Handlers ───────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None):
    """Handle new Socket.IO connection."""
    # Authenticate
    print(f"!!! CONNECT HANDLER CALLED !!! sid={sid}")
    print(f"!!! environ keys: {list(environ.keys())}")
    print(f"!!! auth: {auth}")
    
    logger.info(f"=== CONNECT START === sid={sid}")
    logger.info(f"environ keys: {list(environ.keys())}")
    logger.info(f"auth dict: {auth}")
    user = await authenticate_socket(environ, auth)
    if user is None:
        logger.warning(f"Socket.IO connect rejected: auth failed for {sid}")
        return False

    # Attach user info to session
    await sio.save_session(sid, {"user": user})
    logger.info(f"Socket.IO connected: sid={sid}, user={user.get('id')}")
    return True


@sio.event
async def disconnect(sid: str):
    """Handle Socket.IO disconnection."""
    session = await sio.get_session(sid)
    user = session.get("user", {})
    board_id = session.get("board_id")

    logger.info(f"Socket.IO disconnected: sid={sid}, user={user.get('id')}")

    # Clean up presence if user was on a board
    if board_id and user.get("id"):
        from src.services.presence import remove_user_from_board
        await remove_user_from_board(board_id, user["id"])

        # Notify others
        await sio.emit("user:left", {
            "userId": user["id"],
            "boardId": board_id,
        }, room=f"board:{board_id}")


@sio.on("join:board")
async def handle_join(sid: str, data: dict):
    """Handle join:board event."""
    board_id = data.get("boardId")
    if not board_id:
        await sio.emit("error", {"message": "boardId is required"}, room=sid)
        return

    session = await sio.get_session(sid)
    user = session.get("user", {})
    user_id = user.get("id")

    # Join Socket.IO room
    await sio.enter_room(sid, f"board:{board_id}")
    session["board_id"] = board_id
    await sio.save_session(sid, session)

    # Add user to presence
    if user_id:
        from src.services.presence import add_user_to_board, is_user_online

        already_online = await is_user_online(board_id, user_id)
        await add_user_to_board(board_id, user_id)
        await emit_board_sync(sid, board_id)

        if not already_online:
            await sio.emit("user:joined", {
                "userId": user_id,
                "boardId": board_id,
                "name": user.get("email", "Anonymous"),
            }, room=f"board:{board_id}")


@sio.on("leave:board")
async def handle_leave(sid: str, data: dict):
    """Handle leave:board event."""
    board_id = data.get("boardId")
    if not board_id:
        await sio.emit("error", {"message": "boardId is required"}, room=sid)
        return

    session = await sio.get_session(sid)
    user = session.get("user", {})
    user_id = user.get("id")

    # Remove from presence
    if user_id:
        from src.services.presence import remove_user_from_board
        await remove_user_from_board(board_id, user_id)

        await sio.emit("user:left", {
            "userId": user_id,
            "boardId": board_id,
        }, room=f"board:{board_id}")

    # Leave room
    await sio.leave_room(sid, f"board:{board_id}")
    session["board_id"] = None
    await sio.save_session(sid, session)


@sio.on("chat:sync")
async def handle_chat_sync(sid: str, data: dict):
    """Send current chat state for an already joined board."""
    board_id = data.get("boardId")
    if not board_id:
        await sio.emit("error", {"message": "boardId is required"}, room=sid)
        return

    session = await sio.get_session(sid)
    if session.get("board_id") != board_id:
        await sio.emit("error", {"message": "Join board before requesting chat sync"}, room=sid)
        return

    await emit_board_sync(sid, board_id)


@sio.on("chat:message")
async def handle_chat_message(sid: str, data: dict):
    """Handle chat:message event."""
    from datetime import datetime

    board_id = data.get("boardId")
    text = data.get("text")

    if not board_id or not text:
        await sio.emit("error", {"message": "boardId and text are required"}, room=sid)
        return

    session = await sio.get_session(sid)
    user = session.get("user", {})
    user_id = user.get("id")
    user_email = user.get("email", "Anonymous")

    if not user_id:
        await sio.emit("error", {"message": "User not authenticated"}, room=sid)
        return

    # Create message
    message = {
        "from": user_id,
        "name": user_email,
        "text": text.strip(),
        "boardId": board_id,
        "ts": datetime.utcnow().isoformat(),
    }

    # Save to Redis
    from src.services.chat import save_chat_message
    await save_chat_message(board_id, message)

    # Broadcast to all in room (including sender)
    await sio.emit("chat:message", message, room=f"board:{board_id}")


@sio.on("task:lock")
async def handle_task_lock(sid: str, data: dict):
    """Handle task:lock event."""
    board_id = data.get("boardId")
    task_id = data.get("taskId")

    if not board_id or not task_id:
        await sio.emit("error", {"message": "boardId and taskId are required"}, room=sid)
        return

    session = await sio.get_session(sid)
    user = session.get("user", {})
    user_id = user.get("id")

    if not user_id:
        await sio.emit("error", {"message": "User not authenticated"}, room=sid)
        return

    from src.services.lock import lock_task
    acquired = await lock_task(board_id, task_id, user_id)

    if acquired:
        await sio.emit("task:locked", {
            "taskId": task_id,
            "boardId": board_id,
            "userId": user_id,
        }, room=f"board:{board_id}")
    else:
        await sio.emit("task:lock:failed", {
            "taskId": task_id,
            "boardId": board_id,
            "message": "Task is already locked",
        }, room=sid)


@sio.on("task:unlock")
async def handle_task_unlock(sid: str, data: dict):
    """Handle task:unlock event."""
    board_id = data.get("boardId")
    task_id = data.get("taskId")

    if not board_id or not task_id:
        await sio.emit("error", {"message": "boardId and taskId are required"}, room=sid)
        return

    session = await sio.get_session(sid)
    user = session.get("user", {})
    user_id = user.get("id")

    if not user_id:
        await sio.emit("error", {"message": "User not authenticated"}, room=sid)
        return

    from src.services.lock import unlock_task
    released = await unlock_task(board_id, task_id, user_id)

    if released:
        await sio.emit("task:unlocked", {
            "taskId": task_id,
            "boardId": board_id,
        }, room=f"board:{board_id}")
    else:
        await sio.emit("task:unlock:failed", {
            "taskId": task_id,
            "boardId": board_id,
            "message": "Cannot unlock. Not locked by you or already unlocked",
        }, room=sid)


# ─── Pub/Sub event handler ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Redis URL: {settings.redis_url}")

    # Register Pub/Sub event handler
    async def handle_pubsub_event(board_id: str, event: str, payload: dict):
        """Handle incoming Pub/Sub events from other instances."""
        await sio.emit(event, payload, room=f"board:{board_id}")

    pubsub_service.set_event_handler(handle_pubsub_event)

    # Start Pub/Sub listener as a background task so Task Service webhooks
    # actually reach connected sockets.
    subscriber_task = asyncio.create_task(
        pubsub_service.subscribe_to_events(),
        name="pubsub-subscriber",
    )

    try:
        yield
    finally:
        logger.info("Shutting down Realtime Service")
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("Pub/Sub subscriber task crashed during shutdown")
        await pubsub_service.close()
        await redis_client.close()


# ─── FastAPI app with Socket.IO mounted ─────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description="Real-time Socket.IO service for collaborative dashboard",
    version=settings.app_version,
    lifespan=lifespan,
)

# Mount Socket.IO ASGI app at /socket.io/
app.mount("/socket.io/", socketio_app)

# Include internal routes (webhooks from Task Service).
# Mounted under both /api/webhooks and /internal so the Task Service default
# (realtime_webhook_endpoint=/internal/events) and the nginx-routed form both work.
app.include_router(internal.router, prefix="/api/webhooks", tags=["Internal"])
app.include_router(internal.router, prefix="/internal", tags=["Internal"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "realtime",
        "connections": len(sio.manager.rooms),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

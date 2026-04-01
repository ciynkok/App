"""
Realtime Service - FastAPI WebSocket server.
Manages WebSocket connections, board rooms, chat, and task locks.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

from src.config.settings import settings
from src.config.redis import redis_client
from src.middleware.ws_auth import authenticate_websocket, WebSocketAuthenticationError
from src.handlers.websocket import ConnectionManager
from src.handlers.board import handle_join, handle_leave
from src.handlers.chat import handle_message
from src.handlers.task import handle_lock, handle_unlock
from src.routes import internal
from src.services.pubsub import pubsub_service

# Create connection manager instance
connection_manager = ConnectionManager()


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Redis URL: {settings.redis_url}")

    # Initialize Pub/Sub service event handler
    def handle_pubsub_event(board_id: str, event: str, payload: dict):
        """Handle incoming Pub/Sub events from other instances."""
        # Broadcast to local clients in the room
        import asyncio

        async def broadcast():
            message = {"type": event, "payload": payload}
            await connection_manager.broadcast_to_room(message, f"board:{board_id}")

        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(broadcast())
        except RuntimeError:
            pass  # No event loop running

    pubsub_service.set_event_handler(handle_pubsub_event)

    yield

    # Shutdown
    logger.info("Shutting down Realtime Service")
    await redis_client.close()
    await pubsub_service.close()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real-time WebSocket service for collaborative dashboard",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include internal routes (webhooks from Task Service)
app.include_router(internal.router, prefix="/internal", tags=["Internal"])


@app.websocket("/socket.io/")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.

    Expects JWT token in query params: ?token=<jwt_token>
    """
    # Authenticate WebSocket connection
    try:
        user = await authenticate_websocket(websocket)
    except WebSocketAuthenticationError as e:
        logger.warning(f"WebSocket authentication failed: {e.message}")
        await websocket.close(code=4001)
        return

    # Accept connection
    await connection_manager.accept(websocket, user)
    logger.info(f"WebSocket connected: user={user.get('id')}")

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            event_type = data.get("type")
            payload = data.get("payload", {})

            logger.debug(f"Received event: {event_type} from user={user.get('id')}")

            # Route event to handler
            if event_type == "join:board":
                await handle_join(websocket, payload, connection_manager)

            elif event_type == "leave:board":
                await handle_leave(websocket, payload, connection_manager)

            elif event_type == "chat:message":
                await handle_message(websocket, payload, connection_manager)

            elif event_type == "task:lock":
                await handle_lock(websocket, payload, connection_manager)

            elif event_type == "task:unlock":
                await handle_unlock(websocket, payload, connection_manager)

            else:
                logger.warning(f"Unknown event type: {event_type}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown event type: {event_type}",
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user.get('id')}")

        # Clean up: remove from presence on all boards
        if hasattr(websocket, "current_board_id") and websocket.current_board_id:
            from src.services.presence import remove_user_from_board

            await remove_user_from_board(
                websocket.current_board_id,
                user.get("id"),
            )

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        await connection_manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "realtime",
        "connections": connection_manager.get_connections_count(),
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

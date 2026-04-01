"""
Chat event handlers.
Handles chat:message WebSocket events.
"""
from datetime import datetime
from typing import Any, Dict
from fastapi import WebSocket
from src.handlers.websocket import ConnectionManager
from src.services.chat import save_chat_message
from src.services.pubsub import pubsub_service


async def handle_message(
    websocket: WebSocket,
    payload: Dict[str, Any],
    manager: ConnectionManager,
):
    """
    Handle chat:message event.

    Args:
        websocket: WebSocket connection
        payload: Event payload with boardId, text
        manager: Connection manager instance
    """
    board_id = payload.get("boardId")
    text = payload.get("text")

    if not board_id or not text:
        await websocket.send_json({
            "type": "error",
            "message": "boardId and text are required",
        })
        return

    user = manager.get_user(websocket)
    user_id = user.get("id")
    user_email = user.get("email", "Anonymous")

    if not user_id:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated",
        })
        return

    # Create message object
    message = {
        "from": user_id,
        "name": user_email,
        "text": text.strip(),
        "boardId": board_id,
        "ts": datetime.utcnow().isoformat(),
    }

    # Save to Redis
    await save_chat_message(board_id, message)

    # Broadcast to all in the room (including sender)
    broadcast_message = {
        "type": "chat:message",
        "payload": message,
    }

    await websocket.send_json(broadcast_message)

    # Publish to other instances via Pub/Sub
    await pubsub_service.publish_event(
        board_id,
        "chat:message",
        message,
    )

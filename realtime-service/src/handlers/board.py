"""
Board event handlers.
Handles join:board, leave:board WebSocket events.
"""
from typing import Any, Dict
from fastapi import WebSocket
from src.handlers.websocket import ConnectionManager
from src.services.chat import get_chat_history
from src.services.presence import (
    add_user_to_board,
    remove_user_from_board,
    get_online_users,
)
from src.services.pubsub import pubsub_service


async def handle_join(
    websocket: WebSocket,
    payload: Dict[str, Any],
    manager: ConnectionManager,
):
    """
    Handle join:board event.

    Args:
        websocket: WebSocket connection
        payload: Event payload with boardId
        manager: Connection manager instance
    """
    board_id = payload.get("boardId")

    if not board_id:
        await websocket.send_json({
            "type": "error",
            "message": "boardId is required",
        })
        return

    # Add to WebSocket room
    await websocket.send_json({
        "type": "room:joined",
        "payload": {"boardId": board_id},
    })

    # Store current board on websocket
    if not hasattr(websocket, "current_board_id"):
        websocket.current_board_id = board_id

    # Add user to presence
    user = manager.get_user(websocket)
    user_id = user.get("id")

    if user_id:
        await add_user_to_board(board_id, user_id)

        # Get chat history and send only to this user
        history = await get_chat_history(board_id)
        await websocket.send_json({
            "type": "chat:history",
            "payload": {
                "boardId": board_id,
                "messages": history,
            },
        })

        # Get online users and send only to this user
        online_users = await get_online_users(board_id)
        await websocket.send_json({
            "type": "user:online",
            "payload": {
                "boardId": board_id,
                "users": list(online_users),
            },
        })

        # Notify others about new user
        await websocket.send_json({
            "type": "user:joined",
            "payload": {
                "userId": user_id,
                "boardId": board_id,
                "name": user.get("email", "Anonymous"),
            },
        })

        # Publish to other instances via Pub/Sub
        await pubsub_service.publish_event(
            board_id,
            "user:joined",
            {
                "userId": user_id,
                "boardId": board_id,
                "name": user.get("email", "Anonymous"),
            },
        )


async def handle_leave(
    websocket: WebSocket,
    payload: Dict[str, Any],
    manager: ConnectionManager,
):
    """
    Handle leave:board event.

    Args:
        websocket: WebSocket connection
        payload: Event payload with boardId
        manager: Connection manager instance
    """
    board_id = payload.get("boardId")

    if not board_id:
        await websocket.send_json({
            "type": "error",
            "message": "boardId is required",
        })
        return

    user = manager.get_user(websocket)
    user_id = user.get("id")

    # Remove from presence
    if user_id:
        await remove_user_from_board(board_id, user_id)

        # Notify others about user leaving
        await websocket.send_json({
            "type": "user:left",
            "payload": {
                "userId": user_id,
                "boardId": board_id,
            },
        })

        # Publish to other instances via Pub/Sub
        await pubsub_service.publish_event(
            board_id,
            "user:left",
            {
                "userId": user_id,
                "boardId": board_id,
            },
        )

    # Clear current board from websocket
    if hasattr(websocket, "current_board_id"):
        websocket.current_board_id = None

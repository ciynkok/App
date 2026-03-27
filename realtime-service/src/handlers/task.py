"""
Task event handlers.
Handles task:lock, task:unlock WebSocket events.
"""
from typing import Any, Dict
from fastapi import WebSocket
from src.handlers.websocket import ConnectionManager
from src.services.lock import lock_task, unlock_task
from src.services.pubsub import pubsub_service


async def handle_lock(
    websocket: WebSocket,
    payload: Dict[str, Any],
    manager: ConnectionManager,
):
    """
    Handle task:lock event.

    Args:
        websocket: WebSocket connection
        payload: Event payload with boardId, taskId
        manager: Connection manager instance
    """
    board_id = payload.get("boardId")
    task_id = payload.get("taskId")

    if not board_id or not task_id:
        await websocket.send_json({
            "type": "error",
            "message": "boardId and taskId are required",
        })
        return

    user = manager.get_user(websocket)
    user_id = user.get("id")

    if not user_id:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated",
        })
        return

    # Try to acquire lock
    acquired = await lock_task(board_id, task_id, user_id)

    if acquired:
        # Broadcast lock success
        broadcast_message = {
            "type": "task:locked",
            "payload": {
                "taskId": task_id,
                "boardId": board_id,
                "userId": user_id,
            },
        }

        await websocket.send_json(broadcast_message)

        # Publish to other instances via Pub/Sub
        await pubsub_service.publish_event(
            board_id,
            "task:locked",
            {
                "taskId": task_id,
                "boardId": board_id,
                "userId": user_id,
            },
        )
    else:
        # Lock failed - task already locked
        await websocket.send_json({
            "type": "task:lock:failed",
            "payload": {
                "taskId": task_id,
                "boardId": board_id,
                "message": "Task is already locked by another user",
            },
        })


async def handle_unlock(
    websocket: WebSocket,
    payload: Dict[str, Any],
    manager: ConnectionManager,
):
    """
    Handle task:unlock event.

    Args:
        websocket: WebSocket connection
        payload: Event payload with boardId, taskId
        manager: Connection manager instance
    """
    board_id = payload.get("boardId")
    task_id = payload.get("taskId")

    if not board_id or not task_id:
        await websocket.send_json({
            "type": "error",
            "message": "boardId and taskId are required",
        })
        return

    user = manager.get_user(websocket)
    user_id = user.get("id")

    if not user_id:
        await websocket.send_json({
            "type": "error",
            "message": "User not authenticated",
        })
        return

    # Try to release lock
    released = await unlock_task(board_id, task_id, user_id)

    if released:
        # Broadcast unlock success
        broadcast_message = {
            "type": "task:unlocked",
            "payload": {
                "taskId": task_id,
                "boardId": board_id,
            },
        }

        await websocket.send_json(broadcast_message)

        # Publish to other instances via Pub/Sub
        await pubsub_service.publish_event(
            board_id,
            "task:unlocked",
            {
                "taskId": task_id,
                "boardId": board_id,
            },
        )
    else:
        # Unlock failed - not owner or not locked
        await websocket.send_json({
            "type": "task:unlock:failed",
            "payload": {
                "taskId": task_id,
                "boardId": board_id,
                "message": "Cannot unlock task. Not locked by you or already unlocked",
            },
        })

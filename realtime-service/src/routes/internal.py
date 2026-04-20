"""
Internal routes for receiving webhooks from Task Service.
Handles POST /internal/events endpoint.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from src.services.pubsub import pubsub_service


router = APIRouter()


# Allowed event types from Task Service
ALLOWED_EVENTS = [
    "task.created",
    "task.updated",
    "task.moved",
    "task.deleted",
    "comment.created",
    "comment.updated",
    "comment.deleted",
    "column.created",
    "column.updated",
    "column.deleted",
]


class WebhookEvent(BaseModel):
    """Webhook event payload from Task Service."""
    event_type: str = Field(..., description="Type of event: task.created, task.updated, etc.")
    entity_type: str = Field(..., description="Type of entity: task, comment, board, column")
    entity_id: UUID
    board_id: UUID
    user_id: UUID
    timestamp: datetime
    data: Dict[str, Any] | None = None


class EventResponse(BaseModel):
    """Response for event endpoint."""
    ok: bool
    message: str | None = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: str | None = None


def _build_payload(event: WebhookEvent) -> Dict[str, Any]:
    """
    Build a normalized payload for the given webhook event.

    The resulting object is what WebSocket clients receive via `socket.on(event, ...)`.
    Field names match the REST API shape (snake_case) so that the frontend can
    spread the payload directly into the in-memory task/comment objects.
    """
    data = dict(event.data or {})
    entity_id = str(event.entity_id)
    board_id = str(event.board_id)
    user_id = str(event.user_id)
    timestamp = event.timestamp.isoformat()

    if event.entity_type == "task":
        # `task.moved` carries {old_column_id, new_column_id, position}; translate
        # new_column_id to the canonical column_id so the frontend can apply it as
        # a partial update.
        if "new_column_id" in data:
            data["column_id"] = data.pop("new_column_id")
        data.pop("old_column_id", None)

        payload: Dict[str, Any] = {
            "id": entity_id,
            "board_id": board_id,
            "user_id": user_id,
            "timestamp": timestamp,
            **data,
        }
        return payload

    if event.entity_type == "comment":
        task_id = data.pop("task_id", None)
        payload = {
            "id": entity_id,
            "task_id": task_id,
            "board_id": board_id,
            "author_id": user_id,
            "user_id": user_id,
            "timestamp": timestamp,
            **data,
        }
        return payload

    if event.entity_type == "column":
        payload = {
            "id": entity_id,
            "board_id": board_id,
            "user_id": user_id,
            "timestamp": timestamp,
            **data,
        }
        return payload

    # Fallback — preserve previous shape for unknown entity types.
    return {
        "entityType": event.entity_type,
        "entityId": entity_id,
        "boardId": board_id,
        "userId": user_id,
        "timestamp": timestamp,
        **data,
    }


@router.post("/task-events", response_model=EventResponse)
@router.post("/events", response_model=EventResponse)
async def receive_event(event: WebhookEvent) -> EventResponse:
    """
    Receive event from Task Service and broadcast to WebSocket clients.

    Args:
        event: Webhook event payload

    Returns:
        EventResponse with ok status

    Raises:
        HTTPException: If event type is not allowed
    """
    # Validate event type
    if event.event_type not in ALLOWED_EVENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event type: {event.event_type}",
        )

    # Convert event_type to WebSocket format (e.g., task.created -> task:created)
    ws_event_type = event.event_type.replace(".", ":")

    payload = _build_payload(event)

    # Publish to board channel via Pub/Sub
    # This will broadcast to all clients in the board room
    await pubsub_service.publish_event(
        str(event.board_id),
        ws_event_type,
        payload,
    )

    return EventResponse(ok=True, message=f"Event {ws_event_type} broadcasted")


@router.get("/allowed-events", response_model=List[str])
async def list_allowed_events() -> List[str]:
    """
    Get list of allowed event types.

    Returns:
        List of allowed event type strings
    """
    return ALLOWED_EVENTS


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "realtime"}

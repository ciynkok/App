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

    # Build payload for WebSocket clients
    payload = {
        "entityType": event.entity_type,
        "entityId": str(event.entity_id),
        "boardId": str(event.board_id),
        "userId": str(event.user_id),
        "timestamp": event.timestamp.isoformat(),
        **(event.data or {}),
    }

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

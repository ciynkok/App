"""
Webhook service for sending events to Real-time Service.
"""
import logging
from typing import Optional
from datetime import datetime
import httpx
from src.config import settings
from src.schemas import WebhookEvent


logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhooks to Real-time Service."""
    
    def __init__(self):
        self.base_url = settings.realtime_service_url
        self.endpoint = settings.realtime_webhook_endpoint
        self.timeout = 5.0
    
    async def send_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        board_id: str,
        user_id: str,
        data: Optional[dict] = None
    ) -> bool:
        """
        Send a webhook event to Real-time Service.
        
        Args:
            event_type: Type of event (e.g., task.created, task.updated)
            entity_type: Type of entity (task, comment, board, column)
            entity_id: ID of the entity
            board_id: ID of the board
            user_id: ID of the user who triggered the event
            data: Optional additional data
            
        Returns:
            bool: True if webhook was sent successfully, False otherwise
        """
        event = WebhookEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            board_id=board_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            data=data
        )
        
        url = f"{self.base_url}{self.endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=event.model_dump(mode='json'),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"Webhook sent successfully: {event_type} for {entity_type}:{entity_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook failed with status {response.status_code}: "
                        f"{event_type} for {entity_type}:{entity_id}"
                    )
                    return False
                    
        except httpx.TimeoutException:
            logger.error(f"Webhook timeout: {event_type} for {entity_type}:{entity_id}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Webhook request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False
    
    async def task_created(
        self,
        task_id: str,
        board_id: str,
        user_id: str,
        task_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a task is created."""
        return await self.send_event(
            event_type="task.created",
            entity_type="task",
            entity_id=task_id,
            board_id=board_id,
            user_id=user_id,
            data=task_data
        )
    
    async def task_updated(
        self,
        task_id: str,
        board_id: str,
        user_id: str,
        task_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a task is updated."""
        return await self.send_event(
            event_type="task.updated",
            entity_type="task",
            entity_id=task_id,
            board_id=board_id,
            user_id=user_id,
            data=task_data
        )
    
    async def task_moved(
        self,
        task_id: str,
        board_id: str,
        user_id: str,
        move_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a task is moved between columns."""
        return await self.send_event(
            event_type="task.moved",
            entity_type="task",
            entity_id=task_id,
            board_id=board_id,
            user_id=user_id,
            data=move_data
        )
    
    async def task_deleted(
        self,
        task_id: str,
        board_id: str,
        user_id: str
    ) -> bool:
        """Send webhook when a task is deleted."""
        return await self.send_event(
            event_type="task.deleted",
            entity_type="task",
            entity_id=task_id,
            board_id=board_id,
            user_id=user_id
        )
    
    async def comment_created(
        self,
        comment_id: str,
        task_id: str,
        board_id: str,
        user_id: str,
        comment_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a comment is created."""
        return await self.send_event(
            event_type="comment.created",
            entity_type="comment",
            entity_id=comment_id,
            board_id=board_id,
            user_id=user_id,
            data={"task_id": task_id, **(comment_data or {})}
        )
    
    async def comment_updated(
        self,
        comment_id: str,
        task_id: str,
        board_id: str,
        user_id: str,
        comment_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a comment is updated."""
        return await self.send_event(
            event_type="comment.updated",
            entity_type="comment",
            entity_id=comment_id,
            board_id=board_id,
            user_id=user_id,
            data={"task_id": task_id, **(comment_data or {})}
        )
    
    async def comment_deleted(
        self,
        comment_id: str,
        task_id: str,
        board_id: str,
        user_id: str
    ) -> bool:
        """Send webhook when a comment is deleted."""
        return await self.send_event(
            event_type="comment.deleted",
            entity_type="comment",
            entity_id=comment_id,
            board_id=board_id,
            user_id=user_id,
            data={"task_id": task_id}
        )
    
    async def column_created(
        self,
        column_id: str,
        board_id: str,
        user_id: str,
        column_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a column is created."""
        return await self.send_event(
            event_type="column.created",
            entity_type="column",
            entity_id=column_id,
            board_id=board_id,
            user_id=user_id,
            data=column_data
        )
    
    async def column_updated(
        self,
        column_id: str,
        board_id: str,
        user_id: str,
        column_data: Optional[dict] = None
    ) -> bool:
        """Send webhook when a column is updated."""
        return await self.send_event(
            event_type="column.updated",
            entity_type="column",
            entity_id=column_id,
            board_id=board_id,
            user_id=user_id,
            data=column_data
        )
    
    async def column_deleted(
        self,
        column_id: str,
        board_id: str,
        user_id: str
    ) -> bool:
        """Send webhook when a column is deleted."""
        return await self.send_event(
            event_type="column.deleted",
            entity_type="column",
            entity_id=column_id,
            board_id=board_id,
            user_id=user_id
        )


# Global webhook service instance
webhook_service = WebhookService()

"""
Redis Pub/Sub service for horizontal scaling.
Synchronizes events across multiple Realtime Service instances.
"""
import json
from typing import Callable, Dict, Any, Optional
from redis.asyncio import Redis
from src.config.redis import redis_client
from src.config.settings import settings


# Channel prefix for board events
CHANNEL_PREFIX = "rt:pubsub:board:"


class PubSubService:
    """Redis Pub/Sub service for event synchronization."""

    def __init__(self):
        self._publisher: Optional[Redis] = None
        self._subscriber: Optional[Redis] = None
        self._event_handler: Optional[Callable] = None

    async def get_publisher(self) -> Redis:
        """Get publisher Redis client."""
        if self._publisher is None:
            self._publisher = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._publisher

    async def get_subscriber(self) -> Redis:
        """Get subscriber Redis client."""
        if self._subscriber is None:
            self._subscriber = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._subscriber

    async def publish_event(self, board_id: str, event: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event to a board channel.

        Args:
            board_id: ID of the board
            event: Event type (e.g., task:created, chat:message)
            payload: Event payload
        """
        publisher = await self.get_publisher()
        channel = f"{CHANNEL_PREFIX}{board_id}"

        message = json.dumps({
            "event": event,
            "payload": payload,
        })

        await publisher.publish(channel, message)

    def set_event_handler(self, handler: Callable[[str, str, Dict[str, Any]], None]):
        """
        Set the event handler callback.

        Args:
            handler: Function(board_id, event, payload) to handle incoming events
        """
        self._event_handler = handler

    async def subscribe_to_events(self):
        """
        Subscribe to all board channels.
        Calls the event handler when messages are received.
        """
        if self._event_handler is None:
            raise RuntimeError("Event handler not set")

        subscriber = await self.get_subscriber()
        pubsub = subscriber.pubsub()

        # Subscribe to all board channels
        await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")

        # Listen for messages
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]

                # Extract board_id from channel
                board_id = channel.replace(CHANNEL_PREFIX, "")

                try:
                    parsed = json.loads(data)
                    event = parsed["event"]
                    payload = parsed["payload"]

                    # Call the event handler
                    self._event_handler(board_id, event, payload)

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing pubsub message: {e}")

    async def close(self):
        """Close Pub/Sub connections."""
        if self._publisher:
            await self._publisher.close()
            self._publisher = None

        if self._subscriber:
            await self._subscriber.close()
            self._subscriber = None


# Global Pub/Sub service instance
pubsub_service = PubSubService()

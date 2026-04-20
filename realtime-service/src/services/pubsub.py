"""
Redis Pub/Sub service for horizontal scaling.
Synchronizes events across multiple Realtime Service instances.
"""
import asyncio
import inspect
import json
import logging
from typing import Awaitable, Callable, Dict, Any, Optional, Union
from redis.asyncio import Redis
from src.config.redis import redis_client
from src.config.settings import settings


logger = logging.getLogger(__name__)

EventHandler = Callable[[str, str, Dict[str, Any]], Union[None, Awaitable[None]]]


# Channel prefix for board events
CHANNEL_PREFIX = "rt:pubsub:board:"


class PubSubService:
    """Redis Pub/Sub service for event synchronization."""

    def __init__(self):
        self._publisher: Optional[Redis] = None
        self._subscriber: Optional[Redis] = None
        self._event_handler: Optional[EventHandler] = None

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

    def set_event_handler(self, handler: EventHandler):
        """
        Set the event handler callback.

        Args:
            handler: Function(board_id, event, payload) to handle incoming events.
                     May be sync or async — coroutines are awaited.
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
        logger.info("Pub/Sub subscriber started on pattern %s*", CHANNEL_PREFIX)

        try:
            async for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue

                channel = message["channel"]
                data = message["data"]

                # Extract board_id from channel
                board_id = channel.replace(CHANNEL_PREFIX, "")

                try:
                    parsed = json.loads(data)
                    event = parsed["event"]
                    payload = parsed["payload"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Error parsing pubsub message: %s", e)
                    continue

                try:
                    result = self._event_handler(board_id, event, payload)
                    if inspect.isawaitable(result):
                        await result
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    logger.exception("Pub/Sub handler failed for %s: %s", event, e)
        except asyncio.CancelledError:
            logger.info("Pub/Sub subscriber stopping")
            raise
        finally:
            await pubsub.punsubscribe(f"{CHANNEL_PREFIX}*")
            await pubsub.close()

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

"""
Chat service for managing chat history in Redis.
Stores messages with TTL and provides retrieval functionality.
"""
import json
from typing import List, Dict, Any
from src.config.redis import redis_client
from src.config.settings import settings


# Redis key prefix for chat
CHAT_KEY_PREFIX = "rt:chat:"


async def save_chat_message(board_id: str, message: Dict[str, Any]) -> None:
    """
    Save a chat message to Redis.

    Args:
        board_id: ID of the board
        message: Message dict with from, name, text, boardId, ts
    """
    key = f"{CHAT_KEY_PREFIX}{board_id}"

    # Add message to the beginning of the list
    await redis_client.client.lpush(key, json.dumps(message))

    # Trim to max messages
    await redis_client.client.ltrim(
        key,
        0,
        settings.chat_history_max_messages - 1,
    )

    # Set TTL
    await redis_client.client.expire(key, settings.chat_history_ttl)


async def get_chat_history(board_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get chat history for a board.

    Args:
        board_id: ID of the board
        limit: Maximum number of messages to retrieve

    Returns:
        List of messages (oldest to newest)
    """
    key = f"{CHAT_KEY_PREFIX}{board_id}"

    # Get messages (newest first from lrange)
    messages = await redis_client.client.lrange(key, 0, limit - 1)

    # Parse and reverse to get oldest first
    return [json.loads(msg) for msg in reversed(messages)]


async def clear_chat_history(board_id: str) -> None:
    """
    Clear chat history for a board.

    Args:
        board_id: ID of the board
    """
    key = f"{CHAT_KEY_PREFIX}{board_id}"
    await redis_client.client.delete(key)

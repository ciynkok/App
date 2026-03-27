"""
Presence service for tracking online users on boards.
Uses Redis Sets to manage user presence.
"""
from typing import List, Set
from src.config.redis import redis_client


# Redis key prefix for presence
PRESENCE_KEY_PREFIX = "rt:online:"


async def add_user_to_board(board_id: str, user_id: str) -> None:
    """
    Add a user to the online set for a board.

    Args:
        board_id: ID of the board
        user_id: ID of the user
    """
    key = f"{PRESENCE_KEY_PREFIX}{board_id}"
    await redis_client.client.sadd(key, user_id)


async def remove_user_from_board(board_id: str, user_id: str) -> None:
    """
    Remove a user from the online set for a board.

    Args:
        board_id: ID of the board
        user_id: ID of the user
    """
    key = f"{PRESENCE_KEY_PREFIX}{board_id}"
    await redis_client.client.srem(key, user_id)


async def get_online_users(board_id: str) -> List[str]:
    """
    Get all online users for a board.

    Args:
        board_id: ID of the board

    Returns:
        List of user IDs
    """
    key = f"{PRESENCE_KEY_PREFIX}{board_id}"
    return await redis_client.client.smembers(key)


async def is_user_online(board_id: str, user_id: str) -> bool:
    """
    Check if a user is online on a board.

    Args:
        board_id: ID of the board
        user_id: ID of the user

    Returns:
        True if user is online, False otherwise
    """
    key = f"{PRESENCE_KEY_PREFIX}{board_id}"
    return await redis_client.client.sismember(key, user_id)


async def get_user_boards(user_id: str) -> List[str]:
    """
    Get all boards where a user is online.
    Note: This requires scanning all presence keys.

    Args:
        user_id: ID of the user

    Returns:
        List of board IDs
    """
    boards = []
    pattern = f"{PRESENCE_KEY_PREFIX}*"

    async for key in redis_client.client.scan_iter(match=pattern):
        if await redis_client.client.sismember(key, user_id):
            board_id = key.replace(PRESENCE_KEY_PREFIX, "")
            boards.append(board_id)

    return boards

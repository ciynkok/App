"""
Task lock service for optimistic locking of tasks.
Uses Redis with TTL to manage task editing locks.
"""
from typing import Optional
from src.config.redis import redis_client
from src.config.settings import settings


# Redis key prefix for locks
LOCK_KEY_PREFIX = "rt:board:"
LOCK_KEY_SUFFIX = ":lock:"


async def lock_task(board_id: str, task_id: str, user_id: str) -> bool:
    """
    Try to acquire a lock on a task.

    Args:
        board_id: ID of the board
        task_id: ID of the task
        user_id: ID of the user trying to lock

    Returns:
        True if lock was acquired, False if already locked
    """
    key = f"{LOCK_KEY_PREFIX}{board_id}{LOCK_KEY_SUFFIX}{task_id}"

    # Set with NX (only if not exists) and EX (expire time)
    result = await redis_client.client.set(
        key,
        user_id,
        ex=settings.task_lock_ttl,
        nx=True,
    )

    return result is True


async def unlock_task(board_id: str, task_id: str, user_id: str) -> bool:
    """
    Release a lock on a task.

    Args:
        board_id: ID of the board
        task_id: ID of the task
        user_id: ID of the user trying to unlock

    Returns:
        True if lock was released, False if not owner or not locked
    """
    key = f"{LOCK_KEY_PREFIX}{board_id}{LOCK_KEY_SUFFIX}{task_id}"

    # Only unlock if current user owns the lock
    owner = await redis_client.client.get(key)

    if owner == user_id:
        await redis_client.client.delete(key)
        return True

    return False


async def get_lock_owner(board_id: str, task_id: str) -> Optional[str]:
    """
    Get the user ID who currently holds the lock on a task.

    Args:
        board_id: ID of the board
        task_id: ID of the task

    Returns:
        User ID if locked, None if not locked
    """
    key = f"{LOCK_KEY_PREFIX}{board_id}{LOCK_KEY_SUFFIX}{task_id}"
    return await redis_client.client.get(key)


async def is_task_locked(board_id: str, task_id: str) -> bool:
    """
    Check if a task is currently locked.

    Args:
        board_id: ID of the board
        task_id: ID of the task

    Returns:
        True if task is locked, False otherwise
    """
    key = f"{LOCK_KEY_PREFIX}{board_id}{LOCK_KEY_SUFFIX}{task_id}"
    return await redis_client.client.exists(key) > 0


async def extend_lock(board_id: str, task_id: str, user_id: str) -> bool:
    """
    Extend the TTL of an existing lock.

    Args:
        board_id: ID of the board
        task_id: ID of the task
        user_id: ID of the user

    Returns:
        True if lock was extended, False if not owner
    """
    key = f"{LOCK_KEY_PREFIX}{board_id}{LOCK_KEY_SUFFIX}{task_id}"

    # Only extend if current user owns the lock
    owner = await redis_client.client.get(key)

    if owner == user_id:
        await redis_client.client.expire(key, settings.task_lock_ttl)
        return True

    return False

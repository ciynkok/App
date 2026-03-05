"""
Authentication and authorization middleware for Task Service.
"""
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from src.config import settings
from src.database import get_db
from src.models import BoardMember
from src.schemas import ErrorDetail


# Security scheme for JWT tokens
security = HTTPBearer()


async def verify_jwt_with_auth_service(token: str) -> dict:
    """
    Verify JWT token with Auth Service.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: User information from Auth Service
        
    Raises:
        HTTPException: If token is invalid or Auth Service is unavailable
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.auth_service_url}{settings.auth_service_verify_endpoint}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == status.HTTP_200_OK:
                return response.json()
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token"}}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Auth service unavailable"}}
                )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Failed to connect to Auth Service"}}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        dict: User information including user_id
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    user_info = await verify_jwt_with_auth_service(token)
    
    if not user_info or "user_id" not in user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid token payload"}}
        )
    
    return user_info


async def get_current_user_id(
    current_user: dict = Depends(get_current_user)
) -> str:
    """
    Dependency to get current user ID.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        str: User ID
    """
    return current_user["user_id"]


async def check_board_access(
    board_id: str | UUID,
    user_id: str,
    db: AsyncSession,
    required_role: str = "viewer"
) -> BoardMember:
    """
    Check if user has access to a board with required role.
    
    Args:
        board_id: Board ID
        user_id: User ID
        db: Database session
        required_role: Minimum required role (viewer, editor, admin)
        
    Returns:
        BoardMember: Board member record
        
    Raises:
        HTTPException: If user doesn't have access or role is insufficient
    """
    # Role hierarchy: admin > editor > viewer
    role_hierarchy = {"viewer": 1, "editor": 2, "admin": 3}
    
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You don't have access to this board"
                }
            }
        )
    
    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(required_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "INSUFFICIENT_ROLE",
                    "message": f"Role '{member.role}' is insufficient. Required: '{required_role}'"
                }
            }
        )
    
    return member


async def require_board_viewer(
    board_id: str | UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> BoardMember:
    """
    Dependency to require viewer role on a board.
    
    Args:
        board_id: Board ID
        user_id: Current user ID
        db: Database session
        
    Returns:
        BoardMember: Board member record
    """
    return await check_board_access(board_id, user_id, db, "viewer")


async def require_board_editor(
    board_id: str | UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> BoardMember:
    """
    Dependency to require editor role on a board.
    
    Args:
        board_id: Board ID
        user_id: Current user ID
        db: Database session
        
    Returns:
        BoardMember: Board member record
    """
    return await check_board_access(board_id, user_id, db, "editor")


async def require_board_admin(
    board_id: str | UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> BoardMember:
    """
    Dependency to require admin role on a board.
    
    Args:
        board_id: Board ID
        user_id: Current user ID
        db: Database session
        
    Returns:
        BoardMember: Board member record
    """
    return await check_board_access(board_id, user_id, db, "admin")


async def require_board_owner(
    board_id: str | UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Dependency to require board ownership.
    
    Args:
        board_id: Board ID
        user_id: Current user ID
        db: Database session
        
    Raises:
        HTTPException: If user is not the board owner
    """
    from src.models import Board
    
    result = await db.execute(
        select(Board).where(Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "BOARD_NOT_FOUND",
                    "message": "Board not found"
                }
            }
        )
    
    if str(board.owner_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "NOT_OWNER",
                    "message": "Only the board owner can perform this action"
                }
            }
        )

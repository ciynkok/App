"""
Board API routes for Task Service.
"""
from typing import List
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.config import settings
from src.database import get_db
from src.models import Board, BoardMember, Task
from src.schemas import (
    BoardCreate,
    BoardUpdate,
    BoardResponse,
    BoardWithStats,
    BoardMemberCreate,
    BoardMemberUpdate,
    BoardMemberResponse
)
from src.middleware import (
    get_current_user_id,
    require_board_viewer,
    require_board_owner,
    require_board_admin
)
from src.webhook import webhook_service


router = APIRouter(prefix="/api/boards", tags=["boards"])


async def _lookup_user_by_email(email: str, request: Request) -> dict:
    """Resolve email → user via auth-service, forwarding caller's bearer token."""
    auth_header = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.auth_service_url}/auth/users/by-email",
                params={"email": email},
                headers={"Authorization": auth_header},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Failed to reach Auth Service"}},
        )

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User with this email not found"}},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": "AUTH_SERVICE_ERROR", "message": "Auth service returned an error"}},
        )

    return response.json()


async def _fetch_users_by_ids(user_ids: list[str], request: Request) -> dict:
    """Batch lookup user_id → profile via auth-service. Returns {user_id: profile}.
    Best-effort: returns empty dict on failure so callers can still respond."""
    if not user_ids:
        return {}

    auth_header = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.auth_service_url}/auth/users/by-ids",
                json={"ids": user_ids},
                headers={"Authorization": auth_header},
            )
    except httpx.RequestError:
        return {}

    if response.status_code != status.HTTP_200_OK:
        return {}

    return {item["id"]: item for item in response.json()}


@router.post("", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    board_data: BoardCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new board.

    The user who creates the board becomes the owner and is automatically added as an admin member.
    """
    # Create board
    board = Board(
        title=board_data.title,
        description=board_data.description,
        owner_id=UUID(user_id),
        color=board_data.color
    )

    db.add(board)
    await db.flush()

    # Add creator as admin member
    member = BoardMember(
        board_id=board.id,
        user_id=UUID(user_id),
        role="admin"
    )
    db.add(member)

    await db.commit()
    await db.refresh(board)

    return board


@router.get("", response_model=List[BoardResponse])
async def list_boards(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all boards where the user is a member.
    """
    result = await db.execute(
        select(Board)
        .join(BoardMember, Board.id == BoardMember.board_id)
        .where(BoardMember.user_id == UUID(user_id))
        .order_by(Board.created_at.desc())
    )
    boards = result.scalars().all()
    return boards


@router.get("/{board_id}", response_model=BoardWithStats)
async def get_board(
    board_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get board details with statistics.
    """
    # Check access
    await require_board_viewer(board_id, user_id, db)
    
    # Get board
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOARD_NOT_FOUND", "message": "Board not found"}}
        )
    
    # Get statistics
    total_tasks_result = await db.execute(
        select(func.count(Task.id)).where(Task.board_id == board_id)
    )
    total_tasks = total_tasks_result.scalar() or 0
    
    completed_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.board_id == board_id,
            Task.status == "done"
        )
    )
    completed_tasks = completed_tasks_result.scalar() or 0
    
    members_count_result = await db.execute(
        select(func.count(BoardMember.user_id)).where(BoardMember.board_id == board_id)
    )
    members_count = members_count_result.scalar() or 0
    
    # Build response
    board_dict = {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "owner_id": board.owner_id,
        "color": board.color,
        "created_at": board.created_at,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "members_count": members_count
    }
    
    return board_dict


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: UUID,
    board_data: BoardUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update board details.
    Only the board owner can update the board.
    """
    # Check ownership
    await require_board_owner(board_id, user_id, db)
    
    # Get board
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOARD_NOT_FOUND", "message": "Board not found"}}
        )
    
    # Update fields
    if board_data.title is not None:
        board.title = board_data.title
    if board_data.description is not None:
        board.description = board_data.description
    if board_data.color is not None:
        board.color = board_data.color
    
    await db.commit()
    await db.refresh(board)
    
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a board.
    Only the board owner can delete the board.
    """
    # Check ownership
    await require_board_owner(board_id, user_id, db)
    
    # Get board
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOARD_NOT_FOUND", "message": "Board not found"}}
        )
    
    await db.delete(board)
    await db.commit()


@router.post("/{board_id}/members", response_model=BoardMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_board_member(
    board_id: UUID,
    member_data: BoardMemberCreate,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a member to the board by email.
    Only board admins can add members.
    """
    # Check admin access
    await require_board_admin(board_id, user_id, db)

    # Resolve email → user via auth-service
    profile = await _lookup_user_by_email(member_data.email, request)
    target_user_id = UUID(profile["id"])

    # Check if member already exists
    existing_result = await db.execute(
        select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == target_user_id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "MEMBER_EXISTS", "message": "User is already a board member"}}
        )

    # Create member
    member = BoardMember(
        board_id=board_id,
        user_id=target_user_id,
        role=member_data.role
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return BoardMemberResponse(
        board_id=member.board_id,
        user_id=member.user_id,
        role=member.role,
        email=profile.get("email"),
        name=profile.get("name"),
        avatar_url=profile.get("avatar_url"),
    )


@router.get("/{board_id}/members", response_model=List[BoardMemberResponse])
async def list_board_members(
    board_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of a board, enriched with email/name from auth-service.
    """
    # Check access
    await require_board_admin(board_id, user_id, db)

    result = await db.execute(
        select(BoardMember).where(BoardMember.board_id == board_id)
    )
    members = result.scalars().all()

    profiles = await _fetch_users_by_ids([str(m.user_id) for m in members], request)

    return [
        BoardMemberResponse(
            board_id=m.board_id,
            user_id=m.user_id,
            role=m.role,
            email=(profiles.get(str(m.user_id)) or {}).get("email"),
            name=(profiles.get(str(m.user_id)) or {}).get("name"),
            avatar_url=(profiles.get(str(m.user_id)) or {}).get("avatar_url"),
        )
        for m in members
    ]


@router.put("/{board_id}/members/{member_id}", response_model=BoardMemberResponse)
async def update_board_member(
    board_id: UUID,
    member_id: UUID,
    member_data: BoardMemberUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a board member's role.
    Only board admins can update member roles.
    """
    # Check admin access
    await require_board_admin(board_id, user_id, db)
    
    # Get member
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == member_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MEMBER_NOT_FOUND", "message": "Board member not found"}}
        )
    
    # Update role
    member.role = member_data.role
    await db.commit()
    await db.refresh(member)
    
    return member


@router.delete("/{board_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_board_member(
    board_id: UUID,
    member_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from the board.
    Only board admins can remove members.
    """
    # Check admin access
    await require_board_admin(board_id, user_id, db)
    
    # Get member
    result = await db.execute(
        select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == member_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MEMBER_NOT_FOUND", "message": "Board member not found"}}
        )

    await db.delete(member)
    await db.commit()


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a board.
    Only board owner can delete the board.
    """
    # Get board
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()

    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOARD_NOT_FOUND", "message": "Board not found"}}
        )

    # Check if user is owner
    if str(board.owner_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Only board owner can delete"}}
        )

    await db.delete(board)
    await db.commit()

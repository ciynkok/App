"""
Column API routes for Task Service.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Column, Task
from src.schemas import ColumnCreate, ColumnUpdate, ColumnResponse, ColumnWithTasks
from src.middleware import require_board_editor, require_board_viewer, get_current_user_id
from src.webhook import webhook_service


router = APIRouter(prefix="/api/boards/{board_id}/columns", tags=["columns"])


@router.post("", response_model=ColumnResponse, status_code=status.HTTP_201_CREATED)
async def create_column(
    board_id: UUID,
    column_data: ColumnCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new column in a board.
    Requires editor role on the board.
    """
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Create column
    column = Column(
        board_id=board_id,
        title=column_data.title,
        position=column_data.position
    )
    
    db.add(column)
    await db.commit()
    await db.refresh(column)
    
    # Send webhook
    await webhook_service.column_created(
        column_id=str(column.id),
        board_id=str(board_id),
        user_id=user_id,
        column_data={"title": column.title, "position": column.position}
    )
    
    return column


@router.get("", response_model=List[ColumnResponse])
async def list_columns(
    board_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all columns in a board.
    Requires viewer role on the board.
    """
    # Check access
    await require_board_viewer(board_id, user_id, db)
    
    result = await db.execute(
        select(Column)
        .where(Column.board_id == board_id)
        .order_by(Column.position)
    )
    columns = result.scalars().all()
    return columns


@router.get("/{column_id}", response_model=ColumnWithTasks)
async def get_column(
    board_id: UUID,
    column_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get column details with tasks.
    Requires viewer role on the board.
    """
    # Check access
    await require_board_viewer(board_id, user_id, db)
    
    # Get column
    result = await db.execute(
        select(Column).where(
            Column.id == column_id,
            Column.board_id == board_id
        )
    )
    column = result.scalar_one_or_none()
    
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COLUMN_NOT_FOUND", "message": "Column not found"}}
        )
    
    # Get tasks
    tasks_result = await db.execute(
        select(Task).where(
            Task.column_id == column_id,
            Task.board_id == board_id
        ).order_by(Task.position)
    )
    tasks = tasks_result.scalars().all()
    
    # Build response
    from src.schemas import TaskResponse
    return {
        "id": column.id,
        "board_id": column.board_id,
        "title": column.title,
        "position": column.position,
        "created_at": column.created_at,
        "tasks": [TaskResponse.model_validate(task) for task in tasks]
    }


@router.put("/{column_id}", response_model=ColumnResponse)
async def update_column(
    board_id: UUID,
    column_id: UUID,
    column_data: ColumnUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update column details.
    Requires editor role on the board.
    """
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Get column
    result = await db.execute(
        select(Column).where(
            Column.id == column_id,
            Column.board_id == board_id
        )
    )
    column = result.scalar_one_or_none()
    
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COLUMN_NOT_FOUND", "message": "Column not found"}}
        )
    
    # Update fields
    if column_data.title is not None:
        column.title = column_data.title
    if column_data.position is not None:
        column.position = column_data.position
    
    await db.commit()
    await db.refresh(column)
    
    # Send webhook
    await webhook_service.column_updated(
        column_id=str(column.id),
        board_id=str(board_id),
        user_id=user_id,
        column_data={"title": column.title, "position": column.position}
    )
    
    return column


@router.delete("/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    board_id: UUID,
    column_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a column.
    Requires editor role on the board.
    Note: This will also delete all tasks in the column.
    """
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Get column
    result = await db.execute(
        select(Column).where(
            Column.id == column_id,
            Column.board_id == board_id
        )
    )
    column = result.scalar_one_or_none()
    
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COLUMN_NOT_FOUND", "message": "Column not found"}}
        )
    
    await db.delete(column)
    await db.commit()
    
    # Send webhook
    await webhook_service.column_deleted(
        column_id=str(column.id),
        board_id=str(board_id),
        user_id=user_id
    )

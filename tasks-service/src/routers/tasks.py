"""
Task API routes for Task Service.
"""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from src.database import get_db
from src.models import Task, Column
from src.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskMove,
    TaskResponse,
    TaskFilter
)
from src.middleware import require_board_editor, get_current_user_id
from src.webhook import webhook_service
from src.scheduler import deadline_scheduler


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task.
    Requires editor role on the board.
    """
    # Get column to verify board access
    column_result = await db.execute(
        select(Column).where(Column.id == task_data.column_id)
    )
    column = column_result.scalar_one_or_none()
    
    if not column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COLUMN_NOT_FOUND", "message": "Column not found"}}
        )
    
    # Check access
    await require_board_editor(column.board_id, user_id, db)
    
    # Create task
    task = Task(
        column_id=task_data.column_id,
        board_id=column.board_id,
        title=task_data.title,
        description=task_data.description,
        assignee_id=task_data.assignee_id,
        priority=task_data.priority,
        deadline=task_data.deadline,
        position=task_data.position or 0
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Schedule deadline reminder if deadline is set
    if task.deadline:
        await deadline_scheduler.schedule_task_reminder(
            task_id=str(task.id),
            deadline=task.deadline
        )
    
    # Send webhook
    await webhook_service.task_created(
        task_id=str(task.id),
        board_id=str(task.board_id),
        user_id=user_id,
        task_data={
            "title": task.title,
            "column_id": str(task.column_id),
            "assignee_id": str(task.assignee_id) if task.assignee_id else None
        }
    )
    
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    board_id: UUID | None = Query(None, description="Filter by board ID"),
    column_id: UUID | None = Query(None, description="Filter by column ID"),
    assignee_id: UUID | None = Query(None, description="Filter by assignee ID"),
    priority: str | None = Query(None, pattern=r"^(low|medium|high|urgent)$"),
    status: str | None = Query(None, pattern=r"^(todo|in_progress|review|done)$"),
    search: str | None = Query(None, description="Search in title and description"),
    deadline_before: datetime | None = Query(None, description="Tasks with deadline before this date"),
    deadline_after: datetime | None = Query(None, description="Tasks with deadline after this date"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List and filter tasks.
    """
    # Build query
    query = select(Task)
    
    # Apply filters
    conditions = []
    
    if board_id:
        conditions.append(Task.board_id == board_id)
    if column_id:
        conditions.append(Task.column_id == column_id)
    if assignee_id:
        conditions.append(Task.assignee_id == assignee_id)
    if priority:
        conditions.append(Task.priority == priority)
    if status:
        conditions.append(Task.status == status)
    if deadline_before:
        conditions.append(Task.deadline <= deadline_before)
    if deadline_after:
        conditions.append(Task.deadline >= deadline_after)
    if search:
        conditions.append(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%")
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply pagination and ordering
    query = query.order_by(Task.position, Task.created_at.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details.
    Requires viewer role on the board.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_editor(task.board_id, user_id, db)
    
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update task details.
    Requires editor role on the board.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_editor(task.board_id, user_id, db)
    
    # Track changes for webhook
    changes = {}
    
    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
        changes["title"] = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
        changes["description"] = task_data.description
    if task_data.assignee_id is not None:
        task.assignee_id = task_data.assignee_id
        changes["assignee_id"] = str(task_data.assignee_id)
    if task_data.priority is not None:
        task.priority = task_data.priority
        changes["priority"] = task_data.priority
    if task_data.status is not None:
        task.status = task_data.status
        changes["status"] = task_data.status
    if task_data.deadline is not None:
        # Cancel old reminder
        if task.deadline:
            await deadline_scheduler.cancel_task_reminder(str(task.id))
        
        task.deadline = task_data.deadline
        changes["deadline"] = task_data.deadline.isoformat() if task_data.deadline else None
        
        # Schedule new reminder
        if task_data.deadline:
            await deadline_scheduler.schedule_task_reminder(
                task_id=str(task.id),
                deadline=task_data.deadline
            )
    if task_data.position is not None:
        task.position = task_data.position
        changes["position"] = task_data.position
    
    await db.commit()
    await db.refresh(task)
    
    # Send webhook
    await webhook_service.task_updated(
        task_id=str(task.id),
        board_id=str(task.board_id),
        user_id=user_id,
        task_data=changes
    )
    
    return task


@router.post("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: UUID,
    move_data: TaskMove,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Move a task to another column.
    Requires editor role on the board.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_editor(task.board_id, user_id, db)
    
    # Verify target column exists and belongs to the same board
    column_result = await db.execute(
        select(Column).where(
            Column.id == move_data.target_column_id,
            Column.board_id == task.board_id
        )
    )
    target_column = column_result.scalar_one_or_none()
    
    if not target_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COLUMN_NOT_FOUND", "message": "Target column not found"}}
        )
    
    # Move task
    old_column_id = task.column_id
    task.column_id = move_data.target_column_id
    
    if move_data.new_position is not None:
        task.position = move_data.new_position
    
    await db.commit()
    await db.refresh(task)
    
    # Send webhook
    await webhook_service.task_moved(
        task_id=str(task.id),
        board_id=str(task.board_id),
        user_id=user_id,
        move_data={
            "old_column_id": str(old_column_id),
            "new_column_id": str(move_data.target_column_id),
            "position": task.position
        }
    )
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a task.
    Requires editor role on the board.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    board_id = task.board_id
    
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Cancel deadline reminder
    if task.deadline:
        await deadline_scheduler.cancel_task_reminder(str(task.id))
    
    await db.delete(task)
    await db.commit()
    
    # Send webhook
    await webhook_service.task_deleted(
        task_id=str(task_id),
        board_id=str(board_id),
        user_id=user_id
    )

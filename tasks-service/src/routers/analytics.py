"""
Analytics API routes for Task Service.
"""
from uuid import UUID
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from src.database import get_db
from src.models import Task, Board
from src.schemas import BoardStats, BurnDownDataPoint
from src.middleware import require_board_editor, get_current_user_id


router = APIRouter(prefix="/api/boards/{board_id}/stats", tags=["analytics"])


@router.get("", response_model=BoardStats)
async def get_board_stats(
    board_id: UUID,
    days: int = Query(30, ge=1, le=90, description="Number of days for burn-down chart"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get board statistics including burn-down chart data.
    Requires viewer role on the board.
    """
    # Check board exists
    board_result = await db.execute(select(Board).where(Board.id == board_id))
    board = board_result.scalar_one_or_none()
    
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "BOARD_NOT_FOUND", "message": "Board not found"}}
        )
    
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Get current statistics
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
    
    in_progress_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.board_id == board_id,
            Task.status == "in_progress"
        )
    )
    in_progress_tasks = in_progress_tasks_result.scalar() or 0
    
    todo_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.board_id == board_id,
            Task.status == "todo"
        )
    )
    todo_tasks = todo_tasks_result.scalar() or 0
    
    urgent_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.board_id == board_id,
            Task.priority == "urgent",
            Task.status != "done"
        )
    )
    urgent_tasks = urgent_tasks_result.scalar() or 0
    
    overdue_tasks_result = await db.execute(
        select(func.count(Task.id)).where(
            Task.board_id == board_id,
            Task.deadline < datetime.utcnow(),
            Task.status != "done"
        )
    )
    overdue_tasks = overdue_tasks_result.scalar() or 0
    
    # Generate burn-down chart data
    burn_down_data = await _generate_burn_down_data(db, board_id, days)
    
    return BoardStats(
        board_id=board_id,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        todo_tasks=todo_tasks,
        urgent_tasks=urgent_tasks,
        overdue_tasks=overdue_tasks,
        burn_down_data=burn_down_data
    )


async def _generate_burn_down_data(
    db: AsyncSession,
    board_id: UUID,
    days: int
) -> List[BurnDownDataPoint]:
    """
    Generate burn-down chart data for the specified number of days.
    
    Args:
        db: Database session
        board_id: Board ID
        days: Number of days to generate data for
        
    Returns:
        List of burn-down data points
    """
    burn_down_data = []
    
    # Get the start date (days ago)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Generate data for each day
    for day in range(days + 1):
        current_date = start_date + timedelta(days=day)
        next_date = current_date + timedelta(days=1)
        
        # Count tasks that existed at this point in time
        # (created before or on this day)
        total_at_date_result = await db.execute(
            select(func.count(Task.id)).where(
                Task.board_id == board_id,
                Task.created_at <= next_date
            )
        )
        total_at_date = total_at_date_result.scalar() or 0
        
        # Count tasks that were completed by this point in time
        # (status changed to done before or on this day)
        # Note: This is a simplified version. In production, you'd need
        # a task history table to track status changes accurately.
        completed_at_date_result = await db.execute(
            select(func.count(Task.id)).where(
                Task.board_id == board_id,
                Task.status == "done",
                Task.created_at <= next_date
            )
        )
        completed_at_date = completed_at_date_result.scalar() or 0
        
        remaining_tasks = total_at_date - completed_at_date
        
        burn_down_data.append(
            BurnDownDataPoint(
                date=current_date,
                remaining_tasks=remaining_tasks,
                completed_tasks=completed_at_date
            )
        )
    
    return burn_down_data

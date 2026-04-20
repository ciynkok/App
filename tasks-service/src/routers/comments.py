"""
Comment API routes for Task Service.
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Comment, Task
from src.schemas import CommentCreate, CommentUpdate, CommentResponse
from src.middleware import require_board_editor, require_board_viewer, get_current_user_id
from src.webhook import webhook_service


router = APIRouter(prefix="/api/tasks/{task_id}/comments", tags=["comments"])


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    task_id: UUID,
    comment_data: CommentCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new comment on a task.
    Requires editor role on the board.
    """
    # Get task to verify board access
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_viewer(task.board_id, user_id, db)
    
    # Create comment
    comment = Comment(
        task_id=task_id,
        author_id=UUID(user_id),
        content=comment_data.content
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    # Send webhook
    await webhook_service.comment_created(
        comment_id=str(comment.id),
        task_id=str(task_id),
        board_id=str(task.board_id),
        user_id=user_id,
        comment_data={
            "content": comment.content,
            "author_id": str(comment.author_id),
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        },
    )

    return comment


@router.get("", response_model=List[CommentResponse])
async def list_comments(
    task_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all comments on a task.
    Requires viewer role on the board.
    """
    # Get task to verify board access
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_viewer(task.board_id, user_id, db)
    
    # Get comments
    result = await db.execute(
        select(Comment)
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at)
    )
    comments = result.scalars().all()
    
    return comments


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    task_id: UUID,
    comment_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comment details.
    Requires viewer role on the board.
    """
    # Get comment
    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.task_id == task_id
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMMENT_NOT_FOUND", "message": "Comment not found"}}
        )
    
    # Get task to verify board access
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_editor(task.board_id, user_id, db)
    
    return comment


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    comment_data: CommentUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update comment content.
    Only the comment author can update their own comments.
    Requires editor role on the board.
    """
    # Get comment
    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.task_id == task_id
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMMENT_NOT_FOUND", "message": "Comment not found"}}
        )
    
    # Get task to verify board access
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    # Check access
    await require_board_editor(task.board_id, user_id, db)
    
    # Check ownership
    if str(comment.author_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "NOT_AUTHOR",
                    "message": "Only the comment author can update this comment"
                }
            }
        )
    
    # Update content
    comment.content = comment_data.content
    await db.commit()
    await db.refresh(comment)
    
    # Send webhook
    await webhook_service.comment_updated(
        comment_id=str(comment.id),
        task_id=str(task_id),
        board_id=str(task.board_id),
        user_id=user_id,
        comment_data={
            "content": comment.content,
            "author_id": str(comment.author_id),
            "updated_at": comment.updated_at.isoformat() if getattr(comment, "updated_at", None) else None,
        },
    )

    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a comment.
    Only the comment author can delete their own comments.
    Requires editor role on the board.
    """
    # Get comment
    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.task_id == task_id
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "COMMENT_NOT_FOUND", "message": "Comment not found"}}
        )
    
    # Get task to verify board access
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}}
        )
    
    board_id = task.board_id
    
    # Check access
    await require_board_editor(board_id, user_id, db)
    
    # Check ownership
    if str(comment.author_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "NOT_AUTHOR",
                    "message": "Only the comment author can delete this comment"
                }
            }
        )
    
    await db.delete(comment)
    await db.commit()
    
    # Send webhook
    await webhook_service.comment_deleted(
        comment_id=str(comment_id),
        task_id=str(task_id),
        board_id=str(board_id),
        user_id=user_id
    )

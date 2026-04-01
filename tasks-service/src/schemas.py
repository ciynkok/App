"""
Pydantic schemas for request/response validation in Task Service.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Base Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: dict = Field(
        ...,
        description="Error details with code, message, and optional details"
    )
    
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Error detail object."""
    code: str
    message: str
    details: Optional[dict] = None


# ============================================================================
# Board Schemas
# ============================================================================

class BoardBase(BaseModel):
    """Base board schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")


class BoardCreate(BoardBase):
    """Schema for creating a board."""
    pass


class BoardUpdate(BaseModel):
    """Schema for updating a board."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class BoardResponse(BoardBase):
    """Schema for board response."""
    id: UUID
    owner_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BoardWithStats(BoardResponse):
    """Board response with statistics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    members_count: int = 0


# ============================================================================
# Board Member Schemas
# ============================================================================

class BoardMemberBase(BaseModel):
    """Base board member schema."""
    role: str = Field(default="viewer", pattern=r"^(admin|editor|viewer)$")


class BoardMemberCreate(BoardMemberBase):
    """Schema for adding a board member."""
    user_id: UUID


class BoardMemberUpdate(BaseModel):
    """Schema for updating board member role."""
    role: str = Field(..., pattern=r"^(admin|editor|viewer)$")


class BoardMemberResponse(BoardMemberBase):
    """Schema for board member response."""
    board_id: UUID
    user_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Column Schemas
# ============================================================================

class ColumnBase(BaseModel):
    """Base column schema."""
    title: str = Field(..., min_length=1, max_length=255)
    position: int = Field(default=0, ge=0)


class ColumnCreate(ColumnBase):
    """Schema for creating a column."""
    pass


class ColumnUpdate(BaseModel):
    """Schema for updating a column."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = Field(None, ge=0)


class ColumnResponse(ColumnBase):
    """Schema for column response."""
    id: UUID
    board_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ColumnWithTasks(ColumnResponse):
    """Column response with tasks."""
    tasks: List["TaskResponse"] = []


# ============================================================================
# Task Schemas
# ============================================================================

class TaskBase(BaseModel):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern=r"^(low|medium|high|urgent)$")
    deadline: Optional[datetime] = None


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    column_id: UUID
    assignee_id: Optional[UUID] = None
    position: Optional[int] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(None, pattern=r"^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern=r"^(todo|in_progress|review|done)$")
    deadline: Optional[datetime] = None
    position: Optional[int] = Field(None, ge=0)


class TaskMove(BaseModel):
    """Schema for moving a task to another column."""
    target_column_id: UUID
    new_position: Optional[int] = None


class TaskResponse(TaskBase):
    """Schema for task response."""
    id: UUID
    column_id: UUID
    board_id: UUID
    assignee_id: Optional[UUID]
    status: str
    position: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TaskWithComments(TaskResponse):
    """Task response with comments."""
    comments: List["CommentResponse"] = []


# ============================================================================
# Task Filter Schemas
# ============================================================================

class TaskFilter(BaseModel):
    """Schema for filtering tasks."""
    board_id: Optional[UUID] = None
    column_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(None, pattern=r"^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern=r"^(todo|in_progress|review|done)$")
    search: Optional[str] = None
    deadline_before: Optional[datetime] = None
    deadline_after: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# Comment Schemas
# ============================================================================

class CommentBase(BaseModel):
    """Base comment schema."""
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    """Schema for creating a comment."""
    pass


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""
    content: str = Field(..., min_length=1)


class CommentResponse(CommentBase):
    """Schema for comment response."""
    id: UUID
    task_id: UUID
    author_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Analytics Schemas
# ============================================================================

class BurnDownDataPoint(BaseModel):
    """Single data point for burn-down chart."""
    date: datetime
    remaining_tasks: int
    completed_tasks: int


class BoardStats(BaseModel):
    """Board statistics."""
    board_id: UUID
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    urgent_tasks: int
    overdue_tasks: int
    burn_down_data: List[BurnDownDataPoint]


# ============================================================================
# Webhook Schemas
# ============================================================================

class WebhookEvent(BaseModel):
    """Webhook event payload."""
    event_type: str = Field(..., description="Type of event: task.created, task.updated, etc.")
    entity_type: str = Field(..., description="Type of entity: task, comment, board, column")
    entity_id: UUID
    board_id: UUID
    user_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[dict] = None


# Update forward references
ColumnWithTasks.model_rebuild()
TaskWithComments.model_rebuild()

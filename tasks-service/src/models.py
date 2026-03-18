"""
Database models for Task Service.
SQLAlchemy 2.0 async models for PostgreSQL 'task' schema.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
from sqlalchemy.schema import DefaultClause


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Board(Base):
    """Board model for Kanban boards."""
    __tablename__ = "boards"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=DefaultClause(text("gen_random_uuid()")))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    color = Column(String(7), default="#6366f1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    members = relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")
    columns = relationship("Column", back_populates="board", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="board", cascade="all, delete-orphan")


class BoardMember(Base):
    """Board member model for managing board access."""
    __tablename__ = "board_members"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name="check_role"),
        {"schema": "task"},
    )

    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    role = Column(String(20), nullable=False, default="viewer")

    # Relationships
    board = relationship("Board", back_populates="members")


class Column(Base):
    """Column model for Kanban columns (lists)."""
    __tablename__ = "columns"
    __table_args__ = {"schema": "task"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=DefaultClause(text("gen_random_uuid()")))
    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column", cascade="all, delete-orphan")


class Task(Base):
    """Task model for Kanban tasks."""
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name="check_priority"),
        Index("tasks_board_id_idx", "board_id"),
        Index("tasks_column_id_idx", "column_id"),
        Index("tasks_assignee_id_idx", "assignee_id"),
        {"schema": "task"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=DefaultClause(text("gen_random_uuid()")))
    column_id = Column(UUID(as_uuid=True), ForeignKey("task.columns.id", ondelete="CASCADE"), nullable=False)
    board_id = Column(UUID(as_uuid=True), ForeignKey("task.boards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(UUID(as_uuid=True), nullable=True)
    priority = Column(String(10), default="medium")
    status = Column(String(20), default="todo")
    deadline = Column(DateTime(timezone=True), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    column = relationship("Column", back_populates="tasks")
    board = relationship("Board", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    """Comment model for task comments."""
    __tablename__ = "comments"
    __table_args__ = (
        Index("comments_task_id_idx", "task_id"),
        {"schema": "task"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=DefaultClause(text("gen_random_uuid()")))
    task_id = Column(UUID(as_uuid=True), ForeignKey("task.tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")

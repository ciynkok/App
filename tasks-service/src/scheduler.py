"""
Scheduler service for deadline reminders using APScheduler.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from src.config import settings
from src.database import AsyncSessionLocal
from src.models import Task, BoardMember
from src.webhook import webhook_service


logger = logging.getLogger(__name__)


class DeadlineScheduler:
    """Scheduler for managing deadline reminders."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.enabled = settings.scheduler_enabled
    
    def start(self):
        """Start the scheduler if enabled."""
        if not self.enabled:
            logger.info("Scheduler is disabled")
            return
        
        try:
            # Schedule daily check for upcoming deadlines
            self.scheduler.add_job(
                self.check_upcoming_deadlines,
                trigger=CronTrigger(hour=9, minute=0),  # Run at 9:00 AM daily
                id="check_upcoming_deadlines",
                replace_existing=True
            )
            
            # Schedule daily check for overdue tasks
            self.scheduler.add_job(
                self.check_overdue_tasks,
                trigger=CronTrigger(hour=9, minute=30),  # Run at 9:30 AM daily
                id="check_overdue_tasks",
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    async def check_upcoming_deadlines(self):
        """
        Check for tasks with deadlines in the next 24 hours.
        Send reminders to assignees and board members.
        """
        logger.info("Checking for upcoming deadlines...")
        
        async with AsyncSessionLocal() as db:
            try:
                tomorrow = datetime.utcnow() + timedelta(days=1)
                
                # Find tasks due in the next 24 hours
                result = await db.execute(
                    select(Task).where(
                        and_(
                            Task.deadline.isnot(None),
                            Task.deadline <= tomorrow,
                            Task.deadline > datetime.utcnow(),
                            Task.status != "done"
                        )
                    )
                )
                tasks = result.scalars().all()
                
                logger.info(f"Found {len(tasks)} tasks with upcoming deadlines")
                
                for task in tasks:
                    await self._send_deadline_reminder(db, task, "upcoming")
                    
            except Exception as e:
                logger.error(f"Error checking upcoming deadlines: {e}")
    
    async def check_overdue_tasks(self):
        """
        Check for tasks that are past their deadline.
        Send notifications to assignees and board members.
        """
        logger.info("Checking for overdue tasks...")
        
        async with AsyncSessionLocal() as db:
            try:
                # Find overdue tasks
                result = await db.execute(
                    select(Task).where(
                        and_(
                            Task.deadline.isnot(None),
                            Task.deadline < datetime.utcnow(),
                            Task.status != "done"
                        )
                    )
                )
                tasks = result.scalars().all()
                
                logger.info(f"Found {len(tasks)} overdue tasks")
                
                for task in tasks:
                    await self._send_deadline_reminder(db, task, "overdue")
                    
            except Exception as e:
                logger.error(f"Error checking overdue tasks: {e}")
    
    async def _send_deadline_reminder(
        self,
        db: AsyncSession,
        task: Task,
        reminder_type: str
    ):
        """
        Send deadline reminder for a task.
        
        Args:
            db: Database session
            task: Task with deadline
            reminder_type: Type of reminder (upcoming or overdue)
        """
        try:
            # Get board members to notify
            result = await db.execute(
                select(BoardMember).where(BoardMember.board_id == task.board_id)
            )
            members = result.scalars().all()
            
            # Send webhook for each member
            for member in members:
                await webhook_service.send_event(
                    event_type=f"deadline.{reminder_type}",
                    entity_type="task",
                    entity_id=str(task.id),
                    board_id=str(task.board_id),
                    user_id=str(member.user_id),
                    data={
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "deadline": task.deadline.isoformat() if task.deadline else None,
                        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                        "reminder_type": reminder_type
                    }
                )
            
            logger.info(
                f"Sent {reminder_type} reminder for task {task.id} "
                f"to {len(members)} board members"
            )
            
        except Exception as e:
            logger.error(f"Error sending deadline reminder for task {task.id}: {e}")
    
    async def schedule_task_reminder(self, task_id: str, deadline: datetime):
        """
        Schedule a one-time reminder for a specific task.
        
        Args:
            task_id: Task ID
            deadline: Task deadline
        """
        if not self.enabled:
            return
        
        try:
            # Schedule reminder 1 day before deadline
            reminder_time = deadline - timedelta(days=1)
            
            if reminder_time > datetime.utcnow():
                job_id = f"task_reminder_{task_id}"
                
                self.scheduler.add_job(
                    self._send_task_reminder,
                    trigger="date",
                    run_date=reminder_time,
                    args=[task_id],
                    id=job_id,
                    replace_existing=True
                )
                
                logger.info(f"Scheduled reminder for task {task_id} at {reminder_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling reminder for task {task_id}: {e}")
    
    async def cancel_task_reminder(self, task_id: str):
        """
        Cancel a scheduled reminder for a task.
        
        Args:
            task_id: Task ID
        """
        if not self.enabled:
            return
        
        try:
            job_id = f"task_reminder_{task_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled reminder for task {task_id}")
        except Exception as e:
            logger.warning(f"Could not cancel reminder for task {task_id}: {e}")
    
    async def _send_task_reminder(self, task_id: str):
        """
        Send a reminder for a specific task.
        
        Args:
            task_id: Task ID
        """
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if task and task.deadline and task.status != "done":
                    await self._send_deadline_reminder(db, task, "upcoming")
                    
            except Exception as e:
                logger.error(f"Error sending reminder for task {task_id}: {e}")


# Global scheduler instance
deadline_scheduler = DeadlineScheduler()

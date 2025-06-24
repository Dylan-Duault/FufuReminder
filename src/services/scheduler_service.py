import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from ..models.reminder import Reminder
from ..config.settings import get_settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class SchedulerService:
    """Service for managing reminder scheduling and execution"""
    
    def __init__(self, reminder_service=None):
        self.reminder_service = reminder_service  # Injected to avoid circular imports
        self.settings = get_settings()
        self._scheduled_reminders: Dict[int, Dict[str, Any]] = {}
        self._task: Optional[asyncio.Task] = None
        self._check_interval = self.settings.scheduling.check_interval_minutes * 60  # Convert to seconds
        self.is_running = False
    
    async def start(self) -> None:
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Scheduler stopped")
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler and clean up all scheduled tasks"""
        await self.stop()
        await self.clear_all_scheduled()
        logger.info("Scheduler shutdown complete")
    
    async def schedule_reminder(self, reminder: Reminder) -> None:
        """Schedule a reminder for execution"""
        # Cancel existing task if already scheduled
        if reminder.id in self._scheduled_reminders:
            existing_task = self._scheduled_reminders[reminder.id]["task"]
            existing_task.cancel()
        
        # Calculate delay until execution
        now = datetime.utcnow()
        if reminder.next_execution <= now:
            # Execute immediately if past due
            delay = 0
        else:
            delay = (reminder.next_execution - now).total_seconds()
        
        # Create new task
        task = asyncio.create_task(self._wait_and_execute(reminder, delay))
        
        # Store in scheduled reminders
        self._scheduled_reminders[reminder.id] = {
            "reminder": reminder,
            "task": task,
            "scheduled_at": now
        }
        
        logger.info(
            "Scheduled reminder",
            reminder_id=reminder.id,
            execution_time=reminder.next_execution,
            delay_seconds=delay
        )
    
    async def unschedule_reminder(self, reminder_id: int) -> bool:
        """Unschedule a reminder"""
        if reminder_id not in self._scheduled_reminders:
            return False
        
        task_info = self._scheduled_reminders[reminder_id]
        task_info["task"].cancel()
        del self._scheduled_reminders[reminder_id]
        
        logger.info("Unscheduled reminder", reminder_id=reminder_id)
        return True
    
    async def reschedule_reminder(self, reminder: Reminder) -> None:
        """Reschedule an existing reminder with new execution time"""
        if reminder.id in self._scheduled_reminders:
            await self.unschedule_reminder(reminder.id)
        
        await self.schedule_reminder(reminder)
        
        logger.info(
            "Rescheduled reminder",
            reminder_id=reminder.id,
            new_execution_time=reminder.next_execution
        )
    
    async def update_reminder_schedule(self, reminder_id: int, new_execution_time: datetime) -> bool:
        """Update the execution time for a scheduled reminder"""
        if reminder_id not in self._scheduled_reminders:
            return False
        
        task_info = self._scheduled_reminders[reminder_id]
        reminder = task_info["reminder"]
        reminder.next_execution = new_execution_time
        
        await self.reschedule_reminder(reminder)
        return True
    
    def get_scheduled_count(self) -> int:
        """Get the number of currently scheduled reminders"""
        return len(self._scheduled_reminders)
    
    def is_reminder_scheduled(self, reminder_id: int) -> bool:
        """Check if a reminder is currently scheduled"""
        return reminder_id in self._scheduled_reminders
    
    def get_next_execution_times(self) -> Dict[int, datetime]:
        """Get next execution times for all scheduled reminders"""
        return {
            reminder_id: info["reminder"].next_execution
            for reminder_id, info in self._scheduled_reminders.items()
        }
    
    async def clear_all_scheduled(self) -> int:
        """Clear all scheduled reminders"""
        count = len(self._scheduled_reminders)
        
        for task_info in self._scheduled_reminders.values():
            task_info["task"].cancel()
        
        self._scheduled_reminders.clear()
        
        logger.info("Cleared all scheduled reminders", count=count)
        return count
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that processes due reminders"""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                if self.reminder_service:
                    processed_count = await self.reminder_service.process_due_reminders()
                    if processed_count > 0:
                        logger.info("Processed due reminders", count=processed_count)
                
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop", error=str(e))
                await asyncio.sleep(self._check_interval)  # Continue after error
        
        logger.info("Scheduler loop stopped")
    
    async def _wait_and_execute(self, reminder: Reminder, delay: float) -> None:
        """Wait for the specified delay and then execute the reminder"""
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            
            await self._execute_reminder(reminder)
            
        except asyncio.CancelledError:
            logger.debug("Reminder execution cancelled", reminder_id=reminder.id)
        except Exception as e:
            logger.error(
                "Error executing reminder",
                reminder_id=reminder.id,
                error=str(e)
            )
        finally:
            # Remove from scheduled reminders
            if reminder.id in self._scheduled_reminders:
                del self._scheduled_reminders[reminder.id]
    
    async def _execute_reminder(self, reminder: Reminder) -> None:
        """Execute a reminder (placeholder for actual execution logic)"""
        logger.info(
            "Executing reminder",
            reminder_id=reminder.id,
            user_id=reminder.user_id,
            message_content=reminder.message_content
        )
        
        # This is where the actual reminder execution would happen
        # For now, we just log it. In a full implementation, this would:
        # 1. Send the Discord message
        # 2. Add reaction if validation required
        # 3. Create validation record if needed
        # 4. Update the reminder's next execution time
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "scheduled_count": self.get_scheduled_count(),
            "check_interval_seconds": self._check_interval,
            "next_executions": {
                str(reminder_id): execution_time.isoformat()
                for reminder_id, execution_time in self.get_next_execution_times().items()
            }
        }
    
    async def force_process_due_reminders(self) -> int:
        """Manually trigger processing of due reminders"""
        if self.reminder_service:
            processed_count = await self.reminder_service.process_due_reminders()
            logger.info("Manually processed due reminders", count=processed_count)
            return processed_count
        return 0
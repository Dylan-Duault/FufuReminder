from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from ..repositories.reminder_repo import ReminderRepository
from ..repositories.validation_repo import ValidationRepository
from ..database.models import ReminderModel
from ..models.reminder import Reminder
from ..models.enums import ReminderStatus, ValidationStatus, FrequencyEnum
from ..config.settings import get_settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class ReminderService:
    """Service for managing reminder business logic"""
    
    def __init__(
        self,
        reminder_repo: ReminderRepository,
        validation_repo: ValidationRepository,
        scheduler_service=None  # Optional to avoid circular imports
    ):
        self.reminder_repo = reminder_repo
        self.validation_repo = validation_repo
        self.scheduler_service = scheduler_service
        self.settings = get_settings()
    
    async def create_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        frequency: FrequencyEnum,
        message_content: str,
        created_by: str,
        validation_required: bool = False
    ) -> Reminder:
        """Create a new reminder"""
        
        # Validate input
        if not message_content.strip():
            raise ValueError("Message content cannot be empty")
        
        # Check user reminder limit
        user_reminder_count = await self.reminder_repo.count_by_user_id(user_id)
        if user_reminder_count >= self.settings.limits.max_reminders_per_user:
            raise ValueError("User has reached maximum number of reminders")
        
        # Create domain reminder to calculate next execution
        domain_reminder = Reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=frequency,
            message_content=message_content.strip(),
            validation_required=validation_required,
            created_by=created_by
        )
        
        # Create database model
        reminder_model = ReminderModel(
            user_id=domain_reminder.user_id,
            guild_id=domain_reminder.guild_id,
            channel_id=domain_reminder.channel_id,
            frequency=domain_reminder.frequency,
            message_content=domain_reminder.message_content,
            validation_required=domain_reminder.validation_required,
            status=domain_reminder.status,
            created_by=domain_reminder.created_by,
            next_execution=domain_reminder.next_execution,
            created_at=domain_reminder.created_at,
            updated_at=domain_reminder.updated_at
        )
        
        # Save to database
        created_model = await self.reminder_repo.create(reminder_model)
        
        # Convert back to domain model with ID
        result_reminder = self._model_to_domain(created_model)
        
        # Schedule the reminder
        if self.scheduler_service:
            await self.scheduler_service.schedule_reminder(result_reminder)
        
        logger.info(
            "Created reminder",
            reminder_id=created_model.id,
            user_id=user_id,
            frequency=frequency.value,
            validation_required=validation_required
        )
        
        return result_reminder
    
    async def get_reminder_by_id(self, reminder_id: int) -> Optional[Reminder]:
        """Get a reminder by its ID"""
        model = await self.reminder_repo.get_by_id(reminder_id)
        return self._model_to_domain(model) if model else None
    
    async def get_user_reminders(self, user_id: str) -> List[Reminder]:
        """Get all reminders for a user"""
        models = await self.reminder_repo.find_by_user_id(user_id)
        return [self._model_to_domain(model) for model in models]
    
    async def get_guild_reminders(self, guild_id: str) -> List[Reminder]:
        """Get all reminders for a guild"""
        models = await self.reminder_repo.find_by_guild_id(guild_id)
        return [self._model_to_domain(model) for model in models]
    
    async def update_reminder_status(self, reminder_id: int, status: ReminderStatus) -> bool:
        """Update the status of a reminder"""
        success = await self.reminder_repo.update_status(reminder_id, status)
        
        if success and self.scheduler_service:
            if status == ReminderStatus.PAUSED:
                await self.scheduler_service.unschedule_reminder(reminder_id)
            elif status == ReminderStatus.ACTIVE:
                # Reschedule the reminder
                reminder = await self.get_reminder_by_id(reminder_id)
                if reminder:
                    await self.scheduler_service.schedule_reminder(reminder)
        
        if success:
            logger.info(
                "Updated reminder status",
                reminder_id=reminder_id,
                new_status=status.value
            )
        
        return success
    
    async def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder and its associated validations"""
        
        # First, delete any associated validations
        validations = await self.validation_repo.find_by_reminder_id(reminder_id)
        for validation in validations:
            await self.validation_repo.delete(validation.id)
        
        # Unschedule the reminder
        if self.scheduler_service:
            await self.scheduler_service.unschedule_reminder(reminder_id)
        
        # Delete the reminder
        success = await self.reminder_repo.delete(reminder_id)
        
        if success:
            logger.info(
                "Deleted reminder",
                reminder_id=reminder_id,
                deleted_validations=len(validations)
            )
        
        return success
    
    async def process_due_reminders(self) -> int:
        """Process all reminders that are due for execution"""
        due_reminders = await self.reminder_repo.find_due_reminders()
        processed_count = 0
        
        for reminder_model in due_reminders:
            try:
                # Send the reminder notification
                await self._send_reminder_notification(reminder_model)
                
                # Update next execution time
                domain_reminder = self._model_to_domain(reminder_model)
                domain_reminder.update_next_execution()
                
                await self.reminder_repo.update_next_execution(
                    reminder_model.id,
                    domain_reminder.next_execution
                )
                
                processed_count += 1
                
                logger.info(
                    "Processed due reminder",
                    reminder_id=reminder_model.id,
                    next_execution=domain_reminder.next_execution
                )
                
            except Exception as e:
                logger.error(
                    "Failed to process reminder",
                    reminder_id=reminder_model.id,
                    error=str(e)
                )
        
        return processed_count
    
    async def validate_reminder_permission(self, user_roles: List[str], admin_role_ids: List[int]) -> bool:
        """Check if user has permission to create/manage reminders"""
        # Convert role IDs to strings for comparison if needed
        admin_role_str = [str(role_id) for role_id in admin_role_ids]
        
        # Check if user has any admin roles
        return any(role in admin_role_str for role in user_roles) or \
               any(role in ["admin", "administrator", "moderator"] for role in [r.lower() for r in user_roles])
    
    async def get_reminder_statistics(self) -> Dict[str, Any]:
        """Get reminder statistics"""
        total_reminders = await self.reminder_repo.count()
        active_reminders_models = await self.reminder_repo.find_by_status(ReminderStatus.ACTIVE)
        active_reminders = len(active_reminders_models)
        pending_validations = await self.validation_repo.count_by_status(ValidationStatus.PENDING)
        
        return {
            "total_reminders": total_reminders,
            "active_reminders": active_reminders,
            "paused_reminders": total_reminders - active_reminders,
            "pending_validations": pending_validations
        }
    
    async def cleanup_old_reminders(self, cutoff_days: int = 30) -> int:
        """Clean up old completed reminders"""
        cutoff_date = datetime.utcnow() - timedelta(days=cutoff_days)
        cleaned_count = await self.reminder_repo.cleanup_completed_reminders(cutoff_date)
        
        logger.info(
            "Cleaned up old reminders",
            cleaned_count=cleaned_count,
            cutoff_days=cutoff_days
        )
        
        return cleaned_count
    
    async def bulk_update_reminders(self, reminder_ids: List[int], status: ReminderStatus) -> int:
        """Update status for multiple reminders"""
        updated_count = await self.reminder_repo.bulk_update_status(reminder_ids, status)
        
        # Handle scheduler updates
        if self.scheduler_service:
            if status == ReminderStatus.PAUSED:
                for reminder_id in reminder_ids:
                    await self.scheduler_service.unschedule_reminder(reminder_id)
            elif status == ReminderStatus.ACTIVE:
                for reminder_id in reminder_ids:
                    reminder = await self.get_reminder_by_id(reminder_id)
                    if reminder:
                        await self.scheduler_service.schedule_reminder(reminder)
        
        logger.info(
            "Bulk updated reminders",
            updated_count=updated_count,
            new_status=status.value
        )
        
        return updated_count
    
    async def _send_reminder_notification(self, reminder_model: ReminderModel) -> None:
        """Send reminder notification (placeholder for Discord integration)"""
        # This will be implemented when we create the notification service
        # For now, just log the action
        logger.info(
            "Sending reminder notification",
            reminder_id=reminder_model.id,
            user_id=reminder_model.user_id,
            message_content=reminder_model.message_content
        )
    
    def _model_to_domain(self, model: ReminderModel) -> Reminder:
        """Convert database model to domain model"""
        return Reminder(
            user_id=model.user_id,
            guild_id=model.guild_id,
            channel_id=model.channel_id,
            frequency=model.frequency,
            message_content=model.message_content,
            created_by=model.created_by,
            validation_required=model.validation_required,
            reminder_id=model.id,
            status=model.status,
            created_at=model.created_at,
            next_execution=model.next_execution
        )
    
    async def cleanup_guild_reminders(self, guild_id: str) -> bool:
        """
        Clean up all reminders for a guild when bot is removed.
        
        Args:
            guild_id: The Discord guild ID to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            logger.info("Starting guild reminder cleanup", guild_id=guild_id)
            
            # Get all reminders for this guild
            guild_reminders = await self.reminder_repository.find_by_guild_id(guild_id)
            
            if not guild_reminders:
                logger.info("No reminders found for guild", guild_id=guild_id)
                return True
            
            # Delete all reminders for this guild
            deleted_count = 0
            for reminder in guild_reminders:
                success = await self.reminder_repository.delete(reminder.id)
                if success:
                    deleted_count += 1
                    # Remove from active reminders if present
                    self._active_reminders.discard(reminder.id)
                else:
                    logger.warning(
                        "Failed to delete reminder during guild cleanup",
                        reminder_id=reminder.id,
                        guild_id=guild_id
                    )
            
            logger.info(
                "Guild reminder cleanup complete",
                guild_id=guild_id,
                total_reminders=len(guild_reminders),
                deleted_count=deleted_count
            )
            
            return deleted_count == len(guild_reminders)
            
        except Exception as e:
            logger.error(
                "Failed to cleanup guild reminders",
                guild_id=guild_id,
                error=str(e)
            )
            return False
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.reminder import Reminder
from ..models.enums import FrequencyEnum, ReminderStatus
from ..strategies.frequency_strategy import get_frequency_strategy


class ReminderFactory:
    """Factory for creating Reminder domain objects"""
    
    def create_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        frequency: FrequencyEnum,
        message_content: str,
        created_by: str,
        validation_required: bool = False,
        status: ReminderStatus = ReminderStatus.ACTIVE,
        reminder_id: Optional[int] = None,
        next_execution: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Reminder:
        """Create a new reminder with the given parameters"""
        
        # Validate message content
        if not message_content or not message_content.strip():
            raise ValueError("Message content cannot be empty")
        
        # Calculate next execution time if not provided
        if next_execution is None:
            current_time = datetime.utcnow()
            frequency_strategy = get_frequency_strategy(frequency)
            next_execution = frequency_strategy.calculate_next_execution(current_time)
        
        # Create reminder instance
        return Reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=frequency,
            message_content=message_content.strip(),
            created_by=created_by,
            validation_required=validation_required,
            status=status,
            reminder_id=reminder_id,
            next_execution=next_execution,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def create_from_dict(self, data: Dict[str, Any]) -> Reminder:
        """Create a reminder from a dictionary of data"""
        
        # Extract required fields
        user_id = data["user_id"]
        guild_id = data["guild_id"]
        channel_id = data["channel_id"]
        frequency = data["frequency"]
        message_content = data["message_content"]
        created_by = data["created_by"]
        
        # Extract optional fields with defaults
        validation_required = data.get("validation_required", False)
        status = data.get("status", ReminderStatus.ACTIVE)
        reminder_id = data.get("reminder_id")
        next_execution = data.get("next_execution")
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        return self.create_reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=frequency,
            message_content=message_content,
            created_by=created_by,
            validation_required=validation_required,
            status=status,
            reminder_id=reminder_id,
            next_execution=next_execution,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def bulk_create_reminders(self, reminder_data_list: List[Dict[str, Any]]) -> List[Reminder]:
        """Create multiple reminders from a list of data dictionaries"""
        return [self.create_from_dict(data) for data in reminder_data_list]
    
    def clone_reminder(self, original: Reminder, **overrides) -> Reminder:
        """Clone an existing reminder with optional field overrides"""
        
        # Start with original reminder's data
        data = {
            "user_id": original.user_id,
            "guild_id": original.guild_id,
            "channel_id": original.channel_id,
            "frequency": original.frequency,
            "message_content": original.message_content,
            "created_by": original.created_by,
            "validation_required": original.validation_required,
            "status": original.status,
            "reminder_id": None,  # New reminder gets new ID
            "next_execution": None,  # Will be recalculated
            "created_at": None,  # Will be set to current time
            "updated_at": None   # Will be set to current time
        }
        
        # Apply any overrides
        data.update(overrides)
        
        return self.create_from_dict(data)
    
    def create_hourly_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        message_content: str,
        created_by: str,
        **kwargs
    ) -> Reminder:
        """Convenience method for creating hourly reminders"""
        return self.create_reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=FrequencyEnum.HOURLY,
            message_content=message_content,
            created_by=created_by,
            **kwargs
        )
    
    def create_daily_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        message_content: str,
        created_by: str,
        **kwargs
    ) -> Reminder:
        """Convenience method for creating daily reminders"""
        return self.create_reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=FrequencyEnum.DAILY,
            message_content=message_content,
            created_by=created_by,
            **kwargs
        )
    
    def create_weekly_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        message_content: str,
        created_by: str,
        **kwargs
    ) -> Reminder:
        """Convenience method for creating weekly reminders"""
        return self.create_reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=FrequencyEnum.WEEKLY,
            message_content=message_content,
            created_by=created_by,
            **kwargs
        )
    
    def create_monthly_reminder(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        message_content: str,
        created_by: str,
        **kwargs
    ) -> Reminder:
        """Convenience method for creating monthly reminders"""
        return self.create_reminder(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            frequency=FrequencyEnum.MONTHLY,
            message_content=message_content,
            created_by=created_by,
            **kwargs
        )
from datetime import datetime, timedelta
from typing import Optional
from .enums import FrequencyEnum, ReminderStatus


class Reminder:
    """Domain model for reminders"""
    
    def __init__(
        self,
        user_id: str,
        guild_id: str,
        channel_id: str,
        frequency: FrequencyEnum,
        message_content: str,
        created_by: str,
        validation_required: bool = False,
        reminder_id: Optional[int] = None,
        status: ReminderStatus = ReminderStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        next_execution: Optional[datetime] = None
    ):
        if not message_content.strip():
            raise ValueError("Message content cannot be empty")
        
        if not isinstance(frequency, FrequencyEnum):
            raise ValueError(f"Invalid frequency: {frequency}")
        
        self.id = reminder_id
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.frequency = frequency
        self.message_content = message_content.strip()
        self.validation_required = validation_required
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Set next execution time
        self.next_execution = next_execution or self._calculate_next_execution()
    
    def _calculate_next_execution(self, from_time: Optional[datetime] = None) -> datetime:
        """Calculate the next execution time based on frequency"""
        from ..strategies.frequency_strategy import get_frequency_strategy
        
        base_time = from_time or self.created_at
        strategy = get_frequency_strategy(self.frequency)
        return strategy.calculate_next_execution(base_time)
    
    def update_next_execution(self) -> None:
        """Update next execution time to the next interval"""
        current_time = datetime.utcnow()
        # If the reminder is overdue, calculate from current time, otherwise from next_execution
        base_time = max(current_time, self.next_execution)
        self.next_execution = self._calculate_next_execution(base_time)
        self.updated_at = current_time
    
    def is_due_for_execution(self, current_time: Optional[datetime] = None) -> bool:
        """Check if the reminder is due for execution"""
        check_time = current_time or datetime.utcnow()
        return self.next_execution <= check_time and self.status == ReminderStatus.ACTIVE
    
    def pause(self) -> None:
        """Pause the reminder"""
        self.status = ReminderStatus.PAUSED
        self.updated_at = datetime.utcnow()
    
    def resume(self) -> None:
        """Resume the reminder"""
        self.status = ReminderStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def cancel(self) -> None:
        """Cancel the reminder"""
        self.status = ReminderStatus.CANCELLED
        self.updated_at = datetime.utcnow()
    
    def complete(self) -> None:
        """Mark the reminder as completed"""
        self.status = ReminderStatus.COMPLETED
        self.updated_at = datetime.utcnow()
    
    def __str__(self) -> str:
        return f"Reminder(id={self.id}, user_id={self.user_id}, frequency={self.frequency.value})"
    
    def __repr__(self) -> str:
        return (f"Reminder(id={self.id}, user_id={self.user_id}, "
                f"frequency={self.frequency.value}, status={self.status.value})")
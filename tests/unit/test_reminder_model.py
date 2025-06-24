import pytest
from datetime import datetime, timedelta
from src.models.reminder import Reminder
from src.models.enums import FrequencyEnum, ReminderStatus


class TestReminder:
    """Test cases for the Reminder domain model"""
    
    def test_create_reminder_with_required_fields(self):
        """Test creating a reminder with all required fields"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321", 
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            created_by="admin_123"
        )
        
        assert reminder.user_id == "123456789"
        assert reminder.guild_id == "987654321"
        assert reminder.channel_id == "111222333"
        assert reminder.frequency == FrequencyEnum.DAILY
        assert reminder.message_content == "Test reminder"
        assert reminder.created_by == "admin_123"
        assert reminder.status == ReminderStatus.ACTIVE
        assert reminder.validation_required is False
        assert reminder.next_execution is not None
        assert isinstance(reminder.created_at, datetime)
    
    def test_create_reminder_with_validation_required(self):
        """Test creating a reminder that requires validation"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333", 
            frequency=FrequencyEnum.WEEKLY,
            message_content="Weekly check-in",
            validation_required=True,
            created_by="admin_123"
        )
        
        assert reminder.validation_required is True
        
    def test_calculate_next_execution_daily(self):
        """Test calculating next execution time for daily frequency"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Daily reminder",
            created_by="admin_123"
        )
        
        # Next execution should be roughly 24 hours from creation
        time_diff = reminder.next_execution - reminder.created_at
        assert 23.5 <= time_diff.total_seconds() / 3600 <= 24.5  # Allow 30 min tolerance
    
    def test_calculate_next_execution_weekly(self):
        """Test calculating next execution time for weekly frequency"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.WEEKLY,
            message_content="Weekly reminder",
            created_by="admin_123"
        )
        
        # Next execution should be roughly 7 days from creation
        time_diff = reminder.next_execution - reminder.created_at
        expected_hours = 7 * 24
        assert expected_hours - 1 <= time_diff.total_seconds() / 3600 <= expected_hours + 1
    
    def test_update_next_execution(self):
        """Test updating next execution time"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            created_by="admin_123"
        )
        
        original_next_execution = reminder.next_execution
        reminder.update_next_execution()
        
        # Next execution should be updated
        assert reminder.next_execution != original_next_execution
        
        # Should be roughly 24 hours after the original next execution
        time_diff = reminder.next_execution - original_next_execution
        assert 23.5 <= time_diff.total_seconds() / 3600 <= 24.5
    
    def test_is_due_for_execution(self):
        """Test checking if reminder is due for execution"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        # Create reminder that's due
        reminder_due = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Due reminder",
            created_by="admin_123"
        )
        reminder_due.next_execution = past_time
        
        # Create reminder that's not due
        reminder_not_due = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Not due reminder",
            created_by="admin_123"
        )
        reminder_not_due.next_execution = future_time
        
        assert reminder_due.is_due_for_execution() is True
        assert reminder_not_due.is_due_for_execution() is False
    
    def test_reminder_str_representation(self):
        """Test string representation of reminder"""
        reminder = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            created_by="admin_123"
        )
        
        str_repr = str(reminder)
        assert "123456789" in str_repr
        assert "daily" in str_repr.lower()
    
    def test_invalid_frequency_raises_error(self):
        """Test that invalid frequency raises an error"""
        with pytest.raises(ValueError):
            Reminder(
                user_id="123456789",
                guild_id="987654321",
                channel_id="111222333",
                frequency="invalid_frequency",  # This should raise an error
                message_content="Test reminder",
                created_by="admin_123"
            )
    
    def test_empty_message_content_raises_error(self):
        """Test that empty message content raises an error"""
        with pytest.raises(ValueError):
            Reminder(
                user_id="123456789",
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content="",  # Empty message should raise error
                created_by="admin_123"
            )
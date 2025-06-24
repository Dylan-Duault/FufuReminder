import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from src.factories.reminder_factory import ReminderFactory
from src.models.reminder import Reminder
from src.models.enums import FrequencyEnum, ReminderStatus
from src.strategies.frequency_strategy import get_frequency_strategy


class TestReminderFactory:
    """Test cases for the ReminderFactory"""
    
    @pytest.fixture
    def reminder_factory(self):
        """Create a reminder factory instance"""
        return ReminderFactory()
    
    @pytest.fixture
    def base_reminder_data(self):
        """Base reminder creation data"""
        return {
            "user_id": "123456789",
            "guild_id": "987654321",
            "channel_id": "111222333",
            "frequency": FrequencyEnum.DAILY,
            "message_content": "Daily standup reminder",
            "created_by": "admin_123",
            "validation_required": True
        }
    
    def test_create_reminder_with_all_fields(self, reminder_factory, base_reminder_data):
        """Test creating reminder with all required fields"""
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert isinstance(reminder, Reminder)
        assert reminder.user_id == "123456789"
        assert reminder.guild_id == "987654321"
        assert reminder.channel_id == "111222333"
        assert reminder.frequency == FrequencyEnum.DAILY
        assert reminder.message_content == "Daily standup reminder"
        assert reminder.created_by == "admin_123"
        assert reminder.validation_required is True
        assert reminder.status == ReminderStatus.ACTIVE
    
    def test_create_reminder_with_custom_next_execution(self, reminder_factory, base_reminder_data):
        """Test creating reminder with custom next execution time"""
        # Arrange
        custom_time = datetime(2024, 6, 15, 14, 30, 0)
        base_reminder_data["next_execution"] = custom_time
        
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.next_execution == custom_time
    
    def test_create_reminder_calculates_next_execution_automatically(self, reminder_factory, base_reminder_data):
        """Test that next execution is calculated automatically when not provided"""
        # Arrange
        with patch('src.factories.reminder_factory.datetime') as mock_datetime:
            fixed_time = datetime(2024, 6, 15, 10, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Act
            reminder = reminder_factory.create_reminder(**base_reminder_data)
            
            # Assert
            # For daily frequency, should be current time + 1 day
            expected_next = fixed_time + timedelta(days=1)
            assert reminder.next_execution == expected_next
    
    def test_create_reminder_different_frequencies(self, reminder_factory, base_reminder_data):
        """Test creating reminders with different frequencies"""
        frequencies = [
            (FrequencyEnum.HOURLY, timedelta(hours=1)),
            (FrequencyEnum.DAILY, timedelta(days=1)),
            (FrequencyEnum.WEEKLY, timedelta(weeks=1)),
        ]
        
        with patch('src.factories.reminder_factory.datetime') as mock_datetime:
            fixed_time = datetime(2024, 6, 15, 10, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            for frequency, expected_delta in frequencies:
                # Arrange
                base_reminder_data["frequency"] = frequency
                
                # Act
                reminder = reminder_factory.create_reminder(**base_reminder_data)
                
                # Assert
                expected_next = fixed_time + expected_delta
                assert reminder.next_execution == expected_next
                assert reminder.frequency == frequency
    
    def test_create_reminder_monthly_frequency(self, reminder_factory, base_reminder_data):
        """Test creating reminder with monthly frequency"""
        # Arrange
        base_reminder_data["frequency"] = FrequencyEnum.MONTHLY
        
        with patch('src.factories.reminder_factory.datetime') as mock_datetime:
            # January 15th should go to February 15th
            fixed_time = datetime(2024, 1, 15, 10, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Act
            reminder = reminder_factory.create_reminder(**base_reminder_data)
            
            # Assert
            expected_next = datetime(2024, 2, 15, 10, 0, 0)
            assert reminder.next_execution == expected_next
            assert reminder.frequency == FrequencyEnum.MONTHLY
    
    def test_create_reminder_validation_not_required(self, reminder_factory, base_reminder_data):
        """Test creating reminder without validation requirement"""
        # Arrange
        base_reminder_data["validation_required"] = False
        
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.validation_required is False
    
    def test_create_reminder_with_custom_status(self, reminder_factory, base_reminder_data):
        """Test creating reminder with custom status"""
        # Arrange
        base_reminder_data["status"] = ReminderStatus.PAUSED
        
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.status == ReminderStatus.PAUSED
    
    def test_create_reminder_with_reminder_id(self, reminder_factory, base_reminder_data):
        """Test creating reminder with specific ID"""
        # Arrange
        base_reminder_data["reminder_id"] = 42
        
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.id == 42
    
    def test_create_reminder_timestamps_are_set(self, reminder_factory, base_reminder_data):
        """Test that creation and update timestamps are set"""
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.created_at is not None
        assert reminder.updated_at is not None
        assert isinstance(reminder.created_at, datetime)
        assert isinstance(reminder.updated_at, datetime)
    
    def test_create_reminder_with_custom_timestamps(self, reminder_factory, base_reminder_data):
        """Test creating reminder with custom timestamps"""
        # Arrange
        custom_created = datetime(2024, 1, 1, 12, 0, 0)
        custom_updated = datetime(2024, 1, 2, 12, 0, 0)
        base_reminder_data["created_at"] = custom_created
        base_reminder_data["updated_at"] = custom_updated
        
        # Act
        reminder = reminder_factory.create_reminder(**base_reminder_data)
        
        # Assert
        assert reminder.created_at == custom_created
        assert reminder.updated_at == custom_updated
    
    def test_create_from_dict_full_data(self, reminder_factory):
        """Test creating reminder from dictionary with full data"""
        # Arrange
        reminder_dict = {
            "user_id": "123456789",
            "guild_id": "987654321", 
            "channel_id": "111222333",
            "frequency": FrequencyEnum.WEEKLY,
            "message_content": "Weekly team meeting",
            "created_by": "admin_456",
            "validation_required": False,
            "status": ReminderStatus.ACTIVE,
            "reminder_id": 100,
            "next_execution": datetime(2024, 6, 20, 9, 0, 0),
            "created_at": datetime(2024, 6, 15, 10, 0, 0),
            "updated_at": datetime(2024, 6, 15, 10, 0, 0)
        }
        
        # Act
        reminder = reminder_factory.create_from_dict(reminder_dict)
        
        # Assert
        assert reminder.user_id == "123456789"
        assert reminder.guild_id == "987654321"
        assert reminder.channel_id == "111222333"
        assert reminder.frequency == FrequencyEnum.WEEKLY
        assert reminder.message_content == "Weekly team meeting"
        assert reminder.created_by == "admin_456"
        assert reminder.validation_required is False
        assert reminder.status == ReminderStatus.ACTIVE
        assert reminder.id == 100
        assert reminder.next_execution == datetime(2024, 6, 20, 9, 0, 0)
        assert reminder.created_at == datetime(2024, 6, 15, 10, 0, 0)
        assert reminder.updated_at == datetime(2024, 6, 15, 10, 0, 0)
    
    def test_create_from_dict_minimal_data(self, reminder_factory):
        """Test creating reminder from dictionary with minimal required data"""
        # Arrange
        reminder_dict = {
            "user_id": "123456789",
            "guild_id": "987654321",
            "channel_id": "111222333",
            "frequency": FrequencyEnum.DAILY,
            "message_content": "Daily reminder",
            "created_by": "admin_123"
        }
        
        # Act
        reminder = reminder_factory.create_from_dict(reminder_dict)
        
        # Assert
        assert reminder.user_id == "123456789"
        assert reminder.frequency == FrequencyEnum.DAILY
        assert reminder.message_content == "Daily reminder"
        assert reminder.validation_required is False  # Default value
        assert reminder.status == ReminderStatus.ACTIVE  # Default value
        assert reminder.next_execution is not None  # Should be calculated
        assert reminder.created_at is not None  # Should be set
        assert reminder.updated_at is not None  # Should be set
    
    def test_create_reminder_invalid_frequency(self, reminder_factory, base_reminder_data):
        """Test creating reminder with invalid frequency"""
        # Arrange
        base_reminder_data["frequency"] = "INVALID_FREQUENCY"
        
        # Act & Assert
        with pytest.raises(ValueError):
            reminder_factory.create_reminder(**base_reminder_data)
    
    def test_create_reminder_empty_message_content(self, reminder_factory, base_reminder_data):
        """Test creating reminder with empty message content"""
        # Arrange
        base_reminder_data["message_content"] = ""
        
        # Act & Assert
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            reminder_factory.create_reminder(**base_reminder_data)
    
    def test_create_reminder_none_message_content(self, reminder_factory, base_reminder_data):
        """Test creating reminder with None message content"""
        # Arrange
        base_reminder_data["message_content"] = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            reminder_factory.create_reminder(**base_reminder_data)
    
    def test_create_reminder_whitespace_message_content(self, reminder_factory, base_reminder_data):
        """Test creating reminder with whitespace-only message content"""
        # Arrange
        base_reminder_data["message_content"] = "   \n\t   "
        
        # Act & Assert
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            reminder_factory.create_reminder(**base_reminder_data)
    
    def test_factory_uses_frequency_strategy(self, reminder_factory, base_reminder_data):
        """Test that factory uses frequency strategy for calculation"""
        # Arrange
        base_reminder_data["frequency"] = FrequencyEnum.HOURLY
        
        with patch('src.factories.reminder_factory.get_frequency_strategy') as mock_get_strategy:
            mock_strategy = mock_get_strategy.return_value
            expected_time = datetime(2024, 6, 15, 11, 0, 0)
            mock_strategy.calculate_next_execution.return_value = expected_time
            
            # Act
            reminder = reminder_factory.create_reminder(**base_reminder_data)
            
            # Assert
            mock_get_strategy.assert_called_once_with(FrequencyEnum.HOURLY)
            mock_strategy.calculate_next_execution.assert_called_once()
            assert reminder.next_execution == expected_time
    
    def test_bulk_create_reminders(self, reminder_factory):
        """Test creating multiple reminders in bulk"""
        # Arrange
        reminder_dicts = [
            {
                "user_id": "user1",
                "guild_id": "guild1",
                "channel_id": "channel1",
                "frequency": FrequencyEnum.DAILY,
                "message_content": "Reminder 1",
                "created_by": "admin1"
            },
            {
                "user_id": "user2",
                "guild_id": "guild1", 
                "channel_id": "channel1",
                "frequency": FrequencyEnum.WEEKLY,
                "message_content": "Reminder 2",
                "created_by": "admin1"
            }
        ]
        
        # Act
        reminders = reminder_factory.bulk_create_reminders(reminder_dicts)
        
        # Assert
        assert len(reminders) == 2
        assert reminders[0].user_id == "user1"
        assert reminders[0].frequency == FrequencyEnum.DAILY
        assert reminders[1].user_id == "user2"
        assert reminders[1].frequency == FrequencyEnum.WEEKLY
    
    def test_clone_reminder(self, reminder_factory, base_reminder_data):
        """Test cloning an existing reminder"""
        # Arrange
        original = reminder_factory.create_reminder(**base_reminder_data)
        
        # Act
        cloned = reminder_factory.clone_reminder(original, user_id="new_user_123")
        
        # Assert
        assert cloned.user_id == "new_user_123"  # Changed field
        assert cloned.guild_id == original.guild_id  # Copied field
        assert cloned.frequency == original.frequency  # Copied field
        assert cloned.message_content == original.message_content  # Copied field
        assert cloned.id is None  # Cloned reminder should not have an ID
        assert cloned.created_at != original.created_at  # Should have new timestamp
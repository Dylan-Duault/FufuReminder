import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.reminder_service import ReminderService
from src.repositories.reminder_repo import ReminderRepository
from src.repositories.validation_repo import ValidationRepository
from src.database.models import ReminderModel, ValidationModel
from src.models.reminder import Reminder
from src.models.validation import Validation
from src.models.enums import ReminderStatus, ValidationStatus, FrequencyEnum


class TestReminderService:
    """Test cases for the ReminderService"""
    
    @pytest.fixture
    def mock_reminder_repo(self):
        """Create a mock reminder repository"""
        return AsyncMock(spec=ReminderRepository)
    
    @pytest.fixture
    def mock_validation_repo(self):
        """Create a mock validation repository"""
        return AsyncMock(spec=ValidationRepository)
    
    @pytest.fixture
    def mock_scheduler_service(self):
        """Create a mock scheduler service"""
        scheduler = AsyncMock()
        scheduler.schedule_reminder = AsyncMock()
        scheduler.unschedule_reminder = AsyncMock()
        return scheduler
    
    @pytest.fixture
    def reminder_service(self, mock_reminder_repo, mock_validation_repo, mock_scheduler_service):
        """Create a reminder service instance"""
        return ReminderService(
            reminder_repo=mock_reminder_repo,
            validation_repo=mock_validation_repo,
            scheduler_service=mock_scheduler_service
        )
    
    @pytest.fixture
    def sample_reminder_data(self):
        """Sample reminder creation data"""
        return {
            "user_id": "123456789",
            "guild_id": "987654321",
            "channel_id": "111222333",
            "frequency": FrequencyEnum.DAILY,
            "message_content": "Daily standup reminder",
            "validation_required": True,
            "created_by": "admin_123"
        }
    
    @pytest.mark.asyncio
    async def test_create_reminder_success(self, reminder_service, mock_reminder_repo, mock_scheduler_service, sample_reminder_data):
        """Test successful reminder creation"""
        # Arrange
        mock_reminder_repo.count_by_user_id.return_value = 3  # Under limit
        
        created_model = ReminderModel(
            id=1,
            **sample_reminder_data,
            status=ReminderStatus.ACTIVE,
            next_execution=datetime.utcnow() + timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_reminder_repo.create.return_value = created_model
        
        # Act
        result = await reminder_service.create_reminder(**sample_reminder_data)
        
        # Assert
        assert result is not None
        assert result.user_id == "123456789"
        assert result.frequency == FrequencyEnum.DAILY
        
        # Verify repository calls
        mock_reminder_repo.count_by_user_id.assert_called_once_with("123456789")
        mock_reminder_repo.create.assert_called_once()
        
        # Verify scheduler was called
        mock_scheduler_service.schedule_reminder.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_reminder_user_limit_exceeded(self, reminder_service, mock_reminder_repo, sample_reminder_data):
        """Test reminder creation when user has too many reminders"""
        # Arrange
        mock_reminder_repo.count_by_user_id.return_value = 10  # At limit
        
        # Act & Assert
        with pytest.raises(ValueError, match="User has reached maximum number of reminders"):
            await reminder_service.create_reminder(**sample_reminder_data)
        
        # Verify no creation attempted
        mock_reminder_repo.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_reminder_invalid_message_content(self, reminder_service, sample_reminder_data):
        """Test reminder creation with invalid message content"""
        # Arrange
        sample_reminder_data["message_content"] = ""  # Empty message
        
        # Act & Assert
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await reminder_service.create_reminder(**sample_reminder_data)
    
    @pytest.mark.asyncio
    async def test_get_reminder_by_id_exists(self, reminder_service, mock_reminder_repo):
        """Test getting reminder by ID when it exists"""
        # Arrange
        reminder_id = 1
        mock_model = ReminderModel(
            id=reminder_id,
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            status=ReminderStatus.ACTIVE,
            created_by="admin_123"
        )
        mock_reminder_repo.get_by_id.return_value = mock_model
        
        # Act
        result = await reminder_service.get_reminder_by_id(reminder_id)
        
        # Assert
        assert result is not None
        assert result.id == reminder_id
        assert result.user_id == "123456789"
        mock_reminder_repo.get_by_id.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_get_reminder_by_id_not_found(self, reminder_service, mock_reminder_repo):
        """Test getting reminder by ID when it doesn't exist"""
        # Arrange
        reminder_id = 999
        mock_reminder_repo.get_by_id.return_value = None
        
        # Act
        result = await reminder_service.get_reminder_by_id(reminder_id)
        
        # Assert
        assert result is None
        mock_reminder_repo.get_by_id.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_get_user_reminders(self, reminder_service, mock_reminder_repo):
        """Test getting all reminders for a user"""
        # Arrange
        user_id = "123456789"
        mock_models = [
            ReminderModel(
                id=1, 
                user_id=user_id, 
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content="Reminder 1",
                created_by="admin_123",
                status=ReminderStatus.ACTIVE,
                next_execution=datetime.utcnow() + timedelta(days=1)
            ),
            ReminderModel(
                id=2, 
                user_id=user_id,
                guild_id="987654321",
                channel_id="111222333", 
                frequency=FrequencyEnum.WEEKLY,
                message_content="Reminder 2",
                created_by="admin_123",
                status=ReminderStatus.ACTIVE,
                next_execution=datetime.utcnow() + timedelta(weeks=1)
            )
        ]
        mock_reminder_repo.find_by_user_id.return_value = mock_models
        
        # Act
        result = await reminder_service.get_user_reminders(user_id)
        
        # Assert
        assert len(result) == 2
        assert all(r.user_id == user_id for r in result)
        mock_reminder_repo.find_by_user_id.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_update_reminder_status_success(self, reminder_service, mock_reminder_repo, mock_scheduler_service):
        """Test successful reminder status update"""
        # Arrange
        reminder_id = 1
        new_status = ReminderStatus.PAUSED
        mock_reminder_repo.update_status.return_value = True
        
        # Act
        result = await reminder_service.update_reminder_status(reminder_id, new_status)
        
        # Assert
        assert result is True
        mock_reminder_repo.update_status.assert_called_once_with(reminder_id, new_status)
        
        # When pausing, should unschedule
        if new_status == ReminderStatus.PAUSED:
            mock_scheduler_service.unschedule_reminder.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_update_reminder_status_resume(self, reminder_service, mock_reminder_repo, mock_scheduler_service):
        """Test resuming a paused reminder"""
        # Arrange
        reminder_id = 1
        new_status = ReminderStatus.ACTIVE
        mock_reminder_repo.update_status.return_value = True
        
        mock_model = ReminderModel(
            id=reminder_id,
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            created_by="admin_123",
            status=ReminderStatus.ACTIVE,
            next_execution=datetime.utcnow() + timedelta(days=1)
        )
        mock_reminder_repo.get_by_id.return_value = mock_model
        
        # Act
        result = await reminder_service.update_reminder_status(reminder_id, new_status)
        
        # Assert
        assert result is True
        mock_reminder_repo.update_status.assert_called_once_with(reminder_id, new_status)
        
        # When activating, should reschedule
        mock_scheduler_service.schedule_reminder.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_reminder_success(self, reminder_service, mock_reminder_repo, mock_validation_repo, mock_scheduler_service):
        """Test successful reminder deletion"""
        # Arrange
        reminder_id = 1
        mock_reminder_repo.delete.return_value = True
        mock_validation_repo.find_by_reminder_id.return_value = []
        
        # Act
        result = await reminder_service.delete_reminder(reminder_id)
        
        # Assert
        assert result is True
        mock_scheduler_service.unschedule_reminder.assert_called_once_with(reminder_id)
        mock_reminder_repo.delete.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_delete_reminder_with_validations(self, reminder_service, mock_reminder_repo, mock_validation_repo, mock_scheduler_service):
        """Test deleting reminder that has associated validations"""
        # Arrange
        reminder_id = 1
        mock_validations = [
            ValidationModel(id=1, reminder_id=reminder_id),
            ValidationModel(id=2, reminder_id=reminder_id)
        ]
        mock_validation_repo.find_by_reminder_id.return_value = mock_validations
        mock_validation_repo.delete.return_value = True
        mock_reminder_repo.delete.return_value = True
        
        # Act
        result = await reminder_service.delete_reminder(reminder_id)
        
        # Assert
        assert result is True
        
        # Should delete all validations first
        assert mock_validation_repo.delete.call_count == 2
        mock_reminder_repo.delete.assert_called_once_with(reminder_id)
        mock_scheduler_service.unschedule_reminder.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_process_due_reminders(self, reminder_service, mock_reminder_repo):
        """Test processing due reminders"""
        # Arrange
        due_reminders = [
            ReminderModel(
                id=1,
                user_id="123456789",
                message_content="Due reminder 1",
                validation_required=False,
                frequency=FrequencyEnum.DAILY
            ),
            ReminderModel(
                id=2,
                user_id="987654321", 
                message_content="Due reminder 2",
                validation_required=True,
                frequency=FrequencyEnum.WEEKLY
            )
        ]
        mock_reminder_repo.find_due_reminders.return_value = due_reminders
        mock_reminder_repo.update_next_execution.return_value = True
        
        # Mock the notification service
        with patch.object(reminder_service, '_send_reminder_notification') as mock_send:
            mock_send.return_value = AsyncMock()
            
            # Act
            processed_count = await reminder_service.process_due_reminders()
            
            # Assert
            assert processed_count == 2
            assert mock_send.call_count == 2
            assert mock_reminder_repo.update_next_execution.call_count == 2
    
    @pytest.mark.asyncio
    async def test_validate_reminder_permission_admin(self, reminder_service):
        """Test reminder permission validation for admin user"""
        # Arrange
        user_roles = ["admin", "moderator"]
        admin_role_ids = [123456789, 987654321]
        
        # Act
        result = await reminder_service.validate_reminder_permission(user_roles, admin_role_ids)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_reminder_permission_no_admin(self, reminder_service):
        """Test reminder permission validation for non-admin user"""
        # Arrange
        user_roles = ["member"]
        admin_role_ids = [123456789, 987654321]
        
        # Act
        result = await reminder_service.validate_reminder_permission(user_roles, admin_role_ids)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_reminder_statistics(self, reminder_service, mock_reminder_repo, mock_validation_repo):
        """Test getting reminder statistics"""
        # Arrange
        mock_reminder_repo.count.return_value = 50
        mock_reminder_repo.find_by_status.return_value = [MagicMock()] * 45  # 45 active
        mock_validation_repo.count_by_status.return_value = 10  # 10 pending validations
        
        # Act
        stats = await reminder_service.get_reminder_statistics()
        
        # Assert
        assert stats["total_reminders"] == 50
        assert stats["active_reminders"] == 45
        assert stats["pending_validations"] == 10
        
        mock_reminder_repo.count.assert_called_once()
        mock_reminder_repo.find_by_status.assert_called_once_with(ReminderStatus.ACTIVE)
        mock_validation_repo.count_by_status.assert_called_once_with(ValidationStatus.PENDING)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_reminders(self, reminder_service, mock_reminder_repo):
        """Test cleaning up old completed reminders"""
        # Arrange
        cutoff_days = 30
        mock_reminder_repo.cleanup_completed_reminders.return_value = 15
        
        # Act
        with patch('src.services.reminder_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 31)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            cleaned_count = await reminder_service.cleanup_old_reminders(cutoff_days)
        
        # Assert
        assert cleaned_count == 15
        mock_reminder_repo.cleanup_completed_reminders.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_update_reminders(self, reminder_service, mock_reminder_repo, mock_scheduler_service):
        """Test bulk updating multiple reminders"""
        # Arrange
        reminder_ids = [1, 2, 3]
        new_status = ReminderStatus.PAUSED
        mock_reminder_repo.bulk_update_status.return_value = 3
        
        # Act
        updated_count = await reminder_service.bulk_update_reminders(reminder_ids, new_status)
        
        # Assert
        assert updated_count == 3
        mock_reminder_repo.bulk_update_status.assert_called_once_with(reminder_ids, new_status)
        
        # Should unschedule all when pausing
        assert mock_scheduler_service.unschedule_reminder.call_count == 3
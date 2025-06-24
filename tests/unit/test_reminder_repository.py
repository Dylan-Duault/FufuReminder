import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.reminder_repo import ReminderRepository
from src.database.models import ReminderModel
from src.models.enums import ReminderStatus, FrequencyEnum


class TestReminderRepository:
    """Test cases for the ReminderRepository"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create a reminder repository instance"""
        return ReminderRepository(mock_session)
    
    @pytest.fixture
    def sample_reminder_model(self):
        """Create a sample reminder model for testing"""
        return ReminderModel(
            id=1,
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            validation_required=True,
            status=ReminderStatus.ACTIVE,
            created_by="admin_123",
            next_execution=datetime.utcnow() + timedelta(days=1)
        )
    
    @pytest.mark.asyncio
    async def test_find_by_user_id(self, repository, mock_session, sample_reminder_model):
        """Test finding reminders by user ID"""
        # Arrange
        user_id = "123456789"
        expected_reminders = [sample_reminder_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_user_id(user_id)
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        assert "user_id" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_by_guild_id(self, repository, mock_session, sample_reminder_model):
        """Test finding reminders by guild ID"""
        # Arrange
        guild_id = "987654321"
        expected_reminders = [sample_reminder_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_guild_id(guild_id)
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        assert "guild_id" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_due_reminders(self, repository, mock_session):
        """Test finding reminders that are due for execution"""
        # Arrange
        current_time = datetime.utcnow()
        due_reminder = ReminderModel(
            id=1,
            next_execution=current_time - timedelta(minutes=5),
            status=ReminderStatus.ACTIVE
        )
        expected_reminders = [due_reminder]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_due_reminders(current_time)
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for due reminders
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "next_execution" in query_str
        assert "status" in query_str
    
    @pytest.mark.asyncio
    async def test_find_active_reminders(self, repository, mock_session, sample_reminder_model):
        """Test finding active reminders"""
        # Arrange
        sample_reminder_model.status = ReminderStatus.ACTIVE
        expected_reminders = [sample_reminder_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_active_reminders()
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for active status
        call_args = mock_session.execute.call_args[0][0]
        assert "status" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_by_user_and_guild(self, repository, mock_session, sample_reminder_model):
        """Test finding reminders by both user ID and guild ID"""
        # Arrange
        user_id = "123456789"
        guild_id = "987654321"
        expected_reminders = [sample_reminder_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_user_and_guild(user_id, guild_id)
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for both user_id and guild_id
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "user_id" in query_str
        assert "guild_id" in query_str
    
    @pytest.mark.asyncio
    async def test_count_by_user_id(self, repository, mock_session):
        """Test counting reminders by user ID"""
        # Arrange
        user_id = "123456789"
        expected_count = 3
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.count_by_user_id(user_id)
        
        # Assert
        assert result == expected_count
        mock_session.execute.assert_called_once()
        
        # Verify the query filters by user_id
        call_args = mock_session.execute.call_args[0][0]
        assert "user_id" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_requiring_validation(self, repository, mock_session):
        """Test finding reminders that require validation"""
        # Arrange
        validation_reminder = ReminderModel(
            id=1,
            validation_required=True,
            status=ReminderStatus.ACTIVE
        )
        expected_reminders = [validation_reminder]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_requiring_validation()
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for validation_required
        call_args = mock_session.execute.call_args[0][0]
        assert "validation_required" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_update_status(self, repository, mock_session, sample_reminder_model):
        """Test updating reminder status"""
        # Arrange
        reminder_id = 1
        new_status = ReminderStatus.PAUSED
        
        mock_session.get.return_value = sample_reminder_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.update_status(reminder_id, new_status)
        
        # Assert
        assert result is True
        assert sample_reminder_model.status == new_status
        mock_session.get.assert_called_once_with(ReminderModel, reminder_id)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repository, mock_session):
        """Test updating status of non-existing reminder"""
        # Arrange
        reminder_id = 999
        new_status = ReminderStatus.PAUSED
        
        mock_session.get.return_value = None
        
        # Act
        result = await repository.update_status(reminder_id, new_status)
        
        # Assert
        assert result is False
        mock_session.get.assert_called_once_with(ReminderModel, reminder_id)
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_next_execution(self, repository, mock_session, sample_reminder_model):
        """Test updating next execution time"""
        # Arrange
        reminder_id = 1
        new_execution_time = datetime.utcnow() + timedelta(days=2)
        
        mock_session.get.return_value = sample_reminder_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.update_next_execution(reminder_id, new_execution_time)
        
        # Assert
        assert result is True
        assert sample_reminder_model.next_execution == new_execution_time
        mock_session.get.assert_called_once_with(ReminderModel, reminder_id)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_by_frequency(self, repository, mock_session, sample_reminder_model):
        """Test finding reminders by frequency"""
        # Arrange
        frequency = FrequencyEnum.DAILY
        expected_reminders = [sample_reminder_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_reminders
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_frequency(frequency)
        
        # Assert
        assert result == expected_reminders
        mock_session.execute.assert_called_once()
        
        # Verify the query filters by frequency
        call_args = mock_session.execute.call_args[0][0]
        assert "frequency" in str(call_args)
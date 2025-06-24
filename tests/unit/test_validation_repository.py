import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.validation_repo import ValidationRepository
from src.database.models import ValidationModel
from src.models.enums import ValidationStatus


class TestValidationRepository:
    """Test cases for the ValidationRepository"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create a validation repository instance"""
        return ValidationRepository(mock_session)
    
    @pytest.fixture
    def sample_validation_model(self):
        """Create a sample validation model for testing"""
        return ValidationModel(
            id=1,
            reminder_id=1,
            message_id="444555666",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
    
    @pytest.mark.asyncio
    async def test_find_by_reminder_id(self, repository, mock_session, sample_validation_model):
        """Test finding validations by reminder ID"""
        # Arrange
        reminder_id = 1
        expected_validations = [sample_validation_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_validations
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_reminder_id(reminder_id)
        
        # Assert
        assert result == expected_validations
        mock_session.execute.assert_called_once()
        
        # Verify the query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        assert "reminder_id" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_by_message_id(self, repository, mock_session, sample_validation_model):
        """Test finding validation by message ID"""
        # Arrange
        message_id = "444555666"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_validation_model
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_message_id(message_id)
        
        # Assert
        assert result == sample_validation_model
        mock_session.execute.assert_called_once()
        
        # Verify the query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        assert "message_id" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_by_message_id_not_found(self, repository, mock_session):
        """Test finding validation by message ID when not found"""
        # Arrange
        message_id = "999888777"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_message_id(message_id)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_pending_validations(self, repository, mock_session, sample_validation_model):
        """Test finding pending validations"""
        # Arrange
        sample_validation_model.status = ValidationStatus.PENDING
        expected_validations = [sample_validation_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_validations
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_pending_validations()
        
        # Assert
        assert result == expected_validations
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for pending status
        call_args = mock_session.execute.call_args[0][0]
        assert "status" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_find_expired_validations(self, repository, mock_session):
        """Test finding expired validations"""
        # Arrange
        current_time = datetime.utcnow()
        expired_validation = ValidationModel(
            id=1,
            reminder_id=1,
            status=ValidationStatus.PENDING,
            expires_at=current_time - timedelta(hours=1)
        )
        expected_validations = [expired_validation]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_validations
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_expired_validations(current_time)
        
        # Assert
        assert result == expected_validations
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for expired validations
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "expires_at" in query_str
        assert "status" in query_str
    
    @pytest.mark.asyncio
    async def test_find_by_status(self, repository, mock_session, sample_validation_model):
        """Test finding validations by status"""
        # Arrange
        status = ValidationStatus.VALIDATED
        sample_validation_model.status = status
        expected_validations = [sample_validation_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_validations
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_by_status(status)
        
        # Assert
        assert result == expected_validations
        mock_session.execute.assert_called_once()
        
        # Verify the query filters by status
        call_args = mock_session.execute.call_args[0][0]
        assert "status" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_update_status(self, repository, mock_session, sample_validation_model):
        """Test updating validation status"""
        # Arrange
        validation_id = 1
        new_status = ValidationStatus.VALIDATED
        
        mock_session.get.return_value = sample_validation_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.update_status(validation_id, new_status)
        
        # Assert
        assert result is True
        assert sample_validation_model.status == new_status
        mock_session.get.assert_called_once_with(ValidationModel, validation_id)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repository, mock_session):
        """Test updating status of non-existing validation"""
        # Arrange
        validation_id = 999
        new_status = ValidationStatus.VALIDATED
        
        mock_session.get.return_value = None
        
        # Act
        result = await repository.update_status(validation_id, new_status)
        
        # Assert
        assert result is False
        mock_session.get.assert_called_once_with(ValidationModel, validation_id)
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mark_as_validated(self, repository, mock_session, sample_validation_model):
        """Test marking validation as validated"""
        # Arrange
        validation_id = 1
        validation_time = datetime.utcnow()
        
        mock_session.get.return_value = sample_validation_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.mark_as_validated(validation_id, validation_time)
        
        # Assert
        assert result is True
        assert sample_validation_model.status == ValidationStatus.VALIDATED
        assert sample_validation_model.validated_at == validation_time
        mock_session.get.assert_called_once_with(ValidationModel, validation_id)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_as_expired(self, repository, mock_session, sample_validation_model):
        """Test marking validation as expired"""
        # Arrange
        validation_id = 1
        
        mock_session.get.return_value = sample_validation_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.mark_as_expired(validation_id)
        
        # Assert
        assert result is True
        assert sample_validation_model.status == ValidationStatus.EXPIRED
        mock_session.get.assert_called_once_with(ValidationModel, validation_id)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_active_validations_for_reminder(self, repository, mock_session, sample_validation_model):
        """Test finding active validations for a specific reminder"""
        # Arrange
        reminder_id = 1
        sample_validation_model.status = ValidationStatus.PENDING
        expected_validations = [sample_validation_model]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_validations
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.find_active_validations_for_reminder(reminder_id)
        
        # Assert
        assert result == expected_validations
        mock_session.execute.assert_called_once()
        
        # Verify the query filters for reminder_id and pending status
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "reminder_id" in query_str
        assert "status" in query_str
    
    @pytest.mark.asyncio
    async def test_count_by_status(self, repository, mock_session):
        """Test counting validations by status"""
        # Arrange
        status = ValidationStatus.VALIDATED
        expected_count = 5
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.count_by_status(status)
        
        # Assert
        assert result == expected_count
        mock_session.execute.assert_called_once()
        
        # Verify the query filters by status
        call_args = mock_session.execute.call_args[0][0]
        assert "status" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_validations(self, repository, mock_session):
        """Test cleaning up expired validations"""
        # Arrange
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        expected_deleted_count = 3
        
        mock_result = MagicMock()
        mock_result.rowcount = expected_deleted_count
        mock_session.execute.return_value = mock_result
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.cleanup_expired_validations(cutoff_time)
        
        # Assert
        assert result == expected_deleted_count
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify the delete query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        query_str = str(call_args)
        assert "expires_at" in query_str
        assert "status" in query_str
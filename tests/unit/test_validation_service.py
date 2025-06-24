import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.services.validation_service import ValidationService
from src.repositories.validation_repo import ValidationRepository
from src.repositories.reminder_repo import ReminderRepository
from src.database.models import ValidationModel, ReminderModel
from src.models.validation import Validation
from src.models.enums import ValidationStatus, ReminderStatus, FrequencyEnum


class TestValidationService:
    """Test cases for the ValidationService"""
    
    @pytest.fixture
    def mock_validation_repo(self):
        """Create a mock validation repository"""
        return AsyncMock(spec=ValidationRepository)
    
    @pytest.fixture
    def mock_reminder_repo(self):
        """Create a mock reminder repository"""
        return AsyncMock(spec=ReminderRepository)
    
    @pytest.fixture
    def mock_discord_client(self):
        """Create a mock Discord client"""
        client = AsyncMock(spec=discord.Client)
        
        # Mock guild and member
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_member.kick = AsyncMock()
        mock_guild.get_member.return_value = mock_member
        client.get_guild.return_value = mock_guild
        
        return client
    
    @pytest.fixture
    def validation_service(self, mock_validation_repo, mock_reminder_repo, mock_discord_client):
        """Create a validation service instance"""
        return ValidationService(
            validation_repo=mock_validation_repo,
            reminder_repo=mock_reminder_repo,
            discord_client=mock_discord_client
        )
    
    @pytest.fixture
    def sample_validation_data(self):
        """Sample validation creation data"""
        return {
            "reminder_id": 1,
            "message_id": "123456789012345678",
            "expires_at": datetime.utcnow() + timedelta(hours=48)
        }
    
    @pytest.mark.asyncio
    async def test_create_validation_success(self, validation_service, mock_validation_repo, sample_validation_data):
        """Test successful validation creation"""
        # Arrange
        created_model = ValidationModel(
            id=1,
            **sample_validation_data,
            status=ValidationStatus.PENDING,
            created_at=datetime.utcnow()
        )
        mock_validation_repo.create.return_value = created_model
        
        # Act
        result = await validation_service.create_validation(**sample_validation_data)
        
        # Assert
        assert result is not None
        assert result.reminder_id == 1
        assert result.status == ValidationStatus.PENDING
        mock_validation_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_success(self, validation_service, mock_validation_repo, mock_reminder_repo):
        """Test successful reaction validation processing"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "987654321098765432"
        
        validation_model = ValidationModel(
            id=1,
            reminder_id=1,
            message_id=message_id,
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        reminder_model = ReminderModel(
            id=1,
            user_id=user_id,
            message_content="Test reminder",
            status=ReminderStatus.ACTIVE
        )
        
        mock_validation_repo.find_by_message_id.return_value = validation_model
        mock_reminder_repo.get_by_id.return_value = reminder_model
        mock_validation_repo.mark_as_validated.return_value = True
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is True
        mock_validation_repo.find_by_message_id.assert_called_once_with(message_id)
        mock_reminder_repo.get_by_id.assert_called_once_with(1)
        mock_validation_repo.mark_as_validated.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_wrong_user(self, validation_service, mock_validation_repo, mock_reminder_repo):
        """Test reaction validation with wrong user"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "wrong_user_id"
        
        validation_model = ValidationModel(
            id=1,
            reminder_id=1,
            message_id=message_id,
            status=ValidationStatus.PENDING
        )
        
        reminder_model = ReminderModel(
            id=1,
            user_id="correct_user_id",
            message_content="Test reminder"
        )
        
        mock_validation_repo.find_by_message_id.return_value = validation_model
        mock_reminder_repo.get_by_id.return_value = reminder_model
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is False
        mock_validation_repo.mark_as_validated.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_no_validation_found(self, validation_service, mock_validation_repo):
        """Test reaction validation when no validation is found"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "987654321098765432"
        
        mock_validation_repo.find_by_message_id.return_value = None
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is False
        mock_validation_repo.find_by_message_id.assert_called_once_with(message_id)
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_already_validated(self, validation_service, mock_validation_repo):
        """Test reaction validation when already validated"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "987654321098765432"
        
        validation_model = ValidationModel(
            id=1,
            reminder_id=1,
            message_id=message_id,
            status=ValidationStatus.VALIDATED  # Already validated
        )
        
        mock_validation_repo.find_by_message_id.return_value = validation_model
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is False
        mock_validation_repo.mark_as_validated.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_expired_validations(self, validation_service, mock_validation_repo, mock_reminder_repo, mock_discord_client):
        """Test processing expired validations"""
        # Arrange
        expired_validations = [
            ValidationModel(
                id=1,
                reminder_id=1,
                status=ValidationStatus.PENDING,
                expires_at=datetime.utcnow() - timedelta(hours=1)
            ),
            ValidationModel(
                id=2,
                reminder_id=2,
                status=ValidationStatus.PENDING,
                expires_at=datetime.utcnow() - timedelta(hours=2)
            )
        ]
        
        reminder_models = [
            ReminderModel(id=1, user_id="user1", guild_id="guild1"),
            ReminderModel(id=2, user_id="user2", guild_id="guild2")
        ]
        
        mock_validation_repo.find_expired_validations.return_value = expired_validations
        mock_reminder_repo.get_by_id.side_effect = reminder_models
        mock_validation_repo.mark_as_expired.return_value = True
        
        # Mock Discord objects
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_guild.get_member.return_value = mock_member
        mock_discord_client.get_guild.return_value = mock_guild
        
        # Act
        with patch.object(validation_service, '_kick_user_from_guild') as mock_kick:
            mock_kick.return_value = True
            processed_count = await validation_service.process_expired_validations()
        
        # Assert
        assert processed_count == 2
        assert mock_validation_repo.mark_as_expired.call_count == 2
        assert mock_kick.call_count == 2
    
    @pytest.mark.asyncio
    async def test_check_validation_status_pending(self, validation_service, mock_validation_repo):
        """Test checking validation status when pending"""
        # Arrange
        validation_id = 1
        validation_model = ValidationModel(
            id=validation_id,
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        mock_validation_repo.get_by_id.return_value = validation_model
        
        # Act
        result = await validation_service.check_validation_status(validation_id)
        
        # Assert
        assert result.status == ValidationStatus.PENDING
        assert result.is_pending() is True
        assert result.is_expired() is False
    
    @pytest.mark.asyncio
    async def test_check_validation_status_expired(self, validation_service, mock_validation_repo):
        """Test checking validation status when expired"""
        # Arrange
        validation_id = 1
        validation_model = ValidationModel(
            id=validation_id,
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        mock_validation_repo.get_by_id.return_value = validation_model
        
        # Act
        result = await validation_service.check_validation_status(validation_id)
        
        # Assert
        assert result.status == ValidationStatus.PENDING  # Status in DB unchanged
        assert result.is_expired() is True  # But domain logic shows expired
    
    @pytest.mark.asyncio
    async def test_get_validation_statistics(self, validation_service, mock_validation_repo):
        """Test getting validation statistics"""
        # Arrange
        mock_validation_repo.count_by_status.side_effect = [10, 5, 3, 2]  # pending, validated, expired, failed
        
        # Act
        stats = await validation_service.get_validation_statistics()
        
        # Assert
        assert stats["pending"] == 10
        assert stats["validated"] == 5
        assert stats["expired"] == 3
        assert stats["failed"] == 2
        assert stats["total"] == 20
        
        assert mock_validation_repo.count_by_status.call_count == 4
    
    @pytest.mark.asyncio
    async def test_cleanup_old_validations(self, validation_service, mock_validation_repo):
        """Test cleaning up old validations"""
        # Arrange
        days_old = 7
        mock_validation_repo.cleanup_expired_validations.return_value = 25
        
        # Act
        with patch('src.services.validation_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 31)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            cleaned_count = await validation_service.cleanup_old_validations(days_old)
        
        # Assert
        assert cleaned_count == 25
        mock_validation_repo.cleanup_expired_validations.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_validation_by_message_id(self, validation_service, mock_validation_repo):
        """Test getting validation by message ID"""
        # Arrange
        message_id = "123456789012345678"
        validation_model = ValidationModel(
            id=1,
            message_id=message_id,
            status=ValidationStatus.PENDING
        )
        mock_validation_repo.find_by_message_id.return_value = validation_model
        
        # Act
        result = await validation_service.get_validation_by_message_id(message_id)
        
        # Assert
        assert result is not None
        assert result.message_id == message_id
        mock_validation_repo.find_by_message_id.assert_called_once_with(message_id)
    
    @pytest.mark.asyncio
    async def test_get_validations_for_reminder(self, validation_service, mock_validation_repo):
        """Test getting all validations for a reminder"""
        # Arrange
        reminder_id = 1
        validation_models = [
            ValidationModel(id=1, reminder_id=reminder_id, status=ValidationStatus.VALIDATED),
            ValidationModel(id=2, reminder_id=reminder_id, status=ValidationStatus.PENDING)
        ]
        mock_validation_repo.find_by_reminder_id.return_value = validation_models
        
        # Act
        result = await validation_service.get_validations_for_reminder(reminder_id)
        
        # Assert
        assert len(result) == 2
        assert all(v.reminder_id == reminder_id for v in result)
        mock_validation_repo.find_by_reminder_id.assert_called_once_with(reminder_id)
    
    @pytest.mark.asyncio
    async def test_force_expire_validation(self, validation_service, mock_validation_repo):
        """Test manually expiring a validation"""
        # Arrange
        validation_id = 1
        mock_validation_repo.mark_as_expired.return_value = True
        
        # Act
        result = await validation_service.force_expire_validation(validation_id)
        
        # Assert
        assert result is True
        mock_validation_repo.mark_as_expired.assert_called_once_with(validation_id)
    
    @pytest.mark.asyncio
    async def test_bulk_expire_validations(self, validation_service, mock_validation_repo):
        """Test bulk expiring multiple validations"""
        # Arrange
        validation_ids = [1, 2, 3]
        mock_validation_repo.bulk_mark_expired.return_value = 3
        
        # Act
        expired_count = await validation_service.bulk_expire_validations(validation_ids)
        
        # Assert
        assert expired_count == 3
        mock_validation_repo.bulk_mark_expired.assert_called_once_with(validation_ids)
    
    @pytest.mark.asyncio
    async def test_kick_user_from_guild_success(self, validation_service, mock_discord_client):
        """Test successfully kicking user from guild"""
        # Arrange
        guild_id = "123456789"
        user_id = "987654321"
        
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_member.kick = AsyncMock()
        
        mock_guild.get_member.return_value = mock_member
        mock_discord_client.get_guild.return_value = mock_guild
        
        # Act
        result = await validation_service._kick_user_from_guild(guild_id, user_id, "Validation expired")
        
        # Assert
        assert result is True
        mock_discord_client.get_guild.assert_called_once_with(int(guild_id))
        mock_guild.get_member.assert_called_once_with(int(user_id))
        mock_member.kick.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_kick_user_from_guild_member_not_found(self, validation_service, mock_discord_client):
        """Test kicking user when member not found in guild"""
        # Arrange
        guild_id = "123456789"
        user_id = "987654321"
        
        mock_guild = MagicMock()
        mock_guild.get_member.return_value = None  # Member not found
        mock_discord_client.get_guild.return_value = mock_guild
        
        # Act
        result = await validation_service._kick_user_from_guild(guild_id, user_id, "Validation expired")
        
        # Assert
        assert result is False
        mock_discord_client.get_guild.assert_called_once_with(int(guild_id))
        mock_guild.get_member.assert_called_once_with(int(user_id))
    
    @pytest.mark.asyncio
    async def test_validation_timeout_warning(self, validation_service, mock_validation_repo):
        """Test getting validations that will expire soon"""
        # Arrange
        warning_hours = 6
        warning_time = datetime.utcnow() + timedelta(hours=warning_hours)
        
        expiring_validations = [
            ValidationModel(
                id=1,
                reminder_id=1,
                status=ValidationStatus.PENDING,
                expires_at=datetime.utcnow() + timedelta(hours=3)  # Expires in 3 hours
            )
        ]
        
        mock_validation_repo.find_expiring_soon.return_value = expiring_validations
        
        # Act
        result = await validation_service.get_expiring_validations(warning_hours)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        mock_validation_repo.find_expiring_soon.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_kick_user_from_guild_guild_not_found(self, validation_service, mock_discord_client):
        """Test kicking user when guild not found"""
        # Arrange
        guild_id = "123456789"
        user_id = "987654321"
        mock_discord_client.get_guild.return_value = None
        
        # Act
        result = await validation_service._kick_user_from_guild(guild_id, user_id, "Validation expired")
        
        # Assert
        assert result is False
        mock_discord_client.get_guild.assert_called_once_with(int(guild_id))
    
    @pytest.mark.asyncio
    async def test_kick_user_forbidden_error(self, validation_service, mock_discord_client):
        """Test kicking user with forbidden error"""
        # Arrange
        guild_id = "123456789"
        user_id = "987654321"
        
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_member.kick = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "Forbidden"))
        mock_guild.get_member.return_value = mock_member
        mock_discord_client.get_guild.return_value = mock_guild
        
        # Act
        result = await validation_service._kick_user_from_guild(guild_id, user_id, "Validation expired")
        
        # Assert
        assert result is False
        mock_member.kick.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_kick_user_http_exception(self, validation_service, mock_discord_client):
        """Test kicking user with HTTP exception"""
        # Arrange
        guild_id = "123456789"
        user_id = "987654321"
        
        mock_guild = MagicMock()
        mock_member = MagicMock()
        mock_member.kick = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "HTTP Error"))
        mock_guild.get_member.return_value = mock_member
        mock_discord_client.get_guild.return_value = mock_guild
        
        # Act
        result = await validation_service._kick_user_from_guild(guild_id, user_id, "Validation expired")
        
        # Assert
        assert result is False
        mock_member.kick.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_reminder_not_found(self, validation_service, mock_validation_repo, mock_reminder_repo):
        """Test reaction processing when reminder not found"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "987654321098765432"
        
        validation_model = ValidationModel(
            id=1,
            reminder_id=999,  # Non-existent reminder
            message_id=message_id,
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        mock_validation_repo.find_by_message_id.return_value = validation_model
        mock_reminder_repo.get_by_id.return_value = None
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is False
        mock_reminder_repo.get_by_id.assert_called_once_with(999)
    
    @pytest.mark.asyncio
    async def test_process_reaction_validation_expired_validation(self, validation_service, mock_validation_repo, mock_reminder_repo):
        """Test reaction processing when validation is expired"""
        # Arrange
        message_id = "123456789012345678"
        user_id = "987654321098765432"
        
        validation_model = ValidationModel(
            id=1,
            reminder_id=1,
            message_id=message_id,
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        
        reminder_model = ReminderModel(
            id=1,
            user_id=user_id,
            message_content="Test reminder",
            status=ReminderStatus.ACTIVE
        )
        
        mock_validation_repo.find_by_message_id.return_value = validation_model
        mock_reminder_repo.get_by_id.return_value = reminder_model
        mock_validation_repo.mark_as_expired.return_value = True
        
        # Act
        result = await validation_service.process_reaction_validation(message_id, user_id)
        
        # Assert
        assert result is False
        mock_validation_repo.mark_as_expired.assert_called_once_with(1)
    
    def test_model_to_domain_conversion(self, validation_service):
        """Test conversion from database model to domain model"""
        # Arrange
        validation_model = ValidationModel(
            id=1,
            reminder_id=123,
            message_id="123456789012345678",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            validated_at=None
        )
        
        # Act
        domain_model = validation_service._model_to_domain(validation_model)
        
        # Assert
        assert isinstance(domain_model, Validation)
        assert domain_model.id == 1
        assert domain_model.reminder_id == 123
        assert domain_model.message_id == "123456789012345678"
        assert domain_model.status == ValidationStatus.PENDING
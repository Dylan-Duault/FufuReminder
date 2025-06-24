import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import discord
from src.observers.reaction_observer import ReactionObserver
from src.services.validation_service import ValidationService
from src.models.validation import Validation
from src.models.enums import ValidationStatus


class TestReactionObserver:
    """Test cases for the ReactionObserver"""
    
    @pytest.fixture
    def mock_validation_service(self):
        """Create a mock validation service"""
        service = AsyncMock(spec=ValidationService)
        service.process_validation_reaction = AsyncMock()
        service.get_validation_by_message_id = AsyncMock()
        return service
    
    @pytest.fixture
    def reaction_observer(self, mock_validation_service):
        """Create a reaction observer instance"""
        return ReactionObserver(validation_service=mock_validation_service)
    
    @pytest.fixture
    def mock_reaction(self):
        """Create a mock Discord reaction"""
        reaction = MagicMock(spec=discord.Reaction)
        reaction.emoji = "✅"
        reaction.count = 2  # Bot + user
        
        # Mock message
        message = MagicMock(spec=discord.Message)
        message.id = 123456789012345678
        message.channel.id = 111222333
        message.guild.id = 987654321
        reaction.message = message
        
        return reaction
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock Discord user"""
        user = MagicMock(spec=discord.Member)
        user.id = 555666777
        user.bot = False
        user.guild_permissions.manage_guild = False
        return user
    
    @pytest.fixture
    def mock_bot_user(self):
        """Create a mock bot user"""
        bot_user = MagicMock(spec=discord.Member)
        bot_user.id = 888999000
        bot_user.bot = True
        return bot_user
    
    @pytest.fixture
    def sample_validation(self):
        """Create a sample validation for testing"""
        return Validation(
            reminder_id=1,
            message_id="123456789012345678",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            validation_id=1
        )
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_valid_checkmark(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test processing valid checkmark reaction"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = True
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_called_once_with(str(mock_reaction.message.id))
        mock_validation_service.process_validation_reaction.assert_called_once_with(
            validation_id=sample_validation.id,
            user_id=str(mock_user.id)
        )
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_wrong_emoji(self, reaction_observer, mock_validation_service, mock_reaction, mock_user):
        """Test reaction with wrong emoji is ignored"""
        # Arrange
        mock_reaction.emoji = "❌"  # Wrong emoji
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_not_called()
        mock_validation_service.process_validation_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_bot_user(self, reaction_observer, mock_validation_service, mock_reaction, mock_bot_user):
        """Test bot reactions are ignored"""
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_bot_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_not_called()
        mock_validation_service.process_validation_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_no_validation_found(self, reaction_observer, mock_validation_service, mock_reaction, mock_user):
        """Test reaction on message without validation"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = None
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_called_once_with(str(mock_reaction.message.id))
        mock_validation_service.process_validation_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_validation_processing_failure(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test handling of validation processing failure"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = False
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_called_once()
        mock_validation_service.process_validation_reaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_reaction_add_service_exception(self, reaction_observer, mock_validation_service, mock_reaction, mock_user):
        """Test handling of service exceptions"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.side_effect = Exception("Database error")
        
        # Act - should not raise exception
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_called_once()
        mock_validation_service.process_validation_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_reaction_remove_ignored(self, reaction_observer, mock_validation_service, mock_reaction, mock_user):
        """Test reaction removal is ignored"""
        # Act
        await reaction_observer.on_reaction_remove(mock_reaction, mock_user)
        
        # Assert - no validation service calls should be made
        mock_validation_service.get_validation_by_message_id.assert_not_called()
        mock_validation_service.process_validation_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_unicode_checkmark_emoji(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test unicode checkmark emoji is recognized"""
        # Arrange
        mock_reaction.emoji = "✅"  # Unicode checkmark
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = True
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.process_validation_reaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_custom_checkmark_emoji(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test custom checkmark emoji is recognized"""
        # Arrange
        mock_custom_emoji = MagicMock()
        mock_custom_emoji.name = "checkmark"
        mock_reaction.emoji = mock_custom_emoji
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = True
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.process_validation_reaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_already_completed(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test reaction on already completed validation"""
        # Arrange
        sample_validation.status = ValidationStatus.VALIDATED
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = False  # Already completed
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.process_validation_reaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_expired(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test reaction on expired validation"""
        # Arrange
        sample_validation.expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = False  # Expired
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.process_validation_reaction.assert_called_once()
    
    def test_is_checkmark_emoji_unicode(self, reaction_observer):
        """Test unicode checkmark detection"""
        assert reaction_observer._is_checkmark_emoji("✅") is True
        assert reaction_observer._is_checkmark_emoji("❌") is False
        assert reaction_observer._is_checkmark_emoji("👍") is False
    
    def test_is_checkmark_emoji_custom(self, reaction_observer):
        """Test custom emoji checkmark detection"""
        # Mock custom emoji
        checkmark_emoji = MagicMock()
        checkmark_emoji.name = "checkmark"
        
        green_check_emoji = MagicMock()
        green_check_emoji.name = "green_check"
        
        wrong_emoji = MagicMock()
        wrong_emoji.name = "red_cross"
        
        assert reaction_observer._is_checkmark_emoji(checkmark_emoji) is True
        assert reaction_observer._is_checkmark_emoji(green_check_emoji) is True
        assert reaction_observer._is_checkmark_emoji(wrong_emoji) is False
    
    @pytest.mark.asyncio
    async def test_multiple_reactions_same_user(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test multiple reactions from same user (should process all)"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = True
        
        # Act - simulate multiple quick reactions
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert - both should be processed (validation service handles duplicates)
        assert mock_validation_service.process_validation_reaction.call_count == 2
    
    @pytest.mark.asyncio
    async def test_dm_message_ignored(self, reaction_observer, mock_validation_service, mock_reaction, mock_user):
        """Test reactions in DMs are ignored"""
        # Arrange
        mock_reaction.message.guild = None  # DM message
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        mock_validation_service.get_validation_by_message_id.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_reaction_statistics_tracking(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test reaction processing statistics are tracked"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = True
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        stats = reaction_observer.get_reaction_statistics()
        assert stats["processed_reactions"] == 1
        assert stats["successful_validations"] == 1
        assert stats["failed_validations"] == 0
    
    @pytest.mark.asyncio
    async def test_reaction_statistics_failure(self, reaction_observer, mock_validation_service, mock_reaction, mock_user, sample_validation):
        """Test failed reaction statistics are tracked"""
        # Arrange
        mock_validation_service.get_validation_by_message_id.return_value = sample_validation
        mock_validation_service.process_validation_reaction.return_value = False
        
        # Act
        await reaction_observer.on_reaction_add(mock_reaction, mock_user)
        
        # Assert
        stats = reaction_observer.get_reaction_statistics()
        assert stats["processed_reactions"] == 1
        assert stats["successful_validations"] == 0
        assert stats["failed_validations"] == 1
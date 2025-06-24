import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from src.commands.reminder_commands import ReminderCommands
from src.models.reminder import Reminder
from src.models.enums import FrequencyEnum, ReminderStatus
from src.services.reminder_service import ReminderService
from src.services.notification_service import NotificationService


class TestReminderCommands:
    """Test cases for Discord slash commands"""
    
    @pytest.fixture
    def mock_reminder_service(self):
        """Create a mock reminder service"""
        service = AsyncMock(spec=ReminderService)
        service.create_reminder = AsyncMock()
        service.get_user_reminders = AsyncMock()
        service.delete_reminder = AsyncMock()
        service.update_reminder_status = AsyncMock()
        service.get_reminder_statistics = AsyncMock()
        service.validate_reminder_permission = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_notification_service(self):
        """Create a mock notification service"""
        service = AsyncMock(spec=NotificationService)
        service.send_custom_message = AsyncMock()
        service.send_custom_message_with_embed = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction"""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.response.send_message = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.user.id = 123456789
        interaction.guild.id = 987654321
        interaction.channel.id = 111222333
        interaction.user.guild_permissions.manage_guild = True
        return interaction
    
    @pytest.fixture
    def reminder_commands(self, mock_reminder_service, mock_notification_service):
        """Create reminder commands instance"""
        return ReminderCommands(
            reminder_service=mock_reminder_service,
            notification_service=mock_notification_service
        )
    
    @pytest.fixture
    def sample_reminder(self):
        """Sample reminder for testing"""
        return Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Daily standup reminder",
            created_by="admin_123",
            reminder_id=1,
            validation_required=True
        )
    
    @pytest.mark.asyncio
    async def test_add_reminder_success(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test successful reminder creation"""
        # Arrange
        mock_interaction.user.guild_permissions.manage_guild = True
        mock_reminder_service.create_reminder.return_value = sample_reminder
        
        # Act
        await reminder_commands.add_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user,
            frequency="daily",
            message="Daily standup reminder",
            validation_required=True
        )
        
        # Assert
        mock_reminder_service.create_reminder.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check success message was sent
        call_args = mock_interaction.response.send_message.call_args
        assert "✅ **Reminder created successfully!**" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_add_reminder_permission_denied(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test reminder creation with insufficient permissions"""
        # Arrange
        mock_interaction.user.guild_permissions.manage_guild = False
        
        # Act
        await reminder_commands.add_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user,
            frequency="daily",
            message="Daily standup reminder",
            validation_required=True
        )
        
        # Assert
        mock_reminder_service.create_reminder.assert_not_called()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check error message was sent
        call_args = mock_interaction.response.send_message.call_args
        assert "❌ You don't have permission" in call_args[0][0]  # First positional argument
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_add_reminder_invalid_frequency(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test reminder creation with invalid frequency"""
        # Arrange - permissions are valid
        mock_interaction.user.guild_permissions.manage_guild = True
        
        # Act
        await reminder_commands.add_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user,
            frequency="invalid",
            message="Daily standup reminder",
            validation_required=True
        )
        
        # Assert
        mock_reminder_service.create_reminder.assert_not_called()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check error message
        call_args = mock_interaction.response.send_message.call_args
        assert "❌ Invalid frequency" in call_args[0][0]  # First positional argument
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_add_reminder_service_error(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test reminder creation with service error"""
        # Arrange
        mock_reminder_service.validate_reminder_permission.return_value = True
        mock_reminder_service.create_reminder.side_effect = ValueError("User has reached maximum number of reminders")
        
        # Act
        await reminder_commands.add_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user,
            frequency="daily",
            message="Daily standup reminder",
            validation_required=True
        )
        
        # Assert
        mock_interaction.response.send_message.assert_called_once()
        
        # Check error message
        call_args = mock_interaction.response.send_message.call_args
        assert "❌ Failed to create reminder" in call_args[0][0]  # First positional argument
        assert "User has reached maximum number of reminders" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_list_reminders_success(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test successful reminder listing"""
        # Arrange
        reminders = [sample_reminder]
        mock_reminder_service.get_user_reminders.return_value = reminders
        
        # Act
        await reminder_commands.list_reminders.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user
        )
        
        # Assert
        mock_reminder_service.get_user_reminders.assert_called_once_with(str(mock_interaction.user.id))
        mock_interaction.response.send_message.assert_called_once()
        
        # Check message contains reminder info
        call_args = mock_interaction.response.send_message.call_args
        assert "📋 **Reminders for" in call_args[0][0]  # First positional argument
        assert "Daily standup reminder" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_list_reminders_no_reminders(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test reminder listing with no reminders"""
        # Arrange
        mock_reminder_service.get_user_reminders.return_value = []
        
        # Act
        await reminder_commands.list_reminders.callback(
            reminder_commands,
            interaction=mock_interaction,
            user=mock_interaction.user
        )
        
        # Assert
        mock_interaction.response.send_message.assert_called_once()
        
        # Check empty message
        call_args = mock_interaction.response.send_message.call_args
        assert "You don't have any reminders" in call_args[0][0]  # First positional argument
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_delete_reminder_success(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test successful reminder deletion"""
        # Arrange
        mock_reminder_service.get_reminder_by_id.return_value = sample_reminder
        mock_reminder_service.delete_reminder.return_value = True
        
        # Act
        await reminder_commands.delete_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            reminder_id=1
        )
        
        # Assert
        mock_reminder_service.get_reminder_by_id.assert_called_once_with(1)
        mock_reminder_service.delete_reminder.assert_called_once_with(1)
        mock_interaction.response.send_message.assert_called_once()
        
        # Check success message
        call_args = mock_interaction.response.send_message.call_args
        assert "✅ Reminder deleted successfully" in call_args[0][0]  # First positional argument
    
    @pytest.mark.asyncio
    async def test_delete_reminder_not_found(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test deletion of non-existent reminder"""
        # Arrange
        mock_reminder_service.get_reminder_by_id.return_value = None
        
        # Act
        await reminder_commands.delete_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            reminder_id=999
        )
        
        # Assert
        mock_reminder_service.delete_reminder.assert_not_called()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check error message
        call_args = mock_interaction.response.send_message.call_args
        assert "❌ Reminder with ID 999 not found" in call_args[0][0]  # First positional argument
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_delete_reminder_not_owner(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test deletion by non-owner user"""
        # Arrange
        sample_reminder.user_id = "different_user"
        mock_reminder_service.get_reminder_by_id.return_value = sample_reminder
        mock_interaction.user.guild_permissions.manage_guild = False
        
        # Act
        await reminder_commands.delete_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            reminder_id=1
        )
        
        # Assert
        mock_reminder_service.delete_reminder.assert_not_called()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check permission error
        call_args = mock_interaction.response.send_message.call_args
        assert "❌ You can only delete your own reminders" in call_args[0][0]  # First positional argument
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_pause_reminder_success(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test successful reminder pausing"""
        # Arrange
        mock_reminder_service.get_reminder_by_id.return_value = sample_reminder
        mock_reminder_service.update_reminder_status.return_value = True
        
        # Act
        await reminder_commands.pause_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            reminder_id=1
        )
        
        # Assert
        mock_reminder_service.update_reminder_status.assert_called_once_with(1, ReminderStatus.PAUSED)
        mock_interaction.response.send_message.assert_called_once()
        
        # Check success message
        call_args = mock_interaction.response.send_message.call_args
        assert "⏸️ Reminder paused successfully" in call_args[0][0]  # First positional argument
    
    @pytest.mark.asyncio
    async def test_resume_reminder_success(self, reminder_commands, mock_reminder_service, mock_interaction, sample_reminder):
        """Test successful reminder resuming"""
        # Arrange
        sample_reminder.status = ReminderStatus.PAUSED
        mock_reminder_service.get_reminder_by_id.return_value = sample_reminder
        mock_reminder_service.update_reminder_status.return_value = True
        
        # Act
        await reminder_commands.resume_reminder.callback(
            reminder_commands,
            interaction=mock_interaction,
            reminder_id=1
        )
        
        # Assert
        mock_reminder_service.update_reminder_status.assert_called_once_with(1, ReminderStatus.ACTIVE)
        mock_interaction.response.send_message.assert_called_once()
        
        # Check success message
        call_args = mock_interaction.response.send_message.call_args
        assert "▶️ Reminder resumed successfully" in call_args[0][0]  # First positional argument
    
    @pytest.mark.asyncio
    async def test_stats_command_success(self, reminder_commands, mock_reminder_service, mock_interaction):
        """Test successful stats command"""
        # Arrange
        stats = {
            "total_reminders": 50,
            "active_reminders": 45,
            "pending_validations": 10
        }
        mock_reminder_service.get_reminder_statistics.return_value = stats
        
        # Act
        await reminder_commands.stats.callback(reminder_commands, interaction=mock_interaction)
        
        # Assert
        mock_reminder_service.get_reminder_statistics.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        
        # Check stats were sent via embed
        call_args = mock_interaction.response.send_message.call_args
        assert "embed" in call_args[1]  # Should have embed parameter
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_frequency_validation(self, reminder_commands):
        """Test frequency validation helper"""
        # Valid frequencies
        assert reminder_commands._validate_frequency("hourly") == FrequencyEnum.HOURLY
        assert reminder_commands._validate_frequency("daily") == FrequencyEnum.DAILY
        assert reminder_commands._validate_frequency("weekly") == FrequencyEnum.WEEKLY
        assert reminder_commands._validate_frequency("monthly") == FrequencyEnum.MONTHLY
        
        # Invalid frequency
        assert reminder_commands._validate_frequency("invalid") is None
    
    @pytest.mark.asyncio
    async def test_format_reminder_list(self, reminder_commands, sample_reminder):
        """Test reminder list formatting"""
        reminders = [sample_reminder]
        
        result = reminder_commands._format_reminder_list(reminders, "123456789")
        
        assert "📋 **Reminders for <@123456789>**" in result
        assert "**ID 1** - Daily standup reminder" in result
        assert "🔁 daily" in result
        assert "✅ validation required" in result
        assert "🟢 active" in result
    
    @pytest.mark.asyncio
    async def test_check_reminder_ownership(self, reminder_commands, mock_interaction, sample_reminder):
        """Test reminder ownership validation"""
        # Owner can access
        assert reminder_commands._check_reminder_ownership(mock_interaction, sample_reminder) is True
        
        # Admin can access
        sample_reminder.user_id = "different_user"
        mock_interaction.user.guild_permissions.manage_guild = True
        assert reminder_commands._check_reminder_ownership(mock_interaction, sample_reminder) is True
        
        # Non-owner without admin cannot access
        mock_interaction.user.guild_permissions.manage_guild = False
        assert reminder_commands._check_reminder_ownership(mock_interaction, sample_reminder) is False
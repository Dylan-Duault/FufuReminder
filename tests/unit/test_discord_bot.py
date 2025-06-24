import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from src.bot.discord_bot import FufuRemindBot
from src.services.reminder_service import ReminderService
from src.services.notification_service import NotificationService
from src.services.scheduler_service import SchedulerService
from src.services.validation_service import ValidationService
from src.commands.reminder_commands import ReminderCommands


class TestDiscordBot:
    """Test cases for the Discord bot entry point"""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for the bot"""
        reminder_service = AsyncMock(spec=ReminderService)
        reminder_service.cleanup_guild_reminders = AsyncMock()
        notification_service = AsyncMock(spec=NotificationService)
        scheduler_service = AsyncMock(spec=SchedulerService)
        validation_service = AsyncMock(spec=ValidationService)
        
        return {
            'reminder_service': reminder_service,
            'notification_service': notification_service,
            'scheduler_service': scheduler_service,
            'validation_service': validation_service
        }
    
    @pytest.fixture
    def bot(self, mock_services):
        """Create bot instance with mocked services"""
        with patch('src.bot.discord_bot.get_settings') as mock_settings:
            mock_settings.return_value.discord_token = "test_token"
            mock_settings.return_value.command_prefix = "!"
            
            return FufuRemindBot(
                reminder_service=mock_services['reminder_service'],
                notification_service=mock_services['notification_service'],
                scheduler_service=mock_services['scheduler_service'],
                validation_service=mock_services['validation_service']
            )
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self, bot, mock_services):
        """Test bot initializes with correct services and settings"""
        # Assert bot is properly initialized
        assert bot.reminder_service == mock_services['reminder_service']
        assert bot.notification_service == mock_services['notification_service']
        assert bot.scheduler_service == mock_services['scheduler_service']
        assert bot.validation_service == mock_services['validation_service']
        
        # Check intents are configured correctly
        assert bot.intents.message_content is True
        assert bot.intents.guilds is True
        assert bot.intents.guild_reactions is True
        assert bot.intents.members is True
    
    @pytest.mark.asyncio
    async def test_on_ready_event(self, bot, mock_services):
        """Test bot ready event initializes services"""
        with patch.object(bot, 'sync_slash_commands') as mock_sync, \
             patch.object(bot, 'update_status') as mock_status, \
             patch.object(bot, 'user') as mock_user, \
             patch.object(bot, 'guilds', []):
            mock_sync.return_value = None
            mock_status.return_value = None
            mock_user.name = "FufuRemind" 
            mock_user.id = 123456789
            
            # Call on_ready
            await bot.on_ready()
            
            # Assert services are started
            mock_services['scheduler_service'].start.assert_called_once()
            mock_sync.assert_called_once()
            mock_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_guild_join_event(self, bot):
        """Test bot joins guild and syncs commands"""
        # Arrange
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Test Guild"
        mock_guild.id = 987654321
        mock_guild.member_count = 100
        
        with patch.object(bot, 'sync_slash_commands') as mock_sync:
            mock_sync.return_value = None
            
            # Act
            await bot.on_guild_join(mock_guild)
            
            # Assert
            mock_sync.assert_called_once_with(guild=mock_guild)
    
    @pytest.mark.asyncio
    async def test_on_guild_remove_event(self, bot, mock_services):
        """Test bot cleanup when removed from guild"""
        # Arrange
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.id = 987654321
        mock_guild.name = "Test Guild"
        
        # Act  
        with patch.object(bot, 'update_status') as mock_status:
            mock_status.return_value = None
            await bot.on_guild_remove(mock_guild)
        
        # Assert - should clean up reminders for the guild
        mock_services['reminder_service'].cleanup_guild_reminders.assert_called_once_with(str(mock_guild.id))
    
    @pytest.mark.asyncio
    async def test_sync_slash_commands_global(self, bot):
        """Test syncing slash commands globally"""
        with patch.object(bot.tree, 'sync') as mock_sync:
            mock_sync.return_value = []
            
            # Act
            result = await bot.sync_slash_commands()
            
            # Assert
            assert result is True
            mock_sync.assert_called_once_with()
    
    @pytest.mark.asyncio
    async def test_sync_slash_commands_guild_specific(self, bot):
        """Test syncing slash commands for specific guild"""
        # Arrange
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.id = 987654321
        
        with patch.object(bot.tree, 'sync') as mock_sync:
            mock_sync.return_value = []
            
            # Act
            result = await bot.sync_slash_commands(guild=mock_guild)
            
            # Assert
            assert result is True
            mock_sync.assert_called_once_with(guild=mock_guild)
    
    @pytest.mark.asyncio
    async def test_sync_slash_commands_error(self, bot):
        """Test slash command sync error handling"""
        with patch.object(bot.tree, 'sync') as mock_sync:
            mock_sync.side_effect = Exception("Sync failed")
            
            # Act
            result = await bot.sync_slash_commands()
            
            # Assert
            assert result is False
            mock_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_app_command_error(self, bot):
        """Test application command error handling"""
        # Arrange
        mock_interaction = AsyncMock(spec=discord.Interaction)
        mock_interaction.response.is_done.return_value = False
        mock_interaction.response.send_message = AsyncMock()
        mock_interaction.command = MagicMock()
        mock_interaction.command.name = "test_command"
        mock_interaction.user.id = 123456789
        mock_interaction.guild.id = 987654321
        
        error = discord.app_commands.CommandInvokeError(
            command=MagicMock(),
            original=ValueError("Test error")
        )
        
        # Act
        await bot.on_app_command_error(mock_interaction, error)
        
        # Assert
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "An error occurred" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_on_app_command_error_response_done(self, bot):
        """Test application command error when response already sent"""
        # Arrange
        mock_interaction = AsyncMock(spec=discord.Interaction)
        mock_interaction.response.is_done.return_value = True
        mock_interaction.followup.send = AsyncMock()
        mock_interaction.command = MagicMock()
        mock_interaction.command.name = "test_command"
        mock_interaction.user.id = 123456789
        mock_interaction.guild.id = 987654321
        
        error = discord.app_commands.CommandInvokeError(
            command=MagicMock(),
            original=RuntimeError("Another error")
        )
        
        # Act
        await bot.on_app_command_error(mock_interaction, error)
        
        # Assert
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "An error occurred" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True
    
    @pytest.mark.asyncio
    async def test_on_command_error_handling(self, bot):
        """Test general command error handling"""
        # Arrange
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()
        error = commands.CommandNotFound("Unknown command")
        
        # Act
        await bot.on_command_error(mock_ctx, error)
        
        # Assert - should log but not send message for CommandNotFound
        mock_ctx.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_setup_commands_registration(self, bot, mock_services):
        """Test slash commands are properly registered"""
        # Act
        await bot.setup_commands()
        
        # Assert reminder commands are added to tree
        assert hasattr(bot, 'reminder_commands')
        assert isinstance(bot.reminder_commands, ReminderCommands)
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, bot, mock_services):
        """Test bot cleanup on close"""
        # Act
        await bot.close()
        
        # Assert services are properly cleaned up
        mock_services['scheduler_service'].stop.assert_called_once()
    
    def test_get_guild_count(self, bot):
        """Test getting guild count"""
        # Arrange
        mock_guilds = [MagicMock() for _ in range(3)]
        
        with patch.object(bot, 'guilds', mock_guilds):
            # Act
            count = bot.get_guild_count()
            
            # Assert
            assert count == 3
    
    def test_get_user_count(self, bot):
        """Test getting total user count across guilds"""
        # Arrange
        mock_guild1 = MagicMock()
        mock_guild1.member_count = 50
        mock_guild2 = MagicMock()
        mock_guild2.member_count = 100
        mock_guild3 = MagicMock()
        mock_guild3.member_count = 25
        
        with patch.object(bot, 'guilds', [mock_guild1, mock_guild2, mock_guild3]):
            # Act
            count = bot.get_user_count()
            
            # Assert
            assert count == 175
    
    def test_command_prefix_configuration(self, bot):
        """Test command prefix is properly configured"""
        # Assert
        assert bot.command_prefix == "!"
    
    @pytest.mark.asyncio
    async def test_bot_status_update(self, bot):
        """Test bot status is updated with guild count"""
        # Arrange
        with patch.object(bot, 'guilds', [MagicMock() for _ in range(5)]), \
             patch.object(bot, 'change_presence') as mock_presence:
            
            # Act
            await bot.update_status()
            
            # Assert
            mock_presence.assert_called_once()
            call_args = mock_presence.call_args
            assert "5 servers" in str(call_args[1]['activity'].name)
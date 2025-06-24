import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from src.services.notification_service import NotificationService
from src.models.reminder import Reminder
from src.models.enums import FrequencyEnum, ReminderStatus


class TestNotificationService:
    """Test cases for the NotificationService"""
    
    @pytest.fixture
    def mock_discord_client(self):
        """Create a mock Discord client"""
        client = AsyncMock(spec=discord.Client)
        
        # Mock channel
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_message = AsyncMock(spec=discord.Message)
        mock_message.id = 123456789012345678
        mock_message.add_reaction = AsyncMock()
        mock_channel.send = AsyncMock(return_value=mock_message)
        client.get_channel.return_value = mock_channel
        
        return client
    
    @pytest.fixture
    def mock_validation_service(self):
        """Create a mock validation service"""
        service = AsyncMock()
        service.create_validation = AsyncMock()
        return service
    
    @pytest.fixture
    def notification_service(self, mock_discord_client, mock_validation_service):
        """Create a notification service instance"""
        return NotificationService(
            discord_client=mock_discord_client,
            validation_service=mock_validation_service
        )
    
    @pytest.fixture
    def sample_reminder(self):
        """Create a sample reminder for testing"""
        return Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Daily standup reminder",
            created_by="admin_123",
            reminder_id=1,
            validation_required=True,
            next_execution=datetime.utcnow() + timedelta(days=1)
        )
    
    @pytest.mark.asyncio
    async def test_send_reminder_without_validation(self, notification_service, mock_discord_client, sample_reminder):
        """Test sending reminder without validation requirement"""
        # Arrange
        sample_reminder.validation_required = False
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is True
        mock_discord_client.get_channel.assert_called_once_with(int(sample_reminder.channel_id))
        channel = mock_discord_client.get_channel.return_value
        channel.send.assert_called_once()
        
        # Should not add reaction for non-validation reminders
        message = channel.send.return_value
        message.add_reaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_reminder_with_validation(self, notification_service, mock_discord_client, mock_validation_service, sample_reminder):
        """Test sending reminder with validation requirement"""
        # Arrange
        sample_reminder.validation_required = True
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is True
        mock_discord_client.get_channel.assert_called_once_with(int(sample_reminder.channel_id))
        channel = mock_discord_client.get_channel.return_value
        channel.send.assert_called_once()
        
        # Should add reaction for validation reminders
        message = channel.send.return_value
        message.add_reaction.assert_called_once_with("✅")
        
        # Should create validation record
        mock_validation_service.create_validation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_reminder_channel_not_found(self, notification_service, mock_discord_client, sample_reminder):
        """Test sending reminder when channel is not found"""
        # Arrange
        mock_discord_client.get_channel.return_value = None
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is False
        mock_discord_client.get_channel.assert_called_once_with(int(sample_reminder.channel_id))
    
    @pytest.mark.asyncio
    async def test_send_reminder_discord_forbidden(self, notification_service, mock_discord_client, sample_reminder):
        """Test sending reminder with Discord Forbidden error"""
        # Arrange
        channel = mock_discord_client.get_channel.return_value
        channel.send.side_effect = discord.Forbidden(MagicMock(), "Forbidden")
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is False
        channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_reminder_discord_http_exception(self, notification_service, mock_discord_client, sample_reminder):
        """Test sending reminder with Discord HTTP exception"""
        # Arrange
        channel = mock_discord_client.get_channel.return_value
        channel.send.side_effect = discord.HTTPException(MagicMock(), "HTTP Error")
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is False
        channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_reminder_reaction_error(self, notification_service, mock_discord_client, mock_validation_service, sample_reminder):
        """Test sending reminder when reaction addition fails"""
        # Arrange
        sample_reminder.validation_required = True
        message = mock_discord_client.get_channel.return_value.send.return_value
        message.add_reaction.side_effect = discord.HTTPException(MagicMock(), "Reaction Error")
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is False  # Should fail if reaction can't be added
        mock_validation_service.create_validation.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_reminder_validation_creation_error(self, notification_service, mock_discord_client, mock_validation_service, sample_reminder):
        """Test sending reminder when validation creation fails"""
        # Arrange
        sample_reminder.validation_required = True
        mock_validation_service.create_validation.side_effect = Exception("Validation creation failed")
        
        # Act
        result = await notification_service.send_reminder(sample_reminder)
        
        # Assert
        assert result is False
        # Message should still be sent but validation creation failed
        channel = mock_discord_client.get_channel.return_value
        channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_reminder_embed_basic(self, notification_service, sample_reminder):
        """Test basic reminder embed creation"""
        # Arrange
        sample_reminder.validation_required = False
        
        # Act
        embed = notification_service._create_reminder_embed(sample_reminder)
        
        # Assert
        assert embed.title == "🔔 Reminder Notification"
        assert "Daily standup reminder" in embed.description
        assert "daily" in embed.fields[0].value.lower()
        assert embed.color.value == 0x3498db
    
    @pytest.mark.asyncio
    async def test_create_reminder_embed_with_validation(self, notification_service, sample_reminder):
        """Test reminder embed creation with validation requirement"""
        # Arrange
        sample_reminder.validation_required = True
        
        # Act
        embed = notification_service._create_reminder_embed(sample_reminder)
        
        # Assert
        assert embed.title == "🔔 Reminder Notification"
        assert "Daily standup reminder" in embed.description
        validation_field = next(field for field in embed.fields if "Validation Required" in field.name)
        assert "React with ✅" in validation_field.value
        assert "48 hours" in validation_field.value
    
    @pytest.mark.asyncio
    async def test_create_reminder_embed_different_frequencies(self, notification_service, sample_reminder):
        """Test embed creation for different frequencies"""
        frequencies = [
            (FrequencyEnum.HOURLY, "hourly"),
            (FrequencyEnum.DAILY, "daily"),
            (FrequencyEnum.WEEKLY, "weekly"),
            (FrequencyEnum.MONTHLY, "monthly")
        ]
        
        for frequency, expected_text in frequencies:
            # Arrange
            sample_reminder.frequency = frequency
            
            # Act
            embed = notification_service._create_reminder_embed(sample_reminder)
            
            # Assert
            frequency_field = next(field for field in embed.fields if field.name == "Frequency")
            assert expected_text in frequency_field.value.lower()
    
    @pytest.mark.asyncio
    async def test_send_multiple_reminders(self, notification_service, mock_discord_client):
        """Test sending multiple reminders in bulk"""
        # Arrange
        reminders = [
            Reminder(
                user_id=f"user_{i}",
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content=f"Reminder {i}",
                created_by="admin_123",
                reminder_id=i,
                validation_required=False
            )
            for i in range(3)
        ]
        
        # Act
        results = await notification_service.send_multiple_reminders(reminders)
        
        # Assert
        assert len(results) == 3
        assert all(result is True for result in results)
        assert mock_discord_client.get_channel.call_count == 3
    
    @pytest.mark.asyncio
    async def test_send_multiple_reminders_with_failures(self, notification_service, mock_discord_client):
        """Test sending multiple reminders with some failures"""
        # Arrange
        reminders = [
            Reminder(
                user_id=f"user_{i}",
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content=f"Reminder {i}",
                created_by="admin_123",
                reminder_id=i,
                validation_required=False
            )
            for i in range(3)
        ]
        
        # Make second channel not found
        def get_channel_side_effect(channel_id):
            if channel_id == 111222333:
                return None  # Second call returns None
            return mock_discord_client.get_channel.return_value
        
        mock_discord_client.get_channel.side_effect = [
            mock_discord_client.get_channel.return_value,  # First succeeds
            None,  # Second fails (channel not found)
            mock_discord_client.get_channel.return_value   # Third succeeds
        ]
        
        # Act
        results = await notification_service.send_multiple_reminders(reminders)
        
        # Assert
        assert len(results) == 3
        assert results[0] is True   # First succeeded
        assert results[1] is False  # Second failed
        assert results[2] is True   # Third succeeded
    
    @pytest.mark.asyncio
    async def test_get_notification_statistics(self, notification_service):
        """Test getting notification statistics"""
        # Arrange - manually set the counters
        notification_service._sent_count = 150
        notification_service._failed_count = 5
        
        # Act
        stats = await notification_service.get_notification_statistics()
        
        # Assert
        assert stats["sent_count"] == 150
        assert stats["failed_count"] == 5
        assert stats["success_rate"] == 96.77  # 150/155 * 100
    
    @pytest.mark.asyncio
    async def test_send_custom_message(self, notification_service, mock_discord_client):
        """Test sending custom message to specific channel"""
        # Arrange
        channel_id = "111222333"
        message_content = "Custom notification message"
        
        # Act
        result = await notification_service.send_custom_message(channel_id, message_content)
        
        # Assert
        assert result is True
        mock_discord_client.get_channel.assert_called_once_with(int(channel_id))
        channel = mock_discord_client.get_channel.return_value
        channel.send.assert_called_once_with(message_content)
    
    @pytest.mark.asyncio
    async def test_send_custom_message_with_embed(self, notification_service, mock_discord_client):
        """Test sending custom message with Discord embed"""
        # Arrange
        channel_id = "111222333"
        embed_data = {
            "title": "Reminder Statistics",
            "description": "Current system stats",
            "color": 0x00ff00,
            "fields": [
                {"name": "Active Reminders", "value": "25", "inline": True},
                {"name": "Total Users", "value": "100", "inline": True}
            ]
        }
        
        # Act
        result = await notification_service.send_custom_message_with_embed(channel_id, embed_data)
        
        # Assert
        assert result is True
        mock_discord_client.get_channel.assert_called_once_with(int(channel_id))
        channel = mock_discord_client.get_channel.return_value
        channel.send.assert_called_once()
        
        # Check that an embed was created and sent
        call_args = channel.send.call_args
        assert "embed" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_validation_timeout_calculation(self, notification_service, sample_reminder):
        """Test validation timeout calculation"""
        # Arrange
        sample_reminder.validation_required = True
        
        with patch('src.services.notification_service.datetime') as mock_datetime:
            fixed_time = datetime(2024, 6, 15, 10, 0, 0)
            mock_datetime.utcnow.return_value = fixed_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Act
            expires_at = notification_service._calculate_validation_expiry()
            
            # Assert
            expected_expiry = fixed_time + timedelta(hours=48)
            assert expires_at == expected_expiry
    
    def test_embed_formatting_escapes_markdown(self, notification_service, sample_reminder):
        """Test that embed formatting properly escapes Discord markdown"""
        # Arrange
        sample_reminder.message_content = "**Bold** *italic* `code` @everyone"
        
        # Act
        embed = notification_service._create_reminder_embed(sample_reminder)
        
        # Assert
        # Should sanitize @everyone mentions to [@everyone]
        assert "[@everyone]" in embed.description  # Should be escaped to [@everyone]
        # Should not contain the original unescaped @everyone
        assert "[@everyone]" in embed.description and "@everyone" not in embed.description.replace("[@everyone]", "")
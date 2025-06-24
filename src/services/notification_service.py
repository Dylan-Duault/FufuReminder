from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import discord
import re
from ..models.reminder import Reminder
from ..config.settings import get_settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for sending Discord notifications and managing reactions"""
    
    def __init__(self, discord_client: discord.Client, validation_service=None):
        self.discord_client = discord_client
        self.validation_service = validation_service
        self.settings = get_settings()
        self._sent_count = 0
        self._failed_count = 0
    
    async def send_reminder(self, reminder: Reminder) -> bool:
        """Send a reminder notification to Discord"""
        try:
            # Get the target channel
            channel = self.discord_client.get_channel(int(reminder.channel_id))
            if not channel:
                logger.error(
                    "Channel not found",
                    channel_id=reminder.channel_id,
                    reminder_id=reminder.id
                )
                self._failed_count += 1
                return False
            
            # Create the reminder embed
            embed = self._create_reminder_embed(reminder)
            
            # Send the message with embed
            message = await channel.send(content=f"<@{reminder.user_id}>", embed=embed)
            
            logger.info(
                "Reminder message sent",
                reminder_id=reminder.id,
                channel_id=reminder.channel_id,
                message_id=message.id
            )
            
            # Handle validation if required
            if reminder.validation_required:
                success = await self._handle_validation_setup(reminder, message)
                if not success:
                    self._failed_count += 1
                    return False
            
            self._sent_count += 1
            return True
            
        except discord.Forbidden:
            logger.error(
                "No permission to send message",
                channel_id=reminder.channel_id,
                reminder_id=reminder.id
            )
            self._failed_count += 1
            return False
        except discord.HTTPException as e:
            logger.error(
                "Discord HTTP error sending message",
                channel_id=reminder.channel_id,
                reminder_id=reminder.id,
                error=str(e)
            )
            self._failed_count += 1
            return False
        except Exception as e:
            logger.error(
                "Unexpected error sending reminder",
                reminder_id=reminder.id,
                error=str(e)
            )
            self._failed_count += 1
            return False
    
    async def _handle_validation_setup(self, reminder: Reminder, message: discord.Message) -> bool:
        """Set up validation for a reminder message"""
        try:
            # Add reaction for validation
            await message.add_reaction("✅")
            
            # Create validation record
            expires_at = self._calculate_validation_expiry()
            await self.validation_service.create_validation(
                reminder_id=reminder.id,
                message_id=str(message.id),
                expires_at=expires_at
            )
            
            logger.info(
                "Validation setup complete",
                reminder_id=reminder.id,
                message_id=message.id,
                expires_at=expires_at
            )
            
            return True
            
        except discord.HTTPException as e:
            logger.error(
                "Failed to add reaction",
                message_id=message.id,
                reminder_id=reminder.id,
                error=str(e)
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to create validation",
                reminder_id=reminder.id,
                message_id=message.id,
                error=str(e)
            )
            return False
    
    def _create_reminder_embed(self, reminder: Reminder) -> discord.Embed:
        """Create a modern Discord embed for reminder messages"""
        # Sanitize message content
        sanitized_content = self._sanitize_message_content(reminder.message_content)
        
        # Create the embed with a nice color
        embed = discord.Embed(
            title="🔔 Reminder Notification",
            description=f"**{sanitized_content}**",
            color=0x3498db,  # Nice blue color
            timestamp=datetime.utcnow()
        )
        
        # Add frequency field
        frequency_emoji = {
            "spam": "⚡",
            "hourly": "🕐", 
            "daily": "📅",
            "weekly": "📆",
            "monthly": "🗓️"
        }
        
        embed.add_field(
            name="Frequency",
            value=f"{frequency_emoji.get(reminder.frequency.value, '🔁')} {reminder.frequency.value.title()}",
            inline=True
        )
        
        # Add reminder ID for reference
        embed.add_field(
            name="Reminder ID",
            value=f"#{reminder.id}",
            inline=True
        )
        
        # Add validation field if required
        if reminder.validation_required:
            embed.add_field(
                name="⚠️ Validation Required",
                value="React with ✅ within 48 hours to confirm you've seen this reminder.\nFailure to validate will result in removal from the server.",
                inline=False
            )
        
        embed.set_footer(text="FufuRemind Bot")
        
        return embed
    
    def _sanitize_message_content(self, content: str) -> str:
        """Sanitize message content to prevent Discord markdown injection"""
        # Remove @everyone and @here mentions
        content = re.sub(r'@(everyone|here)', '[@\\1]', content)
        
        # Escape Discord markdown characters (optional - could leave as-is for formatting)
        # content = re.sub(r'([*_`~|])', r'\\\1', content)
        
        return content.strip()
    
    def _calculate_validation_expiry(self) -> datetime:
        """Calculate when validation expires"""
        return datetime.utcnow() + timedelta(hours=self.settings.validation_timeout_hours)
    
    async def send_multiple_reminders(self, reminders: List[Reminder]) -> List[bool]:
        """Send multiple reminders and return list of success/failure results"""
        results = []
        
        for reminder in reminders:
            result = await self.send_reminder(reminder)
            results.append(result)
        
        logger.info(
            "Bulk reminder sending complete",
            total_count=len(reminders),
            success_count=sum(results),
            failure_count=len(reminders) - sum(results)
        )
        
        return results
    
    async def send_custom_message(self, channel_id: str, message_content: str) -> bool:
        """Send a custom message to a specific channel"""
        try:
            channel = self.discord_client.get_channel(int(channel_id))
            if not channel:
                logger.error("Channel not found for custom message", channel_id=channel_id)
                return False
            
            await channel.send(message_content)
            logger.info("Custom message sent", channel_id=channel_id)
            return True
            
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.error(
                "Failed to send custom message",
                channel_id=channel_id,
                error=str(e)
            )
            return False
    
    async def send_custom_message_with_embed(self, channel_id: str, embed_data: Dict[str, Any]) -> bool:
        """Send a custom message with Discord embed"""
        try:
            channel = self.discord_client.get_channel(int(channel_id))
            if not channel:
                logger.error("Channel not found for embed message", channel_id=channel_id)
                return False
            
            # Create Discord embed
            embed = discord.Embed(
                title=embed_data.get("title", ""),
                description=embed_data.get("description", ""),
                color=embed_data.get("color", 0x3498db)
            )
            
            # Add fields if provided
            for field in embed_data.get("fields", []):
                embed.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field.get("inline", False)
                )
            
            # Add footer if provided
            if "footer" in embed_data:
                embed.set_footer(text=embed_data["footer"])
            
            await channel.send(embed=embed)
            logger.info("Embed message sent", channel_id=channel_id)
            return True
            
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.error(
                "Failed to send embed message",
                channel_id=channel_id,
                error=str(e)
            )
            return False
    
    async def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification service statistics"""
        total_attempts = self._sent_count + self._failed_count
        success_rate = (self._sent_count / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "total_attempts": total_attempts,
            "success_rate": round(success_rate, 2)
        }
    
    def reset_statistics(self) -> None:
        """Reset notification statistics counters"""
        self._sent_count = 0
        self._failed_count = 0
        logger.info("Notification statistics reset")
    
    def _get_sent_count(self) -> int:
        """Get count of successfully sent messages"""
        return self._sent_count
    
    def _get_failed_count(self) -> int:
        """Get count of failed message attempts"""
        return self._failed_count
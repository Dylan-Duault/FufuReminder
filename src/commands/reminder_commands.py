import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from datetime import datetime

from ..models.enums import FrequencyEnum, ReminderStatus
from ..services.reminder_service import ReminderService
from ..services.notification_service import NotificationService
from ..config.logging import get_logger

logger = get_logger(__name__)


class ReminderCommands:
    """Discord slash commands for reminder management"""
    
    def __init__(self, reminder_service: ReminderService, notification_service: NotificationService):
        self.reminder_service = reminder_service
        self.notification_service = notification_service
    
    async def add_reminder(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        frequency: str,
        message: str,
        validation_required: bool = False
    ):
        """Create a new reminder"""
        logger.info(
            "Processing reminder_add command", 
            user_id=interaction.user.id,
            target_user_id=user.id,
            frequency=frequency,
            message_preview=message[:50] + "..." if len(message) > 50 else message,
            validation_required=validation_required
        )
        try:
            # Check permissions
            if not await self._check_admin_permissions(interaction):
                await interaction.response.send_message(
                    "❌ You don't have permission to create reminders. Only administrators can create reminders.",
                    ephemeral=True
                )
                return
            
            # Validate frequency
            frequency_enum = self._validate_frequency(frequency.lower())
            if not frequency_enum:
                await interaction.response.send_message(
                    "❌ Invalid frequency. Use: spam, hourly, daily, weekly, or monthly",
                    ephemeral=True
                )
                return
            
            # Validate message
            if not message.strip():
                await interaction.response.send_message(
                    "❌ Message cannot be empty",
                    ephemeral=True
                )
                return
            
            # Create reminder
            reminder = await self.reminder_service.create_reminder(
                user_id=str(user.id),
                guild_id=str(interaction.guild.id),
                channel_id=str(interaction.channel.id),
                frequency=frequency_enum,
                message_content=message.strip(),
                created_by=str(interaction.user.id),
                validation_required=validation_required
            )
            
            # Send success response
            response_message = (
                f"✅ **Reminder created successfully!**\n"
                f"👤 **User:** {user.mention}\n"
                f"📝 **Message:** {message}\n"
                f"🔁 **Frequency:** {frequency}\n"
                f"✅ **Validation:** {'Required' if validation_required else 'Not required'}\n"
                f"📅 **Next execution:** <t:{int(reminder.next_execution.timestamp())}:F>"
            )
            
            await interaction.response.send_message(response_message)
            
            logger.info(
                "Reminder created via slash command",
                reminder_id=reminder.id,
                created_by=interaction.user.id,
                user_id=user.id,
                frequency=frequency
            )
            
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Failed to create reminder: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(
                "Error creating reminder via slash command",
                error=str(e),
                user_id=interaction.user.id
            )
            await interaction.response.send_message(
                "❌ An unexpected error occurred while creating the reminder. Please try again.",
                ephemeral=True
            )
    
    async def list_reminders(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ):
        """List reminders for a user"""
        logger.info(
            "Processing reminder_list command",
            user_id=interaction.user.id,
            target_user_id=user.id if user else "self"
        )
        try:
            # Determine target user
            target_user = user if user else interaction.user
            
            # Check permissions if listing for another user
            if user and user.id != interaction.user.id:
                if not await self._check_admin_permissions(interaction):
                    await interaction.response.send_message(
                        "❌ You can only list your own reminders.",
                        ephemeral=True
                    )
                    return
            
            # Get reminders
            reminders = await self.reminder_service.get_user_reminders(str(target_user.id))
            
            if not reminders:
                await interaction.response.send_message(
                    f"You don't have any reminders yet. Use `/reminder_add` to create one!",
                    ephemeral=True
                )
                return
            
            # Format reminder list
            response = self._format_reminder_list(reminders, str(target_user.id))
            
            await interaction.response.send_message(response, ephemeral=True)
            
        except Exception as e:
            logger.error(
                "Error listing reminders",
                error=str(e),
                user_id=interaction.user.id
            )
            await interaction.response.send_message(
                "❌ An error occurred while retrieving reminders.",
                ephemeral=True
            )
    
    async def delete_reminder(
        self,
        interaction: discord.Interaction,
        reminder_id: int
    ):
        """Delete a reminder"""
        try:
            # Get reminder
            reminder = await self.reminder_service.get_reminder_by_id(reminder_id)
            if not reminder:
                await interaction.response.send_message(
                    f"❌ Reminder with ID {reminder_id} not found.",
                    ephemeral=True
                )
                return
            
            # Check ownership
            if not self._check_reminder_ownership(interaction, reminder):
                await interaction.response.send_message(
                    "❌ You can only delete your own reminders or you need admin permissions.",
                    ephemeral=True
                )
                return
            
            # Delete reminder
            success = await self.reminder_service.delete_reminder(reminder_id)
            
            if success:
                await interaction.response.send_message(
                    f"✅ Reminder deleted successfully!",
                    ephemeral=True
                )
                
                logger.info(
                    "Reminder deleted via slash command",
                    reminder_id=reminder_id,
                    deleted_by=interaction.user.id
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to delete reminder. Please try again.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(
                "Error deleting reminder",
                error=str(e),
                reminder_id=reminder_id,
                user_id=interaction.user.id
            )
            await interaction.response.send_message(
                "❌ An error occurred while deleting the reminder.",
                ephemeral=True
            )
    
    async def pause_reminder(
        self,
        interaction: discord.Interaction,
        reminder_id: int
    ):
        """Pause a reminder"""
        await self._update_reminder_status(
            interaction, 
            reminder_id, 
            ReminderStatus.PAUSED,
            "⏸️ Reminder paused successfully!",
            "pause"
        )
    
    async def resume_reminder(
        self,
        interaction: discord.Interaction,
        reminder_id: int
    ):
        """Resume a reminder"""
        await self._update_reminder_status(
            interaction,
            reminder_id,
            ReminderStatus.ACTIVE,
            "▶️ Reminder resumed successfully!",
            "resume"
        )
    
    async def stats(self, interaction: discord.Interaction):
        """Show reminder statistics"""
        try:
            stats = await self.reminder_service.get_reminder_statistics()
            
            embed = discord.Embed(
                title="📊 Reminder Statistics",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Total Reminders",
                value=f"{stats['total_reminders']}",
                inline=True
            )
            embed.add_field(
                name="Active Reminders",
                value=f"{stats['active_reminders']}",
                inline=True
            )
            embed.add_field(
                name="Pending Validations",
                value=f"{stats['pending_validations']}",
                inline=True
            )
            
            embed.set_footer(text="FufuRemind Bot")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(
                "Error getting reminder statistics",
                error=str(e),
                user_id=interaction.user.id
            )
            await interaction.response.send_message(
                "❌ An error occurred while retrieving statistics.",
                ephemeral=True
            )
    
    async def _update_reminder_status(
        self,
        interaction: discord.Interaction,
        reminder_id: int,
        new_status: ReminderStatus,
        success_message: str,
        action: str
    ):
        """Helper method to update reminder status"""
        try:
            # Get reminder
            reminder = await self.reminder_service.get_reminder_by_id(reminder_id)
            if not reminder:
                await interaction.response.send_message(
                    f"❌ Reminder with ID {reminder_id} not found.",
                    ephemeral=True
                )
                return
            
            # Check ownership
            if not self._check_reminder_ownership(interaction, reminder):
                await interaction.response.send_message(
                    f"❌ You can only {action} your own reminders or you need admin permissions.",
                    ephemeral=True
                )
                return
            
            # Update status
            success = await self.reminder_service.update_reminder_status(reminder_id, new_status)
            
            if success:
                await interaction.response.send_message(success_message, ephemeral=True)
                
                logger.info(
                    f"Reminder {action}d via slash command",
                    reminder_id=reminder_id,
                    updated_by=interaction.user.id,
                    new_status=new_status.value
                )
            else:
                await interaction.response.send_message(
                    f"❌ Failed to {action} reminder. Please try again.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(
                f"Error {action}ing reminder",
                error=str(e),
                reminder_id=reminder_id,
                user_id=interaction.user.id
            )
            await interaction.response.send_message(
                f"❌ An error occurred while {action}ing the reminder.",
                ephemeral=True
            )
    
    def _validate_frequency(self, frequency: str) -> Optional[FrequencyEnum]:
        """Validate and convert frequency string to enum"""
        frequency_map = {
            "spam": FrequencyEnum.SPAM,
            "hourly": FrequencyEnum.HOURLY,
            "daily": FrequencyEnum.DAILY,
            "weekly": FrequencyEnum.WEEKLY,
            "monthly": FrequencyEnum.MONTHLY,
        }
        return frequency_map.get(frequency.lower())
    
    def _format_reminder_list(self, reminders: List, user_id: str) -> str:
        """Format reminder list for display"""
        lines = [f"📋 **Reminders for <@{user_id}>**\n"]
        
        for reminder in reminders:
            status_emoji = "🟢" if reminder.status == ReminderStatus.ACTIVE else "⏸️"
            validation_text = "✅ validation required" if reminder.validation_required else "⭕ no validation"
            
            lines.append(
                f"**ID {reminder.id}** - {reminder.message_content}\n"
                f"🔁 {reminder.frequency.value} | {validation_text} | {status_emoji} {reminder.status.value}\n"
                f"📅 Next: <t:{int(reminder.next_execution.timestamp())}:R>\n"
            )
        
        return "\n".join(lines)
    
    def _check_reminder_ownership(self, interaction: discord.Interaction, reminder) -> bool:
        """Check if user can modify the reminder"""
        # Owner can always modify
        if str(interaction.user.id) == reminder.user_id:
            return True
        
        # Admin can modify any reminder
        if interaction.user.guild_permissions.manage_guild:
            return True
        
        return False
    
    async def _check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permissions"""
        # For now, just check Discord permissions
        return interaction.user.guild_permissions.manage_guild
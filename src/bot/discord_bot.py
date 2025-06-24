import asyncio
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands

from ..config.settings import get_settings
from ..config.logging import get_logger
from ..services.reminder_service import ReminderService
from ..services.notification_service import NotificationService
from ..services.scheduler_service import SchedulerService
from ..services.validation_service import ValidationService
from ..commands.reminder_commands import ReminderCommands
from ..observers.reaction_observer import ReactionObserver

logger = get_logger(__name__)


class FufuRemindBot(commands.Bot):
    """
    Discord bot for managing scheduled reminders with user validation.
    
    Features:
    - Slash commands for reminder management
    - Automatic reminder scheduling and execution
    - User validation via reactions with timeout
    - Admin-only reminder creation with permission checks
    - Comprehensive error handling and logging
    """
    
    def __init__(
        self,
        reminder_service: ReminderService,
        notification_service: NotificationService,
        scheduler_service: SchedulerService,
        validation_service: ValidationService
    ):
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for reading message content
        intents.guilds = True          # Required for guild events
        intents.guild_reactions = True  # Required for reaction events
        intents.members = True         # Required for member management
        
        # Get bot settings
        self.settings = get_settings()
        
        # Initialize bot with command prefix and intents
        super().__init__(
            command_prefix=self.settings.command_prefix,
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Store service dependencies
        self.reminder_service = reminder_service
        self.notification_service = notification_service
        self.scheduler_service = scheduler_service
        self.validation_service = validation_service
        
        # Initialize command and event handlers
        self.reminder_commands = None
        self.reaction_observer = None
    
    async def setup_commands(self):
        """Set up slash commands for the bot"""
        try:
            # Create reminder commands instance
            self.reminder_commands = ReminderCommands(
                reminder_service=self.reminder_service,
                notification_service=self.notification_service
            )
            
            # Create reaction observer
            self.reaction_observer = ReactionObserver(
                validation_service=self.validation_service
            )
            
            # Add commands to the command tree
            self.tree.add_command(self.reminder_commands.add_reminder)
            self.tree.add_command(self.reminder_commands.list_reminders)
            self.tree.add_command(self.reminder_commands.delete_reminder)
            self.tree.add_command(self.reminder_commands.pause_reminder)
            self.tree.add_command(self.reminder_commands.resume_reminder)
            self.tree.add_command(self.reminder_commands.stats)
            
            logger.info("Slash commands registered successfully")
            
        except Exception as e:
            logger.error("Failed to setup commands", error=str(e))
            raise
    
    async def on_ready(self):
        """Event triggered when bot is ready and connected to Discord"""
        try:
            logger.info(
                "Bot connected to Discord",
                bot_name=self.user.name,
                bot_id=self.user.id,
                guild_count=len(self.guilds),
                user_count=self.get_user_count()
            )
            
            # Set up slash commands
            await self.setup_commands()
            
            # Sync slash commands with Discord
            await self.sync_slash_commands()
            
            # Start the scheduler service
            await self.scheduler_service.start()
            
            # Update bot status
            await self.update_status()
            
            logger.info("Bot initialization complete")
            
        except Exception as e:
            logger.error("Error in on_ready event", error=str(e))
            raise
    
    async def on_guild_join(self, guild: discord.Guild):
        """Event triggered when bot joins a new guild"""
        try:
            logger.info(
                "Bot joined new guild",
                guild_name=guild.name,
                guild_id=guild.id,
                member_count=guild.member_count
            )
            
            # Sync slash commands for the new guild
            await self.sync_slash_commands(guild=guild)
            
            # Update bot status with new guild count
            await self.update_status()
            
        except Exception as e:
            logger.error(
                "Error handling guild join",
                guild_id=guild.id,
                error=str(e)
            )
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Event triggered when bot is removed from a guild"""
        try:
            logger.info(
                "Bot removed from guild",
                guild_name=guild.name,
                guild_id=guild.id
            )
            
            # Clean up all reminders for this guild
            await self.reminder_service.cleanup_guild_reminders(str(guild.id))
            
            # Update bot status with new guild count
            await self.update_status()
            
        except Exception as e:
            logger.error(
                "Error handling guild removal",
                guild_id=guild.id,
                error=str(e)
            )
    
    async def sync_slash_commands(self, guild: Optional[discord.Guild] = None) -> bool:
        """Sync slash commands with Discord API"""
        try:
            if guild:
                # Sync commands for specific guild (faster for testing)
                synced = await self.tree.sync(guild=guild)
                logger.info(
                    "Slash commands synced for guild",
                    guild_id=guild.id,
                    command_count=len(synced)
                )
            else:
                # Sync commands globally (takes up to 1 hour to propagate)
                synced = await self.tree.sync()
                logger.info(
                    "Slash commands synced globally",
                    command_count=len(synced)
                )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to sync slash commands",
                guild_id=guild.id if guild else None,
                error=str(e)
            )
            return False
    
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """Handle slash command errors"""
        try:
            logger.error(
                "Application command error",
                command=interaction.command.name if interaction.command else "unknown",
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None,
                error=str(error)
            )
            
            # Send user-friendly error message
            error_message = (
                "❌ An error occurred while processing your command. "
                "Please try again or contact an administrator if the problem persists."
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                await interaction.followup.send(error_message, ephemeral=True)
                
        except Exception as e:
            logger.error("Error in error handler", error=str(e))
    
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        """Handle reaction add events"""
        if self.reaction_observer:
            await self.reaction_observer.on_reaction_add(reaction, user)
    
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        """Handle reaction remove events"""
        if self.reaction_observer:
            await self.reaction_observer.on_reaction_remove(reaction, user)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle general command errors"""
        # Ignore certain errors to reduce log noise
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(
            "Command error",
            command=ctx.command.name if ctx.command else "unknown",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            error=str(error)
        )
    
    async def update_status(self):
        """Update bot status with current statistics"""
        try:
            guild_count = len(self.guilds)
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{guild_count} servers | /reminder_add to get started"
            )
            
            await self.change_presence(
                status=discord.Status.online,
                activity=activity
            )
            
            logger.debug("Bot status updated", guild_count=guild_count)
            
        except Exception as e:
            logger.error("Failed to update bot status", error=str(e))
    
    async def close(self):
        """Clean shutdown of the bot"""
        try:
            logger.info("Bot shutdown initiated")
            
            # Stop the scheduler service
            await self.scheduler_service.stop()
            
            # Close database connections and cleanup
            # This will be handled by the service layer
            
            # Call parent close method
            await super().close()
            
            logger.info("Bot shutdown complete")
            
        except Exception as e:
            logger.error("Error during bot shutdown", error=str(e))
            raise
    
    def get_guild_count(self) -> int:
        """Get the number of guilds the bot is in"""
        return len(self.guilds)
    
    def get_user_count(self) -> int:
        """Get the total number of users across all guilds"""
        return sum(guild.member_count for guild in self.guilds if guild.member_count)
    
    async def run_bot(self):
        """Run the bot with proper error handling"""
        try:
            logger.info("Starting FufuRemind bot")
            
            # Start the bot
            await self.start(self.settings.discord_token)
            
        except discord.LoginFailure:
            logger.error("Invalid Discord token provided")
            raise
        except discord.HTTPException as e:
            logger.error("Discord HTTP error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error starting bot", error=str(e))
            raise


async def create_bot() -> FufuRemindBot:
    """
    Factory function to create and configure the Discord bot.
    
    This function handles dependency injection and service initialization.
    """
    # Import here to avoid circular imports
    from ..database.connection import DatabaseManager
    from ..repositories.reminder_repo import ReminderRepository
    from ..repositories.validation_repo import ValidationRepository
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Create repositories
        reminder_repo = ReminderRepository(db_manager.get_session)
        validation_repo = ValidationRepository(db_manager.get_session)
        
        # Create services
        reminder_service = ReminderService(reminder_repo, validation_repo)
        scheduler_service = SchedulerService(reminder_service)
        
        # Create bot first
        bot = FufuRemindBot(
            reminder_service=reminder_service,
            notification_service=None,  # Will be created below
            scheduler_service=scheduler_service,
            validation_service=None     # Will be created below
        )
        
        # Create services that need Discord client
        validation_service = ValidationService(validation_repo, reminder_repo, bot)
        notification_service = NotificationService(
            discord_client=bot,
            validation_service=validation_service
        )
        
        # Inject services into bot
        bot.validation_service = validation_service
        bot.notification_service = notification_service
        
        logger.info("Bot created successfully with all dependencies")
        return bot
        
    except Exception as e:
        logger.error("Failed to create bot", error=str(e))
        raise


def main():
    """Main entry point for the bot application"""
    async def run():
        bot = await create_bot()
        try:
            await bot.run_bot()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error("Bot crashed", error=str(e))
            raise
        finally:
            await bot.close()
    
    # Run the bot
    asyncio.run(run())


if __name__ == "__main__":
    main()
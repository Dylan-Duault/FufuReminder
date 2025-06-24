#!/usr/bin/env python3
"""
FufuRemind Discord Bot - Main Entry Point

Enterprise-grade Discord bot for scheduled reminders with user validation system.

Usage:
    python main.py

Environment Variables Required:
    DISCORD_TOKEN - Discord bot token
    DATABASE_URL - Database connection string (optional, defaults to SQLite)
    VALIDATION_TIMEOUT_HOURS - Hours before validation expires (optional, default 48)

Features:
    - Admin-only reminder creation with frequency options (hourly/daily/weekly/monthly)
    - Optional user validation via ✅ reaction with 48-hour timeout
    - Automatic user removal for failed validations
    - Comprehensive slash command interface
    - Persistent SQLite storage with clean architecture
    - Structured logging and error handling
"""

import asyncio
import sys
import signal
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.bot.discord_bot import create_bot
from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class FufuRemindApplication:
    """Main application class for FufuRemind bot"""
    
    def __init__(self):
        self.bot = None
        self.shutdown_event = asyncio.Event()
    
    
    async def shutdown(self):
        """Gracefully shutdown the bot"""
        try:
            logger.info("🛑 Initiating graceful shutdown...")
            
            if self.bot:
                await self.bot.close()
                logger.info("✅ Bot closed successfully")
            
            # Cancel any remaining tasks
            tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            if tasks:
                logger.info(f"🧹 Cancelling {len(tasks)} remaining tasks...")
                for task in tasks:
                    task.cancel()
                
                # Wait for tasks to complete
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info("✅ Shutdown complete")
            
        except Exception as e:
            logger.error("⚠️ Error during shutdown", error=str(e))
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}")
            # Use asyncio to safely set the event from the signal handler
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(self.shutdown_event.set)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Main application run loop"""
        bot_task = None
        try:
            # Create and configure bot
            logger.info("🚀 Starting FufuRemind Discord Bot")
            
            # Validate configuration
            settings = get_settings()
            if not settings.discord_token:
                logger.error("❌ DISCORD_TOKEN not found in environment variables")
                logger.error("Please set DISCORD_TOKEN in config/.env file")
                return 1
            
            # Debug: Log token info (first/last 10 chars for security)
            token = settings.discord_token
            logger.info(f"🔑 Token loaded: {token[:10]}...{token[-10:]} (length: {len(token)})")
            
            logger.info("✅ Configuration validated")
            
            # Create and configure bot
            self.bot = await create_bot()
            logger.info("✅ Bot instance created with all dependencies")
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start the bot as a task
            logger.info("🔗 Connecting to Discord...")
            bot_task = asyncio.create_task(self.bot.run_bot())
            
            # Wait for shutdown signal or bot task completion
            done, pending = await asyncio.wait(
                [bot_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except KeyboardInterrupt:
            logger.info("⚠️ Keyboard interrupt received")
            return 0
        except Exception as e:
            logger.error("💥 Unexpected error in main loop", error=str(e))
            return 1
        
        finally:
            # Always attempt graceful shutdown
            if bot_task and not bot_task.done():
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
            await self.shutdown()
        
        return 0


async def main():
    """Main entry point"""
    print("🎯 FufuRemind Discord Bot")
    print("=" * 50)
    
    # Create and run application
    app = FufuRemindApplication()
    exit_code = await app.run()
    
    return exit_code


def cli_main():
    """Command line interface entry point"""
    try:
        # Run the async main function
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        logger.info("⚠️ Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error("💥 Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
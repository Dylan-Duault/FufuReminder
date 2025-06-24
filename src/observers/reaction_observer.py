from typing import Dict, Any, Union
import discord
from ..services.validation_service import ValidationService
from ..config.logging import get_logger

logger = get_logger(__name__)


class ReactionObserver:
    """
    Observer for Discord reaction events to handle user validation.
    
    This class processes ✅ reactions on reminder messages to validate
    that users have seen their reminders. Failed validations result in
    automatic user removal from the server.
    """
    
    def __init__(self, validation_service: ValidationService):
        self.validation_service = validation_service
        
        # Statistics tracking
        self._processed_reactions = 0
        self._successful_validations = 0
        self._failed_validations = 0
    
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        """
        Handle reaction add events for validation processing.
        
        Args:
            reaction: The Discord reaction that was added
            user: The user who added the reaction
        """
        try:
            # Ignore bot reactions
            if user.bot:
                return
            
            # Ignore reactions in DMs (no guild)
            if not reaction.message.guild:
                return
            
            # Only process checkmark reactions
            if not self._is_checkmark_emoji(reaction.emoji):
                return
            
            logger.debug(
                "Processing validation reaction",
                message_id=reaction.message.id,
                user_id=user.id,
                emoji=str(reaction.emoji)
            )
            
            # Check if this message has a validation record
            validation = await self.validation_service.get_validation_by_message_id(
                str(reaction.message.id)
            )
            
            if not validation:
                logger.debug(
                    "No validation found for message",
                    message_id=reaction.message.id
                )
                return
            
            # Process the validation reaction
            success = await self.validation_service.process_validation_reaction(
                validation_id=validation.id,
                user_id=str(user.id)
            )
            
            # Update statistics
            self._processed_reactions += 1
            if success:
                self._successful_validations += 1
                logger.info(
                    "User validation successful",
                    validation_id=validation.id,
                    user_id=user.id,
                    message_id=reaction.message.id
                )
            else:
                self._failed_validations += 1
                logger.debug(
                    "User validation failed or already processed",
                    validation_id=validation.id,
                    user_id=user.id,
                    message_id=reaction.message.id
                )
            
        except Exception as e:
            logger.error(
                "Error processing validation reaction",
                message_id=reaction.message.id,
                user_id=user.id,
                error=str(e)
            )
            self._failed_validations += 1
    
    async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
        """
        Handle reaction remove events.
        
        Currently, removing reactions does not affect validation status.
        Once a user has validated, the validation remains complete.
        
        Args:
            reaction: The Discord reaction that was removed
            user: The user who removed the reaction
        """
        # We don't process reaction removals for validation
        # Once validated, the status should remain
        pass
    
    def _is_checkmark_emoji(self, emoji: Union[str, discord.Emoji]) -> bool:
        """
        Check if the emoji is a valid checkmark for validation.
        
        Args:
            emoji: The emoji to check (unicode string or custom emoji)
            
        Returns:
            True if the emoji is a valid checkmark, False otherwise
        """
        # Unicode checkmark
        if isinstance(emoji, str):
            return emoji == "✅"
        
        # Custom emoji - check name contains checkmark-like terms
        if hasattr(emoji, 'name'):
            checkmark_names = [
                "checkmark", "check", "green_check", "tick", 
                "confirm", "yes", "approve", "validated"
            ]
            return any(name in emoji.name.lower() for name in checkmark_names)
        
        return False
    
    def get_reaction_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about reaction processing.
        
        Returns:
            Dictionary containing reaction processing statistics
        """
        return {
            "processed_reactions": self._processed_reactions,
            "successful_validations": self._successful_validations,
            "failed_validations": self._failed_validations,
            "success_rate": (
                (self._successful_validations / self._processed_reactions * 100)
                if self._processed_reactions > 0 else 0
            )
        }
    
    def reset_statistics(self) -> None:
        """Reset reaction processing statistics"""
        self._processed_reactions = 0
        self._successful_validations = 0
        self._failed_validations = 0
        logger.info("Reaction observer statistics reset")
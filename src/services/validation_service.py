from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import discord
from ..repositories.validation_repo import ValidationRepository
from ..repositories.reminder_repo import ReminderRepository
from ..database.models import ValidationModel
from ..models.validation import Validation
from ..models.enums import ValidationStatus
from ..config.settings import get_settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class ValidationService:
    """Service for managing reminder validations and user reactions"""
    
    def __init__(
        self,
        validation_repo: ValidationRepository,
        reminder_repo: ReminderRepository,
        discord_client: discord.Client
    ):
        self.validation_repo = validation_repo
        self.reminder_repo = reminder_repo
        self.discord_client = discord_client
        self.settings = get_settings()
    
    async def create_validation(
        self,
        reminder_id: int,
        message_id: str,
        expires_at: datetime
    ) -> Validation:
        """Create a new validation for a reminder"""
        
        validation_model = ValidationModel(
            reminder_id=reminder_id,
            message_id=message_id,
            status=ValidationStatus.PENDING,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        created_model = await self.validation_repo.create(validation_model)
        
        logger.info(
            "Created validation",
            validation_id=created_model.id,
            reminder_id=reminder_id,
            message_id=message_id,
            expires_at=expires_at
        )
        
        return self._model_to_domain(created_model)
    
    async def process_reaction_validation(self, message_id: str, user_id: str) -> bool:
        """Process a reaction for validation"""
        
        # Find the validation by message ID
        validation_model = await self.validation_repo.find_by_message_id(message_id)
        if not validation_model:
            logger.debug("No validation found for message", message_id=message_id)
            return False
        
        # Check if validation is still pending
        if validation_model.status != ValidationStatus.PENDING:
            logger.debug(
                "Validation not pending",
                validation_id=validation_model.id,
                status=validation_model.status.value
            )
            return False
        
        # Get the associated reminder to check user
        reminder_model = await self.reminder_repo.get_by_id(validation_model.reminder_id)
        if not reminder_model:
            logger.error(
                "Reminder not found for validation",
                validation_id=validation_model.id,
                reminder_id=validation_model.reminder_id
            )
            return False
        
        # Check if the reaction is from the correct user
        if reminder_model.user_id != user_id:
            logger.debug(
                "Reaction from wrong user",
                validation_id=validation_model.id,
                expected_user=reminder_model.user_id,
                actual_user=user_id
            )
            return False
        
        # Check if validation hasn't expired
        validation_domain = self._model_to_domain(validation_model)
        if validation_domain.is_expired():
            logger.info(
                "Validation expired",
                validation_id=validation_model.id,
                expires_at=validation_model.expires_at
            )
            await self.validation_repo.mark_as_expired(validation_model.id)
            return False
        
        # Mark as validated
        validation_time = datetime.utcnow()
        success = await self.validation_repo.mark_as_validated(
            validation_model.id,
            validation_time
        )
        
        if success:
            logger.info(
                "Validation completed",
                validation_id=validation_model.id,
                user_id=user_id,
                validated_at=validation_time
            )
        
        return success
    
    async def process_expired_validations(self) -> int:
        """Process all expired validations and kick users"""
        expired_validations = await self.validation_repo.find_expired_validations()
        processed_count = 0
        
        for validation_model in expired_validations:
            try:
                # Get the associated reminder
                reminder_model = await self.reminder_repo.get_by_id(validation_model.reminder_id)
                if not reminder_model:
                    logger.error(
                        "Reminder not found for expired validation",
                        validation_id=validation_model.id,
                        reminder_id=validation_model.reminder_id
                    )
                    continue
                
                # Mark validation as expired
                await self.validation_repo.mark_as_expired(validation_model.id)
                
                # Kick the user from the guild
                kick_success = await self._kick_user_from_guild(
                    reminder_model.guild_id,
                    reminder_model.user_id,
                    "Failed to validate reminder within 48 hours"
                )
                
                if kick_success:
                    logger.info(
                        "User kicked for expired validation",
                        validation_id=validation_model.id,
                        user_id=reminder_model.user_id,
                        guild_id=reminder_model.guild_id
                    )
                
                processed_count += 1
                
            except Exception as e:
                logger.error(
                    "Failed to process expired validation",
                    validation_id=validation_model.id,
                    error=str(e)
                )
        
        return processed_count
    
    async def check_validation_status(self, validation_id: int) -> Optional[Validation]:
        """Check the status of a validation"""
        model = await self.validation_repo.get_by_id(validation_id)
        return self._model_to_domain(model) if model else None
    
    async def get_validation_by_message_id(self, message_id: str) -> Optional[Validation]:
        """Get validation by Discord message ID"""
        model = await self.validation_repo.find_by_message_id(message_id)
        return self._model_to_domain(model) if model else None
    
    async def get_validations_for_reminder(self, reminder_id: int) -> List[Validation]:
        """Get all validations for a specific reminder"""
        models = await self.validation_repo.find_by_reminder_id(reminder_id)
        return [self._model_to_domain(model) for model in models]
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        pending = await self.validation_repo.count_by_status(ValidationStatus.PENDING)
        validated = await self.validation_repo.count_by_status(ValidationStatus.VALIDATED)
        expired = await self.validation_repo.count_by_status(ValidationStatus.EXPIRED)
        failed = await self.validation_repo.count_by_status(ValidationStatus.FAILED)
        
        total = pending + validated + expired + failed
        
        return {
            "pending": pending,
            "validated": validated,
            "expired": expired,
            "failed": failed,
            "total": total
        }
    
    async def cleanup_old_validations(self, days_old: int = 7) -> int:
        """Clean up old expired/failed validations"""
        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        cleaned_count = await self.validation_repo.cleanup_expired_validations(cutoff_time)
        
        logger.info(
            "Cleaned up old validations",
            cleaned_count=cleaned_count,
            cutoff_days=days_old
        )
        
        return cleaned_count
    
    async def force_expire_validation(self, validation_id: int) -> bool:
        """Manually expire a validation"""
        success = await self.validation_repo.mark_as_expired(validation_id)
        
        if success:
            logger.info("Manually expired validation", validation_id=validation_id)
        
        return success
    
    async def bulk_expire_validations(self, validation_ids: List[int]) -> int:
        """Bulk expire multiple validations"""
        expired_count = await self.validation_repo.bulk_mark_expired(validation_ids)
        
        logger.info(
            "Bulk expired validations",
            expired_count=expired_count,
            validation_ids=validation_ids
        )
        
        return expired_count
    
    async def get_expiring_validations(self, warning_hours: int = 6) -> List[Validation]:
        """Get validations that will expire soon"""
        warning_time = datetime.utcnow() + timedelta(hours=warning_hours)
        models = await self.validation_repo.find_expiring_soon(warning_time)
        return [self._model_to_domain(model) for model in models]
    
    async def _kick_user_from_guild(self, guild_id: str, user_id: str, reason: str) -> bool:
        """Kick a user from a guild"""
        try:
            guild = self.discord_client.get_guild(int(guild_id))
            if not guild:
                logger.error("Guild not found", guild_id=guild_id)
                return False
            
            member = guild.get_member(int(user_id))
            if not member:
                logger.warning(
                    "Member not found in guild",
                    guild_id=guild_id,
                    user_id=user_id
                )
                return False
            
            await member.kick(reason=reason)
            
            logger.info(
                "Successfully kicked user",
                guild_id=guild_id,
                user_id=user_id,
                reason=reason
            )
            
            return True
            
        except discord.Forbidden:
            logger.error(
                "No permission to kick user",
                guild_id=guild_id,
                user_id=user_id
            )
            return False
        except discord.HTTPException as e:
            logger.error(
                "HTTP error kicking user",
                guild_id=guild_id,
                user_id=user_id,
                error=str(e)
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error kicking user",
                guild_id=guild_id,
                user_id=user_id,
                error=str(e)
            )
            return False
    
    def _model_to_domain(self, model: ValidationModel) -> Validation:
        """Convert database model to domain model"""
        return Validation(
            reminder_id=model.reminder_id,
            expires_at=model.expires_at,
            validation_id=model.id,
            message_id=model.message_id,
            status=model.status,
            created_at=model.created_at,
            validated_at=model.validated_at
        )
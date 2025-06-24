from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from .base import BaseRepository
from ..database.models import ValidationModel
from ..models.enums import ValidationStatus


class ValidationRepository(BaseRepository[ValidationModel]):
    """Repository for validation-specific database operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ValidationModel)
    
    async def find_by_reminder_id(self, reminder_id: int) -> List[ValidationModel]:
        """Find all validations for a specific reminder"""
        result = await self.session.execute(
            select(ValidationModel).where(ValidationModel.reminder_id == reminder_id)
        )
        return result.scalars().all()
    
    async def find_by_message_id(self, message_id: str) -> Optional[ValidationModel]:
        """Find validation by Discord message ID"""
        result = await self.session.execute(
            select(ValidationModel).where(ValidationModel.message_id == message_id)
        )
        return result.scalars().first()
    
    async def find_pending_validations(self) -> List[ValidationModel]:
        """Find all pending validations"""
        result = await self.session.execute(
            select(ValidationModel).where(ValidationModel.status == ValidationStatus.PENDING)
        )
        return result.scalars().all()
    
    async def find_expired_validations(self, current_time: Optional[datetime] = None) -> List[ValidationModel]:
        """Find validations that have expired"""
        check_time = current_time or datetime.utcnow()
        result = await self.session.execute(
            select(ValidationModel).where(
                ValidationModel.expires_at <= check_time,
                ValidationModel.status == ValidationStatus.PENDING
            )
        )
        return result.scalars().all()
    
    async def find_by_status(self, status: ValidationStatus) -> List[ValidationModel]:
        """Find validations by status"""
        result = await self.session.execute(
            select(ValidationModel).where(ValidationModel.status == status)
        )
        return result.scalars().all()
    
    async def update_status(self, validation_id: int, status: ValidationStatus) -> bool:
        """Update the status of a validation"""
        validation = await self.session.get(ValidationModel, validation_id)
        if validation:
            validation.status = status
            await self.session.commit()
            return True
        return False
    
    async def mark_as_validated(self, validation_id: int, validated_at: Optional[datetime] = None) -> bool:
        """Mark a validation as validated"""
        validation = await self.session.get(ValidationModel, validation_id)
        if validation:
            validation.status = ValidationStatus.VALIDATED
            validation.validated_at = validated_at or datetime.utcnow()
            await self.session.commit()
            return True
        return False
    
    async def mark_as_expired(self, validation_id: int) -> bool:
        """Mark a validation as expired"""
        validation = await self.session.get(ValidationModel, validation_id)
        if validation:
            validation.status = ValidationStatus.EXPIRED
            await self.session.commit()
            return True
        return False
    
    async def find_active_validations_for_reminder(self, reminder_id: int) -> List[ValidationModel]:
        """Find active (pending) validations for a specific reminder"""
        result = await self.session.execute(
            select(ValidationModel).where(
                ValidationModel.reminder_id == reminder_id,
                ValidationModel.status == ValidationStatus.PENDING
            )
        )
        return result.scalars().all()
    
    async def count_by_status(self, status: ValidationStatus) -> int:
        """Count validations by status"""
        result = await self.session.execute(
            select(func.count(ValidationModel.id)).where(ValidationModel.status == status)
        )
        return result.scalar()
    
    async def cleanup_expired_validations(self, cutoff_time: datetime) -> int:
        """Delete expired validations older than cutoff time"""
        result = await self.session.execute(
            delete(ValidationModel).where(
                ValidationModel.expires_at < cutoff_time,
                ValidationModel.status.in_([ValidationStatus.EXPIRED, ValidationStatus.FAILED])
            )
        )
        await self.session.commit()
        return result.rowcount
    
    async def find_expiring_soon(self, warning_time: datetime) -> List[ValidationModel]:
        """Find validations that will expire soon"""
        result = await self.session.execute(
            select(ValidationModel).where(
                ValidationModel.expires_at <= warning_time,
                ValidationModel.status == ValidationStatus.PENDING
            )
        )
        return result.scalars().all()
    
    async def bulk_mark_expired(self, validation_ids: List[int]) -> int:
        """Mark multiple validations as expired"""
        from sqlalchemy import update
        
        result = await self.session.execute(
            update(ValidationModel)
            .where(ValidationModel.id.in_(validation_ids))
            .values(status=ValidationStatus.EXPIRED)
        )
        await self.session.commit()
        return result.rowcount
    
    async def find_by_reminder_and_message(self, reminder_id: int, message_id: str) -> Optional[ValidationModel]:
        """Find validation by both reminder ID and message ID"""
        result = await self.session.execute(
            select(ValidationModel).where(
                ValidationModel.reminder_id == reminder_id,
                ValidationModel.message_id == message_id
            )
        )
        return result.scalars().first()
    
    async def count_by_reminder_id(self, reminder_id: int) -> int:
        """Count validations for a specific reminder"""
        result = await self.session.execute(
            select(func.count(ValidationModel.id)).where(ValidationModel.reminder_id == reminder_id)
        )
        return result.scalar()
    
    async def get_latest_validation_for_reminder(self, reminder_id: int) -> Optional[ValidationModel]:
        """Get the most recent validation for a reminder"""
        result = await self.session.execute(
            select(ValidationModel)
            .where(ValidationModel.reminder_id == reminder_id)
            .order_by(ValidationModel.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from .base import BaseRepository
from ..database.models import ReminderModel
from ..models.enums import ReminderStatus, FrequencyEnum


class ReminderRepository(BaseRepository[ReminderModel]):
    """Repository for reminder-specific database operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReminderModel)
    
    async def find_by_user_id(self, user_id: str) -> List[ReminderModel]:
        """Find all reminders for a specific user"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.user_id == user_id)
        )
        return result.scalars().all()
    
    async def find_by_guild_id(self, guild_id: str) -> List[ReminderModel]:
        """Find all reminders for a specific guild"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.guild_id == guild_id)
        )
        return result.scalars().all()
    
    async def find_due_reminders(self, current_time: Optional[datetime] = None) -> List[ReminderModel]:
        """Find all reminders that are due for execution"""
        check_time = current_time or datetime.utcnow()
        result = await self.session.execute(
            select(ReminderModel).where(
                ReminderModel.next_execution <= check_time,
                ReminderModel.status == ReminderStatus.ACTIVE
            )
        )
        return result.scalars().all()
    
    async def find_active_reminders(self) -> List[ReminderModel]:
        """Find all active reminders"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.status == ReminderStatus.ACTIVE)
        )
        return result.scalars().all()
    
    async def find_by_user_and_guild(self, user_id: str, guild_id: str) -> List[ReminderModel]:
        """Find reminders for a specific user in a specific guild"""
        result = await self.session.execute(
            select(ReminderModel).where(
                ReminderModel.user_id == user_id,
                ReminderModel.guild_id == guild_id
            )
        )
        return result.scalars().all()
    
    async def count_by_user_id(self, user_id: str) -> int:
        """Count reminders for a specific user"""
        result = await self.session.execute(
            select(func.count(ReminderModel.id)).where(ReminderModel.user_id == user_id)
        )
        return result.scalar()
    
    async def find_requiring_validation(self) -> List[ReminderModel]:
        """Find reminders that require validation"""
        result = await self.session.execute(
            select(ReminderModel).where(
                ReminderModel.validation_required == True,
                ReminderModel.status == ReminderStatus.ACTIVE
            )
        )
        return result.scalars().all()
    
    async def update_status(self, reminder_id: int, status: ReminderStatus) -> bool:
        """Update the status of a reminder"""
        reminder = await self.session.get(ReminderModel, reminder_id)
        if reminder:
            reminder.status = status
            reminder.updated_at = datetime.utcnow()
            await self.session.commit()
            return True
        return False
    
    async def update_next_execution(self, reminder_id: int, next_execution: datetime) -> bool:
        """Update the next execution time of a reminder"""
        reminder = await self.session.get(ReminderModel, reminder_id)
        if reminder:
            reminder.next_execution = next_execution
            reminder.updated_at = datetime.utcnow()
            await self.session.commit()
            return True
        return False
    
    async def find_by_frequency(self, frequency: FrequencyEnum) -> List[ReminderModel]:
        """Find reminders by frequency"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.frequency == frequency)
        )
        return result.scalars().all()
    
    async def find_by_status(self, status: ReminderStatus) -> List[ReminderModel]:
        """Find reminders by status"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.status == status)
        )
        return result.scalars().all()
    
    async def find_by_channel_id(self, channel_id: str) -> List[ReminderModel]:
        """Find reminders for a specific channel"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.channel_id == channel_id)
        )
        return result.scalars().all()
    
    async def find_created_by(self, creator_user_id: str) -> List[ReminderModel]:
        """Find reminders created by a specific user"""
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.created_by == creator_user_id)
        )
        return result.scalars().all()
    
    async def bulk_update_status(self, reminder_ids: List[int], status: ReminderStatus) -> int:
        """Update status for multiple reminders"""
        result = await self.session.execute(
            update(ReminderModel)
            .where(ReminderModel.id.in_(reminder_ids))
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
    
    async def cleanup_completed_reminders(self, cutoff_date: datetime) -> int:
        """Delete completed reminders older than cutoff date"""
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(ReminderModel).where(
                ReminderModel.status == ReminderStatus.COMPLETED,
                ReminderModel.updated_at < cutoff_date
            )
        )
        await self.session.commit()
        return result.rowcount
    
    async def find_by_guild_id(self, guild_id: str) -> List[ReminderModel]:
        """Find all reminders for a specific guild"""
        from sqlalchemy import select
        
        result = await self.session.execute(
            select(ReminderModel).where(ReminderModel.guild_id == guild_id)
        )
        return result.scalars().all()
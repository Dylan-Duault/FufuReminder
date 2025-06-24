from abc import ABC
from typing import TypeVar, Generic, List, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import DeclarativeBase

T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T], ABC):
    """Base repository providing common CRUD operations"""
    
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    async def create(self, entity: T) -> T:
        """Create a new entity in the database"""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get an entity by its ID"""
        return await self.session.get(self.model_class, entity_id)
    
    async def update(self, entity: T) -> T:
        """Update an existing entity"""
        merged_entity = await self.session.merge(entity)
        await self.session.commit()
        return merged_entity
    
    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by its ID"""
        entity = await self.session.get(self.model_class, entity_id)
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False
    
    async def exists(self, entity_id: int) -> bool:
        """Check if an entity exists by its ID"""
        entity = await self.session.get(self.model_class, entity_id)
        return entity is not None
    
    async def list_all(self) -> List[T]:
        """Get all entities"""
        result = await self.session.execute(
            select(self.model_class)
        )
        return result.scalars().all()
    
    async def count(self) -> int:
        """Count all entities"""
        result = await self.session.execute(
            select(func.count(self.model_class.id))
        )
        return result.scalar()
    
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities in bulk"""
        self.session.add_all(entities)
        await self.session.commit()
        for entity in entities:
            await self.session.refresh(entity)
        return entities
    
    async def bulk_delete(self, entity_ids: List[int]) -> int:
        """Delete multiple entities by their IDs"""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id.in_(entity_ids))
        )
        await self.session.commit()
        return result.rowcount
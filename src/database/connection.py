import aiosqlite
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from ..config.settings import get_settings
from ..config.logging import get_logger
from .models import Base

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connection and session lifecycle"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or get_settings().database_url
        self.engine = None
        self.session_factory = None
        
    async def initialize(self) -> None:
        """Initialize database connection and create tables"""
        logger.info("Initializing database connection", database_url=self.database_url)
        
        # Ensure database directory exists for SQLite
        if self.database_url.startswith("sqlite"):
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
    
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.session_factory()
    
    async def close(self) -> None:
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()
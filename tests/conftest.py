import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base
from src.database.connection import DatabaseManager
from src.models.enums import FrequencyEnum, ValidationStatus, ReminderStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_database():
    """Create a test database for each test"""
    # Use in-memory SQLite for fast testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield session_factory
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_database):
    """Create a database session for each test"""
    async with test_database() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_discord_client():
    """Mock Discord client for testing"""
    client = AsyncMock()
    client.get_guild.return_value = MagicMock(id=12345)
    client.get_channel.return_value = MagicMock(id=67890)
    client.get_user.return_value = MagicMock(id=11111, mention="<@11111>")
    return client


@pytest.fixture
def mock_discord_interaction():
    """Mock Discord interaction for testing commands"""
    interaction = AsyncMock()
    interaction.user = MagicMock(id=11111, mention="<@11111>")
    interaction.guild = MagicMock(id=12345)
    interaction.channel = MagicMock(id=67890)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


@pytest.fixture
def sample_reminder_data():
    """Sample reminder data for testing"""
    return {
        "user_id": "123456789",
        "guild_id": "987654321",
        "channel_id": "111222333",
        "frequency": FrequencyEnum.DAILY,
        "message_content": "Don't forget to drink water!",
        "next_execution": datetime.utcnow() + timedelta(days=1),
        "validation_required": True,
        "created_by": "admin_user_id"
    }


@pytest.fixture
def sample_validation_data():
    """Sample validation data for testing"""
    return {
        "reminder_id": 1,
        "message_id": "444555666",
        "status": ValidationStatus.PENDING,
        "expires_at": datetime.utcnow() + timedelta(hours=48)
    }
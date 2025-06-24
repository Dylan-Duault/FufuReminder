import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.base import BaseRepository
from src.database.models import ReminderModel


class TestRepository(BaseRepository[ReminderModel]):
    """Test implementation of BaseRepository for testing"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReminderModel)


class TestBaseRepository:
    """Test cases for the BaseRepository abstract class"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def repository(self, mock_session):
        """Create a test repository instance"""
        return TestRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_create_new_entity(self, repository, mock_session):
        """Test creating a new entity"""
        # Arrange
        test_model = ReminderModel(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency="daily",
            message_content="Test reminder",
            created_by="admin_123"
        )
        
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None
        
        # Act
        result = await repository.create(test_model)
        
        # Assert
        assert result == test_model
        mock_session.add.assert_called_once_with(test_model)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(test_model)
    
    @pytest.mark.asyncio
    async def test_get_by_id_existing(self, repository, mock_session):
        """Test getting an entity by ID when it exists"""
        # Arrange
        test_id = 1
        expected_model = ReminderModel(id=test_id)
        mock_session.get.return_value = expected_model
        
        # Act
        result = await repository.get_by_id(test_id)
        
        # Assert
        assert result == expected_model
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test getting an entity by ID when it doesn't exist"""
        # Arrange
        test_id = 999
        mock_session.get.return_value = None
        
        # Act
        result = await repository.get_by_id(test_id)
        
        # Assert
        assert result is None
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
    
    @pytest.mark.asyncio
    async def test_update_existing_entity(self, repository, mock_session):
        """Test updating an existing entity"""
        # Arrange
        test_model = ReminderModel(
            id=1,
            user_id="123456789",
            message_content="Updated content"
        )
        
        mock_session.merge.return_value = test_model
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.update(test_model)
        
        # Assert
        assert result == test_model
        mock_session.merge.assert_called_once_with(test_model)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_existing_entity(self, repository, mock_session):
        """Test deleting an existing entity"""
        # Arrange
        test_id = 1
        test_model = ReminderModel(id=test_id)
        mock_session.get.return_value = test_model
        mock_session.delete.return_value = None
        mock_session.commit.return_value = None
        
        # Act
        result = await repository.delete(test_id)
        
        # Assert
        assert result is True
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
        mock_session.delete.assert_called_once_with(test_model)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_non_existing_entity(self, repository, mock_session):
        """Test deleting a non-existing entity"""
        # Arrange
        test_id = 999
        mock_session.get.return_value = None
        
        # Act
        result = await repository.delete(test_id)
        
        # Assert
        assert result is False
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_exists_when_entity_exists(self, repository, mock_session):
        """Test checking existence when entity exists"""
        # Arrange
        test_id = 1
        mock_session.get.return_value = ReminderModel(id=test_id)
        
        # Act
        result = await repository.exists(test_id)
        
        # Assert
        assert result is True
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
    
    @pytest.mark.asyncio
    async def test_exists_when_entity_does_not_exist(self, repository, mock_session):
        """Test checking existence when entity doesn't exist"""
        # Arrange
        test_id = 999
        mock_session.get.return_value = None
        
        # Act
        result = await repository.exists(test_id)
        
        # Assert
        assert result is False
        mock_session.get.assert_called_once_with(ReminderModel, test_id)
    
    @pytest.mark.asyncio
    async def test_list_all_entities(self, repository, mock_session):
        """Test listing all entities"""
        # Arrange
        expected_models = [
            ReminderModel(id=1),
            ReminderModel(id=2),
            ReminderModel(id=3)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_models
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.list_all()
        
        # Assert
        assert result == expected_models
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_all_entities(self, repository, mock_session):
        """Test counting all entities"""
        # Arrange
        expected_count = 5
        mock_result = MagicMock()
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await repository.count()
        
        # Assert
        assert result == expected_count
        mock_session.execute.assert_called_once()
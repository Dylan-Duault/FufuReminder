import pytest
from datetime import datetime, timedelta
from src.repositories.reminder_repo import ReminderRepository
from src.repositories.validation_repo import ValidationRepository
from src.database.models import ReminderModel, ValidationModel
from src.models.enums import ReminderStatus, ValidationStatus, FrequencyEnum


class TestRepositoryIntegration:
    """Integration tests for repositories with real database"""
    
    @pytest.mark.asyncio
    async def test_reminder_repository_crud_operations(self, db_session):
        """Test complete CRUD operations for reminder repository"""
        repo = ReminderRepository(db_session)
        
        # Create
        reminder_data = ReminderModel(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test integration reminder",
            validation_required=True,
            status=ReminderStatus.ACTIVE,
            created_by="admin_123",
            next_execution=datetime.utcnow() + timedelta(days=1)
        )
        
        created_reminder = await repo.create(reminder_data)
        assert created_reminder.id is not None
        assert created_reminder.user_id == "123456789"
        
        # Read
        retrieved_reminder = await repo.get_by_id(created_reminder.id)
        assert retrieved_reminder is not None
        assert retrieved_reminder.message_content == "Test integration reminder"
        
        # Update
        retrieved_reminder.message_content = "Updated message"
        updated_reminder = await repo.update(retrieved_reminder)
        assert updated_reminder.message_content == "Updated message"
        
        # Query operations
        user_reminders = await repo.find_by_user_id("123456789")
        assert len(user_reminders) == 1
        assert user_reminders[0].id == created_reminder.id
        
        guild_reminders = await repo.find_by_guild_id("987654321")
        assert len(guild_reminders) == 1
        
        active_reminders = await repo.find_active_reminders()
        assert len(active_reminders) == 1
        
        # Update status
        result = await repo.update_status(created_reminder.id, ReminderStatus.PAUSED)
        assert result is True
        
        updated_reminder = await repo.get_by_id(created_reminder.id)
        assert updated_reminder.status == ReminderStatus.PAUSED
        
        # Delete
        deleted = await repo.delete(created_reminder.id)
        assert deleted is True
        
        # Verify deletion
        deleted_reminder = await repo.get_by_id(created_reminder.id)
        assert deleted_reminder is None
    
    @pytest.mark.asyncio
    async def test_validation_repository_crud_operations(self, db_session):
        """Test complete CRUD operations for validation repository"""
        repo = ValidationRepository(db_session)
        
        # Create
        validation_data = ValidationModel(
            reminder_id=1,
            message_id="444555666",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
        
        created_validation = await repo.create(validation_data)
        assert created_validation.id is not None
        assert created_validation.reminder_id == 1
        
        # Read
        retrieved_validation = await repo.get_by_id(created_validation.id)
        assert retrieved_validation is not None
        assert retrieved_validation.message_id == "444555666"
        
        # Query operations
        reminder_validations = await repo.find_by_reminder_id(1)
        assert len(reminder_validations) == 1
        
        message_validation = await repo.find_by_message_id("444555666")
        assert message_validation is not None
        assert message_validation.id == created_validation.id
        
        pending_validations = await repo.find_pending_validations()
        assert len(pending_validations) == 1
        
        # Mark as validated
        validation_time = datetime.utcnow()
        result = await repo.mark_as_validated(created_validation.id, validation_time)
        assert result is True
        
        updated_validation = await repo.get_by_id(created_validation.id)
        assert updated_validation.status == ValidationStatus.VALIDATED
        assert updated_validation.validated_at == validation_time
        
        # Delete
        deleted = await repo.delete(created_validation.id)
        assert deleted is True
        
        # Verify deletion
        deleted_validation = await repo.get_by_id(created_validation.id)
        assert deleted_validation is None
    
    @pytest.mark.asyncio
    async def test_reminder_due_functionality(self, db_session):
        """Test finding due reminders functionality"""
        repo = ReminderRepository(db_session)
        
        # Create past due reminder
        past_reminder = ReminderModel(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.HOURLY,
            message_content="Past due reminder",
            status=ReminderStatus.ACTIVE,
            created_by="admin_123",
            next_execution=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Create future reminder
        future_reminder = ReminderModel(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Future reminder",
            status=ReminderStatus.ACTIVE,
            created_by="admin_123",
            next_execution=datetime.utcnow() + timedelta(days=1)
        )
        
        await repo.create(past_reminder)
        await repo.create(future_reminder)
        
        # Test finding due reminders
        due_reminders = await repo.find_due_reminders()
        assert len(due_reminders) == 1
        assert due_reminders[0].message_content == "Past due reminder"
        
        # Test updating next execution
        new_execution = datetime.utcnow() + timedelta(hours=1)
        result = await repo.update_next_execution(past_reminder.id, new_execution)
        assert result is True
        
        updated_reminder = await repo.get_by_id(past_reminder.id)
        assert updated_reminder.next_execution == new_execution
        
        # Now should have no due reminders
        due_reminders = await repo.find_due_reminders()
        assert len(due_reminders) == 0
    
    @pytest.mark.asyncio
    async def test_validation_expiry_functionality(self, db_session):
        """Test validation expiry functionality"""
        repo = ValidationRepository(db_session)
        
        # Create expired validation
        expired_validation = ValidationModel(
            reminder_id=1,
            message_id="expired_msg",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Create active validation
        active_validation = ValidationModel(
            reminder_id=2,
            message_id="active_msg",
            status=ValidationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        await repo.create(expired_validation)
        await repo.create(active_validation)
        
        # Test finding expired validations
        expired_validations = await repo.find_expired_validations()
        assert len(expired_validations) == 1
        assert expired_validations[0].message_id == "expired_msg"
        
        # Mark expired validation as expired
        result = await repo.mark_as_expired(expired_validation.id)
        assert result is True
        
        updated_validation = await repo.get_by_id(expired_validation.id)
        assert updated_validation.status == ValidationStatus.EXPIRED
        
        # Test cleanup
        cutoff_time = datetime.utcnow() + timedelta(hours=1)
        cleaned_count = await repo.cleanup_expired_validations(cutoff_time)
        assert cleaned_count == 1  # Should delete the expired validation
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, db_session):
        """Test bulk operations"""
        repo = ReminderRepository(db_session)
        
        # Create multiple reminders
        reminders = []
        for i in range(3):
            reminder = ReminderModel(
                user_id=f"user_{i}",
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content=f"Bulk reminder {i}",
                status=ReminderStatus.ACTIVE,
                created_by="admin_123",
                next_execution=datetime.utcnow() + timedelta(days=i+1)
            )
            reminders.append(reminder)
        
        # Bulk create
        created_reminders = await repo.bulk_create(reminders)
        assert len(created_reminders) == 3
        
        # Verify all have IDs
        reminder_ids = [r.id for r in created_reminders]
        assert all(id is not None for id in reminder_ids)
        
        # Bulk update status
        updated_count = await repo.bulk_update_status(reminder_ids, ReminderStatus.PAUSED)
        assert updated_count == 3
        
        # Verify status updates
        for reminder_id in reminder_ids:
            reminder = await repo.get_by_id(reminder_id)
            assert reminder.status == ReminderStatus.PAUSED
        
        # Bulk delete
        deleted_count = await repo.bulk_delete(reminder_ids)
        assert deleted_count == 3
        
        # Verify deletions
        for reminder_id in reminder_ids:
            reminder = await repo.get_by_id(reminder_id)
            assert reminder is None
    
    @pytest.mark.asyncio
    async def test_count_operations(self, db_session):
        """Test count operations"""
        reminder_repo = ReminderRepository(db_session)
        validation_repo = ValidationRepository(db_session)
        
        # Create reminders for specific user
        user_id = "count_test_user"
        for i in range(5):
            reminder = ReminderModel(
                user_id=user_id,
                guild_id="987654321",
                channel_id="111222333",
                frequency=FrequencyEnum.DAILY,
                message_content=f"Count test reminder {i}",
                status=ReminderStatus.ACTIVE,
                created_by="admin_123",
                next_execution=datetime.utcnow() + timedelta(days=i+1)
            )
            created_reminder = await reminder_repo.create(reminder)
            
            # Create validation for each reminder
            validation = ValidationModel(
                reminder_id=created_reminder.id,
                message_id=f"count_msg_{i}",
                status=ValidationStatus.PENDING if i < 3 else ValidationStatus.VALIDATED,
                expires_at=datetime.utcnow() + timedelta(hours=48)
            )
            await validation_repo.create(validation)
        
        # Test counts
        user_reminder_count = await reminder_repo.count_by_user_id(user_id)
        assert user_reminder_count == 5
        
        total_reminders = await reminder_repo.count()
        assert total_reminders >= 5
        
        pending_validations = await validation_repo.count_by_status(ValidationStatus.PENDING)
        assert pending_validations == 3
        
        validated_validations = await validation_repo.count_by_status(ValidationStatus.VALIDATED)
        assert validated_validations == 2
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.scheduler_service import SchedulerService
from src.models.reminder import Reminder
from src.models.enums import FrequencyEnum, ReminderStatus


class TestSchedulerService:
    """Test cases for the SchedulerService"""
    
    @pytest.fixture
    def mock_reminder_service(self):
        """Create a mock reminder service"""
        service = AsyncMock()
        service.process_due_reminders = AsyncMock(return_value=3)
        return service
    
    @pytest.fixture
    def scheduler_service(self, mock_reminder_service):
        """Create a scheduler service instance"""
        return SchedulerService(reminder_service=mock_reminder_service)
    
    @pytest.fixture
    def sample_reminder(self):
        """Create a sample reminder for testing"""
        return Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Test reminder",
            created_by="admin_123",
            reminder_id=1
        )
    
    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler_service, mock_reminder_service):
        """Test starting the scheduler"""
        # Act
        await scheduler_service.start()
        
        # Assert
        assert scheduler_service.is_running is True
        assert scheduler_service._task is not None
        assert not scheduler_service._task.done()
        
        # Cleanup
        await scheduler_service.stop()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler_service):
        """Test stopping the scheduler"""
        # Arrange
        await scheduler_service.start()
        assert scheduler_service.is_running is True
        
        # Act
        await scheduler_service.stop()
        
        # Assert
        assert scheduler_service.is_running is False
        assert scheduler_service._task is None
    
    @pytest.mark.asyncio
    async def test_schedule_reminder(self, scheduler_service, sample_reminder):
        """Test scheduling a reminder"""
        # Act
        await scheduler_service.schedule_reminder(sample_reminder)
        
        # Assert
        assert sample_reminder.id in scheduler_service._scheduled_reminders
        task_info = scheduler_service._scheduled_reminders[sample_reminder.id]
        assert task_info["reminder"] == sample_reminder
        assert task_info["task"] is not None
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_already_scheduled(self, scheduler_service, sample_reminder):
        """Test scheduling a reminder that's already scheduled"""
        # Arrange
        await scheduler_service.schedule_reminder(sample_reminder)
        original_task = scheduler_service._scheduled_reminders[sample_reminder.id]["task"]
        
        # Act
        await scheduler_service.schedule_reminder(sample_reminder)
        
        # Wait a moment for cancellation to process
        await asyncio.sleep(0.01)
        
        # Assert - should replace the existing task
        assert sample_reminder.id in scheduler_service._scheduled_reminders
        new_task = scheduler_service._scheduled_reminders[sample_reminder.id]["task"]
        assert new_task != original_task
        assert original_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_unschedule_reminder(self, scheduler_service, sample_reminder):
        """Test unscheduling a reminder"""
        # Arrange
        await scheduler_service.schedule_reminder(sample_reminder)
        assert sample_reminder.id in scheduler_service._scheduled_reminders
        
        # Act
        result = await scheduler_service.unschedule_reminder(sample_reminder.id)
        
        # Assert
        assert result is True
        assert sample_reminder.id not in scheduler_service._scheduled_reminders
    
    @pytest.mark.asyncio
    async def test_unschedule_reminder_not_found(self, scheduler_service):
        """Test unscheduling a reminder that doesn't exist"""
        # Act
        result = await scheduler_service.unschedule_reminder(999)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reschedule_reminder(self, scheduler_service, sample_reminder):
        """Test rescheduling a reminder"""
        # Arrange
        await scheduler_service.schedule_reminder(sample_reminder)
        original_task = scheduler_service._scheduled_reminders[sample_reminder.id]["task"]
        
        new_execution_time = datetime.utcnow() + timedelta(hours=2)
        sample_reminder.next_execution = new_execution_time
        
        # Act
        await scheduler_service.reschedule_reminder(sample_reminder)
        
        # Wait a moment for cancellation to process
        await asyncio.sleep(0.01)
        
        # Assert
        assert sample_reminder.id in scheduler_service._scheduled_reminders
        new_task = scheduler_service._scheduled_reminders[sample_reminder.id]["task"]
        assert new_task != original_task
        assert original_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_reschedule_reminder_not_scheduled(self, scheduler_service, sample_reminder):
        """Test rescheduling a reminder that wasn't scheduled"""
        # Act
        await scheduler_service.reschedule_reminder(sample_reminder)
        
        # Assert - should just schedule it
        assert sample_reminder.id in scheduler_service._scheduled_reminders
    
    @pytest.mark.asyncio
    async def test_get_scheduled_count(self, scheduler_service, sample_reminder):
        """Test getting count of scheduled reminders"""
        # Arrange
        assert scheduler_service.get_scheduled_count() == 0
        
        # Act
        await scheduler_service.schedule_reminder(sample_reminder)
        
        # Assert
        assert scheduler_service.get_scheduled_count() == 1
    
    @pytest.mark.asyncio
    async def test_is_reminder_scheduled(self, scheduler_service, sample_reminder):
        """Test checking if reminder is scheduled"""
        # Arrange
        assert scheduler_service.is_reminder_scheduled(sample_reminder.id) is False
        
        # Act
        await scheduler_service.schedule_reminder(sample_reminder)
        
        # Assert
        assert scheduler_service.is_reminder_scheduled(sample_reminder.id) is True
    
    @pytest.mark.asyncio
    async def test_clear_all_scheduled(self, scheduler_service, sample_reminder):
        """Test clearing all scheduled reminders"""
        # Arrange
        await scheduler_service.schedule_reminder(sample_reminder)
        
        reminder2 = Reminder(
            user_id="987654321",
            guild_id="123456789",
            channel_id="111222333",
            frequency=FrequencyEnum.WEEKLY,
            message_content="Another reminder",
            created_by="admin_456",
            reminder_id=2
        )
        await scheduler_service.schedule_reminder(reminder2)
        
        assert scheduler_service.get_scheduled_count() == 2
        
        # Act
        cleared_count = await scheduler_service.clear_all_scheduled()
        
        # Assert
        assert cleared_count == 2
        assert scheduler_service.get_scheduled_count() == 0
    
    @pytest.mark.asyncio
    async def test_reminder_execution_flow(self, scheduler_service, sample_reminder):
        """Test the reminder execution flow"""
        # Arrange
        with patch.object(scheduler_service, '_execute_reminder') as mock_execute:
            mock_execute.return_value = AsyncMock()
            
            # Set execution time to very soon
            sample_reminder.next_execution = datetime.utcnow() + timedelta(seconds=0.1)
            
            # Act
            await scheduler_service.schedule_reminder(sample_reminder)
            
            # Wait for execution
            await asyncio.sleep(0.2)
            
            # Assert
            mock_execute.assert_called_once_with(sample_reminder)
    
    @pytest.mark.asyncio
    async def test_scheduler_main_loop(self, scheduler_service, mock_reminder_service):
        """Test the main scheduler loop"""
        # Arrange
        scheduler_service._check_interval = 0.1  # Very short interval for testing
        
        # Act
        await scheduler_service.start()
        
        # Wait for a couple of cycles
        await asyncio.sleep(0.3)
        
        await scheduler_service.stop()
        
        # Assert - should have called process_due_reminders multiple times
        assert mock_reminder_service.process_due_reminders.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_handle_scheduler_error(self, scheduler_service, mock_reminder_service):
        """Test scheduler error handling"""
        # Arrange
        mock_reminder_service.process_due_reminders.side_effect = Exception("Test error")
        scheduler_service._check_interval = 0.1
        
        # Act
        await scheduler_service.start()
        await asyncio.sleep(0.2)
        await scheduler_service.stop()
        
        # Assert - should continue running despite errors
        assert scheduler_service.is_running is False  # Stopped by us
        assert mock_reminder_service.process_due_reminders.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_next_execution_times(self, scheduler_service):
        """Test getting next execution times for scheduled reminders"""
        # Arrange
        reminder1 = Reminder(
            user_id="123456789",
            guild_id="987654321",
            channel_id="111222333",
            frequency=FrequencyEnum.DAILY,
            message_content="Daily reminder",
            created_by="admin_123",
            reminder_id=1
        )
        reminder1.next_execution = datetime.utcnow() + timedelta(hours=1)
        
        reminder2 = Reminder(
            user_id="987654321",
            guild_id="123456789",
            channel_id="111222333",
            frequency=FrequencyEnum.WEEKLY,
            message_content="Weekly reminder",
            created_by="admin_456",
            reminder_id=2
        )
        reminder2.next_execution = datetime.utcnow() + timedelta(days=1)
        
        await scheduler_service.schedule_reminder(reminder1)
        await scheduler_service.schedule_reminder(reminder2)
        
        # Act
        execution_times = scheduler_service.get_next_execution_times()
        
        # Assert
        assert len(execution_times) == 2
        assert 1 in execution_times
        assert 2 in execution_times
        assert execution_times[1] == reminder1.next_execution
        assert execution_times[2] == reminder2.next_execution
    
    @pytest.mark.asyncio
    async def test_update_reminder_schedule(self, scheduler_service, sample_reminder):
        """Test updating a reminder's schedule"""
        # Arrange
        await scheduler_service.schedule_reminder(sample_reminder)
        original_execution = sample_reminder.next_execution
        
        # Act
        new_execution = datetime.utcnow() + timedelta(hours=5)
        await scheduler_service.update_reminder_schedule(sample_reminder.id, new_execution)
        
        # Assert
        task_info = scheduler_service._scheduled_reminders[sample_reminder.id]
        assert task_info["reminder"].next_execution == new_execution
        assert task_info["reminder"].next_execution != original_execution
    
    @pytest.mark.asyncio
    async def test_update_reminder_schedule_not_found(self, scheduler_service):
        """Test updating schedule for non-existent reminder"""
        # Act
        new_execution = datetime.utcnow() + timedelta(hours=5)
        result = await scheduler_service.update_reminder_schedule(999, new_execution)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_scheduler_shutdown_cleanup(self, scheduler_service, sample_reminder):
        """Test that scheduler properly cleans up on shutdown"""
        # Arrange
        await scheduler_service.start()
        await scheduler_service.schedule_reminder(sample_reminder)
        
        assert scheduler_service.get_scheduled_count() == 1
        assert scheduler_service.is_running is True
        
        # Act
        await scheduler_service.shutdown()
        
        # Assert
        assert scheduler_service.is_running is False
        assert scheduler_service.get_scheduled_count() == 0
        assert scheduler_service._task is None
    
    @pytest.mark.asyncio
    async def test_scheduler_with_past_due_reminder(self, scheduler_service, sample_reminder):
        """Test scheduling a reminder that's already past due"""
        # Arrange
        sample_reminder.next_execution = datetime.utcnow() - timedelta(hours=1)  # Past due
        
        with patch.object(scheduler_service, '_execute_reminder') as mock_execute:
            mock_execute.return_value = AsyncMock()
            
            # Act
            await scheduler_service.schedule_reminder(sample_reminder)
            
            # Wait a moment for immediate execution
            await asyncio.sleep(0.1)
            
            # Assert
            mock_execute.assert_called_once_with(sample_reminder)
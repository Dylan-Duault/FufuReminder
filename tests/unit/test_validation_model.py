import pytest
from datetime import datetime, timedelta
from src.models.validation import Validation
from src.models.enums import ValidationStatus


class TestValidation:
    """Test cases for the Validation domain model"""
    
    def test_create_validation_with_required_fields(self):
        """Test creating a validation with all required fields"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        assert validation.reminder_id == 1
        assert validation.expires_at == expires_at
        assert validation.status == ValidationStatus.PENDING
        assert validation.message_id is None
        assert validation.validated_at is None
        assert isinstance(validation.created_at, datetime)
    
    def test_create_validation_with_message_id(self):
        """Test creating a validation with message ID"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            message_id="123456789",
            expires_at=expires_at
        )
        
        assert validation.message_id == "123456789"
    
    def test_mark_as_validated(self):
        """Test marking validation as validated"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        validation.mark_as_validated()
        
        assert validation.status == ValidationStatus.VALIDATED
        assert validation.validated_at is not None
        assert isinstance(validation.validated_at, datetime)
    
    def test_mark_as_expired(self):
        """Test marking validation as expired"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        validation.mark_as_expired()
        
        assert validation.status == ValidationStatus.EXPIRED
    
    def test_mark_as_failed(self):
        """Test marking validation as failed"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        validation.mark_as_failed()
        
        assert validation.status == ValidationStatus.FAILED
    
    def test_is_expired_when_past_expiry(self):
        """Test checking if validation is expired when past expiry time"""
        past_expiry = datetime.utcnow() - timedelta(hours=1)
        
        validation = Validation(
            reminder_id=1,
            expires_at=past_expiry
        )
        
        assert validation.is_expired() is True
    
    def test_is_not_expired_when_before_expiry(self):
        """Test checking if validation is not expired when before expiry time"""
        future_expiry = datetime.utcnow() + timedelta(hours=1)
        
        validation = Validation(
            reminder_id=1,
            expires_at=future_expiry
        )
        
        assert validation.is_expired() is False
    
    def test_time_until_expiry_positive(self):
        """Test getting positive time until expiry"""
        future_expiry = datetime.utcnow() + timedelta(hours=2)
        
        validation = Validation(
            reminder_id=1,
            expires_at=future_expiry
        )
        
        time_until = validation.time_until_expiry()
        assert time_until.total_seconds() > 0
        assert 1.9 <= time_until.total_seconds() / 3600 <= 2.1  # ~2 hours
    
    def test_time_until_expiry_negative(self):
        """Test getting negative time until expiry for expired validation"""
        past_expiry = datetime.utcnow() - timedelta(hours=1)
        
        validation = Validation(
            reminder_id=1,
            expires_at=past_expiry
        )
        
        time_until = validation.time_until_expiry()
        assert time_until.total_seconds() < 0
    
    def test_validation_str_representation(self):
        """Test string representation of validation"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        str_repr = str(validation)
        assert "1" in str_repr  # reminder_id
        assert "pending" in str_repr.lower()
    
    def test_cannot_validate_expired_validation(self):
        """Test that expired validation cannot be marked as validated"""
        past_expiry = datetime.utcnow() - timedelta(hours=1)
        
        validation = Validation(
            reminder_id=1,
            expires_at=past_expiry
        )
        
        with pytest.raises(ValueError, match="Cannot validate expired validation"):
            validation.mark_as_validated()
    
    def test_cannot_validate_already_validated(self):
        """Test that already validated validation cannot be validated again"""
        expires_at = datetime.utcnow() + timedelta(hours=48)
        
        validation = Validation(
            reminder_id=1,
            expires_at=expires_at
        )
        
        validation.mark_as_validated()
        
        with pytest.raises(ValueError, match="Validation already completed"):
            validation.mark_as_validated()
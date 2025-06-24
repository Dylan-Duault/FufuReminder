from datetime import datetime, timedelta
from typing import Optional
from .enums import ValidationStatus


class Validation:
    """Domain model for reminder validations"""
    
    def __init__(
        self,
        reminder_id: int,
        expires_at: datetime,
        validation_id: Optional[int] = None,
        message_id: Optional[str] = None,
        status: ValidationStatus = ValidationStatus.PENDING,
        created_at: Optional[datetime] = None,
        validated_at: Optional[datetime] = None
    ):
        self.id = validation_id
        self.reminder_id = reminder_id
        self.message_id = message_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.validated_at = validated_at
        self.expires_at = expires_at
    
    def mark_as_validated(self) -> None:
        """Mark the validation as successfully validated"""
        if self.is_expired():
            raise ValueError("Cannot validate expired validation")
        
        if self.status in [ValidationStatus.VALIDATED, ValidationStatus.FAILED]:
            raise ValueError("Validation already completed")
        
        self.status = ValidationStatus.VALIDATED
        self.validated_at = datetime.utcnow()
    
    def mark_as_expired(self) -> None:
        """Mark the validation as expired"""
        self.status = ValidationStatus.EXPIRED
    
    def mark_as_failed(self) -> None:
        """Mark the validation as failed"""
        self.status = ValidationStatus.FAILED
    
    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """Check if the validation has expired"""
        check_time = current_time or datetime.utcnow()
        return check_time >= self.expires_at
    
    def time_until_expiry(self, current_time: Optional[datetime] = None) -> timedelta:
        """Get the time remaining until expiry (negative if expired)"""
        check_time = current_time or datetime.utcnow()
        return self.expires_at - check_time
    
    def is_pending(self) -> bool:
        """Check if the validation is still pending"""
        return self.status == ValidationStatus.PENDING and not self.is_expired()
    
    def is_completed(self) -> bool:
        """Check if the validation is completed (validated, expired, or failed)"""
        return self.status in [ValidationStatus.VALIDATED, ValidationStatus.EXPIRED, ValidationStatus.FAILED]
    
    def __str__(self) -> str:
        return f"Validation(id={self.id}, reminder_id={self.reminder_id}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return (f"Validation(id={self.id}, reminder_id={self.reminder_id}, "
                f"status={self.status.value}, expires_at={self.expires_at})")
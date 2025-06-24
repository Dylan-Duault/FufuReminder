from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from ..models.enums import FrequencyEnum, ValidationStatus, ReminderStatus

Base = declarative_base()


class ReminderModel(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), nullable=False, index=True)
    guild_id = Column(String(20), nullable=False, index=True)
    channel_id = Column(String(20), nullable=False)
    frequency = Column(Enum(FrequencyEnum), nullable=False)
    message_content = Column(Text, nullable=False)
    next_execution = Column(DateTime, nullable=False, index=True)
    validation_required = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(ReminderStatus), nullable=False, default=ReminderStatus.ACTIVE)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(20), nullable=False)
    
    # Relationships
    validations = relationship("ValidationModel", back_populates="reminder", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ReminderModel(id={self.id}, user_id={self.user_id}, frequency={self.frequency})>"


class ValidationModel(Base):
    __tablename__ = 'validations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reminder_id = Column(Integer, ForeignKey('reminders.id'), nullable=False, index=True)
    message_id = Column(String(20), nullable=True)
    status = Column(Enum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    reminder = relationship("ReminderModel", back_populates="validations")
    
    def __repr__(self) -> str:
        return f"<ValidationModel(id={self.id}, reminder_id={self.reminder_id}, status={self.status})>"
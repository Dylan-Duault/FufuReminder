from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import json


class BotConfig(BaseModel):
    command_prefix: str = "/"
    description: str = "FufuRemind - Enterprise Discord Reminder Bot"
    status: str = "Managing reminders"
    activity_type: str = "watching"


class FeatureConfig(BaseModel):
    auto_kick_enabled: bool = True
    reaction_validation: bool = True
    reminder_persistence: bool = True


class LimitsConfig(BaseModel):
    max_reminders_per_user: int = 10
    max_message_length: int = 2000
    command_cooldown_seconds: int = 5


class SchedulingConfig(BaseModel):
    check_interval_minutes: float = 0.5  # 30 seconds for spam reminders
    max_concurrent_reminders: int = 100


class Settings(BaseSettings):
    # Discord Configuration
    discord_token: str = Field(..., env="DISCORD_TOKEN")
    discord_guild_id: Optional[int] = Field(None, env="DISCORD_GUILD_ID")
    reminder_channel_id: Optional[int] = Field(None, env="REMINDER_CHANNEL_ID")
    command_prefix: str = Field("!", env="COMMAND_PREFIX")
    
    # Admin Configuration  
    admin_role_ids: List[int] = Field(default=[], env="ADMIN_ROLE_IDS")
    
    # Validation Configuration
    validation_timeout_hours: int = Field(48, env="VALIDATION_TIMEOUT_HOURS")
    validation_emoji: str = Field("✅", env="VALIDATION_EMOJI")
    
    # Database Configuration
    database_url: str = Field("sqlite+aiosqlite:///data/reminders.db", env="DATABASE_URL")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # Configuration objects
    bot: BotConfig = BotConfig()
    features: FeatureConfig = FeatureConfig()
    limits: LimitsConfig = LimitsConfig()
    scheduling: SchedulingConfig = SchedulingConfig()
    
    @field_validator("admin_role_ids", mode="before")
    @classmethod
    def parse_admin_role_ids(cls, v):
        if isinstance(v, str):
            return [int(role_id.strip()) for role_id in v.split(",") if role_id.strip()]
        elif isinstance(v, int):
            return [v]  # Convert single int to list
        return v
    
    @field_validator("validation_timeout_hours")
    @classmethod
    def validate_timeout_hours(cls, v):
        if v < 1 or v > 168:  # 1 hour to 1 week
            raise ValueError("Validation timeout must be between 1 and 168 hours")
        return v
    
    model_config = {
        "env_file": Path(__file__).parent.parent.parent / "config" / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
        
    @classmethod
    def load_from_config_file(cls, config_file: Path = Path("config/config.json")):
        """Load configuration from environment and optionally from JSON file"""
        # First create settings with environment variables (this loads .env file automatically)
        settings = cls()
        
        # Then optionally override with JSON config if it exists
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = json.load(f)
                
            settings.bot = BotConfig(**config_data.get("bot", {}))
            settings.features = FeatureConfig(**config_data.get("features", {}))
            settings.limits = LimitsConfig(**config_data.get("limits", {}))
            settings.scheduling = SchedulingConfig(**config_data.get("scheduling", {}))
            
        return settings


# Global settings instance - will be initialized when needed
settings = None

def get_settings() -> Settings:
    """Get or create the global settings instance"""
    global settings
    if settings is None:
        try:
            settings = Settings.load_from_config_file()
        except Exception as e:
            # For testing or when config is not available, create minimal settings
            import os
            print(f"DEBUG: Exception loading settings: {e}")
            print(f"DEBUG: DISCORD_TOKEN from os.getenv: {os.getenv('DISCORD_TOKEN', 'NOT_FOUND')}")
            settings = Settings(
                discord_token=os.getenv("DISCORD_TOKEN", "test_token"),
                reminder_channel_id=int(os.getenv("REMINDER_CHANNEL_ID", "123456789")),
                admin_role_ids=[int(os.getenv("ADMIN_ROLE_IDS", "987654321"))],
            )
    return settings
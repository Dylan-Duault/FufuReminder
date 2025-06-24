from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import calendar
from ..models.enums import FrequencyEnum


class FrequencyStrategy(ABC):
    """Abstract base class for frequency calculation strategies"""
    
    @property
    @abstractmethod
    def frequency(self) -> FrequencyEnum:
        """Return the frequency enum this strategy handles"""
        pass
    
    @abstractmethod
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate the next execution time based on frequency"""
        pass


class SpamStrategy(FrequencyStrategy):
    """Strategy for spam frequency calculations (every minute)"""
    
    @property
    def frequency(self) -> FrequencyEnum:
        return FrequencyEnum.SPAM
    
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time for spam frequency (every minute)"""
        return current_time + timedelta(minutes=1)


class HourlyStrategy(FrequencyStrategy):
    """Strategy for hourly frequency calculations"""
    
    @property
    def frequency(self) -> FrequencyEnum:
        return FrequencyEnum.HOURLY
    
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time for hourly frequency"""
        return current_time + timedelta(hours=1)


class DailyStrategy(FrequencyStrategy):
    """Strategy for daily frequency calculations"""
    
    @property
    def frequency(self) -> FrequencyEnum:
        return FrequencyEnum.DAILY
    
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time for daily frequency"""
        return current_time + timedelta(days=1)


class WeeklyStrategy(FrequencyStrategy):
    """Strategy for weekly frequency calculations"""
    
    @property
    def frequency(self) -> FrequencyEnum:
        return FrequencyEnum.WEEKLY
    
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time for weekly frequency"""
        return current_time + timedelta(weeks=1)


class MonthlyStrategy(FrequencyStrategy):
    """Strategy for monthly frequency calculations"""
    
    @property
    def frequency(self) -> FrequencyEnum:
        return FrequencyEnum.MONTHLY
    
    def calculate_next_execution(self, current_time: datetime) -> datetime:
        """Calculate next execution time for monthly frequency"""
        # Handle month rollover and varying month lengths
        current_year = current_time.year
        current_month = current_time.month
        current_day = current_time.day
        
        # Calculate next month
        if current_month == 12:
            next_year = current_year + 1
            next_month = 1
        else:
            next_year = current_year
            next_month = current_month + 1
        
        # Handle day adjustment for months with fewer days
        max_day_in_next_month = calendar.monthrange(next_year, next_month)[1]
        next_day = min(current_day, max_day_in_next_month)
        
        return current_time.replace(
            year=next_year,
            month=next_month,
            day=next_day
        )


# Factory function for getting frequency strategies
def get_frequency_strategy(frequency: FrequencyEnum) -> FrequencyStrategy:
    """Factory function to get appropriate frequency strategy"""
    strategy_map = {
        FrequencyEnum.SPAM: SpamStrategy,
        FrequencyEnum.HOURLY: HourlyStrategy,
        FrequencyEnum.DAILY: DailyStrategy,
        FrequencyEnum.WEEKLY: WeeklyStrategy,
        FrequencyEnum.MONTHLY: MonthlyStrategy,
    }
    
    if frequency not in strategy_map:
        raise ValueError(f"Unsupported frequency: {frequency}")
    
    return strategy_map[frequency]()
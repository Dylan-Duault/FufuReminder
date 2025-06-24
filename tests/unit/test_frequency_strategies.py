import pytest
from datetime import datetime, timedelta
from src.strategies.frequency_strategy import FrequencyStrategy, HourlyStrategy, DailyStrategy, WeeklyStrategy, MonthlyStrategy
from src.models.enums import FrequencyEnum


class TestFrequencyStrategy:
    """Test cases for frequency calculation strategies"""
    
    @pytest.fixture
    def hourly_strategy(self):
        """Create hourly frequency strategy"""
        return HourlyStrategy()
    
    @pytest.fixture
    def daily_strategy(self):
        """Create daily frequency strategy"""
        return DailyStrategy()
    
    @pytest.fixture
    def weekly_strategy(self):
        """Create weekly frequency strategy"""
        return WeeklyStrategy()
    
    @pytest.fixture
    def monthly_strategy(self):
        """Create monthly frequency strategy"""
        return MonthlyStrategy()
    
    @pytest.fixture
    def base_time(self):
        """Fixed base time for consistent testing"""
        return datetime(2024, 1, 15, 10, 30, 0)  # Monday, 10:30 AM
    
    def test_hourly_strategy_calculate_next(self, hourly_strategy, base_time):
        """Test hourly frequency calculation"""
        # Act
        next_time = hourly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = base_time + timedelta(hours=1)
        assert next_time == expected
    
    def test_hourly_strategy_frequency_enum(self, hourly_strategy):
        """Test hourly strategy frequency enum"""
        assert hourly_strategy.frequency == FrequencyEnum.HOURLY
    
    def test_daily_strategy_calculate_next(self, daily_strategy, base_time):
        """Test daily frequency calculation"""
        # Act
        next_time = daily_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = base_time + timedelta(days=1)
        assert next_time == expected
    
    def test_daily_strategy_frequency_enum(self, daily_strategy):
        """Test daily strategy frequency enum"""
        assert daily_strategy.frequency == FrequencyEnum.DAILY
    
    def test_weekly_strategy_calculate_next(self, weekly_strategy, base_time):
        """Test weekly frequency calculation"""
        # Act
        next_time = weekly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = base_time + timedelta(weeks=1)
        assert next_time == expected
    
    def test_weekly_strategy_frequency_enum(self, weekly_strategy):
        """Test weekly strategy frequency enum"""
        assert weekly_strategy.frequency == FrequencyEnum.WEEKLY
    
    def test_monthly_strategy_calculate_next_same_month(self, monthly_strategy):
        """Test monthly frequency calculation within same month"""
        # Arrange - January 15th, should go to February 15th
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        
        # Act
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = datetime(2024, 2, 15, 10, 30, 0)
        assert next_time == expected
    
    def test_monthly_strategy_calculate_next_end_of_month(self, monthly_strategy):
        """Test monthly frequency calculation at end of month"""
        # Arrange - January 31st, should go to February 29th (2024 is leap year)
        base_time = datetime(2024, 1, 31, 10, 30, 0)
        
        # Act
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = datetime(2024, 2, 29, 10, 30, 0)  # February has 29 days in 2024
        assert next_time == expected
    
    def test_monthly_strategy_calculate_next_february_to_march(self, monthly_strategy):
        """Test monthly frequency calculation from February to March"""
        # Arrange - February 29th, should go to March 29th
        base_time = datetime(2024, 2, 29, 10, 30, 0)
        
        # Act
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = datetime(2024, 3, 29, 10, 30, 0)
        assert next_time == expected
    
    def test_monthly_strategy_frequency_enum(self, monthly_strategy):
        """Test monthly strategy frequency enum"""
        assert monthly_strategy.frequency == FrequencyEnum.MONTHLY
    
    def test_monthly_strategy_year_rollover(self, monthly_strategy):
        """Test monthly frequency calculation across year boundary"""
        # Arrange - December 15th, should go to January 15th next year
        base_time = datetime(2024, 12, 15, 10, 30, 0)
        
        # Act
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Assert
        expected = datetime(2025, 1, 15, 10, 30, 0)
        assert next_time == expected
    
    def test_strategy_validation_positive_intervals(self, hourly_strategy, daily_strategy, weekly_strategy, monthly_strategy):
        """Test that all strategies return future times"""
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        
        strategies = [hourly_strategy, daily_strategy, weekly_strategy, monthly_strategy]
        
        for strategy in strategies:
            next_time = strategy.calculate_next_execution(base_time)
            assert next_time > base_time, f"{strategy.__class__.__name__} should return future time"
    
    def test_strategy_time_preservation(self, daily_strategy):
        """Test that time components are preserved in calculation"""
        # Arrange - specific time should be preserved
        base_time = datetime(2024, 1, 15, 14, 45, 30)
        
        # Act
        next_time = daily_strategy.calculate_next_execution(base_time)
        
        # Assert
        assert next_time.hour == 14
        assert next_time.minute == 45
        assert next_time.second == 30
        assert next_time.date() == (base_time + timedelta(days=1)).date()


class TestFrequencyStrategyFactory:
    """Test cases for frequency strategy factory"""
    
    def test_get_strategy_hourly(self):
        """Test getting hourly strategy from factory"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        strategy = get_frequency_strategy(FrequencyEnum.HOURLY)
        assert isinstance(strategy, HourlyStrategy)
        assert strategy.frequency == FrequencyEnum.HOURLY
    
    def test_get_strategy_daily(self):
        """Test getting daily strategy from factory"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        strategy = get_frequency_strategy(FrequencyEnum.DAILY)
        assert isinstance(strategy, DailyStrategy)
        assert strategy.frequency == FrequencyEnum.DAILY
    
    def test_get_strategy_weekly(self):
        """Test getting weekly strategy from factory"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        strategy = get_frequency_strategy(FrequencyEnum.WEEKLY)
        assert isinstance(strategy, WeeklyStrategy)
        assert strategy.frequency == FrequencyEnum.WEEKLY
    
    def test_get_strategy_monthly(self):
        """Test getting monthly strategy from factory"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        strategy = get_frequency_strategy(FrequencyEnum.MONTHLY)
        assert isinstance(strategy, MonthlyStrategy)
        assert strategy.frequency == FrequencyEnum.MONTHLY
    
    def test_get_strategy_invalid_frequency(self):
        """Test getting strategy with invalid frequency"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        with pytest.raises(ValueError, match="Unsupported frequency"):
            get_frequency_strategy("INVALID")
    
    def test_strategy_factory_returns_same_instance(self):
        """Test that factory returns consistent instances"""
        from src.strategies.frequency_strategy import get_frequency_strategy
        
        strategy1 = get_frequency_strategy(FrequencyEnum.DAILY)
        strategy2 = get_frequency_strategy(FrequencyEnum.DAILY)
        
        # Should return same type but can be different instances
        assert type(strategy1) == type(strategy2)
        assert strategy1.frequency == strategy2.frequency


class TestFrequencyStrategyEdgeCases:
    """Test edge cases for frequency strategies"""
    
    def test_leap_year_february_monthly(self):
        """Test monthly calculation in leap year February"""
        monthly_strategy = MonthlyStrategy()
        
        # Leap year February 29th
        base_time = datetime(2024, 2, 29, 12, 0, 0)
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Should go to March 29th
        expected = datetime(2024, 3, 29, 12, 0, 0)
        assert next_time == expected
    
    def test_non_leap_year_february_monthly(self):
        """Test monthly calculation in non-leap year February"""
        monthly_strategy = MonthlyStrategy()
        
        # Non-leap year January 31st going to February
        base_time = datetime(2023, 1, 31, 12, 0, 0)
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Should go to February 28th (last day of February in non-leap year)
        expected = datetime(2023, 2, 28, 12, 0, 0)
        assert next_time == expected
    
    def test_monthly_strategy_may_31_to_june(self):
        """Test monthly calculation from May 31st to June"""
        monthly_strategy = MonthlyStrategy()
        
        # May 31st going to June (30 days)
        base_time = datetime(2024, 5, 31, 12, 0, 0)
        next_time = monthly_strategy.calculate_next_execution(base_time)
        
        # Should go to June 30th
        expected = datetime(2024, 6, 30, 12, 0, 0)
        assert next_time == expected
    
    def test_calculation_with_microseconds(self):
        """Test that microseconds are handled correctly"""
        daily_strategy = DailyStrategy()
        
        base_time = datetime(2024, 1, 15, 10, 30, 45, 123456)
        next_time = daily_strategy.calculate_next_execution(base_time)
        
        # Microseconds should be preserved
        expected = datetime(2024, 1, 16, 10, 30, 45, 123456)
        assert next_time == expected
        assert next_time.microsecond == 123456
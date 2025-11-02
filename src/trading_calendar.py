#!/usr/bin/env python3
"""
Trading Calendar Utility
Validates if a date is a US market trading day
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import pandas_market_calendars as mcal


class TradingCalendar:
    """US Market Trading Calendar"""

    def __init__(self):
        """Initialize with NYSE calendar"""
        self.nyse = mcal.get_calendar('NYSE')
        self._cache = {}  # Cache for valid trading days

    def is_trading_day(self, date: str) -> bool:
        """
        Check if a date is a valid US trading day

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            True if it's a trading day, False otherwise
        """
        # Check cache first
        if date in self._cache:
            return self._cache[date]

        try:
            # Get trading schedule for the date
            date_obj = pd.Timestamp(date)
            schedule = self.nyse.schedule(start_date=date, end_date=date)

            # If schedule has entries, it's a trading day
            is_valid = len(schedule) > 0

            # Cache the result
            self._cache[date] = is_valid

            return is_valid

        except Exception as e:
            # If there's any error, assume it's not a trading day
            print(f"Warning: Could not verify trading day for {date}: {e}")
            return False

    def get_last_trading_day(self, before_date: Optional[str] = None) -> str:
        """
        Get the last trading day before a given date

        Args:
            before_date: Date string in YYYY-MM-DD format (default: today)

        Returns:
            Last trading day in YYYY-MM-DD format
        """
        if before_date is None:
            before_date = datetime.now().strftime('%Y-%m-%d')

        # Get schedule for past 10 days
        start = pd.Timestamp(before_date) - pd.Timedelta(days=10)
        end = pd.Timestamp(before_date)

        schedule = self.nyse.schedule(start_date=start, end_date=end)

        if len(schedule) == 0:
            raise ValueError(f"No trading days found before {before_date}")

        # Get the last trading day
        last_day = schedule.index[-1]
        return last_day.strftime('%Y-%m-%d')

    def get_next_trading_day(self, after_date: Optional[str] = None) -> str:
        """
        Get the next trading day after a given date

        Args:
            after_date: Date string in YYYY-MM-DD format (default: today)

        Returns:
            Next trading day in YYYY-MM-DD format
        """
        if after_date is None:
            after_date = datetime.now().strftime('%Y-%m-%d')

        # Get schedule for next 10 days
        start = pd.Timestamp(after_date) + pd.Timedelta(days=1)
        end = start + pd.Timedelta(days=10)

        schedule = self.nyse.schedule(start_date=start, end_date=end)

        if len(schedule) == 0:
            raise ValueError(f"No trading days found after {after_date}")

        # Get the first trading day
        next_day = schedule.index[0]
        return next_day.strftime('%Y-%m-%d')

    def get_trading_days_in_range(self, start_date: str, end_date: str) -> list:
        """
        Get all trading days in a date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of trading days in YYYY-MM-DD format
        """
        schedule = self.nyse.schedule(start_date=start_date, end_date=end_date)
        return [day.strftime('%Y-%m-%d') for day in schedule.index]


# Singleton instance
_calendar = None


def get_trading_calendar() -> TradingCalendar:
    """Get singleton trading calendar instance"""
    global _calendar
    if _calendar is None:
        _calendar = TradingCalendar()
    return _calendar


def is_trading_day(date: str) -> bool:
    """
    Quick check if a date is a trading day

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        True if it's a trading day, False otherwise
    """
    calendar = get_trading_calendar()
    return calendar.is_trading_day(date)


def get_last_trading_day(before_date: Optional[str] = None) -> str:
    """
    Get the last trading day

    Args:
        before_date: Date string in YYYY-MM-DD format (default: today)

    Returns:
        Last trading day in YYYY-MM-DD format
    """
    calendar = get_trading_calendar()
    return calendar.get_last_trading_day(before_date)


if __name__ == '__main__':
    # Test the module
    import sys

    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = datetime.now().strftime('%Y-%m-%d')

    print(f"Testing trading calendar for {date}")
    print(f"Is trading day: {is_trading_day(date)}")

    if not is_trading_day(date):
        print(f"Last trading day: {get_last_trading_day(date)}")

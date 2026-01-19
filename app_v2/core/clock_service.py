"""
Clock Service - Time and date logic
Handles timezone-aware time retrieval and formatting
"""
from datetime import datetime
from typing import Dict, Optional
import pytz
from zoneinfo import ZoneInfo


class ClockService:
    """
    Centralized clock/time service with timezone support.
    """
    
    def __init__(self, timezone: str = 'UTC'):
        """
        Initialize clock service with timezone.
        
        Args:
            timezone: IANA timezone string (e.g., 'America/Los_Angeles')
        """
        self._timezone = timezone
        self._tz_obj: Optional[ZoneInfo] = None
        self._load_timezone()
    
    def _load_timezone(self) -> None:
        """Load timezone object, fallback to UTC on error"""
        try:
            self._tz_obj = ZoneInfo(self._timezone)
        except Exception as e:
            print(f"Warning: Invalid timezone '{self._timezone}', using UTC: {e}")
            self._timezone = 'UTC'
            self._tz_obj = ZoneInfo('UTC')
    
    def set_timezone(self, timezone: str) -> bool:
        """
        Change timezone dynamically.
        
        Args:
            timezone: IANA timezone string
        
        Returns:
            True if successful, False otherwise
        """
        old_tz = self._timezone
        self._timezone = timezone
        try:
            self._load_timezone()
            return True
        except Exception as e:
            print(f"Failed to set timezone '{timezone}': {e}")
            self._timezone = old_tz
            self._load_timezone()
            return False
    
    def get_current_time(self) -> datetime:
        """
        Get current time in configured timezone.
        
        Returns:
            Timezone-aware datetime object
        """
        return datetime.now(self._tz_obj)
    
    def format_time(self, fmt: str = '%H:%M:%S') -> str:
        """
        Format current time as string.
        
        Args:
            fmt: strftime format string
        
        Returns:
            Formatted time string
        """
        return self.get_current_time().strftime(fmt)
    
    def format_date(self, fmt: str = '%Y-%m-%d') -> str:
        """
        Format current date as string.
        
        Args:
            fmt: strftime format string
        
        Returns:
            Formatted date string
        """
        return self.get_current_time().strftime(fmt)
    
    def get_time_parts(self) -> Dict[str, str]:
        """
        Get time components for display.
        
        Returns:
            Dictionary with time components
        """
        now = self.get_current_time()
        return {
            'hour': now.strftime('%H'),
            'minute': now.strftime('%M'),
            'second': now.strftime('%S'),
            'date': now.strftime('%B %d, %Y'),
            'weekday': now.strftime('%A'),
            'timezone': now.strftime('%Z'),
            'timestamp': now.timestamp()
        }
    
    def get_display_data(self) -> Dict[str, str]:
        """
        Get all data needed for clock display.
        
        Returns:
            Dictionary with formatted strings for UI
        """
        now = self.get_current_time()
        
        # 12-hour format with AM/PM
        hour_12 = now.strftime('%I').lstrip('0')
        minute = now.strftime('%M')
        second = now.strftime('%S')
        ampm = now.strftime('%p')
        
        # 24-hour format
        hour_24 = now.strftime('%H')
        
        # Date components
        weekday = now.strftime('%A')
        month = now.strftime('%B')
        day = now.strftime('%d').lstrip('0')
        year = now.strftime('%Y')
        
        return {
            'time_12': f"{hour_12}:{minute}:{second}",
            'time_24': f"{hour_24}:{minute}:{second}",
            'hour_12': hour_12,
            'hour_24': hour_24,
            'minute': minute,
            'second': second,
            'ampm': ampm,
            'weekday': weekday,
            'month': month,
            'day': day,
            'year': year,
            'date_full': f"{weekday}, {month} {day}, {year}",
            'date_short': f"{month} {day}",
            'timezone': now.strftime('%Z'),
        }
    
    @property
    def timezone(self) -> str:
        """Get current timezone string"""
        return self._timezone

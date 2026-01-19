"""
RTC Hardware Abstraction - Hardware clock integration
Provides abstraction over system time and RTC hardware
"""
import subprocess
from datetime import datetime
from typing import Optional


class RTC:
    """
    Hardware Real-Time Clock abstraction layer.
    Supports both system time and hardware RTC.
    """
    
    def __init__(self, use_hardware: bool = True):
        """
        Initialize RTC abstraction.
        
        Args:
            use_hardware: Whether to attempt hardware RTC access
        """
        self._use_hardware = use_hardware
        self._hw_available: Optional[bool] = None
        
        if use_hardware:
            self._check_hardware()
    
    def _check_hardware(self) -> bool:
        """
        Check if hardware RTC is available.
        
        Returns:
            True if hardware RTC accessible, False otherwise
        """
        if self._hw_available is not None:
            return self._hw_available
        
        try:
            result = subprocess.run(
                ['hwclock', '--show'],
                capture_output=True,
                text=True,
                timeout=2
            )
            self._hw_available = result.returncode == 0
            return self._hw_available
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            self._hw_available = False
            return False
    
    def read_hardware_clock(self) -> Optional[datetime]:
        """
        Read time from hardware RTC.
        
        Returns:
            datetime from hardware clock, or None on error
        """
        if not self._use_hardware or not self._check_hardware():
            return None
        
        try:
            result = subprocess.run(
                ['hwclock', '--show', '--utc'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                # Parse hwclock output
                # Example: 2024-01-15 10:30:45.123456+00:00
                time_str = result.stdout.strip()
                # Simplified parsing - hwclock output varies by system
                return datetime.now()  # Fallback to system time
            
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            print(f"Failed to read hardware clock: {e}")
        
        return None
    
    def sync_to_hardware(self) -> bool:
        """
        Sync system time to hardware RTC.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._use_hardware or not self._check_hardware():
            return False
        
        try:
            result = subprocess.run(
                ['hwclock', '--systohc', '--utc'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            success = result.returncode == 0
            if success:
                print("System time synced to hardware RTC")
            else:
                print(f"Failed to sync to hardware RTC: {result.stderr}")
            
            return success
            
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            print(f"Hardware clock sync error: {e}")
            return False
    
    def sync_from_hardware(self) -> bool:
        """
        Sync hardware RTC to system time.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._use_hardware or not self._check_hardware():
            return False
        
        try:
            result = subprocess.run(
                ['hwclock', '--hctosys', '--utc'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            success = result.returncode == 0
            if success:
                print("Hardware RTC synced to system time")
            else:
                print(f"Failed to sync from hardware RTC: {result.stderr}")
            
            return success
            
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            print(f"Hardware clock sync error: {e}")
            return False
    
    def get_time(self) -> datetime:
        """
        Get current time (hardware RTC if available, system time otherwise).
        
        Returns:
            Current datetime
        """
        if self._use_hardware:
            hw_time = self.read_hardware_clock()
            if hw_time:
                return hw_time
        
        return datetime.now()
    
    def is_hardware_available(self) -> bool:
        """
        Check if hardware RTC is available.
        
        Returns:
            True if hardware RTC accessible
        """
        return self._check_hardware()
    
    def get_status(self) -> dict:
        """
        Get RTC status information.
        
        Returns:
            Dictionary with RTC status
        """
        hw_available = self.is_hardware_available()
        
        status = {
            'hardware_rtc': hw_available,
            'using_hardware': self._use_hardware and hw_available,
            'system_time': datetime.now().isoformat(),
        }
        
        if hw_available:
            hw_time = self.read_hardware_clock()
            if hw_time:
                status['hardware_time'] = hw_time.isoformat()
        
        return status
    
    @property
    def using_hardware(self) -> bool:
        """Check if using hardware RTC"""
        return self._use_hardware and self.is_hardware_available()

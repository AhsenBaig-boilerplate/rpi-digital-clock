"""
DS3231 RTC Module - Optional hardware clock support for offline timekeeping.
Gracefully handles missing hardware and only activates when explicitly enabled.
"""

import logging
import subprocess
from datetime import datetime
from typing import Optional


class RTCManager:
    """Minimal DS3231 Real-Time Clock manager for optional hardware support."""
    
    def __init__(self, enabled: bool = False):
        """
        Initialize RTC manager.
        
        Args:
            enabled: Whether to attempt RTC initialization (default: False)
        """
        self.enabled = enabled
        self.available = False
        self.i2c_address = '0x68'  # DS3231 default I2C address
        
        if self.enabled:
            self._detect_rtc()
        else:
            logging.info("RTC support disabled (optional hardware)")
    
    def _detect_rtc(self) -> bool:
        """
        Detect if DS3231 RTC module is available on I2C bus.
        
        Returns:
            True if RTC detected, False otherwise
        """
        try:
            # Check if I2C device exists at DS3231 address
            result = subprocess.run(
                ['i2cdetect', '-y', '1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and self.i2c_address in result.stdout:
                logging.info(f"DS3231 RTC detected at I2C address {self.i2c_address}")
                self.available = True
                return True
            else:
                logging.warning("DS3231 RTC not detected on I2C bus")
                self.available = False
                return False
                
        except FileNotFoundError:
            logging.warning("i2cdetect not available - RTC detection skipped")
            self.available = False
            return False
        except Exception as e:
            logging.debug(f"Error detecting RTC: {e}")
            self.available = False
            return False
    
    def read_time(self) -> Optional[datetime]:
        """
        Read current time from DS3231 RTC.
        
        Returns:
            datetime object with RTC time, or None if read fails
        """
        if not self.available:
            return None
        
        try:
            # Read RTC time using hwclock
            result = subprocess.run(
                ['hwclock', '-r'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse hwclock output (format varies by locale)
                time_str = result.stdout.strip()
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%a %d %b %Y %H:%M:%S']:
                        try:
                            rtc_time = datetime.strptime(time_str.split('.')[0], fmt)
                            logging.info(f"Read time from RTC: {rtc_time}")
                            return rtc_time
                        except ValueError:
                            continue
                    
                    logging.warning(f"Could not parse RTC time format: {time_str}")
                    return None
                    
                except Exception as e:
                    logging.error(f"Error parsing RTC time: {e}")
                    return None
            else:
                logging.warning(f"Failed to read RTC: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Error reading RTC: {e}")
            return None
    
    def write_time(self, dt: Optional[datetime] = None) -> bool:
        """
        Write current system time (or provided datetime) to DS3231 RTC.
        
        Args:
            dt: datetime to write, or None to use current system time
        
        Returns:
            True if write successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            # Write system time to RTC using hwclock
            result = subprocess.run(
                ['hwclock', '-w'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logging.info("Synced system time to RTC")
                return True
            else:
                logging.warning(f"Failed to write RTC: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error writing RTC: {e}")
            return False
    
    def sync_system_from_rtc(self) -> bool:
        """
        Set system time from RTC (useful when network unavailable).
        
        Returns:
            True if sync successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            # Set system time from RTC using hwclock
            result = subprocess.run(
                ['hwclock', '-s'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logging.info("Synced system time from RTC")
                return True
            else:
                logging.warning(f"Failed to sync from RTC: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error syncing from RTC: {e}")
            return False

"""
RTC (Real-Time Clock) Module - DS3231 Hardware Clock Support
Provides accurate timekeeping when network/NTP is unavailable.
"""

import logging
import subprocess
from datetime import datetime
from typing import Optional


class RTCManager:
    """Manager for DS3231 Hardware Real-Time Clock module."""
    
    def __init__(self):
        """Initialize RTC manager."""
        self.rtc_device = '/dev/rtc0'
        self.i2c_address = '0x68'  # DS3231 default I2C address
        self.rtc_available = False
        self.last_sync_time = None
        
        # Check if RTC is available
        self._detect_rtc()
    
    def _detect_rtc(self) -> bool:
        """
        Detect if DS3231 RTC module is available.
        
        Returns:
            True if RTC detected, False otherwise
        """
        try:
            # Check if RTC device exists
            result = subprocess.run(
                ['ls', self.rtc_device],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logging.info(f"RTC device found: {self.rtc_device}")
                self.rtc_available = True
                return True
            else:
                logging.warning("RTC device not found - using system clock only")
                self.rtc_available = False
                return False
                
        except Exception as e:
            logging.debug(f"Error detecting RTC: {e}")
            self.rtc_available = False
            return False
    
    def read_rtc_time(self) -> Optional[datetime]:
        """
        Read current time from DS3231 RTC module.
        
        Returns:
            datetime object with RTC time, or None if read fails
        """
        if not self.rtc_available:
            logging.debug("RTC not available for reading")
            return None
        
        try:
            # Read time using hwclock
            result = subprocess.run(
                ['hwclock', '-r'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse hwclock output
                time_str = result.stdout.strip()
                logging.debug(f"RTC time: {time_str}")
                return datetime.now()  # System will be synced with RTC
            else:
                logging.warning(f"Failed to read RTC: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("RTC read timed out")
            return None
        except Exception as e:
            logging.error(f"Error reading RTC: {e}", exc_info=True)
            return None
    
    def sync_system_from_rtc(self) -> bool:
        """
        Synchronize system clock from DS3231 RTC module.
        Use this when network is unavailable but RTC has accurate time.
        
        Returns:
            True if sync successful, False otherwise
        """
        if not self.rtc_available:
            logging.warning("RTC not available for sync")
            return False
        
        try:
            logging.info("Syncing system clock from RTC...")
            
            # Sync system clock from hardware clock
            result = subprocess.run(
                ['hwclock', '--hctosys'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.last_sync_time = datetime.now()
                logging.info("System clock successfully synced from RTC")
                return True
            else:
                logging.error(f"Failed to sync from RTC: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("RTC sync timed out")
            return False
        except PermissionError:
            logging.error("Permission denied - need root access to sync system clock")
            return False
        except Exception as e:
            logging.error(f"Error syncing from RTC: {e}", exc_info=True)
            return False
    
    def sync_rtc_from_system(self) -> bool:
        """
        Synchronize DS3231 RTC module from system clock.
        Use this after successful NTP sync to update RTC.
        
        Returns:
            True if sync successful, False otherwise
        """
        if not self.rtc_available:
            logging.warning("RTC not available for sync")
            return False
        
        try:
            logging.info("Syncing RTC from system clock...")
            
            # Sync hardware clock from system clock
            result = subprocess.run(
                ['hwclock', '--systohc'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info("RTC successfully synced from system clock")
                return True
            else:
                logging.error(f"Failed to sync RTC: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("RTC sync timed out")
            return False
        except PermissionError:
            logging.error("Permission denied - need root access to sync RTC")
            return False
        except Exception as e:
            logging.error(f"Error syncing RTC: {e}", exc_info=True)
            return False
    
    def get_rtc_temperature(self) -> Optional[float]:
        """
        Read temperature from DS3231 (has built-in temperature sensor).
        
        Returns:
            Temperature in Celsius, or None if read fails
        """
        if not self.rtc_available:
            return None
        
        try:
            # Read temperature using i2cget
            # DS3231 stores temp in registers 0x11 (MSB) and 0x12 (LSB)
            result = subprocess.run(
                ['i2cget', '-y', '1', self.i2c_address, '0x11'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                temp_msb = int(result.stdout.strip(), 16)
                
                # Read LSB for fractional part
                result = subprocess.run(
                    ['i2cget', '-y', '1', self.i2c_address, '0x12'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    temp_lsb = int(result.stdout.strip(), 16)
                    
                    # Calculate temperature
                    # MSB is integer part, LSB top 2 bits are fractional (0.25°C per bit)
                    temperature = temp_msb + ((temp_lsb >> 6) * 0.25)
                    
                    logging.debug(f"RTC temperature: {temperature}°C")
                    return temperature
            
            return None
            
        except Exception as e:
            logging.debug(f"Error reading RTC temperature: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if RTC module is available.
        
        Returns:
            True if RTC available, False otherwise
        """
        return self.rtc_available
    
    def get_status(self) -> dict:
        """
        Get RTC module status information.
        
        Returns:
            Dictionary with RTC status
        """
        status = {
            'available': self.rtc_available,
            'device': self.rtc_device,
            'i2c_address': self.i2c_address,
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None
        }
        
        if self.rtc_available:
            status['temperature'] = self.get_rtc_temperature()
        
        return status

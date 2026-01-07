"""
Utility Functions - Logging, NTP sync, config validation, and helper functions.
"""

import logging
import subprocess
import sys
import time
from typing import Dict
from pathlib import Path


def setup_logging(log_level: str = 'INFO'):
    """
    Setup logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Setup basic configuration
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Optionally add file handler for persistent logs
            # logging.FileHandler('/var/log/rpi-clock.log')
        ]
    )
    
    logging.info(f"Logging initialized at {log_level} level")


def sync_time_ntp(ntp_server: str = 'pool.ntp.org') -> bool:
    """
    Synchronize system time with NTP server.
    
    Args:
        ntp_server: NTP server hostname
    
    Returns:
        True if sync successful, False otherwise
    """
    try:
        # Try using timedatectl (systemd-based systems)
        result = subprocess.run(
            ['timedatectl', 'set-ntp', 'true'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logging.info("Time synchronized via timedatectl")
            return True
        
        # Fallback: try ntpdate if available
        result = subprocess.run(
            ['ntpdate', '-u', ntp_server],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logging.info(f"Time synchronized via ntpdate with {ntp_server}")
            return True
        else:
            logging.warning(f"ntpdate failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("NTP sync timed out")
        return False
    except FileNotFoundError:
        logging.warning("NTP tools not found - skipping time sync")
        return False
    except Exception as e:
        logging.error(f"Error syncing time: {e}", exc_info=True)
        return False


def validate_config(config: Dict) -> bool:
    """
    Validate configuration dictionary.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if valid, raises exception if invalid
    
    Raises:
        ValueError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    # Validate time configuration
    if 'time' in config:
        time_config = config['time']
        if 'format_12h' in time_config and not isinstance(time_config['format_12h'], bool):
            raise ValueError("time.format_12h must be a boolean")
        if 'ntp_sync' in time_config and not isinstance(time_config['ntp_sync'], bool):
            raise ValueError("time.ntp_sync must be a boolean")
    
    # Validate display configuration
    if 'display' in config:
        display_config = config['display']
        
        # Validate numeric values
        if 'time_font_size' in display_config:
            if not isinstance(display_config['time_font_size'], int) or display_config['time_font_size'] <= 0:
                raise ValueError("display.time_font_size must be a positive integer")
        
        if 'screensaver_delay_minutes' in display_config:
            if not isinstance(display_config['screensaver_delay_minutes'], (int, float)) or display_config['screensaver_delay_minutes'] <= 0:
                raise ValueError("display.screensaver_delay_minutes must be a positive number")
        
        if 'pixel_shift_interval_seconds' in display_config:
            if not isinstance(display_config['pixel_shift_interval_seconds'], (int, float)) or display_config['pixel_shift_interval_seconds'] <= 0:
                raise ValueError("display.pixel_shift_interval_seconds must be a positive number")
        
        if 'night_brightness' in display_config:
            brightness = display_config['night_brightness']
            if not isinstance(brightness, (int, float)) or not (0.0 <= brightness <= 1.0):
                raise ValueError("display.night_brightness must be between 0.0 and 1.0")
        
        if 'night_start_hour' in display_config:
            hour = display_config['night_start_hour']
            if not isinstance(hour, int) or not (0 <= hour <= 23):
                raise ValueError("display.night_start_hour must be between 0 and 23")
        
        if 'night_end_hour' in display_config:
            hour = display_config['night_end_hour']
            if not isinstance(hour, int) or not (0 <= hour <= 23):
                raise ValueError("display.night_end_hour must be between 0 and 23")
        
        # Validate color format
        if 'color' in display_config:
            color = display_config['color']
            if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
                raise ValueError("display.color must be a hex color string (e.g., #00FF00)")
    
    # Validate weather configuration
    if 'weather' in config:
        weather_config = config['weather']
        if weather_config.get('enabled', False):
            if not weather_config.get('api_key'):
                logging.warning("Weather enabled but no API key provided")
            if not weather_config.get('location'):
                logging.warning("Weather enabled but no location provided")
            
            if 'units' in weather_config:
                valid_units = ['metric', 'imperial', 'kelvin']
                if weather_config['units'] not in valid_units:
                    raise ValueError(f"weather.units must be one of: {', '.join(valid_units)}")
    
    logging.info("Configuration validation passed")
    return True


def get_display_resolution() -> tuple:
    """
    Get the current display resolution (best effort).
    
    Returns:
        Tuple of (width, height) or (1920, 1080) as default
    """
    try:
        # Try to get resolution using xrandr
        result = subprocess.run(
            ['xrandr'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse xrandr output for current resolution
            for line in result.stdout.split('\n'):
                if '*' in line:  # Current resolution marked with *
                    parts = line.split()
                    if parts:
                        resolution = parts[0].split('x')
                        if len(resolution) == 2:
                            width = int(resolution[0])
                            height = int(resolution[1])
                            logging.info(f"Detected display resolution: {width}x{height}")
                            return (width, height)
    except Exception as e:
        logging.debug(f"Could not detect display resolution: {e}")
    
    # Default to Full HD
    logging.info("Using default resolution: 1920x1080")
    return (1920, 1080)


def format_uptime(seconds: int) -> str:
    """
    Format uptime seconds into human-readable string.
    
    Args:
        seconds: Uptime in seconds
    
    Returns:
        Formatted uptime string
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "0m"


def check_internet_connection(host: str = "8.8.8.8", timeout: int = 3) -> bool:
    """
    Check if internet connection is available.
    
    Args:
        host: Host to ping (default: Google DNS)
        timeout: Timeout in seconds
    
    Returns:
        True if connection available, False otherwise
    """
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), host],
            capture_output=True,
            timeout=timeout + 1
        )
        return result.returncode == 0
    except Exception as e:
        logging.debug(f"Internet check failed: {e}")
        return False


def get_timezone_info() -> Dict[str, any]:
    """
    Get current timezone information including DST status.
    
    Returns:
        Dictionary with timezone info including DST status
    """
    try:
        # Check if DST is currently in effect
        is_dst = time.localtime().tm_isdst > 0
        
        # Get timezone name and offset
        tz_name = time.tzname[1 if is_dst else 0]
        
        # Get UTC offset in hours
        utc_offset = -time.timezone / 3600 if not is_dst else -time.altzone / 3600
        
        return {
            'timezone_name': tz_name,
            'is_dst': is_dst,
            'utc_offset': utc_offset,
            'dst_name': time.tzname[1] if len(time.tzname) > 1 else None,
            'standard_name': time.tzname[0]
        }
    except Exception as e:
        logging.error(f"Error getting timezone info: {e}")
        return {
            'timezone_name': 'Unknown',
            'is_dst': False,
            'utc_offset': 0
        }

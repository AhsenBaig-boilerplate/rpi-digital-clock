#!/usr/bin/env python3
"""
Raspberry Pi Digital Clock - Main Application
Displays a customizable digital clock with weather on a TV screen via HDMI.
Includes screen burn-in prevention features.
"""

import os
import sys
import logging
import signal
import yaml
from pathlib import Path
from clock_ui import ClockUI
from utils import setup_logging, sync_time_ntp, validate_config, check_internet_connection, get_timezone_info
from rtc import RTCManager

# Configuration file path
CONFIG_PATH = Path(__file__).parent / "config.yaml"

# Global reference to UI for signal handling
clock_ui = None


def load_config(config_path: Path) -> dict:
    """Load and validate configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Helper function to get env var with optional BALENA_ prefix
        def get_env(name: str) -> str:
            return os.environ.get(f'BALENA_{name}') or os.environ.get(name)
        
        # Override with environment variables if present
        
        # Timezone setting
        if 'time' in config:
            timezone = get_env('TIMEZONE')
            if timezone:
                config['time']['timezone'] = timezone
                logging.info(f"Using TIMEZONE from environment: {timezone}")
        
        # Weather settings
        if 'weather' in config:
            weather_api_key = get_env('WEATHER_API_KEY')
            if weather_api_key:
                config['weather']['api_key'] = weather_api_key
                logging.info("Using WEATHER_API_KEY from environment variable")
            
            weather_location = get_env('WEATHER_LOCATION')
            if weather_location:
                config['weather']['location'] = weather_location
                logging.info(f"Using WEATHER_LOCATION from environment: {weather_location}")
            
            weather_units = get_env('WEATHER_UNITS')
            if weather_units:
                config['weather']['units'] = weather_units
                logging.info(f"Using WEATHER_UNITS from environment: {weather_units}")
            
            weather_enabled = get_env('WEATHER_ENABLED')
            if weather_enabled is not None:
                config['weather']['enabled'] = weather_enabled.lower() in ('true', '1', 'yes')
        
        # Display settings
        if 'display' in config:
            display_orientation = get_env('DISPLAY_ORIENTATION')
            if display_orientation:
                config['display']['orientation'] = display_orientation.lower()
                logging.info(f"Using DISPLAY_ORIENTATION from environment: {display_orientation}")
            
            display_color = get_env('DISPLAY_COLOR')
            if display_color:
                config['display']['color'] = display_color
                logging.info(f"Using DISPLAY_COLOR from environment: {display_color}")
            
            time_format = get_env('TIME_FORMAT_12H')
            if time_format is not None:
                config['time']['format_12h'] = time_format.lower() in ('true', '1', 'yes')
            
            show_seconds = get_env('SHOW_SECONDS')
            if show_seconds is not None:
                config['display']['show_seconds'] = show_seconds.lower() in ('true', '1', 'yes')
            
            date_format = get_env('DATE_FORMAT')
            if date_format:
                config['display']['date_format'] = date_format
            
            font_family = get_env('FONT_FAMILY')
            if font_family:
                config['display']['font_family'] = font_family
            
            time_font_size = get_env('TIME_FONT_SIZE')
            if time_font_size:
                config['display']['time_font_size'] = int(time_font_size)
        
        # Burn-in prevention settings
        if 'display' in config:
            screensaver_enabled = get_env('SCREENSAVER_ENABLED')
            if screensaver_enabled is not None:
                config['display']['screensaver_enabled'] = screensaver_enabled.lower() in ('true', '1', 'yes')
            
            screensaver_start = get_env('SCREENSAVER_START_HOUR')
            if screensaver_start:
                config['display']['screensaver_start_hour'] = int(screensaver_start)
            
            screensaver_end = get_env('SCREENSAVER_END_HOUR')
            if screensaver_end:
                config['display']['screensaver_end_hour'] = int(screensaver_end)
            
            pixel_shift_enabled = get_env('PIXEL_SHIFT_ENABLED')
            if pixel_shift_enabled is not None:
                config['display']['pixel_shift_enabled'] = pixel_shift_enabled.lower() in ('true', '1', 'yes')
            
            dim_at_night = get_env('DIM_AT_NIGHT')
            if dim_at_night is not None:
                config['display']['dim_at_night'] = dim_at_night.lower() in ('true', '1', 'yes')
            
            night_brightness = get_env('NIGHT_BRIGHTNESS')
            if night_brightness:
                config['display']['night_brightness'] = float(night_brightness)
        
        # Validate configuration
        validate_config(config)
        logging.info("Configuration loaded successfully")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    if clock_ui:
        clock_ui.cleanup()
    sys.exit(0)


def main():
    """Main application entry point."""
    global clock_ui
    
    # Setup logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    setup_logging(log_level)
    
    logging.info("=" * 60)
    logging.info("Raspberry Pi Digital Clock - Starting")
    logging.info("=" * 60)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = load_config(CONFIG_PATH)
    
    # Set timezone from config
    timezone = config.get('time', {}).get('timezone', 'America/New_York')
    try:
        import subprocess
        subprocess.run(['ln', '-sf', f'/usr/share/zoneinfo/{timezone}', '/etc/localtime'], check=True)
        subprocess.run(['sh', '-c', f'echo "{timezone}" > /etc/timezone'], check=True)
        logging.info(f"System timezone set to: {timezone}")
        
        # Log DST information
        tz_info = get_timezone_info()
        if tz_info['is_dst']:
            logging.info(f"Daylight Saving Time is active ({tz_info['timezone_name']}, UTC{tz_info['utc_offset']:+.1f})")
        else:
            logging.info(f"Standard time is active ({tz_info['timezone_name']}, UTC{tz_info['utc_offset']:+.1f})")
            if tz_info.get('dst_name'):
                logging.info(f"DST will be automatically observed when applicable (switches to {tz_info['dst_name']})")
    except Exception as e:
        logging.warning(f"Could not set system timezone: {e}")
    
    # Initialize RTC manager
    rtc_enabled = config.get('time', {}).get('rtc_enabled', True)
    rtc_manager = RTCManager() if rtc_enabled else None
    
    if rtc_manager and rtc_manager.is_available():
        logging.info("DS3231 RTC module detected")
        rtc_status = rtc_manager.get_status()
        if rtc_status.get('temperature'):
            logging.info(f"RTC temperature: {rtc_status['temperature']:.2f}°C")
    
    # Time synchronization strategy with RTC fallback
    ntp_enabled = config.get('time', {}).get('ntp_sync', True)
    time_synced = False
    
    if ntp_enabled:
        # Check internet connection
        has_internet = check_internet_connection()
        
        if has_internet:
            logging.info("Internet connection available, syncing with NTP...")
            ntp_server = config.get('time', {}).get('ntp_server', 'pool.ntp.org')
            
            if sync_time_ntp(ntp_server):
                logging.info("Time synchronized successfully via NTP")
                time_synced = True
                
                # Update RTC with accurate NTP time
                if rtc_manager and rtc_manager.is_available():
                    if rtc_manager.sync_rtc_from_system():
                        logging.info("RTC updated with NTP time")
            else:
                logging.warning("NTP sync failed")
        else:
            logging.warning("No internet connection available")
    
    # Fallback to RTC if NTP sync failed or disabled
    if not time_synced and rtc_manager and rtc_manager.is_available():
        logging.info("Syncing system time from RTC module...")
        if rtc_manager.sync_system_from_rtc():
            logging.info("Time synchronized from RTC module")
            time_synced = True
        else:
            logging.warning("RTC sync failed")
    
    if not time_synced:
        logging.warning("Time synchronization unavailable - using system time")
    
    # Initialize and run the clock UI
    try:
        clock_ui = ClockUI(config)
        logging.info("Starting clock display...")
        clock_ui.run()
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error in main application: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if clock_ui:
            clock_ui.cleanup()
        logging.info("Application shut down successfully")


if __name__ == "__main__":
    main()

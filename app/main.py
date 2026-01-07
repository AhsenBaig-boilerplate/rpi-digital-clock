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
from utils import setup_logging, sync_time_ntp, validate_config, check_internet_connection
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
        
        # Override with environment variables if present
        if 'weather' in config:
            weather_api_key = os.environ.get('WEATHER_API_KEY')
            if weather_api_key:
                config['weather']['api_key'] = weather_api_key
                logging.info("Using WEATHER_API_KEY from environment variable")
            
            weather_location = os.environ.get('WEATHER_LOCATION')
            if weather_location:
                config['weather']['location'] = weather_location
                logging.info(f"Using WEATHER_LOCATION from environment: {weather_location}")
        
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

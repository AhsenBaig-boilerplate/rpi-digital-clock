"""
Utility Functions - Logging configuration and build info helpers.
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional


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


def load_build_info() -> Optional[dict]:
    """Load build info JSON embedded in the app image if present."""
    build_path = Path(__file__).parent / "build-info.json"
    try:
        if build_path.exists():
            with open(build_path, "r") as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return None


def format_build_info(info: dict) -> str:
    """Return a concise single-line summary of build info for logging."""
    if not info:
        return "(no build-info.json)"
    sha = str(info.get("git_sha", ""))
    short_sha = sha[:7] if sha else ""
    ref = info.get("git_ref") or ""
    ver = info.get("git_version") or ""
    time_str = info.get("build_time") or ""
    return f"commit={short_sha} ref={ref} version={ver} built={time_str}"


def log_runtime_summary(config: dict, build_info: Optional[dict] = None):
    """
    Log comprehensive runtime summary including environment and build info.
    
    Args:
        config: Application configuration dict
        build_info: Build information dict from build-info.json
    """
    import os
    
    # Runtime summary
    rtc_status = "Enabled" if config.get('time', {}).get('rtc_enabled', False) else "Disabled"
    logging.info(f"Runtime summary: PIL RGB565 | Icons: Vector | RTC: {rtc_status}")
    logging.info("Status icons: network, sync_ok, sync_old, error, settings")
    
    # Build info with git tag
    if build_info:
        git_ver = build_info.get('git_version', 'unknown')
        git_sha = build_info.get('git_sha', '')
        short_sha = git_sha[:7] if git_sha else ''
        git_ref = build_info.get('git_ref', '')
        build_time = build_info.get('build_time', '')
        logging.info(f"Version: {git_ver} ({short_sha}) ref={git_ref} built={build_time}")
    
    # Device metadata (balena environment)
    balena_vars = {
        'BALENA_DEVICE_NAME': os.getenv('BALENA_DEVICE_NAME'),
        'BALENA_DEVICE_TYPE': os.getenv('BALENA_DEVICE_TYPE'),
        'BALENA_DEVICE_UUID': os.getenv('BALENA_DEVICE_UUID'),
        'BALENA_SERVICE_NAME': os.getenv('BALENA_SERVICE_NAME'),
        'BALENA_APP_NAME': os.getenv('BALENA_APP_NAME'),
    }
    
    # Only log if we're in balena environment
    if any(balena_vars.values()):
        logging.info("Device metadata (balena environment):")
        for key, value in balena_vars.items():
            if value:
                logging.info(f"  [Device] {key}={value}")
    
    # Environment variables (masked where sensitive)
    logging.info("Environment variables (masked where sensitive):")
    
    # Service-level variables (from device/fleet config)
    sensitive_keys = ['API_KEY', 'TOKEN', 'PASSWORD', 'SECRET']
    env_vars = {
        'WEATHER_API_KEY': os.getenv('WEATHER_API_KEY') or os.getenv('BALENA_WEATHER_API_KEY'),
        'WEATHER_LOCATION': os.getenv('WEATHER_LOCATION') or os.getenv('BALENA_WEATHER_LOCATION'),
        'WEATHER_UNITS': os.getenv('WEATHER_UNITS') or os.getenv('BALENA_WEATHER_UNITS'),
        'TIMEZONE': os.getenv('TIMEZONE') or os.getenv('BALENA_TIMEZONE') or os.getenv('TZ'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL'),
        'DISPLAY_ORIENTATION': os.getenv('DISPLAY_ORIENTATION'),
        'DISPLAY_COLOR': os.getenv('DISPLAY_COLOR'),
        'TIME_FORMAT_12H': os.getenv('TIME_FORMAT_12H'),
        'SHOW_SECONDS': os.getenv('SHOW_SECONDS'),
        'PIXEL_SHIFT_ENABLED': os.getenv('PIXEL_SHIFT_ENABLED'),
        'SCREENSAVER_ENABLED': os.getenv('SCREENSAVER_ENABLED'),
        'DIM_AT_NIGHT': os.getenv('DIM_AT_NIGHT'),
    }
    
    for key, value in env_vars.items():
        if value is not None:
            # Mask sensitive values
            if any(s in key.upper() for s in sensitive_keys):
                masked_value = '****'
            else:
                masked_value = value
            
            logging.info(f"  [Service(clock)] {key}={masked_value}")

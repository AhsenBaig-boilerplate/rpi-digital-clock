"""
Utility Functions - Logging configuration for the application.
"""

import logging
import sys


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

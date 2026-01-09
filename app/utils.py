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

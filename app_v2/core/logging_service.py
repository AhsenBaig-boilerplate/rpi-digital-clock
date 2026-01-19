"""
Logging Service - Structured logging with configurable levels
"""
import sys
import logging
from typing import Optional
from datetime import datetime


class LoggingService:
    """
    Centralized logging service with structured output.
    """
    
    def __init__(self, name: str = 'rpi-clock', level: str = 'INFO'):
        """
        Initialize logging service.
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self._logger = logging.getLogger(name)
        self._set_level(level)
        self._setup_handlers()
    
    def _set_level(self, level: str) -> None:
        """Set logging level from string"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        log_level = level_map.get(level.upper(), logging.INFO)
        self._logger.setLevel(log_level)
    
    def _setup_handlers(self) -> None:
        """Setup console handler with formatting"""
        # Remove existing handlers
        self._logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._logger.level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self._logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        Log error message.
        
        Args:
            message: Error message
            exc_info: Include exception traceback
            **kwargs: Additional context
        """
        self._logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        Log critical message.
        
        Args:
            message: Critical message
            exc_info: Include exception traceback
            **kwargs: Additional context
        """
        self._logger.critical(message, exc_info=exc_info, extra=kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback"""
        self._logger.exception(message, extra=kwargs)
    
    def set_level(self, level: str) -> None:
        """
        Change logging level dynamically.
        
        Args:
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self._set_level(level)
        for handler in self._logger.handlers:
            handler.setLevel(self._logger.level)
    
    def log_startup(self, version: str, config: dict) -> None:
        """
        Log application startup information.
        
        Args:
            version: Application version
            config: Configuration summary
        """
        self.info("="*60)
        self.info(f"RPI Digital Clock v{version} starting up")
        self.info(f"Python: {sys.version.split()[0]}")
        self.info(f"Timezone: {config.get('timezone', 'UTC')}")
        self.info(f"Display: {config.get('display', {}).get('width', 0)}x{config.get('display', {}).get('height', 0)}")
        self.info(f"Weather: {'enabled' if config.get('weather', {}).get('enabled') else 'disabled'}")
        self.info("="*60)
    
    def log_shutdown(self) -> None:
        """Log application shutdown"""
        self.info("="*60)
        self.info("RPI Digital Clock shutting down")
        self.info("="*60)
    
    @property
    def logger(self) -> logging.Logger:
        """Get underlying logger instance"""
        return self._logger


# Global singleton instance
_logging_service: Optional[LoggingService] = None


def get_logger(name: str = 'rpi-clock', level: str = 'INFO') -> LoggingService:
    """
    Get or create logging service singleton.
    
    Args:
        name: Logger name
        level: Log level
    
    Returns:
        LoggingService instance
    """
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService(name, level)
    return _logging_service

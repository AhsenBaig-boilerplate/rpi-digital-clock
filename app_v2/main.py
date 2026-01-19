"""
Main entry point for RPI Digital Clock v2
"""
import sys
import signal
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app_v2.core.config_service import config
from app_v2.core.clock_service import ClockService
from app_v2.core.weather_service import WeatherService
from app_v2.core.health_service import HealthService
from app_v2.core.logging_service import get_logger
from app_v2.hardware.rtc import RTC
from app_v2.hardware.display_info import DisplayInfo
from app_v2.ui.main_window import MainWindow


class Application:
    """
    Main application orchestrator.
    """
    
    def __init__(self):
        """Initialize application"""
        # Load configuration
        config.reload()
        
        # Initialize logging
        log_level = config.get('logging.level', 'INFO')
        self._logger = get_logger('rpi-clock', log_level)
        
        # Log startup
        version = config.get('app.version', '2.0.0')
        self._logger.log_startup(version, self._get_config_summary())
        
        # Initialize services
        self._clock_service = None
        self._weather_service = None
        self._health_service = None
        self._rtc = None
        self._main_window = None
    
    def _get_config_summary(self) -> dict:
        """Get configuration summary for logging"""
        return {
            'timezone': config.get('timezone', 'UTC'),
            'display': {
                'width': config.get('display.width', 800),
                'height': config.get('display.height', 480),
                'fullscreen': config.get('display.fullscreen', True),
            },
            'weather': {
                'enabled': config.get('weather.enabled', True),
            }
        }
    
    def _initialize_services(self) -> None:
        """Initialize all services"""
        self._logger.info("Initializing services")
        
        # Clock service
        timezone = config.get('timezone', 'UTC')
        self._clock_service = ClockService(timezone)
        self._logger.info(f"Clock service initialized: timezone={timezone}")
        
        # Weather service
        if config.get('weather.enabled', True):
            api_key = config.get('weather.api_key', '')
            location = config.get('weather.location', 'Los Angeles, US')
            units = config.get('weather.units', 'imperial')
            cache_ttl = config.get('weather.cache_ttl', 900)
            
            if api_key and api_key != 'your_api_key_here':
                self._weather_service = WeatherService(api_key, location, units, cache_ttl)
                self._logger.info(f"Weather service initialized: location={location}")
            else:
                self._logger.warning("Weather disabled: no API key configured")
        else:
            self._logger.info("Weather service disabled in config")
        
        # Health service
        heartbeat_interval = config.get('health.heartbeat_interval', 5)
        timeout = config.get('health.timeout', 15)
        self._health_service = HealthService(heartbeat_interval, timeout)
        self._health_service.set_freeze_callback(self._on_ui_freeze)
        self._health_service.set_recover_callback(self._on_ui_recover)
        self._logger.info("Health service initialized")
        
        # RTC hardware
        if config.get('rtc.enabled', True):
            self._rtc = RTC(use_hardware=True)
            status = self._rtc.get_status()
            if status['hardware_rtc']:
                self._logger.info("Hardware RTC detected and enabled")
            else:
                self._logger.warning("Hardware RTC not available, using system time")
    
    def _initialize_ui(self) -> None:
        """Initialize UI window"""
        self._logger.info("Initializing UI")
        
        # Detect display or use config
        display_info = DisplayInfo()
        width = config.get('display.width', 0)
        height = config.get('display.height', 0)
        
        if width == 0 or height == 0:
            width, height = display_info.detect()
            self._logger.info(f"Auto-detected display: {width}x{height}")
        else:
            self._logger.info(f"Using configured display: {width}x{height}")
        
        fullscreen = config.get('display.fullscreen', True)
        update_interval = config.get('display.update_interval', 1000)
        
        # Create main window
        self._main_window = MainWindow(
            clock_service=self._clock_service,
            weather_service=self._weather_service,
            health_service=self._health_service,
            logger=self._logger,
            width=width,
            height=height,
            fullscreen=fullscreen,
            update_interval=update_interval
        )
        
        self._main_window.initialize()
        self._logger.info("UI initialized successfully")
    
    def _on_ui_freeze(self) -> None:
        """Callback when UI freezes"""
        self._logger.error("UI FREEZE DETECTED - display is not responding")
    
    def _on_ui_recover(self) -> None:
        """Callback when UI recovers from freeze"""
        self._logger.info("UI recovered from freeze")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self._logger.info(f"Received signal {signum}, shutting down")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self) -> None:
        """Run the application"""
        try:
            self._setup_signal_handlers()
            self._initialize_services()
            self._initialize_ui()
            
            self._logger.info("Application started successfully")
            
            # Start UI event loop (blocking)
            self._main_window.start()
            
        except KeyboardInterrupt:
            self._logger.info("Keyboard interrupt received")
        except Exception as e:
            self._logger.critical(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Cleanup and shutdown"""
        self._logger.info("Shutting down application")
        
        # Stop UI
        if self._main_window and self._main_window.is_running():
            self._main_window.stop()
        
        # Stop health monitoring
        if self._health_service:
            self._health_service.stop_monitoring()
        
        self._logger.log_shutdown()


def main():
    """Main entry point"""
    app = Application()
    app.run()


if __name__ == '__main__':
    main()

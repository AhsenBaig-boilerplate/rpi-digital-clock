"""
Main Window - Tkinter clock display with non-blocking updates
"""
import tkinter as tk
from typing import Optional, Dict, Any
from ..core.clock_service import ClockService
from ..core.weather_service import WeatherService
from ..core.health_service import HealthService
from ..core.logging_service import LoggingService
from .theme import Theme
from .layout import Layout


class MainWindow:
    """
    Main Tkinter window for digital clock display.
    """
    
    def __init__(
        self,
        clock_service: ClockService,
        weather_service: Optional[WeatherService],
        health_service: HealthService,
        logger: LoggingService,
        width: int = 800,
        height: int = 480,
        fullscreen: bool = True,
        update_interval: int = 1000
    ):
        """
        Initialize main window.
        
        Args:
            clock_service: Clock service instance
            weather_service: Weather service instance (optional)
            health_service: Health monitoring service
            logger: Logging service
            width: Window width
            height: Window height
            fullscreen: Whether to run fullscreen
            update_interval: UI update interval in milliseconds
        """
        self._clock = clock_service
        self._weather = weather_service
        self._health = health_service
        self._logger = logger
        
        self._width = width
        self._height = height
        self._fullscreen = fullscreen
        self._update_interval = update_interval
        
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._layout: Optional[Layout] = None
        
        self._text_ids: Dict[str, int] = {}
        self._running = False
        
        self._weather_update_counter = 0
        self._weather_update_frequency = 60  # Update weather every 60 UI updates (60 seconds)
    
    def initialize(self) -> None:
        """Initialize Tkinter window and canvas"""
        self._logger.info("Initializing UI window")
        
        # Create root window
        self._root = tk.Tk()
        self._root.title("RPI Digital Clock")
        self._root.configure(bg=Theme.BG_PRIMARY)
        
        # Set window size
        if self._fullscreen:
            self._root.attributes('-fullscreen', True)
            self._root.config(cursor='none')  # Hide cursor in fullscreen
        else:
            self._root.geometry(f"{self._width}x{self._height}")
        
        # Create canvas for drawing
        self._canvas = tk.Canvas(
            self._root,
            width=self._width,
            height=self._height,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize layout manager
        self._layout = Layout(self._width, self._height)
        
        # Create text elements
        self._create_ui_elements()
        
        # Bind escape key to exit fullscreen
        self._root.bind('<Escape>', self._exit_fullscreen)
        
        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self.stop)
        
        self._logger.info(f"UI initialized: {self._width}x{self._height}")
    
    def _create_ui_elements(self) -> None:
        """Create UI text elements on canvas"""
        layout = self._layout.get_full_layout()
        
        # Time display
        time_config = layout['time']
        self._text_ids['time'] = self._canvas.create_text(
            time_config['x'], time_config['y'],
            text="00:00:00",
            font=time_config['font'],
            fill=time_config['color'],
            anchor=time_config['anchor']
        )
        
        # Date display
        date_config = layout['date']
        self._text_ids['date'] = self._canvas.create_text(
            date_config['x'], date_config['y'],
            text="Loading...",
            font=date_config['font'],
            fill=date_config['color'],
            anchor=date_config['anchor']
        )
        
        # Weather display
        if self._weather:
            weather_config = layout['weather']
            self._text_ids['weather'] = self._canvas.create_text(
                weather_config['x'], weather_config['y'],
                text="Loading weather...",
                font=weather_config['font'],
                fill=weather_config['color'],
                anchor=weather_config['anchor']
            )
    
    def _update_ui(self) -> None:
        """Update UI elements with current data"""
        if not self._running:
            return
        
        try:
            # Update time
            display_data = self._clock.get_display_data()
            time_str = display_data['time_24']
            self._canvas.itemconfig(self._text_ids['time'], text=time_str)
            
            # Update date
            date_str = display_data['date_full']
            self._canvas.itemconfig(self._text_ids['date'], text=date_str)
            
            # Update weather (less frequently)
            if self._weather:
                self._weather_update_counter += 1
                if self._weather_update_counter >= self._weather_update_frequency:
                    self._update_weather()
                    self._weather_update_counter = 0
            
            # Send heartbeat to health service
            self._health.heartbeat()
            
        except Exception as e:
            self._logger.error(f"UI update error: {e}", exc_info=True)
        
        # Schedule next update
        if self._running and self._root:
            self._root.after(self._update_interval, self._update_ui)
    
    def _update_weather(self) -> None:
        """Update weather display"""
        if not self._weather or 'weather' not in self._text_ids:
            return
        
        try:
            weather_data = self._weather.get_weather()
            
            if weather_data:
                display = weather_data.get('display', {})
                temp = display.get('temp', 'N/A')
                condition = display.get('condition', 'Unknown')
                
                weather_str = f"{temp} • {condition}"
                
                # Update color based on condition
                color = Theme.get_weather_color(condition)
                self._canvas.itemconfig(
                    self._text_ids['weather'],
                    text=weather_str,
                    fill=color
                )
            else:
                self._canvas.itemconfig(
                    self._text_ids['weather'],
                    text="Weather unavailable",
                    fill=Theme.FG_DIM
                )
        
        except Exception as e:
            self._logger.error(f"Weather update error: {e}")
    
    def _exit_fullscreen(self, event=None) -> None:
        """Exit fullscreen mode"""
        if self._root and self._fullscreen:
            self._root.attributes('-fullscreen', False)
            self._root.config(cursor='')
            self._fullscreen = False
            self._logger.info("Exited fullscreen mode")
    
    def start(self) -> None:
        """Start UI event loop"""
        if not self._root:
            self.initialize()
        
        self._logger.info("Starting UI event loop")
        self._running = True
        
        # Start health monitoring
        self._health.start_monitoring()
        
        # Initial weather update
        if self._weather:
            self._update_weather()
        
        # Start UI updates
        self._root.after(self._update_interval, self._update_ui)
        
        # Run main loop
        self._root.mainloop()
    
    def stop(self) -> None:
        """Stop UI and cleanup"""
        self._logger.info("Stopping UI")
        self._running = False
        
        # Stop health monitoring
        self._health.stop_monitoring()
        
        # Destroy window
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception as e:
                self._logger.error(f"Error during UI cleanup: {e}")
        
        self._root = None
    
    def is_running(self) -> bool:
        """Check if UI is running"""
        return self._running

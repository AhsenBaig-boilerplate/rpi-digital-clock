"""
Clock UI Module - Handles the display of clock, weather, and screen burn-in prevention.
Uses Tkinter for GUI rendering on HDMI display.
"""

import tkinter as tk
from datetime import datetime
import logging
import random
from weather import WeatherService


class ClockUI:
    """Main clock UI with burn-in prevention features."""
    
    def __init__(self, config: dict):
        """Initialize the clock UI with configuration."""
        self.config = config
        self.root = None
        self.time_label = None
        self.date_label = None
        self.weather_label = None
        self.weather_service = None
        
        # Screen burn-in prevention settings
        self.screensaver_enabled = config.get('display', {}).get('screensaver_enabled', True)
        self.screensaver_start_hour = config.get('display', {}).get('screensaver_start_hour', 15)  # 3 PM
        self.screensaver_end_hour = config.get('display', {}).get('screensaver_end_hour', 12)  # 12 PM (noon)
        self.pixel_shift_enabled = config.get('display', {}).get('pixel_shift_enabled', True)
        self.pixel_shift_interval = config.get('display', {}).get('pixel_shift_interval_seconds', 30) * 1000  # Convert to ms
        self.dim_at_night = config.get('display', {}).get('dim_at_night', True)
        self.night_brightness = config.get('display', {}).get('night_brightness', 0.3)
        self.night_start_hour = config.get('display', {}).get('night_start_hour', 22)
        self.night_end_hour = config.get('display', {}).get('night_end_hour', 6)
        
        # Position tracking for pixel shift
        self.current_x_offset = 0
        self.current_y_offset = 0
        self.max_pixel_shift = 20  # Maximum pixels to shift in any direction
        
        # Screen saver state
        self.screensaver_active = False
        
        # Initialize weather service if enabled
        if config.get('weather', {}).get('enabled', False):
            self.weather_service = WeatherService(config.get('weather', {}))
        
        logging.info("Clock UI initialized")
    
    def setup_ui(self):
        """Setup the Tkinter UI elements."""
        self.root = tk.Tk()
        self.root.title("Raspberry Pi Clock")
        
        # Configure for fullscreen on TV
        self.root.attributes('-fullscreen', True)
        self.root.configure(background='black', cursor='none')
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        logging.info(f"Screen dimensions: {screen_width}x{screen_height}")
        
        # Bind escape key to exit (for development/testing)
        self.root.bind('<Escape>', lambda e: self.cleanup())
        
        # Main container frame for positioning
        self.container = tk.Frame(self.root, bg='black')
        self.container.place(relx=0.5, rely=0.5, anchor='center')
        
        # Time display configuration - auto-scale based on screen size
        time_config = self.config.get('display', {})
        font_family = time_config.get('font_family', 'Helvetica')
        
        # Scale font sizes to screen (use smaller sizes for better fit)
        time_font_size = min(time_config.get('time_font_size', 80), int(screen_height * 0.15))
        date_font_size = min(time_config.get('date_font_size', 30), int(screen_height * 0.06))
        weather_font_size = min(time_config.get('weather_font_size', 24), int(screen_height * 0.05))
        
        color = time_config.get('color', '#00FF00')
        
        # Time label with wraplength to prevent cutoff
        self.time_label = tk.Label(
            self.container,
            text="",
            font=(font_family, time_font_size, 'bold'),
            fg=color,
            bg='black',
            wraplength=int(screen_width * 0.9)
        )
        self.time_label.pack(pady=(0, 10))
        
        # Date label with wraplength
        self.date_label = tk.Label(
            self.container,
            text="",
            font=(font_family, date_font_size),
            fg=color,
            bg='black',
            wraplength=int(screen_width * 0.9)
        )
        self.date_label.pack(pady=(0, 10))
        
        # Weather label (if enabled) with wraplength
        if self.weather_service:
            self.weather_label = tk.Label(
                self.container,
                text="",
                font=(font_family, weather_font_size),
                fg=color,
                bg='black',
                wraplength=int(screen_width * 0.9)
            )
            self.weather_label.pack(pady=(0, 10))
        
        logging.info("UI setup completed")
    
    def update_time(self):
        """Update the time display."""
        if self.root is None:
            return
        
        try:
            now = datetime.now()
            
            # Check if screensaver should be active based on time schedule
            self.check_screensaver_schedule(now)
            
            # Format time based on configuration
            time_format_12h = self.config.get('time', {}).get('format_12h', True)
            show_seconds = self.config.get('display', {}).get('show_seconds', True)
            
            if time_format_12h:
                if show_seconds:
                    time_str = now.strftime("%I:%M:%S %p")
                else:
                    time_str = now.strftime("%I:%M %p")
            else:
                if show_seconds:
                    time_str = now.strftime("%H:%M:%S")
                else:
                    time_str = now.strftime("%H:%M")
            
            # Update time label
            if not self.screensaver_active:
                self.time_label.config(text=time_str)
                
                # Update date
                date_format = self.config.get('display', {}).get('date_format', "%A, %B %d, %Y")
                date_str = now.strftime(date_format)
                self.date_label.config(text=date_str)
                
                # Apply night dimming
                if self.dim_at_night:
                    self.apply_night_dimming(now)
            
            # Schedule next update (every 1 second if showing seconds, otherwise every minute)
            update_interval = 1000 if show_seconds else 60000
            self.root.after(update_interval, self.update_time)
            
        except Exception as e:
            logging.error(f"Error updating time: {e}", exc_info=True)
    
    def update_weather(self):
        """Update the weather display."""
        if self.weather_service and self.weather_label and not self.screensaver_active:
            try:
                weather_data = self.weather_service.get_weather()
                if weather_data:
                    temp = weather_data.get('temp', '--')
                    condition = weather_data.get('condition', 'Unknown')
                    humidity = weather_data.get('humidity', '--')
                    
                    weather_str = f"{condition} • {temp}° • Humidity: {humidity}%"
                    self.weather_label.config(text=weather_str)
                    logging.debug(f"Weather updated: {weather_str}")
            except Exception as e:
                logging.error(f"Error updating weather: {e}", exc_info=True)
        
        # Update weather every 10 minutes
        if self.root:
            self.root.after(600000, self.update_weather)
    
    def apply_night_dimming(self, current_time: datetime):
        """Apply dimming effect during night hours."""
        current_hour = current_time.hour
        
        # Check if we're in night hours
        is_night = False
        if self.night_start_hour > self.night_end_hour:
            # Night period crosses midnight (e.g., 22:00 to 6:00)
            is_night = current_hour >= self.night_start_hour or current_hour < self.night_end_hour
        else:
            # Night period within same day
            is_night = self.night_start_hour <= current_hour < self.night_end_hour
        
        if is_night:
            # Calculate dimmed color
            base_color = self.config.get('display', {}).get('color', '#00FF00')
            dimmed_color = self.dim_color(base_color, self.night_brightness)
            self.time_label.config(fg=dimmed_color)
            self.date_label.config(fg=dimmed_color)
            if self.weather_label:
                self.weather_label.config(fg=dimmed_color)
        else:
            # Restore original color
            original_color = self.config.get('display', {}).get('color', '#00FF00')
            self.time_label.config(fg=original_color)
            self.date_label.config(fg=original_color)
            if self.weather_label:
                self.weather_label.config(fg=original_color)
    
    def dim_color(self, hex_color: str, brightness: float) -> str:
        """Dim a hex color by a brightness factor (0.0 to 1.0)."""
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Apply brightness
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def check_screensaver_schedule(self, current_time: datetime):
        """Check if screensaver should be active based on time schedule."""
        if not self.screensaver_enabled:
            return
        
        current_hour = current_time.hour
        
        # Check if we're in screensaver hours
        should_be_active = False
        if self.screensaver_start_hour > self.screensaver_end_hour:
            # Screensaver period crosses midnight (e.g., 15:00 to 12:00)
            should_be_active = current_hour >= self.screensaver_start_hour or current_hour < self.screensaver_end_hour
        else:
            # Screensaver period within same day
            should_be_active = self.screensaver_start_hour <= current_hour < self.screensaver_end_hour
        
        if should_be_active and not self.screensaver_active:
            self.activate_screensaver()
        elif not should_be_active and self.screensaver_active:
            self.deactivate_screensaver()
    
    def apply_pixel_shift(self):
        """Apply subtle pixel shifting to prevent burn-in."""
        if not self.pixel_shift_enabled or self.screensaver_active:
            if self.root:
                self.root.after(self.pixel_shift_interval, self.apply_pixel_shift)
            return
        
        try:
            # Generate random shift within bounds
            self.current_x_offset = random.randint(-self.max_pixel_shift, self.max_pixel_shift)
            self.current_y_offset = random.randint(-self.max_pixel_shift, self.max_pixel_shift)
            
            # Update container position
            self.container.place(
                relx=0.5,
                rely=0.5,
                anchor='center',
                x=self.current_x_offset,
                y=self.current_y_offset
            )
            
            logging.debug(f"Pixel shift applied: x={self.current_x_offset}, y={self.current_y_offset}")
        except Exception as e:
            logging.error(f"Error applying pixel shift: {e}", exc_info=True)
        
        # Schedule next shift
        if self.root:
            self.root.after(self.pixel_shift_interval, self.apply_pixel_shift)
    
    def activate_screensaver(self):
        """Activate screensaver by blanking the screen."""
        self.screensaver_active = True
        self.time_label.config(text="")
        self.date_label.config(text="")
        if self.weather_label:
            self.weather_label.config(text="")
        
        logging.info("Screensaver activated - screen blanked")
    
    def deactivate_screensaver(self):
        """Deactivate screensaver and restore display."""
        if self.screensaver_active:
            self.screensaver_active = False
            logging.info("Screensaver deactivated - display restored")
    
    def run(self):
        """Start the clock UI main loop."""
        self.setup_ui()
        
        # Start update loops
        self.update_time()
        if self.weather_service:
            self.update_weather()
        
        # Start pixel shift
        if self.pixel_shift_enabled:
            self.root.after(self.pixel_shift_interval, self.apply_pixel_shift)
        
        logging.info("Clock UI running - entering main loop")
        
        # Start Tkinter main loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logging.info("UI interrupted by user")
        except Exception as e:
            logging.error(f"Error in UI main loop: {e}", exc_info=True)
    
    def cleanup(self):
        """Clean up resources and close the UI."""
        logging.info("Cleaning up UI resources")
        
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
        
        logging.info("UI cleanup completed")

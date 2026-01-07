#!/usr/bin/env python3
"""
Pygame-based clock display - reliable fullscreen rendering for Raspberry Pi.
"""

import pygame
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import yaml

# Import weather service
try:
    from weather import WeatherService
except ImportError:
    WeatherService = None


class PygameClock:
    """Pygame-based digital clock display."""
    
    def __init__(self, config: dict):
        """Initialize pygame clock."""
        self.config = config
        self.running = True
        
        # Initialize pygame
        pygame.init()
        pygame.mouse.set_visible(False)
        
        # Get display info and set fullscreen
        display_info = pygame.display.Info()
        self.screen_width = display_info.current_w
        self.screen_height = display_info.current_h
        
        logging.info(f"Screen resolution: {self.screen_width}x{self.screen_height}")
        
        # Create fullscreen display
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.FULLSCREEN
        )
        pygame.display.set_caption("Digital Clock")
        
        # Load configuration
        display_config = config.get('display', {})
        self.color = self.hex_to_rgb(display_config.get('color', '#00FF00'))
        self.bg_color = (0, 0, 0)  # Black background
        
        # Font sizes
        self.time_font_size = display_config.get('time_font_size', 120)
        self.date_font_size = display_config.get('date_font_size', 40)
        self.weather_font_size = display_config.get('weather_font_size', 30)
        
        # Time format
        time_config = config.get('time', {})
        self.format_12h = time_config.get('format_12h', True)
        self.show_seconds = display_config.get('show_seconds', True)
        
        # Initialize fonts
        self.init_fonts()
        
        # Weather service
        self.weather_service = None
        if config.get('weather', {}).get('enabled', False):
            api_key = os.environ.get('WEATHER_API_KEY') or config.get('weather', {}).get('api_key', '')
            if api_key and WeatherService:
                self.weather_service = WeatherService(config.get('weather', {}))
        
        # Clock for FPS
        self.clock = pygame.time.Clock()
        
        # Weather update tracking
        self.last_weather_update = 0
        self.weather_text = ""
        
        logging.info("Pygame clock initialized")
    
    def init_fonts(self):
        """Initialize fonts."""
        try:
            # Try to use a nice font
            font_name = self.config.get('display', {}).get('font_family', 'freesans')
            self.time_font = pygame.font.SysFont(font_name, self.time_font_size, bold=True)
            self.date_font = pygame.font.SysFont(font_name, self.date_font_size)
            self.weather_font = pygame.font.SysFont(font_name, self.weather_font_size)
            logging.info(f"Using system font: {font_name}")
        except:
            # Fallback to default font
            self.time_font = pygame.font.Font(None, self.time_font_size)
            self.date_font = pygame.font.Font(None, self.date_font_size)
            self.weather_font = pygame.font.Font(None, self.weather_font_size)
            logging.warning("Using default pygame font")
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def format_time(self, now):
        """Format time string."""
        if self.format_12h:
            if self.show_seconds:
                return now.strftime("%I:%M:%S %p")
            else:
                return now.strftime("%I:%M %p")
        else:
            if self.show_seconds:
                return now.strftime("%H:%M:%S")
            else:
                return now.strftime("%H:%M")
    
    def format_date(self, now):
        """Format date string."""
        date_format = self.config.get('display', {}).get('date_format', "%A, %B %d, %Y")
        return now.strftime(date_format)
    
    def update_weather(self):
        """Update weather data."""
        if not self.weather_service:
            return
        
        # Update every 10 minutes
        current_time = pygame.time.get_ticks()
        if current_time - self.last_weather_update < 600000:  # 10 minutes
            return
        
        try:
            weather_data = self.weather_service.get_weather()
            if weather_data:
                temp = weather_data.get('temp', '--')
                condition = weather_data.get('condition', '')
                humidity = weather_data.get('humidity', '--')
                self.weather_text = f"{condition} • {temp}° • Humidity: {humidity}%"
                logging.info(f"Weather updated: {self.weather_text}")
        except Exception as e:
            logging.error(f"Error updating weather: {e}")
        
        self.last_weather_update = current_time
    
    def render(self):
        """Render the clock display."""
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Get current time
        now = datetime.now()
        
        # Format strings
        time_str = self.format_time(now)
        date_str = self.format_date(now)
        
        # Render text surfaces
        time_surface = self.time_font.render(time_str, True, self.color)
        date_surface = self.date_font.render(date_str, True, self.color)
        
        # Calculate positions (centered)
        time_rect = time_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 60))
        date_rect = date_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2 + 60))
        
        # Blit to screen
        self.screen.blit(time_surface, time_rect)
        self.screen.blit(date_surface, date_rect)
        
        # Render weather if available
        if self.weather_text:
            weather_surface = self.weather_font.render(self.weather_text, True, self.color)
            weather_rect = weather_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2 + 120))
            self.screen.blit(weather_surface, weather_rect)
        
        # Update display
        pygame.display.flip()
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    self.running = False
    
    def run(self):
        """Main loop."""
        logging.info("Starting clock display loop")
        
        # Initial weather update
        self.update_weather()
        
        frame_count = 0
        
        try:
            while self.running:
                # Handle events
                self.handle_events()
                
                # Update weather periodically
                self.update_weather()
                
                # Render
                self.render()
                
                # Limit to 1 FPS (update once per second)
                self.clock.tick(1)
                
                frame_count += 1
                if frame_count % 60 == 0:  # Log every minute
                    logging.debug(f"Clock running - {frame_count} frames rendered")
        
        except KeyboardInterrupt:
            logging.info("Clock interrupted by user")
        except Exception as e:
            logging.error(f"Error in clock loop: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        logging.info("Cleaning up pygame resources")
        pygame.quit()
        logging.info("Clock display stopped")


def main():
    """Main entry point."""
    from utils import setup_logging
    
    # Setup logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    setup_logging(log_level)
    
    logging.info("=" * 60)
    logging.info("Raspberry Pi Digital Clock (Pygame) - Starting")
    logging.info("=" * 60)
    
    # Load configuration
    CONFIG_PATH = Path(__file__).parent / "config.yaml"
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded")
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Create and run clock
    clock = PygameClock(config)
    clock.run()


if __name__ == '__main__':
    main()

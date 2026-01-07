#!/usr/bin/env python3
"""
Pygame-based clock display - reliable fullscreen rendering for Raspberry Pi.
"""

import pygame
import os
import sys
import logging
import socket
import subprocess
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
        self.time_font_size = display_config.get('time_font_size', 180)  # Increased from 120
        self.date_font_size = display_config.get('date_font_size', 60)   # Increased from 40
        self.weather_font_size = display_config.get('weather_font_size', 40)  # Increased from 30
        
        # Time format
        time_config = config.get('time', {})
        self.format_12h = time_config.get('format_12h', True)
        self.show_seconds = display_config.get('show_seconds', True)
        
        # Initialize fonts
        self.init_fonts()
        
        # Status bar configuration
        self.status_font_size = 22  # Slightly larger for better visibility
        self.show_status_bar = True
        self.status_color = tuple(int(c * 0.6) for c in self.color)  # Dimmer version of main color
        
        # Network and sync tracking
        self.last_ntp_sync = None
        self.network_status = "Unknown"
        self.timezone_name = os.environ.get('TZ', 'UTC')
        self.last_status_check = 0
        
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
        
        # Get initial NTP sync time
        self.check_last_ntp_sync()
        
        logging.info("Pygame clock initialized")
    
    def init_fonts(self):
        """Initialize fonts."""
        try:
            # Try to use a nice font
            font_name = self.config.get('display', {}).get('font_family', 'freesans')
            self.time_font = pygame.font.SysFont(font_name, self.time_font_size, bold=True)
            self.date_font = pygame.font.SysFont(font_name, self.date_font_size)
            self.weather_font = pygame.font.SysFont(font_name, self.weather_font_size)
            self.status_font = pygame.font.SysFont(font_name, self.status_font_size)
            logging.info(f"Using system font: {font_name}")
        except:
            # Fallback to default font
            self.time_font = pygame.font.Font(None, self.time_font_size)
            self.date_font = pygame.font.Font(None, self.date_font_size)
            self.weather_font = pygame.font.Font(None, self.weather_font_size)
            self.status_font = pygame.font.Font(None, self.status_font_size)
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
    
    def check_network_status(self):
        """Check network/WiFi connectivity."""
        try:
            # Try to connect to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            # Try to get WiFi signal strength (works on Pi with wireless)
            try:
                result = subprocess.run(
                    ['iwconfig'], 
                    capture_output=True, 
                    text=True, 
                    timeout=2
                )
                if 'Link Quality' in result.stdout:
                    # Extract signal quality
                    for line in result.stdout.split('\n'):
                        if 'Link Quality' in line:
                            quality = line.split('Link Quality=')[1].split()[0]
                            self.network_status = f"WiFi {quality}"
                            return
                # WiFi interface found but no quality info
                self.network_status = "WiFi Connected"
            except:
                # Not WiFi, but has network
                self.network_status = "Ethernet Connected"
        except:
            self.network_status = "No Network"
    
    def check_last_ntp_sync(self):
        """Check last NTP synchronization time."""
        try:
            # Try timedatectl first (systemd)
            result = subprocess.run(
                ['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip() == 'yes':
                self.last_ntp_sync = datetime.now()
                return
        except:
            pass
        
        # Fallback: check if ntpdate was used (from logs or assume recent sync)
        if not self.last_ntp_sync:
            # Assume synced at startup
            self.last_ntp_sync = datetime.now()
    
    def get_time_since_sync(self):
        """Get human-readable time since last NTP sync."""
        if not self.last_ntp_sync:
            return "Never"
        
        delta = datetime.now() - self.last_ntp_sync
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    
    def update_status(self):
        """Update status information periodically."""
        current_time = pygame.time.get_ticks()
        
        # Update every 30 seconds
        if current_time - self.last_status_check < 30000:
            return
        
        self.check_network_status()
        self.last_status_check = current_time
    
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
        
        # Render status bar at bottom
        if self.show_status_bar:
            self.render_status_bar()
        
        # Update display
        pygame.display.flip()
    
    def render_status_bar(self):
        """Render status bar with system information."""
        # Status items with emojis
        status_items = []
        
        # Network status with emoji
        if self.network_status:
            if "WiFi" in self.network_status:
                icon = "📶"
            elif "Ethernet" in self.network_status:
                icon = "🌐"
            else:
                icon = "❌"
            status_items.append(f"{icon} {self.network_status}")
        else:
            status_items.append("❌ No Network")
        
        # Timezone with emoji
        if self.timezone_name:
            status_items.append(f"🌍 {self.timezone_name}")
        
        # Last sync with emoji
        status_items.append(f"🔄 {self.get_time_since_sync()}")
        
        status_text = " | ".join(status_items)
        
        # Render status text
        status_surface = self.status_font.render(status_text, True, self.status_color)
        
        # Position at bottom center with some padding
        status_rect = status_surface.get_rect(
            center=(self.screen_width // 2, self.screen_height - 20)
        )
        
        # Draw status bar
        self.screen.blit(status_surface, status_rect)
    
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
        
        # Initial updates
        self.update_weather()
        self.check_network_status()
        
        frame_count = 0
        
        try:
            while self.running:
                # Handle events
                self.handle_events()
                
                # Update weather periodically
                self.update_weather()
                
                # Update status information
                self.update_status()
                
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

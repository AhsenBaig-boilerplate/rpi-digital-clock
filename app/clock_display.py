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
import random
from datetime import datetime
from pathlib import Path
import yaml
from typing import Optional

# Import weather service
try:
    from weather import WeatherService
except ImportError:
    WeatherService = None


class PygameClock:
    """Pygame-based digital clock display."""
    
    def __init__(self, config: dict, build_info: Optional[dict] = None):
        """Initialize pygame clock with robust error handling."""
        self.config = config
        self.running = True
        self.build_info = build_info or {}
        
        # SDL configuration - must be set BEFORE pygame.init()
        os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Disable audio
        if 'SDL_VIDEODRIVER' not in os.environ:
            os.environ['SDL_VIDEODRIVER'] = 'fbcon'  # Direct framebuffer
        
        logging.info(f"SDL Video Driver: {os.environ.get('SDL_VIDEODRIVER')}")
        
        # Initialize pygame display subsystem explicitly
        try:
            pygame.display.init()
            logging.info("Pygame display subsystem initialized")
        except Exception as e:
            logging.error(f"Failed to initialize pygame display: {e}")
            raise
        
        # Disable audio explicitly (already disabled via env, but belt and suspenders)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except:
            pass
        
        # Get framebuffer resolution
        try:
            display_info = pygame.display.Info()
            self.screen_width = display_info.current_w
            self.screen_height = display_info.current_h
            logging.info(f"Framebuffer resolution: {self.screen_width}x{self.screen_height}")
        except Exception as e:
            logging.error(f"Failed to get display info: {e}")
            # Fallback to common resolution
            self.screen_width = 1920
            self.screen_height = 1200
            logging.warning(f"Using fallback resolution: {self.screen_width}x{self.screen_height}")
        
        # Create fullscreen display
        try:
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
            )
            pygame.display.set_caption("Digital Clock")
            logging.info("Pygame display created successfully")
        except Exception as e:
            logging.error(f"Failed to create display: {e}")
            raise
        
        # Hide mouse cursor
        try:
            pygame.mouse.set_visible(False)
        except:
            pass  # Not critical
        
        # Load configuration
        display_config = config.get('display', {})
        self.color = self.hex_to_rgb(display_config.get('color', '#00FF00'))
        self.bg_color = (0, 0, 0)  # Black background
        
        # Calculate font scaling based on screen resolution
        # Base sizes designed for 1920x1200, scale proportionally for other resolutions
        base_width = 1920
        base_height = 1200
        scale_factor = min(self.screen_width / base_width, self.screen_height / base_height)
        
        logging.info(f"Font scale factor: {scale_factor:.2f} (based on {self.screen_width}x{self.screen_height})")
        
        # Font sizes - scale based on resolution for optimal space usage
        # Large defaults for distance visibility (use 70-80% of screen height for time)
        base_time_size = display_config.get('time_font_size', 280)
        base_date_size = display_config.get('date_font_size', 90)
        base_weather_size = display_config.get('weather_font_size', 60)
        base_status_size = 28
        
        self.time_font_size = int(base_time_size * scale_factor)
        self.date_font_size = int(base_date_size * scale_factor)
        self.weather_font_size = int(base_weather_size * scale_factor)
        self.status_font_size = int(base_status_size * scale_factor)
        
        logging.info(f"Scaled font sizes: time={self.time_font_size}, date={self.date_font_size}, weather={self.weather_font_size}, status={self.status_font_size}")
        
        # Time format
        time_config = config.get('time', {})
        self.format_12h = time_config.get('format_12h', True)
        self.show_seconds = display_config.get('show_seconds', True)
        
        # Initialize fonts (must be after font size definitions)
        self.init_fonts()
        
        # Status bar configuration
        self.show_status_bar = True
        self.status_color = tuple(int(c * 0.6) for c in self.color)  # Dimmer version of main color
        
        # Network and sync tracking
        self.last_ntp_sync = None
        self.network_status = "Unknown"
        self.timezone_name = os.environ.get('TZ', 'UTC')
        self.last_status_check = 0
        
        # Screensaver configuration
        self.screensaver_enabled = display_config.get('screensaver_enabled', True)
        self.screensaver_start = display_config.get('screensaver_start_hour', 2)
        self.screensaver_end = display_config.get('screensaver_end_hour', 5)
        
        # Night dimming configuration
        self.dim_at_night = display_config.get('dim_at_night', True)
        self.night_brightness = display_config.get('night_brightness', 0.3)
        self.night_start = display_config.get('night_start_hour', 22)
        self.night_end = display_config.get('night_end_hour', 6)
        self.current_brightness = 1.0
        
        # Pixel shift configuration (prevent burn-in)
        self.pixel_shift_enabled = display_config.get('pixel_shift_enabled', True)
        self.pixel_shift_interval = display_config.get('pixel_shift_interval_seconds', 30) * 1000  # Convert to ms
        self.pixel_shift_disable_start = display_config.get('pixel_shift_disable_start_hour', 12)
        self.pixel_shift_disable_end = display_config.get('pixel_shift_disable_end_hour', 14)
        self.last_pixel_shift = 0
        self.pixel_shift_x = 0
        self.pixel_shift_y = 0
        self.pixel_shift_max = 10  # Maximum pixels to shift in any direction
        
        if self.screensaver_enabled:
            logging.info(f"Screensaver enabled: {self.screensaver_start:02d}:00 - {self.screensaver_end:02d}:00")
        if self.dim_at_night:
            logging.info(f"Night dimming enabled: {self.night_start:02d}:00 - {self.night_end:02d}:00 at {self.night_brightness*100:.0f}% brightness")
        if self.pixel_shift_enabled:
            logging.info(f"Pixel shift enabled: ±{self.pixel_shift_max}px every {display_config.get('pixel_shift_interval_seconds', 30)}s (disabled {self.pixel_shift_disable_start:02d}:00-{self.pixel_shift_disable_end:02d}:00)")
        
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
        
        # Log pixel shift status
        if self.pixel_shift_enabled:
            logging.info(f"Pixel shift enabled: ±{self.pixel_shift_max}px every {display_config.get('pixel_shift_interval_seconds', 30)}s")
        else:
            logging.info("Pixel shift disabled")
        
        # Log build info summary if available
        try:
            from utils import format_build_info
            logging.info(f"Build info: {format_build_info(self.build_info)}")
        except Exception:
            pass
        
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
    
    def is_in_time_window(self, current_hour, start_hour, end_hour):
        """Check if current hour is within a time window (handles midnight wraparound)."""
        if start_hour <= end_hour:
            # Normal case: e.g., 12:00 to 14:00
            return start_hour <= current_hour < end_hour
        else:
            # Wraparound case: e.g., 22:00 to 6:00 (crosses midnight)
            return current_hour >= start_hour or current_hour < end_hour
    
    def should_show_display(self):
        """Check if display should be shown (screensaver check)."""
        if not self.screensaver_enabled:
            return True
        
        current_hour = datetime.now().hour
        in_screensaver_window = self.is_in_time_window(current_hour, self.screensaver_start, self.screensaver_end)
        return not in_screensaver_window
    
    def update_brightness(self):
        """Update brightness based on time of day."""
        if not self.dim_at_night:
            self.current_brightness = 1.0
            return
        
        current_hour = datetime.now().hour
        if self.is_in_time_window(current_hour, self.night_start, self.night_end):
            self.current_brightness = self.night_brightness
        else:
            self.current_brightness = 1.0
    
    def apply_brightness(self, color):
        """Apply current brightness to a color tuple."""
        return tuple(int(c * self.current_brightness) for c in color)
    
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
    
    def update_pixel_shift(self):
        """Update pixel shift offset to prevent burn-in."""
        if not self.pixel_shift_enabled:
            return
        
        # Check if we're in the disable window
        current_hour = datetime.now().hour
        if self.is_in_time_window(current_hour, self.pixel_shift_disable_start, self.pixel_shift_disable_end):
            # Reset to center during disable window
            if self.pixel_shift_x != 0 or self.pixel_shift_y != 0:
                self.pixel_shift_x = 0
                self.pixel_shift_y = 0
                logging.info("Pixel shift disabled (viewing hours) - centered display")
            return
        
        current_time = pygame.time.get_ticks()
        if current_time - self.last_pixel_shift < self.pixel_shift_interval:
            return
        
        # Generate new random offset within max range
        self.pixel_shift_x = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
        self.pixel_shift_y = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
        self.last_pixel_shift = current_time
        
        logging.info(f"Pixel shift applied: x={self.pixel_shift_x:+d}, y={self.pixel_shift_y:+d}")
    
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
        import time as time_module
        t_start = time_module.time()
        
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Check screensaver
        if not self.should_show_display():
            pygame.display.flip()
            return
        
        # Update brightness
        self.update_brightness()
        
        # Get current time
        now = datetime.now()
        t_time = time_module.time()
        
        # Format strings
        time_str = self.format_time(now)
        date_str = self.format_date(now)
        
        # Apply brightness to colors
        display_color = self.apply_brightness(self.color)
        status_color = self.apply_brightness(self.status_color)
        
        # Render text surfaces with brightness applied
        time_surface = self.time_font.render(time_str, True, display_color)
        date_surface = self.date_font.render(date_str, True, display_color)
        t_font = time_module.time()
        
        # Calculate positions (centered) with pixel shift offset
        center_x = self.screen_width // 2 + self.pixel_shift_x
        center_y = self.screen_height // 2 + self.pixel_shift_y
        
        time_rect = time_surface.get_rect(center=(center_x, center_y - 60))
        date_rect = date_surface.get_rect(center=(center_x, center_y + 60))
        
        # Blit to screen
        self.screen.blit(time_surface, time_rect)
        self.screen.blit(date_surface, date_rect)
        
        # Render weather if available
        if self.weather_text:
            weather_surface = self.weather_font.render(self.weather_text, True, display_color)
            weather_rect = weather_surface.get_rect(center=(center_x, center_y + 120))
            self.screen.blit(weather_surface, weather_rect)
        
        # Render status bar at bottom
        if self.show_status_bar:
            self.render_status_bar(status_color)
        
        t_blit = time_module.time()
        
        # Update display
        pygame.display.flip()
        t_flip = time_module.time()
        
        # Log timing every 10 seconds
        if not hasattr(self, '_last_timing_log'):
            self._last_timing_log = 0
        if time_module.time() - self._last_timing_log > 10:
            self._last_timing_log = time_module.time()
            total = (t_flip - t_start) * 1000
            font = (t_font - t_time) * 1000
            blit = (t_blit - t_font) * 1000
            flip = (t_flip - t_blit) * 1000
            logging.info(f"Render timing: total={total:.1f}ms (font={font:.1f}ms, blit={blit:.1f}ms, flip={flip:.1f}ms) @ {self.screen_width}x{self.screen_height}")
    
    def render_status_bar(self, status_color):
        """Render status bar with system information."""
        # Status items with symbols (pygame 1.9.6 compatible - no emoji support)
        status_items = []
        
        # Network status with symbol
        if self.network_status:
            if "WiFi" in self.network_status:
                icon = "WiFi:"
            elif "Ethernet" in self.network_status:
                icon = "Net:"
            else:
                icon = "X"
            status_items.append(f"{icon} {self.network_status}")
        else:
            status_items.append("X No Network")
        
        # Timezone with symbol
        if self.timezone_name:
            status_items.append(f"TZ: {self.timezone_name}")
        
        # Last sync with symbol
        status_items.append(f"Sync: {self.get_time_since_sync()}")
        
        # Build/version info (concise)
        if self.build_info:
            try:
                ver = self.build_info.get("git_version") or ""
                sha = self.build_info.get("git_sha") or ""
                short_sha = sha[:7] if isinstance(sha, str) and sha else ""
                parts = []
                if ver:
                    parts.append(ver)
                if short_sha:
                    parts.append(short_sha)
                if parts:
                    status_items.append(" ".join(parts))
            except Exception:
                pass
        
        status_text = " | ".join(status_items)
        
        # Render status text with brightness-adjusted color
        try:
            status_surface = self.status_font.render(status_text, True, status_color)
        except UnicodeError as e:
            # Fallback to ASCII-only if Unicode fails
            logging.warning(f"Unicode error in status bar, using ASCII fallback: {e}")
            status_text = status_text.encode('ascii', 'replace').decode('ascii')
            status_surface = self.status_font.render(status_text, True, status_color)
        
        # Position at bottom center with pixel shift for burn-in protection
        status_rect = status_surface.get_rect(
            center=(self.screen_width // 2 + self.pixel_shift_x, self.screen_height - 20 + self.pixel_shift_y)
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
                
                # Update pixel shift
                self.update_pixel_shift()
                
                # Render
                self.render()
                
                # Limit to 10 FPS to catch second boundaries reliably
                self.clock.tick(10)
                
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
    from utils import setup_logging, load_build_info, format_build_info
    
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
    
    # Build info logging
    build_info = load_build_info()
    logging.info(f"Build info: {format_build_info(build_info)}")
    
    # Create and run clock
    clock = PygameClock(config, build_info=build_info)
    clock.run()


if __name__ == '__main__':
    main()

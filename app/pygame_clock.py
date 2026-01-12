#!/usr/bin/env python3
"""
Pygame-based clock with sprite caching for Pi Zero W optimization.
Renders digits once, composites from cache. Hardware-accelerated on Pi.
"""

import os
import sys
import logging
import time
import pygame
from datetime import datetime
from pathlib import Path
import yaml
from typing import Optional, Dict, Tuple

# Optional imports
try:
    from weather import WeatherService
except:
    WeatherService = None

try:
    from rtc import RTCManager
except:
    RTCManager = None


class PygameClock:
    """Hardware-accelerated pygame clock with sprite caching."""
    
    def __init__(self, config: dict, build_info: Optional[dict] = None):
        """Initialize pygame clock."""
        self.config = config
        self.build_info = build_info or {}
        self.running = True
        
        # Initialize pygame
        pygame.init()
        
        # Display configuration
        display_config = config.get('display', {})
        self.color = self.hex_to_rgb(display_config.get('color', '#00FF00'))
        self.bg_color = (0, 0, 0)
        
        # Font sizes
        self.time_font_size = display_config.get('time_font_size', 280)
        self.date_font_size = display_config.get('date_font_size', 90)
        self.status_font_size = 28
        
        # Time format
        time_config = config.get('time', {})
        format_12h_env = os.environ.get('TIME_FORMAT_12H', '').lower()
        if format_12h_env in ('true', '1', 'yes'):
            self.format_12h = True
        elif format_12h_env in ('false', '0', 'no'):
            self.format_12h = False
        else:
            self.format_12h = time_config.get('format_12h', True)
        
        show_seconds_env = os.environ.get('SHOW_SECONDS', '').lower()
        if show_seconds_env in ('true', '1', 'yes'):
            self.show_seconds = True
        elif show_seconds_env in ('false', '0', 'no'):
            self.show_seconds = False
        else:
            self.show_seconds = display_config.get('show_seconds', True)
        
        # Burn-in prevention
        self.pixel_shift_enabled = display_config.get('pixel_shift_enabled', True)
        self.pixel_shift_interval = display_config.get('pixel_shift_interval_seconds', 30)
        self.last_pixel_shift = time.time()
        self.pixel_shift_x = 0
        self.pixel_shift_y = 0
        self.pixel_shift_max = 10
        
        # Screensaver
        self.screensaver_enabled = display_config.get('screensaver_enabled', True)
        self.screensaver_start = display_config.get('screensaver_start_hour', 2)
        self.screensaver_end = display_config.get('screensaver_end_hour', 5)
        
        # Night dimming
        self.dim_at_night = display_config.get('dim_at_night', True)
        self.night_brightness = display_config.get('night_brightness', 0.3)
        self.night_start = display_config.get('night_start_hour', 22)
        self.night_end = display_config.get('night_end_hour', 6)
        self.current_brightness = 1.0
        
        # Setup display for Pi Zero framebuffer
        # Force SDL2 to use framebuffer device
        os.environ['SDL_VIDEODRIVER'] = 'fbcon'
        os.environ['SDL_FBDEV'] = '/dev/fb0'
        os.environ['SDL_NOMOUSE'] = '1'
        
        try:
            # Initialize with specific framebuffer size
            self.screen = pygame.display.set_mode((1920, 1200), pygame.HWSURFACE | pygame.DOUBLEBUF)
            logging.info(f"Pygame framebuffer mode initialized")
        except Exception as e:
            logging.error(f"Pygame init failed: {e}")
            # Fallback: try without flags
            try:
                self.screen = pygame.display.set_mode((1920, 1200))
            except Exception as e2:
                logging.error(f"Pygame fallback failed: {e2}")
                raise
        
        self.width, self.height = self.screen.get_size()
        logging.info(f"Display initialized: {self.width}x{self.height}")
        
        pygame.display.set_caption("Digital Clock")
        
        # Load fonts
        self.init_fonts()
        
        # Pre-render sprite cache
        self.sprite_cache = {}
        self.prerender_sprites()
        
        # Weather service (optional)
        self.weather_service = None
        self.weather_text = ""
        weather_config = config.get('weather', {})
        if weather_config.get('enabled', False) and WeatherService:
            api_key = os.environ.get('WEATHER_API_KEY') or weather_config.get('api_key')
            if api_key:
                try:
                    self.weather_service = WeatherService(weather_config, api_key)
                    logging.info("Weather service initialized")
                except Exception as e:
                    logging.warning(f"Weather service disabled: {e}")
        
        # Status info
        self.network_status = "Unknown"
        self.last_ntp_sync = ""
        
        # Performance tracking
        self.frame_times = []
        
        logging.info("Pygame clock initialized")
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def init_fonts(self):
        """Initialize pygame fonts."""
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        
        font_file = None
        for path in font_paths:
            if os.path.exists(path):
                font_file = path
                break
        
        if font_file:
            self.time_font = pygame.font.Font(font_file, self.time_font_size)
            self.date_font = pygame.font.Font(font_file, self.date_font_size)
            self.status_font = pygame.font.Font(font_file, self.status_font_size)
            logging.info(f"Using font: {font_file}")
        else:
            self.time_font = pygame.font.Font(None, self.time_font_size)
            self.date_font = pygame.font.Font(None, self.date_font_size)
            self.status_font = pygame.font.Font(None, self.status_font_size)
            logging.warning("Using default pygame font")
    
    def prerender_sprites(self):
        """Pre-render all possible characters as sprites."""
        logging.info("Pre-rendering sprite cache...")
        
        # Characters needed: 0-9, :, space, A, M, P
        chars = '0123456789: AMP'
        
        for char in chars:
            # Time sprites (large)
            surface = self.time_font.render(char, True, self.color)
            self.sprite_cache[f'time_{char}'] = surface
            
            # Date sprites (medium)
            if char.isdigit() or char in ' ,-/:':
                surface = self.date_font.render(char, True, self.color)
                self.sprite_cache[f'date_{char}'] = surface
        
        # Pre-render common date words
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for word in months + days:
            surface = self.date_font.render(word, True, self.color)
            self.sprite_cache[f'date_{word}'] = surface
        
        logging.info(f"Cached {len(self.sprite_cache)} sprites")
    
    def render_text_from_cache(self, text: str, y_pos: int, prefix: str = 'time') -> pygame.Rect:
        """Render text by compositing cached sprites."""
        x_offset = 0
        total_width = 0
        total_height = 0
        
        # Calculate total width first for centering
        for char in text:
            key = f'{prefix}_{char}'
            if key in self.sprite_cache:
                sprite = self.sprite_cache[key]
                total_width += sprite.get_width()
                total_height = max(total_height, sprite.get_height())
        
        # Center horizontally with pixel shift
        x_start = (self.width - total_width) // 2 + self.pixel_shift_x
        x_offset = x_start
        
        # Render each character
        for char in text:
            key = f'{prefix}_{char}'
            if key in self.sprite_cache:
                sprite = self.sprite_cache[key]
                self.screen.blit(sprite, (x_offset, y_pos + self.pixel_shift_y))
                x_offset += sprite.get_width()
            elif prefix == 'date':
                # Try whole word lookup for date
                remaining = text[text.index(char):]
                for word_len in range(len(remaining), 0, -1):
                    word = remaining[:word_len]
                    word_key = f'date_{word}'
                    if word_key in self.sprite_cache:
                        sprite = self.sprite_cache[word_key]
                        self.screen.blit(sprite, (x_offset, y_pos + self.pixel_shift_y))
                        x_offset += sprite.get_width()
                        # Skip ahead
                        for _ in range(word_len - 1):
                            text = text[1:]
                        break
        
        return pygame.Rect(x_start, y_pos + self.pixel_shift_y, total_width, total_height)
    
    def render_text_direct(self, text: str, font: pygame.font.Font, y_pos: int) -> pygame.Rect:
        """Fallback: render text directly (not from cache)."""
        color = self.apply_brightness(self.color)
        surface = font.render(text, True, color)
        x_pos = (self.width - surface.get_width()) // 2 + self.pixel_shift_x
        self.screen.blit(surface, (x_pos, y_pos + self.pixel_shift_y))
        return pygame.Rect(x_pos, y_pos + self.pixel_shift_y, surface.get_width(), surface.get_height())
    
    def apply_brightness(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Apply brightness adjustment to color."""
        return tuple(int(c * self.current_brightness) for c in color)
    
    def update_brightness(self):
        """Update brightness based on time of day."""
        if not self.dim_at_night:
            self.current_brightness = 1.0
            return
        
        current_hour = datetime.now().hour
        
        # Check if in night hours
        if self.night_start > self.night_end:
            # Spans midnight
            in_night = current_hour >= self.night_start or current_hour < self.night_end
        else:
            in_night = self.night_start <= current_hour < self.night_end
        
        self.current_brightness = self.night_brightness if in_night else 1.0
    
    def should_show_display(self) -> bool:
        """Check if display should be shown (screensaver)."""
        if not self.screensaver_enabled:
            return True
        
        current_hour = datetime.now().hour
        
        if self.screensaver_start > self.screensaver_end:
            # Spans midnight
            return not (current_hour >= self.screensaver_start or current_hour < self.screensaver_end)
        else:
            return not (self.screensaver_start <= current_hour < self.screensaver_end)
    
    def update_pixel_shift(self):
        """Update pixel shift for burn-in prevention."""
        if not self.pixel_shift_enabled:
            self.pixel_shift_x = 0
            self.pixel_shift_y = 0
            return
        
        now = time.time()
        if now - self.last_pixel_shift >= self.pixel_shift_interval:
            # Simple random walk
            import random
            self.pixel_shift_x = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.pixel_shift_y = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.last_pixel_shift = now
    
    def format_time(self, dt: datetime) -> str:
        """Format time string."""
        if self.format_12h:
            if self.show_seconds:
                return dt.strftime('%I:%M:%S %p').lstrip('0')
            else:
                return dt.strftime('%I:%M %p').lstrip('0')
        else:
            if self.show_seconds:
                return dt.strftime('%H:%M:%S')
            else:
                return dt.strftime('%H:%M')
    
    def format_date(self, dt: datetime) -> str:
        """Format date string."""
        date_format = self.config.get('display', {}).get('date_format', '%A, %B %d, %Y')
        return dt.strftime(date_format)
    
    def render(self):
        """Render the clock display."""
        t_start = time.time()
        
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Check screensaver
        if not self.should_show_display():
            pygame.display.flip()
            return
        
        # Update brightness and pixel shift
        self.update_brightness()
        self.update_pixel_shift()
        
        # Get current time
        now = datetime.now()
        time_str = self.format_time(now)
        date_str = self.format_date(now)
        
        # Render time (centered, upper portion)
        center_y = self.height // 2
        time_y = center_y - 100
        self.render_text_from_cache(time_str, time_y, 'time')
        
        # Render date (centered, lower portion)
        date_y = center_y + 80
        self.render_text_direct(date_str, self.date_font, date_y)
        
        # Render status bar (bottom)
        if self.build_info:
            version = self.build_info.get('git_version', '')
            sha = self.build_info.get('git_sha', '')[:7] if self.build_info.get('git_sha') else ''
            status_text = f"{version} {sha}" if version or sha else ""
            if status_text:
                color = self.apply_brightness(tuple(int(c * 0.3) for c in self.color))
                status_surface = self.status_font.render(status_text, True, color)
                status_x = self.width - status_surface.get_width() - 20
                status_y = self.height - status_surface.get_height() - 20
                self.screen.blit(status_surface, (status_x, status_y))
        
        # Update display
        pygame.display.flip()
        
        # Track performance
        elapsed = (time.time() - t_start) * 1000
        self.frame_times.append(elapsed)
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)
        
        if len(self.frame_times) % 60 == 0:
            avg = sum(self.frame_times) / len(self.frame_times)
            logging.info(f"Render timing: avg={avg:.1f}ms, last={elapsed:.1f}ms")
    
    def run(self):
        """Main loop."""
        logging.info("Starting pygame clock loop")
        
        clock = pygame.time.Clock()
        last_second = -1
        
        try:
            while self.running:
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                            self.running = False
                
                # Render on second change
                current_second = datetime.now().second
                if current_second != last_second:
                    self.render()
                    last_second = current_second
                
                # Cap at 60 FPS (will mostly idle waiting for second change)
                clock.tick(60)
        
        except KeyboardInterrupt:
            logging.info("Clock interrupted by user")
        finally:
            pygame.quit()
            logging.info("Pygame clock shutdown complete")


def main():
    """Main entry point."""
    # Setup logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("============================================================")
    logging.info("Raspberry Pi Digital Clock (Pygame) - Starting")
    logging.info("============================================================")
    
    # Load configuration
    config_path = Path(__file__).parent / 'config.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded")
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        config = {}
    
    # Load build info
    build_info = {}
    build_info_path = Path('/app/build_info.json')
    if build_info_path.exists():
        try:
            import json
            with open(build_info_path, 'r') as f:
                build_info = json.load(f)
            logging.info(f"Build info: {build_info}")
        except Exception as e:
            logging.warning(f"Could not load build info: {e}")
    
    # Create and run clock
    try:
        clock = PygameClock(config, build_info)
        clock.run()
    except Exception as e:
        logging.error(f"Clock failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

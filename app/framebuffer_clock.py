#!/usr/bin/env python3
"""
Direct framebuffer clock display - fast rendering for Raspberry Pi.
No X11, no pygame - just raw framebuffer access via PIL.
"""

import os
import sys
import logging
import socket
import subprocess
import random
import time
from datetime import datetime
from pathlib import Path
import yaml
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

# Import weather service
try:
    from weather import WeatherService
except ImportError:
    WeatherService = None


class FramebufferClock:
    """Direct framebuffer digital clock display."""
    
    def __init__(self, config: dict, build_info: Optional[dict] = None):
        """Initialize framebuffer clock."""
        self.config = config
        self.running = True
        self.build_info = build_info or {}
        
        # Open framebuffer device
        self.fb_device = os.environ.get('FRAMEBUFFER', '/dev/fb0')
        logging.info(f"Opening framebuffer device: {self.fb_device}")
        
        # Get framebuffer info
        self.fb_width, self.fb_height = self.get_framebuffer_size()
        logging.info(f"Framebuffer resolution: {self.fb_width}x{self.fb_height}")
        
        
        # Detect framebuffer pixel format
        self.fb_bpp = self.get_bits_per_pixel()
        logging.info(f"Framebuffer bits-per-pixel: {self.fb_bpp}")
        # Load configuration
        display_config = config.get('display', {})
        self.color = self.hex_to_rgb(display_config.get('color', '#00FF00'))
        self.bg_color = (0, 0, 0)  # Black background
        
        # Font sizes
        self.time_font_size = display_config.get('time_font_size', 280)
        self.date_font_size = display_config.get('date_font_size', 90)
        self.weather_font_size = display_config.get('weather_font_size', 60)
        self.status_font_size = 28
        
        logging.info(f"Font sizes: time={self.time_font_size}, date={self.date_font_size}, weather={self.weather_font_size}, status={self.status_font_size}")
        
        # Time format
        time_config = config.get('time', {})
        self.format_12h = time_config.get('format_12h', True)
        self.show_seconds = display_config.get('show_seconds', True)
        
        # Initialize fonts
        self.init_fonts()
        
        # Status bar configuration
        self.show_status_bar = True
        self.status_color = tuple(int(c * 0.6) for c in self.color)
        
        # Network and sync tracking
        self.last_ntp_sync = None
        self.network_status = "Unknown"
        self.timezone_name = os.environ.get('TIMEZONE') or os.environ.get('TZ') or 'UTC'
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
        
        # Pixel shift configuration
        self.pixel_shift_enabled = display_config.get('pixel_shift_enabled', True)
        self.pixel_shift_interval = display_config.get('pixel_shift_interval_seconds', 30)
        self.pixel_shift_disable_start = display_config.get('pixel_shift_disable_start_hour', 12)
        self.pixel_shift_disable_end = display_config.get('pixel_shift_disable_end_hour', 14)
        self.last_pixel_shift = 0
        self.pixel_shift_x = 0
        self.pixel_shift_y = 0
        self.pixel_shift_max = 10
        
        # Weather service
        self.weather_service = None
        weather_enabled = os.environ.get('WEATHER_ENABLED', '').lower() in ('true', '1', 'yes') or config.get('weather', {}).get('enabled', False)
        if weather_enabled:
            api_key = os.environ.get('WEATHER_API_KEY') or config.get('weather', {}).get('api_key', '')
            location = os.environ.get('WEATHER_LOCATION') or config.get('weather', {}).get('location', '')
            if api_key and location and WeatherService:
                self.weather_service = WeatherService(config.get('weather', {}))
                logging.info(f"Weather service enabled for location: {location}")
            elif not api_key:
                logging.warning("Weather service disabled: WEATHER_API_KEY not set")
            elif not location:
                logging.warning("Weather service disabled: WEATHER_LOCATION not set")
        
        # Weather update tracking
        self.last_weather_update = 0
        self.weather_text = ""
        
        # Get initial NTP sync time
        self.check_last_ntp_sync()
        
        # Log build info
        try:
            from utils import format_build_info
            logging.info(f"Build info: {format_build_info(self.build_info)}")
        except Exception:
            pass
        
        logging.info("Framebuffer clock initialized")
    
    def get_framebuffer_size(self):
        """Get framebuffer dimensions."""
        try:
            with open('/sys/class/graphics/fb0/virtual_size', 'r') as f:
                w, h = f.read().strip().split(',')
                return int(w), int(h)
        except:
            # Fallback to common size
            return 1920, 1200
    
    def get_bits_per_pixel(self) -> int:
        """Read framebuffer bits-per-pixel from sysfs, default to 16 if unknown."""
        try:
            with open('/sys/class/graphics/fb0/bits_per_pixel', 'r') as f:
                bpp = int(f.read().strip())
                return bpp
        except Exception:
            return 16
    
    def init_fonts(self):
        """Initialize TrueType fonts."""
        try:
            # Try to find Helvetica or similar fonts
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
            
            if not font_file:
                raise Exception("No suitable font found")
            
            self.time_font = ImageFont.truetype(font_file, self.time_font_size)
            self.date_font = ImageFont.truetype(font_file, self.date_font_size)
            self.weather_font = ImageFont.truetype(font_file, self.weather_font_size)
            self.status_font = ImageFont.truetype(font_file, self.status_font_size)
            logging.info(f"Using TrueType font: {font_file}")
        except Exception as e:
            logging.error(f"Failed to load TrueType fonts: {e}")
            # Fallback to default PIL font
            self.time_font = ImageFont.load_default()
            self.date_font = ImageFont.load_default()
            self.weather_font = ImageFont.load_default()
            self.status_font = ImageFont.load_default()
            logging.warning("Using default PIL font")
    
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
        """Check if current hour is within a time window."""
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:
            return current_hour >= start_hour or current_hour < end_hour
    
    def should_show_display(self):
        """Check if display should be shown."""
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
        """Check network connectivity."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.network_status = "Connected"
        except:
            self.network_status = "No Network"
    
    def check_last_ntp_sync(self):
        """Check last NTP synchronization time."""
        try:
            result = subprocess.run(['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip() == 'yes':
                self.last_ntp_sync = datetime.now()
        except:
            if not self.last_ntp_sync:
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
        """Update pixel shift offset."""
        if not self.pixel_shift_enabled:
            return
        current_hour = datetime.now().hour
        if self.is_in_time_window(current_hour, self.pixel_shift_disable_start, self.pixel_shift_disable_end):
            return
        
        now = time.time()
        if now - self.last_pixel_shift > self.pixel_shift_interval:
            self.pixel_shift_x = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.pixel_shift_y = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.last_pixel_shift = now
            logging.debug(f"Pixel shift applied: x={self.pixel_shift_x:+d}, y={self.pixel_shift_y:+d}")
    
    def update_weather(self):
        """Update weather information periodically."""
        if not self.weather_service:
            return
        now = time.time()
        if now - self.last_weather_update > 600:  # Update every 10 minutes
            try:
                weather = self.weather_service.get_weather()
                if weather:
                    self.weather_text = f"{weather.get('temp', '')}° {weather.get('description', '')}"
                self.last_weather_update = now
            except Exception as e:
                logging.error(f"Weather update failed: {e}")
    
    def update_status(self):
        """Update status information periodically."""
        now = time.time()
        if now - self.last_status_check > 30:  # Update every 30 seconds
            self.check_network_status()
            self.check_last_ntp_sync()
            self.last_status_check = now
    
    def render(self):
        """Render the clock display to framebuffer."""
        t_start = time.time()
        
        try:
            # Create image
            image = Image.new('RGB', (self.fb_width, self.fb_height), self.bg_color)
            draw = ImageDraw.Draw(image)
            
            # Check screensaver
            if not self.should_show_display():
                logging.debug("Screensaver active - blanking display")
                self.write_to_framebuffer(image)
                return
        except Exception as e:
            logging.error(f"Error in render setup: {e}", exc_info=True)
            return
        
        # Update brightness
        self.update_brightness()
        
        # Get current time
        now = datetime.now()
        time_str = self.format_time(now)
        date_str = self.format_date(now)
        
        # Apply brightness
        display_color = self.apply_brightness(self.color)
        status_color = self.apply_brightness(self.status_color)
        
        t_prep = time.time()
        
        # Calculate center position with pixel shift
        center_x = self.fb_width // 2 + self.pixel_shift_x
        center_y = self.fb_height // 2 + self.pixel_shift_y
        
        # Draw time (centered)
        time_bbox = draw.textbbox((0, 0), time_str, font=self.time_font)
        time_w = time_bbox[2] - time_bbox[0]
        time_h = time_bbox[3] - time_bbox[1]
        time_x = center_x - time_w // 2
        time_y = center_y - time_h // 2 - 60
        draw.text((time_x, time_y), time_str, font=self.time_font, fill=display_color)
        
        # Draw date (centered)
        date_bbox = draw.textbbox((0, 0), date_str, font=self.date_font)
        date_w = date_bbox[2] - date_bbox[0]
        date_x = center_x - date_w // 2
        date_y = center_y + 60
        draw.text((date_x, date_y), date_str, font=self.date_font, fill=display_color)
        
        # Draw weather if available
        if self.weather_text:
            weather_bbox = draw.textbbox((0, 0), self.weather_text, font=self.weather_font)
            weather_w = weather_bbox[2] - weather_bbox[0]
            weather_x = center_x - weather_w // 2
            weather_y = center_y + 120
            draw.text((weather_x, weather_y), self.weather_text, font=self.weather_font, fill=display_color)
        
        # Draw status bar
        if self.show_status_bar:
            status_items = []
            if self.network_status:
                status_items.append(f"Net: {self.network_status}")
            if self.timezone_name:
                status_items.append(f"TZ: {self.timezone_name}")
            status_items.append(f"Sync: {self.get_time_since_sync()}")
            
            # Add version info
            if self.build_info:
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
            
            status_text = " | ".join(status_items)
            status_bbox = draw.textbbox((0, 0), status_text, font=self.status_font)
            status_w = status_bbox[2] - status_bbox[0]
            status_x = self.fb_width // 2 - status_w // 2
            status_y = self.fb_height - 30
            draw.text((status_x, status_y), status_text, font=self.status_font, fill=status_color)
        
        t_draw = time.time()
        
        # Write to framebuffer
        self.write_to_framebuffer(image)
        
        t_write = time.time()
        
        # Log timing periodically
        if not hasattr(self, '_last_timing_log'):
            self._last_timing_log = 0
        if time.time() - self._last_timing_log > 10:
            self._last_timing_log = time.time()
            total = (t_write - t_start) * 1000
            prep = (t_prep - t_start) * 1000
            draw_time = (t_draw - t_prep) * 1000
            write = (t_write - t_draw) * 1000
            logging.info(f"Render timing: total={total:.1f}ms (prep={prep:.1f}ms, draw={draw_time:.1f}ms, write={write:.1f}ms) @ {self.fb_width}x{self.fb_height}")
    
    def write_to_framebuffer(self, image):
        """Write image directly to framebuffer device."""
        try:
            # Convert image to match framebuffer pixel format
            if self.fb_bpp == 32:
                # BGRA is commonly used; alpha ignored by framebuffer
                buf = image.convert('BGRA').tobytes()
            elif self.fb_bpp == 24:
                # 24-bit BGR
                buf = image.convert('BGR').tobytes()
            elif self.fb_bpp == 16:
                # 16-bit RGB565 - fast conversion using array module
                # RGB565: RRRRRGGGGGGBBBBB (5 bits red, 6 bits green, 5 bits blue)
                import array
                rgb_image = image.convert('RGB')
                rgb_bytes = rgb_image.tobytes()
                
                # Pre-allocate uint16 array
                pixel_count = self.fb_width * self.fb_height
                rgb565 = array.array('H')  # unsigned short (uint16)
                
                # Vectorized conversion: process pixels in stride
                for i in range(0, len(rgb_bytes), 3):
                    r = (rgb_bytes[i] >> 3) & 0x1F       # Top 5 bits of red
                    g = (rgb_bytes[i+1] >> 2) & 0x3F     # Top 6 bits of green
                    b = (rgb_bytes[i+2] >> 3) & 0x1F     # Top 5 bits of blue
                    rgb565.append((r << 11) | (g << 5) | b)
                
                buf = rgb565.tobytes()
            else:
                # Fallback: write 24-bit BGR
                buf = image.convert('BGR').tobytes()
            
            expected_size = self.fb_width * self.fb_height * max(1, self.fb_bpp // 8)
            if len(buf) != expected_size:
                logging.warning(f"Framebuffer write size mismatch: expected={expected_size}, got={len(buf)} (bpp={self.fb_bpp})")
            with open(self.fb_device, 'wb') as fb:
                fb.write(buf)
        except Exception as e:
            logging.error(f"Failed to write to framebuffer: {e}")
    
    def run(self):
        """Main loop."""
        logging.info("Starting framebuffer clock display loop")
        
        # Initial updates
        self.update_weather()
        self.check_network_status()
        
        frame_count = 0
        
        try:
            while self.running:
                # Update weather periodically
                self.update_weather()
                
                # Update status information
                self.update_status()
                
                # Update pixel shift
                self.update_pixel_shift()
                
                # Render
                self.render()
                
                # Sleep for 100ms (10 FPS)
                time.sleep(0.1)
                
                frame_count += 1
                if frame_count % 600 == 0:  # Log every minute
                    logging.debug(f"Clock running - {frame_count} frames rendered")
        
        except KeyboardInterrupt:
            logging.info("Clock interrupted by user")
        except Exception as e:
            logging.error(f"Error in clock loop: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        logging.info("Framebuffer clock stopped")


def main():
    """Main entry point."""
    from utils import setup_logging, load_build_info, format_build_info
    
    # Setup logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    setup_logging(log_level)
    
    logging.info("=" * 60)
    logging.info("Raspberry Pi Digital Clock (Framebuffer) - Starting")
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
    clock = FramebufferClock(config, build_info=build_info)
    clock.run()


if __name__ == '__main__':
    main()

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
import select
import termios
import tty
from datetime import datetime
from pathlib import Path
import yaml
from PIL import Image, ImageDraw, ImageFont
import numpy as np
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
        
        # Shadow framebuffer buffer (RGB565) for partial updates
        if self.get_bits_per_pixel() != 16:
            logging.warning("Optimized blitter assumes 16bpp RGB565; other bpp will fallback to full-frame writes")
        self.fb_shadow = np.zeros((self.fb_height, self.fb_width), dtype='<u2')
        # Track last drawn rects for clearing
        self._last_time_rect = None
        self._last_date_rect = None
        self._last_status_rect = None
        
        
        # Detect framebuffer pixel format
        self.fb_bpp = self.get_bits_per_pixel()
        logging.info(f"Framebuffer bits-per-pixel: {self.fb_bpp}")
        # Load configuration
        display_config = config.get('display', {})
        self.color = self.hex_to_rgb(display_config.get('color', '#00FF00'))
        self.bg_color = (0, 0, 0)  # Black background
        
        # Base font sizes (before scaling)
        self.base_time_font_size = display_config.get('time_font_size', 280)
        self.base_date_font_size = display_config.get('date_font_size', 90)
        self.base_weather_font_size = display_config.get('weather_font_size', 60)
        self.status_font_size = 28
        
        # Optional logical resolution scaling from env DISPLAY_RESOLUTION (e.g. "1280x720")
        scale = self.get_display_scale()
        self.time_font_size = max(10, int(self.base_time_font_size * scale))
        self.date_font_size = max(8, int(self.base_date_font_size * scale))
        self.weather_font_size = max(8, int(self.base_weather_font_size * scale))
        
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
        
        # Settings menu state
        self.show_settings_menu = False
        
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

    def get_display_scale(self) -> float:
        """Compute scale factor based on DISPLAY_RESOLUTION env var.
        If not set or invalid, return 1.0. Scale is capped at 1.0 (no upscaling).
        """
        env_res = os.environ.get('DISPLAY_RESOLUTION', '').lower().strip()
        if not env_res or 'x' not in env_res:
            return 1.0
        try:
            parts = env_res.split('x')
            lw = int(parts[0])
            lh = int(parts[1])
            if lw <= 0 or lh <= 0:
                return 1.0
            sw = min(1.0, lw / float(self.fb_width))
            sh = min(1.0, lh / float(self.fb_height))
            scale = min(sw, sh)
            logging.info(f"DISPLAY_RESOLUTION={lw}x{lh} -> scale={scale:.3f}")
            return scale if scale > 0 else 1.0
        except Exception:
            return 1.0
    
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
                # Prefer Linux-specific %-I to suppress leading zero; fallback if unsupported
                try:
                    return now.strftime("%-I:%M:%S %p")
                except Exception:
                    s = now.strftime("%I:%M:%S %p")
                    return s.lstrip('0') if s.startswith('0') else s
            else:
                try:
                    return now.strftime("%-I:%M %p")
                except Exception:
                    s = now.strftime("%I:%M %p")
                    return s.lstrip('0') if s.startswith('0') else s
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
        """Render the clock display using partial updates into shadow buffer."""
        t_start = time.time()
        
        try:
            # If screensaver, blank shadow and write
            if not self.should_show_display():
                logging.debug("Screensaver active - blanking display")
                self.fb_shadow.fill(0)
                self.write_to_framebuffer(None)
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
        
        # Calculate center position with pixel shift (full resolution)
        center_x = self.fb_width // 2 + self.pixel_shift_x
        center_y = self.fb_height // 2 + self.pixel_shift_y
        
        # Dynamic margins and offsets scaled to DISPLAY_RESOLUTION if provided
        scale = self.get_display_scale()
        margin = int(10 * scale)
        time_offset_y = int(60 * scale)
        date_offset_y = int(100 * scale)
        
        # Render time to its own surface (RGB888), then blit
        time_bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0,0), time_str, font=self.time_font)
        time_w = time_bbox[2] - time_bbox[0]
        time_h = time_bbox[3] - time_bbox[1]
        # Clamp to avoid cropping
        time_x = max(margin, min(self.fb_width - margin - time_w, center_x - time_w // 2))
        time_y = max(margin, min(self.fb_height - margin - time_h, center_y - time_h // 2 - time_offset_y))
        time_img = Image.new('RGB', (time_w, time_h), (0,0,0))
        # Draw at negative bbox origin to include full glyph bounds
        ImageDraw.Draw(time_img).text((-time_bbox[0], -time_bbox[1]), time_str, font=self.time_font, fill=display_color)
        self.blit_rgb_image(time_img, time_x, time_y, clear_last_rect_attr='_last_time_rect')
        
        # Render date
        date_bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0,0), date_str, font=self.date_font)
        date_w = date_bbox[2] - date_bbox[0]
        date_h = date_bbox[3] - date_bbox[1]
        date_x = max(margin, min(self.fb_width - margin - date_w, center_x - date_w // 2))
        date_y = max(margin, min(self.fb_height - margin - date_h, center_y + date_offset_y))
        date_img = Image.new('RGB', (date_w, date_h), (0,0,0))
        # Draw at negative bbox origin to include full glyph bounds
        ImageDraw.Draw(date_img).text((-date_bbox[0], -date_bbox[1]), date_str, font=self.date_font, fill=display_color)
        self.blit_rgb_image(date_img, date_x, date_y, clear_last_rect_attr='_last_date_rect')
        
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
            # Network with emoji
            if self.network_status:
                if "Connected" in self.network_status:
                    status_items.append(f"🌐 {self.network_status}")
                else:
                    status_items.append(f"✗ {self.network_status}")
            # Timezone with emoji
            if self.timezone_name:
                status_items.append(f"📍 {self.timezone_name}")
            # Sync with emoji
            sync_time = self.get_time_since_sync()
            if sync_time == "Just now" or "m ago" in sync_time:
                status_items.append(f"✓ Sync: {sync_time}")
            else:
                status_items.append(f"⏰ Sync: {sync_time}")
            
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
            status_bbox = ImageDraw.Draw(Image.new('RGB', (1,1))).textbbox((0,0), status_text, font=self.status_font)
            status_w = status_bbox[2] - status_bbox[0]
            status_h = status_bbox[3] - status_bbox[1]
            # Apply pixel shift to status bar for burn-in protection
            status_x = max(margin, min(self.fb_width - margin - status_w, self.fb_width // 2 - status_w // 2 + self.pixel_shift_x))
            status_y = max(margin, self.fb_height - status_h - margin + self.pixel_shift_y)
            status_img = Image.new('RGB', (status_w, status_h), (0,0,0))
            # Draw at negative bbox origin to include full glyph bounds
            ImageDraw.Draw(status_img).text((-status_bbox[0], -status_bbox[1]), status_text, font=self.status_font, fill=status_color)
            self.blit_rgb_image(status_img, status_x, status_y, clear_last_rect_attr='_last_status_rect')
        
        t_draw = time.time()
        # Write shadow buffer to framebuffer
        self.write_to_framebuffer(None)
        t_write = time.time()
        
        # Log timing on every render for debugging
        if not hasattr(self, '_last_timing_log'):
            self._last_timing_log = 0
        if time.time() - self._last_timing_log > 5:  # Log every 5 seconds
            self._last_timing_log = time.time()
            total = (t_write - t_start) * 1000
            prep = (t_prep - t_start) * 1000
            draw_time = (t_draw - t_prep) * 1000
            write = (t_write - t_draw) * 1000
            logging.info(f"Render timing: total={total:.1f}ms (prep={prep:.1f}ms, draw={draw_time:.1f}ms, write={write:.1f}ms) @ {self.fb_width}x{self.fb_height}")
    
    def write_to_framebuffer(self, image):
        """Write image directly to framebuffer device."""
        try:
            # For partial-update path we write the shadow buffer
            if self.fb_bpp == 16 and isinstance(self.fb_shadow, np.ndarray):
                with open(self.fb_device, 'wb') as fb:
                    fb.write(self.fb_shadow.tobytes())
            else:
                # Fallback: full-frame conversion from provided image
                if self.fb_bpp == 32:
                    buf = image.convert('BGRA').tobytes()
                elif self.fb_bpp == 24:
                    buf = image.convert('BGR').tobytes()
                elif self.fb_bpp == 16:
                    rgb_image = image.convert('RGB')
                    arr = np.frombuffer(rgb_image.tobytes(), dtype=np.uint8).reshape((self.fb_height, self.fb_width, 3))
                    r = (arr[:, :, 0] >> 3).astype(np.uint16)
                    g = (arr[:, :, 1] >> 2).astype(np.uint16)
                    b = (arr[:, :, 2] >> 3).astype(np.uint16)
                    buf = ((r << 11) | (g << 5) | b).astype('<u2').tobytes()
                else:
                    buf = image.convert('BGR').tobytes()
                with open(self.fb_device, 'wb') as fb:
                    fb.write(buf)
        except Exception as e:
            logging.error(f"Failed to write to framebuffer: {e}")

    def blit_rgb_image(self, img: Image.Image, x: int, y: int, clear_last_rect_attr: str):
        """Convert a small RGB888 PIL image to RGB565 and blit into shadow buffer at (x,y).
        Clears previous rect stored in the attribute to avoid trails.
        """
        if self.fb_bpp != 16 or not isinstance(self.fb_shadow, np.ndarray):
            # Fallback: draw onto a full-size image (rare path)
            full = Image.new('RGB', (self.fb_width, self.fb_height), self.bg_color)
            full.paste(img, (x, y))
            self.write_to_framebuffer(full)
            return
        # Clear previous rect if any
        last_rect = getattr(self, clear_last_rect_attr, None)
        if last_rect:
            lx, ly, lw, lh = last_rect
            lx2 = max(0, min(self.fb_width, lx + lw))
            ly2 = max(0, min(self.fb_height, ly + lh))
            self.fb_shadow[ly:ly2, lx:lx2].fill(0)
        w, h = img.size
        if w <= 0 or h <= 0:
            return
        # Bounds clamp
        x2 = min(self.fb_width, x + w)
        y2 = min(self.fb_height, y + h)
        w = max(0, x2 - x)
        h = max(0, y2 - y)
        if w == 0 or h == 0:
            return
        # Convert to RGB565
        arr = np.frombuffer(img.tobytes(), dtype=np.uint8).reshape((img.height, img.width, 3))[:h, :w]
        r = (arr[:, :, 0] >> 3).astype(np.uint16)
        g = (arr[:, :, 1] >> 2).astype(np.uint16)
        b = (arr[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = ((r << 11) | (g << 5) | b)
        # Blit into shadow
        self.fb_shadow[y:y2, x:x2] = rgb565
        # Store rect
        setattr(self, clear_last_rect_attr, (x, y, w, h))
    
    def render_settings_menu(self):
        """Render on-screen settings menu overlay."""
        # Create semi-transparent overlay
        overlay_w = int(self.fb_width * 0.6)
        overlay_h = int(self.fb_height * 0.8)
        overlay_x = (self.fb_width - overlay_w) // 2
        overlay_y = (self.fb_height - overlay_h) // 2
        
        # Create menu background with border
        menu_img = Image.new('RGB', (overlay_w, overlay_h), (20, 20, 40))
        draw = ImageDraw.Draw(menu_img)
        
        # Draw border
        draw.rectangle([0, 0, overlay_w-1, overlay_h-1], outline=(0, 255, 0), width=3)
        
        # Menu title
        title_text = "⚙ SETTINGS MENU"
        title_font = self.date_font
        draw.text((20, 20), title_text, font=title_font, fill=(0, 255, 0))
        
        # Menu items
        menu_items = [
            "",
            "Press keys to adjust settings:",
            "",
            "1 - Toggle 12/24 hour format",
            "2 - Toggle seconds display",
            "3 - Toggle screensaver",
            "4 - Toggle night dimming",
            "5 - Toggle pixel shift",
            "6 - Restart clock",
            "",
            "ESC or Q - Close menu",
        ]
        
        y_offset = 100
        item_font = self.status_font
        for item in menu_items:
            draw.text((40, y_offset), item, font=item_font, fill=(200, 200, 200))
            y_offset += 40
        
        # Current settings display
        y_offset += 20
        draw.text((40, y_offset), "Current Settings:", font=title_font, fill=(0, 255, 0))
        y_offset += 50
        
        settings_info = [
            f"Time Format: {'12-hour' if self.format_12h else '24-hour'}",
            f"Show Seconds: {'Yes' if self.show_seconds else 'No'}",
            f"Screensaver: {'Enabled' if self.screensaver_enabled else 'Disabled'}",
            f"Night Dim: {'Enabled' if self.dim_at_night else 'Disabled'}",
            f"Pixel Shift: {'Enabled' if self.pixel_shift_enabled else 'Disabled'}",
        ]
        
        for info in settings_info:
            draw.text((40, y_offset), info, font=item_font, fill=(200, 200, 200))
            y_offset += 35
        
        # Blit menu overlay
        self.blit_rgb_image(menu_img, overlay_x, overlay_y, clear_last_rect_attr='_last_menu_rect')
    
    def check_keyboard_input(self):
        """Check for keyboard input (non-blocking)."""
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                # Read one character
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())
                    key = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
                return key
            except Exception as e:
                logging.debug(f"Keyboard input error: {e}")
                return None
        return None
    
    def handle_settings_input(self, key):
        """Handle keyboard input for settings menu."""
        if key in ['q', 'Q', '\x1b']:  # ESC or Q
            self.show_settings_menu = False
            # Clear menu rect
            if hasattr(self, '_last_menu_rect'):
                lx, ly, lw, lh = self._last_menu_rect
                self.fb_shadow[ly:ly+lh, lx:lx+lw].fill(0)
                self._last_menu_rect = None
            logging.info("Settings menu closed")
            return
        
        # Setting toggles
        if key == '1':
            self.format_12h = not self.format_12h
            logging.info(f"Time format: {'12h' if self.format_12h else '24h'}")
        elif key == '2':
            self.show_seconds = not self.show_seconds
            logging.info(f"Show seconds: {self.show_seconds}")
        elif key == '3':
            self.screensaver_enabled = not self.screensaver_enabled
            logging.info(f"Screensaver: {self.screensaver_enabled}")
        elif key == '4':
            self.dim_at_night = not self.dim_at_night
            logging.info(f"Night dimming: {self.dim_at_night}")
        elif key == '5':
            self.pixel_shift_enabled = not self.pixel_shift_enabled
            logging.info(f"Pixel shift: {self.pixel_shift_enabled}")
        elif key == '6':
            logging.info("Restart requested from settings menu")
            self.running = False
    
    def run(self):
        """Main loop."""
        logging.info("Starting framebuffer clock display loop")
        logging.info("Press 'S' key to open settings menu")
        
        # Initial updates
        self.update_weather()
        self.check_network_status()
        
        frame_count = 0
        last_second = -1
        loop_count = 0
        
        try:
            while self.running:
                loop_count += 1
                
                # Check for keyboard input
                key = self.check_keyboard_input()
                if key:
                    if key == 's' or key == 'S':
                        # Toggle settings menu
                        self.show_settings_menu = not self.show_settings_menu
                        logging.info(f"Settings menu: {'opened' if self.show_settings_menu else 'closed'}")
                    elif self.show_settings_menu:
                        # Handle settings menu input
                        self.handle_settings_input(key)
                
                # Render settings menu if open
                if self.show_settings_menu:
                    self.render_settings_menu()
                    self.write_to_framebuffer(None)
                    time.sleep(0.1)
                    continue
                
                # Check if second has changed
                current_second = datetime.now().second
                
                # Only render when time changes
                if current_second != last_second:
                    # Update weather periodically
                    self.update_weather()
                    
                    # Update status information
                    self.update_status()
                    
                    # Update pixel shift
                    self.update_pixel_shift()
                    
                    # Render
                    self.render()
                    
                    last_second = current_second
                    frame_count += 1
                    
                    if frame_count % 60 == 0:  # Log every minute
                        avg_loops = loop_count / frame_count if frame_count > 0 else 0
                        logging.info(f"Clock stats: {frame_count} renders, {loop_count} loops, {avg_loops:.1f} loops/render")
                
                # Check for restart flag
                if os.path.exists('/tmp/restart_clock'):
                    logging.info("Restart flag detected - exiting")
                    os.remove('/tmp/restart_clock')
                    break
                
                # Short sleep to avoid busy-waiting
                time.sleep(0.05)
        
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

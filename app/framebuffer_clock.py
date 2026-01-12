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
import time
import select
import termios
import tty
import mmap
import math
from datetime import datetime
from pathlib import Path
import yaml
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import Optional

# Optional evdev input (touch/mouse)
try:
    from evdev import InputDevice, ecodes, list_devices
except Exception:
    InputDevice = None
    ecodes = None
    list_devices = lambda: []

# Lazy imports for optional features (loaded only when enabled)
WeatherService = None
RTCManager = None


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
        
        # Determine framebuffer pixel format once
        self.fb_bpp = self.get_bits_per_pixel()
        # Shadow framebuffer buffer (RGB565) for partial updates
        if self.fb_bpp != 16:
            logging.warning("Optimized blitter assumes 16bpp RGB565; other bpp will fallback to full-frame writes")
        self.fb_shadow = np.zeros((self.fb_height, self.fb_width), dtype='<u2')
        # Track last drawn rects for clearing
        self._last_time_rect = None
        self._last_date_rect = None
        self._last_status_rect = None
        # Track dirty rectangles for partial framebuffer writes
        self._dirty_rects = []
        # Try to memory-map framebuffer for fast partial writes
        self.fb_mmap = None
        try:
            if self.fb_bpp == 16:
                fb_size = self.fb_width * self.fb_height * 2
                fb = open(self.fb_device, 'r+b', buffering=0)
                self.fb_mmap = mmap.mmap(fb.fileno(), fb_size, access=mmap.ACCESS_WRITE)
                self._fb_stride_bytes = self.fb_width * 2
                self._fb_file = fb  # keep file open for mapping lifetime
                logging.info("/dev/fb0 memory-mapped for fast partial updates")
        except Exception as e:
            self.fb_mmap = None
            self._fb_file = None
            logging.warning(f"Framebuffer mmap not available, falling back to writes: {e}")

        # Log framebuffer pixel format
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
        # Cache this once - don't recalculate every render!
        self.display_scale = self.get_display_scale()
        self.time_font_size = max(10, int(self.base_time_font_size * self.display_scale))
        self.date_font_size = max(8, int(self.base_date_font_size * self.display_scale))
        self.weather_font_size = max(8, int(self.base_weather_font_size * self.display_scale))
        
        logging.info(f"Font sizes: time={self.time_font_size}, date={self.date_font_size}, weather={self.weather_font_size}, status={self.status_font_size}")
        
        # Time format - check env vars first, then config
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

        # Auto-shrink time when too wide (env or config; default enabled)
        auto_shrink_env = os.environ.get('AUTO_SHRINK_TIME', '').lower()
        if auto_shrink_env in ('true', '1', 'yes'):
            self.auto_shrink_time = True
        elif auto_shrink_env in ('false', '0', 'no'):
            self.auto_shrink_time = False
        else:
            self.auto_shrink_time = display_config.get('auto_shrink_time', True)
        
        # Initialize fonts
        self.init_fonts()

        # Cache helpers (init before prerender to avoid AttributeError)
        self._bbox_cache = {}  # Cache text bboxes
        try:
            self._temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        except Exception:
            self._temp_draw = None

        # Pre-render sprite cache for fast compositing (7-15x faster than text rendering)
        self._sprite_cache = {}
        self._prerender_time_sprites()
        
        # Status bar configuration
        self.show_status_bar = True
        self.status_color = tuple(int(c * 0.25) for c in self.color)  # Much dimmer for informational display
        
        # Status bar position - FIXED to avoid artifacts during rotation
        # self.status_bar_positions = ['bottom-left', 'bottom-right', 'top-left', 'top-right']
        # self.current_status_position = 0
        # self.last_status_position_change = time.time()
        # self.status_position_interval = 120  # Change position every 2 minutes
        self.status_bar_position = 'bottom-right'  # Fixed position
        self.status_item_regions = []  # [(name, (x,y,w,h))]
        
        # Network and sync tracking
        self.last_ntp_sync = None
        self.network_status = "Unknown"
        self.timezone_name = os.environ.get('TIMEZONE') or os.environ.get('TZ') or 'UTC'
        self.last_status_check = 0
        
        # Screensaver configuration - check env vars first
        screensaver_env = os.environ.get('SCREENSAVER_ENABLED', '').lower()
        if screensaver_env in ('true', '1', 'yes'):
            self.screensaver_enabled = True
        elif screensaver_env in ('false', '0', 'no'):
            self.screensaver_enabled = False
        else:
            self.screensaver_enabled = display_config.get('screensaver_enabled', True)
        self.screensaver_start = int(os.environ.get('SCREENSAVER_START_HOUR', display_config.get('screensaver_start_hour', 2)))
        self.screensaver_end = int(os.environ.get('SCREENSAVER_END_HOUR', display_config.get('screensaver_end_hour', 5)))
        
        # Night dimming configuration - check env vars first
        dim_at_night_env = os.environ.get('DIM_AT_NIGHT', '').lower()
        if dim_at_night_env in ('true', '1', 'yes'):
            self.dim_at_night = True
        elif dim_at_night_env in ('false', '0', 'no'):
            self.dim_at_night = False
        else:
            self.dim_at_night = display_config.get('dim_at_night', True)
        self.night_brightness = float(os.environ.get('NIGHT_BRIGHTNESS', display_config.get('night_brightness', 0.3)))
        self.night_start = int(os.environ.get('NIGHT_START_HOUR', display_config.get('night_start_hour', 22)))
        self.night_end = int(os.environ.get('NIGHT_END_HOUR', display_config.get('night_end_hour', 6)))
        self.current_brightness = 1.0
        
        # Pixel shift configuration - check env vars first
        pixel_shift_env = os.environ.get('PIXEL_SHIFT_ENABLED', '').lower()
        if pixel_shift_env in ('true', '1', 'yes'):
            self.pixel_shift_enabled = True
        elif pixel_shift_env in ('false', '0', 'no'):
            self.pixel_shift_enabled = False
        else:
            self.pixel_shift_enabled = display_config.get('pixel_shift_enabled', True)
        self.pixel_shift_interval = int(os.environ.get('PIXEL_SHIFT_INTERVAL_SECONDS', display_config.get('pixel_shift_interval_seconds', 60)))  # Less frequent updates
        self.pixel_shift_disable_start = int(os.environ.get('PIXEL_SHIFT_DISABLE_START_HOUR', display_config.get('pixel_shift_disable_start_hour', 12)))
        self.pixel_shift_disable_end = int(os.environ.get('PIXEL_SHIFT_DISABLE_END_HOUR', display_config.get('pixel_shift_disable_end_hour', 14)))
        self.last_pixel_shift = 0
        self.pixel_shift_x = 0
        self.pixel_shift_y = 0
        self.pixel_shift_max = 30  # Increased from 10 to make burn-in prevention more visible
        # Track previous shift to detect changes and clear artifacts
        self._prev_pixel_shift_x = 0
        self._prev_pixel_shift_y = 0
        # Allow disabling horizontal pixel shift for strict centering of time
        ps_time_env = os.environ.get('PIXEL_SHIFT_TIME_ENABLED', '').lower()
        if ps_time_env in ('true', '1', 'yes'):
            self.pixel_shift_time_enabled = True
        elif ps_time_env in ('false', '0', 'no'):
            self.pixel_shift_time_enabled = False
        else:
            # Default: keep time horizontally centered (no X shift)
            self.pixel_shift_time_enabled = False
        
        # Weather service - lazy load only if enabled
        self.weather_service = None
        weather_enabled = os.environ.get('WEATHER_ENABLED', '').lower() in ('true', '1', 'yes') or config.get('weather', {}).get('enabled', False)
        if weather_enabled:
            # Lazy import
            global WeatherService
            if WeatherService is None:
                try:
                    from weather import WeatherService
                except ImportError:
                    logging.warning("Weather enabled but weather.py not found")
                    WeatherService = None
            
            if WeatherService:
                api_key = os.environ.get('WEATHER_API_KEY') or config.get('weather', {}).get('api_key', '')
                location = os.environ.get('WEATHER_LOCATION') or config.get('weather', {}).get('location', '')
                if api_key and location:
                    self.weather_service = WeatherService(config.get('weather', {}))
                    logging.info(f"Weather service enabled for location: {location}")
                elif not api_key:
                    logging.warning("Weather service disabled: WEATHER_API_KEY not set")
                elif not location:
                    logging.warning("Weather service disabled: WEATHER_LOCATION not set")
        
        # Weather update tracking
        self.last_weather_update = 0
        self.weather_text = ""
        
        # Initialize RTC manager only if enabled - lazy load
        rtc_enabled = os.environ.get('RTC_ENABLED', '').lower() in ('true', '1', 'yes') or config.get('time', {}).get('rtc_enabled', False)
        self.rtc_manager = None
        if rtc_enabled:
            # Lazy import
            global RTCManager
            if RTCManager is None:
                try:
                    from rtc import RTCManager
                except ImportError:
                    logging.info("RTC enabled but rtc.py not found")
                    RTCManager = None
            
            if RTCManager:
                try:
                    self.rtc_manager = RTCManager(enabled=True)
                    if self.rtc_manager.available:
                        logging.info("RTC manager initialized and hardware detected")
                except Exception as e:
                    logging.warning(f"RTC initialization failed: {e}")
        
        # Get initial NTP sync time
        self.check_last_ntp_sync()
        
        # Settings state
        self.show_settings_menu = False  # legacy flag (unused)
        self.show_settings_overlay = False
        self.active_settings_tab = 'Display'
        self.overlay_buttons = []  # [(name, (x,y,w,h), callback)]
        self.pointer_x = self.fb_width // 2
        self.pointer_y = self.fb_height // 2
        self.pointer_down = False
        self._init_input_devices()
        
        # Log build info
        try:
            from utils import format_build_info
            logging.info(f"Build info: {format_build_info(self.build_info)}")
        except Exception:
            pass
        
        # Native time renderer (Rust daemon) integration
        self.native_renderer_enabled = os.environ.get('NATIVE_TIME_RENDERER', '').lower() in ('true', '1', 'yes')
        self.native_proc = None
        self._native_restart_attempts = 0
        self._last_native_restart = 0
        self._last_date_sent = None
        if self.native_renderer_enabled:
            try:
                bin_path = os.environ.get('NATIVE_TIME_BIN', str(Path(__file__).parent / 'native' / 'clock_fb_rust' / 'target' / 'release' / 'clock_fb_rust'))
                logging.info(f"Starting native time renderer: {bin_path}")
                self.native_proc = subprocess.Popen([bin_path], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logging.error(f"Failed to start native renderer: {e}")
                self.native_renderer_enabled = False
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
            
            # Emoji font path
            emoji_font_paths = [
                '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
                '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf',
            ]
            
            font_file = None
            for path in font_paths:
                if os.path.exists(path):
                    font_file = path
                    break
            
            if not font_file:
                raise Exception("No suitable font found")
            # Keep the chosen font file for dynamic sizing later
            self.font_file = font_file
            
            self.time_font = ImageFont.truetype(self.font_file, self.time_font_size)
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
        
        # Simple font cache for dynamic sizing (size -> ImageFont)
        try:
            self._font_cache = {}
            if hasattr(self, 'time_font_size') and getattr(self, 'font_file', None):
                self._font_cache[self.time_font_size] = self.time_font
        except Exception:
            self._font_cache = {}
    
    def _prerender_time_sprites(self):
        """Pre-render all time characters as sprites for fast compositing.
        This eliminates expensive per-frame text rendering (750ms -> 50-100ms).
        Also caches date characters for full optimization.
        """
        logging.info("Pre-rendering time sprite cache...")
        t_start = time.time()
        
        # Characters needed for time display
        chars = '0123456789: AMP'
        # Also cache date characters: letters, digits, comma, space for date rendering
        date_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789, '
        
        # Use a temporary draw context for bbox measurement
        temp_draw = self._temp_draw or ImageDraw.Draw(Image.new('RGB', (1,1)))
        
        for char in chars:
            # Special handling for space (no visible pixels)
            if char == ' ':
                # Create empty sprite with reasonable width
                space_width = int(self.time_font_size * 0.3)  # 30% of font size
                sprite = Image.new('RGB', (space_width, self.time_font_size), (0, 0, 0))
                self._sprite_cache[char] = {
                    'image': sprite,
                    'width': space_width,
                    'height': self.time_font_size,
                    'baseline_offset': 0,
                    'y_offset': 0,  # Track top offset for alignment
                    'font': 'time'
                }
                continue
            
            # Render on VERY large canvas to capture everything (especially wide chars like M)
            large_size = int(self.time_font_size * 4)
            temp_img = Image.new('RGB', (large_size, large_size), (0, 0, 0))
            temp_draw_img = ImageDraw.Draw(temp_img)
            
            # Render at center of canvas
            center = large_size // 2
            temp_draw_img.text((center, center), char, 
                             font=self.time_font, fill=self.color, anchor='mm')
            
            # Find actual pixel bounds
            bbox = temp_img.getbbox()
            if not bbox:
                logging.warning(f"No pixels rendered for '{char}', skipping")
                continue
            
            # Crop to actual content + padding for antialiasing
            pad = 8
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(large_size, bbox[2] + pad)
            y1 = min(large_size, bbox[3] + pad)
            
            sprite = temp_img.crop((x0, y0, x1, y1))
            sprite_w = sprite.width
            sprite_h = sprite.height
            
            # Calculate y_offset from center to preserve baseline alignment
            y_offset_from_center = y0 - center
            
            # Store sprite and its positioning info
            self._sprite_cache[char] = {
                'image': sprite,
                'width': sprite_w,
                'height': sprite_h,
                'baseline_offset': 0,
                'y_offset': y_offset_from_center,  # For baseline alignment
                'font': 'time'
            }
        
        # Render date character sprites (smaller font)
        for char in date_chars:
            # Special handling for space
            if char == ' ':
                space_width = int(self.date_font_size * 0.3)
                sprite = Image.new('RGB', (space_width, self.date_font_size), (0, 0, 0))
                cache_key = f'date_{char}'
                self._sprite_cache[cache_key] = {
                    'image': sprite,
                    'width': space_width,
                    'height': self.date_font_size,
                    'baseline_offset': 0,
                    'y_offset': 0,
                    'font': 'date'
                }
                continue
            
            # Render on large canvas
            large_size = int(self.date_font_size * 4)
            temp_img = Image.new('RGB', (large_size, large_size), (0, 0, 0))
            temp_draw_img = ImageDraw.Draw(temp_img)
            
            center = large_size // 2
            temp_draw_img.text((center, center), char,
                             font=self.date_font, fill=self.color, anchor='mm')
            
            bbox = temp_img.getbbox()
            if not bbox:
                continue
            
            pad = 5
            x0 = max(0, bbox[0] - pad)
            y0 = max(0, bbox[1] - pad)
            x1 = min(large_size, bbox[2] + pad)
            y1 = min(large_size, bbox[3] + pad)
            
            sprite = temp_img.crop((x0, y0, x1, y1))
            sprite_w = sprite.width
            sprite_h = sprite.height
            y_offset_from_center = y0 - center
            
            # Store with 'date_' prefix to distinguish from time sprites
            cache_key = f'date_{char}'
            self._sprite_cache[cache_key] = {
                'image': sprite,
                'width': sprite_w,
                'height': sprite_h,
                'baseline_offset': 0,
                'y_offset': y_offset_from_center,
                'font': 'date'
            }
        
        elapsed = (time.time() - t_start) * 1000
        logging.info(f"Cached {len(self._sprite_cache)} sprites (time + date chars) in {elapsed:.1f}ms")
    
    def _composite_time_from_cache(self, time_str: str, color: tuple) -> Image.Image:
        """Composite time string from pre-rendered sprite cache.
        Returns PIL Image ready for blitting. Much faster than text rendering.
        Applies brightness to sprites if color differs from cached color.
        """
        if not time_str or not self._sprite_cache:
            logging.debug(f"Cache composite skipped: time_str='{time_str}', cache_size={len(self._sprite_cache)}")
            return None
        
        # Calculate total width and max height
        total_width = 0
        max_height = 0
        sprites_to_use = []
        
        # Debug: log the time string being rendered (once per minute to avoid spam)
        if not hasattr(self, '_last_time_str_logged') or self._last_time_str_logged != time_str[:5]:
            logging.info(f"Time string: {repr(time_str)} (len={len(time_str)}, chars={[c for c in time_str]})")
            self._last_time_str_logged = time_str[:5]
        
        for char in time_str:
            if char not in self._sprite_cache:
                # Cache miss - log details and fallback
                logging.warning(f"Sprite cache MISS for char='{char}' (ord={ord(char)}, time_str='{time_str}')")
                return None
            sprite_info = self._sprite_cache[char]
            sprites_to_use.append(sprite_info)
            total_width += sprite_info['width']
            max_height = max(max_height, sprite_info['height'])
        
        # Find the minimum y_offset (highest top) to determine canvas height
        min_y_offset = 0
        max_bottom_offset = 0
        for sprite_info in sprites_to_use:
            y_off = sprite_info.get('y_offset', 0)
            min_y_offset = min(min_y_offset, y_off)
            max_bottom_offset = max(max_bottom_offset, y_off + sprite_info['height'])
        
        # Canvas height to fit all sprites aligned to common baseline
        canvas_height = max_bottom_offset - min_y_offset
        
        # Create composite canvas
        composite = Image.new('RGB', (total_width, canvas_height), (0, 0, 0))
        
        # Check if we need to apply brightness (color differs from cached self.color)
        needs_tint = color != self.color
        brightness_factor = color[0] / max(1, self.color[0]) if self.color[0] > 0 else 1.0
        
        # Blit each sprite aligned to common baseline
        x_offset = 0
        for sprite_info in sprites_to_use:
            sprite_img = sprite_info['image']
            
            # Apply brightness if needed (for night dimming)
            if needs_tint and brightness_factor != 1.0:
                # Tint sprite by adjusting pixel values
                arr = np.array(sprite_img)
                arr = (arr * brightness_factor).astype(np.uint8)
                sprite_img = Image.fromarray(arr)
            
            # Position sprite based on y_offset for baseline alignment
            y_offset = sprite_info.get('y_offset', 0) - min_y_offset
            composite.paste(sprite_img, (x_offset, y_offset))
            x_offset += sprite_info['width']
        
        return composite
    
    def _composite_date_from_cache(self, date_str: str, color: tuple) -> Image.Image:
        """Composite date string from pre-rendered sprite cache.
        Much faster than ImageDraw.text() for date rendering.
        """
        if not date_str or not self._sprite_cache:
            return None
        
        # Normalize date string (remove extra spaces that might break cache)
        date_str = ' '.join(date_str.split())
        
        total_width = 0
        max_height = 0
        sprites_to_use = []
        missing_chars = []
        
        for char in date_str:
            cache_key = f'date_{char}'
            if cache_key not in self._sprite_cache:
                # Track missing character for logging
                missing_chars.append(char)
                continue
            sprite_info = self._sprite_cache[cache_key]
            sprites_to_use.append(sprite_info)
            total_width += sprite_info['width']
            max_height = max(max_height, sprite_info['height'])
        
        # If any characters are missing, fallback
        if missing_chars:
            if not hasattr(self, '_date_cache_missing_logged'):
                logging.warning(f"Date cache missing chars: {missing_chars} in '{date_str}'")
                self._date_cache_missing_logged = True
            return None
        
        # Find min/max y_offset for baseline alignment
        min_y_offset = 0
        max_bottom_offset = 0
        for sprite_info in sprites_to_use:
            y_off = sprite_info.get('y_offset', 0)
            min_y_offset = min(min_y_offset, y_off)
            max_bottom_offset = max(max_bottom_offset, y_off + sprite_info['height'])
        
        canvas_height = max_bottom_offset - min_y_offset
        composite = Image.new('RGB', (total_width, canvas_height), (0, 0, 0))
        
        # Apply brightness if needed
        needs_tint = color != self.color
        brightness_factor = color[0] / max(1, self.color[0]) if self.color[0] > 0 else 1.0
        
        x_offset = 0
        for sprite_info in sprites_to_use:
            sprite_img = sprite_info['image']
            
            if needs_tint and brightness_factor != 1.0:
                arr = np.array(sprite_img)
                arr = (arr * brightness_factor).astype(np.uint8)
                sprite_img = Image.fromarray(arr)
            
            # Baseline aligned position
            y_offset = sprite_info.get('y_offset', 0) - min_y_offset
            composite.paste(sprite_img, (x_offset, y_offset))
            x_offset += sprite_info['width']
        
        return composite

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_icon(self, draw, x, y, icon_type, color):
        """Draw a tiny bitmap icon (10x10) for status items."""
        if icon_type == 'network':
            # Globe/wifi icon
            draw.ellipse([x+2, y+2, x+8, y+8], outline=color)
            draw.line([x+5, y+2, x+5, y+8], fill=color)
            draw.line([x+2, y+5, x+8, y+5], fill=color)
        elif icon_type == 'sync_ok':
            # Checkmark
            draw.line([x+2, y+5, x+4, y+7], fill=color, width=2)
            draw.line([x+4, y+7, x+8, y+3], fill=color, width=2)
        elif icon_type == 'sync_old':
            # Clock icon
            draw.ellipse([x+2, y+2, x+8, y+8], outline=color)
            draw.line([x+5, y+3, x+5, y+5], fill=color)
            draw.line([x+5, y+5, x+7, y+5], fill=color)
        elif icon_type == 'error':
            # X mark
            draw.line([x+2, y+2, x+8, y+8], fill=color, width=2)
            draw.line([x+8, y+2, x+2, y+8], fill=color, width=2)
        elif icon_type == 'settings':
            # Gear icon
            draw.rectangle([x+3, y+3, x+7, y+7], outline=color)
            draw.line([x+5, y+1, x+5, y+3], fill=color)
            draw.line([x+5, y+7, x+5, y+9], fill=color)
            draw.line([x+1, y+5, x+3, y+5], fill=color)
            draw.line([x+7, y+5, x+9, y+5], fill=color)

    def _render_status_bar(self, status_items, status_color, margin):
        """Render status bar with icons and text. Caches result and only redraws when changed."""
        if not status_items:
            return
        
        # Create simplified cache key (ignore exact sync time to avoid constant re-renders)
        # Only track item names and network/version status (sync time changes every second)
        cache_items = []
        for name, label in status_items:
            if name in ('sync_ok', 'sync_old'):
                # Just track sync status, not exact time
                cache_items.append((name, 'sync'))
            else:
                cache_items.append((name, label))
        cache_key = (tuple(cache_items), status_color, self.status_bar_position)
        
        # Debug: Log cache key on first few renders
        if not hasattr(self, '_cache_key_log_count'):
            self._cache_key_log_count = 0
        if self._cache_key_log_count < 5:
            self._cache_key_log_count += 1
            logging.info(f"Status cache key: {cache_key}")
            if hasattr(self, '_status_cache_key'):
                logging.info(f"Previous cache key: {self._status_cache_key}")
                logging.info(f"Keys match: {self._status_cache_key == cache_key}")
        
        # Check if we can use cached status bar
        if hasattr(self, '_status_cache_key') and self._status_cache_key == cache_key:
            # Status hasn't changed, use cached image and position
            if hasattr(self, '_status_cached_img') and hasattr(self, '_status_cached_pos'):
                if not hasattr(self, '_status_cache_hit_logged'):
                    logging.info("Status bar cache HIT - using cached render")
                    self._status_cache_hit_logged = True
                status_img = self._status_cached_img
                status_x, status_y = self._status_cached_pos
                self.blit_rgb_image(status_img, status_x, status_y, clear_last_rect_attr='_last_status_rect', skip_write=True)
                return
        
        position_name = self.status_bar_position  # Use fixed position
        
        # Calculate dimensions
        status_w = 0
        status_h = 0
        min_y_offset = 0
        for idx, (name, label) in enumerate(status_items):
            if name in ['network', 'error', 'sync_ok', 'sync_old', 'settings']:
                status_w += 12
            lb = self._temp_draw.textbbox((0,0), label, font=self.status_font)
            status_w += lb[2] - lb[0]
            status_h = max(status_h, lb[3] - lb[1])
            min_y_offset = min(min_y_offset, lb[1])
            if idx < len(status_items) - 1:
                sep = self._temp_draw.textbbox((0,0), " | ", font=self.status_font)
                status_w += sep[2] - sep[0]
        
        v_pad = max(5, -min_y_offset + 3)
        status_h += v_pad
        
        # Position based on rotation
        if position_name == 'bottom-left':
            status_x = margin
            status_y = self.fb_height - status_h - margin
        elif position_name == 'bottom-right':
            status_x = self.fb_width - status_w - margin
            status_y = self.fb_height - status_h - margin
        elif position_name == 'top-left':
            status_x = margin
            status_y = margin
        else:  # top-right
            status_x = self.fb_width - status_w - margin
            status_y = margin
        
        # Render status bar
        status_img = Image.new('RGB', (status_w, status_h), (0,0,0))
        status_draw = ImageDraw.Draw(status_img)
        cursor_x = 0
        text_y = -min_y_offset if min_y_offset < 0 else 0
        for idx, (name, label) in enumerate(status_items):
            if name in ['network', 'error', 'sync_ok', 'sync_old', 'settings']:
                self._draw_icon(status_draw, cursor_x, text_y, name, status_color)
                cursor_x += 12
            status_draw.text((cursor_x, text_y), label, font=self.status_font, fill=status_color)
            lb = self._temp_draw.textbbox((0,0), label, font=self.status_font)
            cursor_x += lb[2] - lb[0]
            if idx < len(status_items) - 1:
                status_draw.text((cursor_x, 0), " | ", font=self.status_font, fill=status_color)
                sep = self._temp_draw.textbbox((0,0), " | ", font=self.status_font)
                cursor_x += sep[2] - sep[0]
        
        # Build clickable regions
        self.status_item_regions = []
        cursor_rel_x = 0
        for idx, (name, label) in enumerate(status_items):
            icon_w = 12 if name in ['network', 'error', 'sync_ok', 'sync_old', 'settings'] else 0
            lb = self._temp_draw.textbbox((0,0), label, font=self.status_font)
            iw = icon_w + (lb[2] - lb[0])
            ih = lb[3] - lb[1]
            self.status_item_regions.append((name, (status_x + cursor_rel_x, status_y, iw, ih)))
            cursor_rel_x += iw
            if idx < len(status_items) - 1:
                sep = self._temp_draw.textbbox((0,0), " | ", font=self.status_font)
                cursor_rel_x += sep[2] - sep[0]
        
        self.blit_rgb_image(status_img, status_x, status_y, clear_last_rect_attr='_last_status_rect', skip_write=True)
        
        # Cache the rendered status bar
        self._status_cache_key = cache_key
        self._status_cached_img = status_img
        self._status_cached_pos = (status_x, status_y)

    # ------------------------
    # Input handling
    # ------------------------
    def _init_input_devices(self):
        self.input_devices = []
        try:
            if InputDevice is None:
                logging.info("evdev not available; input disabled")
                return
            for path in list_devices():
                try:
                    dev = InputDevice(path)
                    caps = dev.capabilities(verbose=True)
                    if 'EV_ABS' in dict(caps) or 'EV_REL' in dict(caps):
                        try:
                            dev.set_nonblocking(True)
                        except Exception:
                            pass
                        self.input_devices.append(dev)
                        logging.info(f"Input device added: {dev.name} ({path})")
                except Exception as e:
                    logging.debug(f"Skip input device {path}: {e}")
        except Exception as e:
            logging.warning(f"Failed to init input devices: {e}")

    def _poll_input(self):
        if not self.input_devices or ecodes is None:
            return
        for dev in list(self.input_devices):
            try:
                for event in dev.read_many():
                    if event.type == ecodes.EV_ABS:
                        if event.code == ecodes.ABS_X:
                            ai = dev.absinfo(ecodes.ABS_X)
                            rng = max(1, ai.max - ai.min)
                            self.pointer_x = int((event.value - ai.min) * (self.fb_width - 1) / rng)
                        elif event.code == ecodes.ABS_Y:
                            ai = dev.absinfo(ecodes.ABS_Y)
                            rng = max(1, ai.max - ai.min)
                            self.pointer_y = int((event.value - ai.min) * (self.fb_height - 1) / rng)
                        elif event.code in (getattr(ecodes, 'ABS_MT_POSITION_X', 0), getattr(ecodes, 'ABS_MT_POSITION_Y', 1)):
                            try:
                                ai = dev.absinfo(event.code)
                                rng = max(1, ai.max - ai.min)
                                if event.code == getattr(ecodes, 'ABS_MT_POSITION_X', 0):
                                    self.pointer_x = int((event.value - ai.min) * (self.fb_width - 1) / rng)
                                else:
                                    self.pointer_y = int((event.value - ai.min) * (self.fb_height - 1) / rng)
                            except Exception:
                                pass
                    elif event.type == ecodes.EV_REL:
                        if event.code == ecodes.REL_X:
                            self.pointer_x = max(0, min(self.fb_width - 1, self.pointer_x + event.value))
                        elif event.code == ecodes.REL_Y:
                            self.pointer_y = max(0, min(self.fb_height - 1, self.pointer_y + event.value))
                    elif event.type == ecodes.EV_KEY:
                        if event.code in (getattr(ecodes, 'BTN_TOUCH', 0x14a), getattr(ecodes, 'BTN_LEFT', 0x110)):
                            if event.value == 1:
                                self.pointer_down = True
                            elif event.value == 0 and self.pointer_down:
                                self.pointer_down = False
                                self._handle_tap(self.pointer_x, self.pointer_y)
            except BlockingIOError:
                continue
            except Exception as e:
                logging.debug(f"Input read error: {e}")

    def _handle_tap(self, x, y):
        if self.show_settings_overlay:
            for name, rect, cb in list(self.overlay_buttons):
                rx, ry, rw, rh = rect
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    try:
                        cb()
                    except Exception as e:
                        logging.warning(f"Button '{name}' action failed: {e}")
                    return
            return
        for name, rect in list(self.status_item_regions):
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                tab_map = { 'network': 'System', 'timezone': 'Time', 'sync': 'System', 'version': 'About' }
                self.active_settings_tab = tab_map.get(name, 'Display')
                self.show_settings_overlay = True
                logging.info(f"Open settings overlay: {self.active_settings_tab}")
                return

    # ------------------------
    # Settings overlay
    # ------------------------
    def _add_button(self, name, rect, callback):
        self.overlay_buttons.append((name, rect, callback))

    def _render_button(self, draw, x, y, w, h, label, active=False):
        border = (80, 80, 80)
        fill = (30, 30, 30) if not active else (50, 50, 50)
        draw.rectangle([x, y, x+w, y+h], fill=fill, outline=border)
        tw, th = draw.textbbox((0,0), label, font=self.status_font)[2:4]
        tx = x + (w - tw) // 2
        ty = y + (h - th) // 2
        draw.text((tx, ty), label, font=self.status_font, fill=(200,200,200))

    def _render_settings_overlay(self):
        overlay = Image.new('RGB', (self.fb_width, self.fb_height), (0,0,0))
        d = ImageDraw.Draw(overlay)
        panel_margin = 40
        d.rectangle([panel_margin, panel_margin, self.fb_width - panel_margin, self.fb_height - panel_margin], fill=(10,10,10), outline=(60,60,60))
        tabs = ['Display', 'Time', 'Status', 'System', 'About']
        tab_w = 180
        tab_h = 60
        self.overlay_buttons = []
        x = panel_margin + 20
        y = panel_margin + 20
        for t in tabs:
            self._render_button(d, x, y, tab_w, tab_h, t, active=(t==self.active_settings_tab))
            self._add_button(f"tab:{t}", (x, y, tab_w, tab_h), lambda t=t: self._set_active_tab(t))
            x += tab_w + 12
        close_w = 100
        self._render_button(d, self.fb_width - panel_margin - close_w - 20, panel_margin + 20, close_w, tab_h, 'Close')
        self._add_button('close', (self.fb_width - panel_margin - close_w - 20, panel_margin + 20, close_w, tab_h), self._close_overlay)
        cx0 = panel_margin + 20
        cy0 = panel_margin + tab_h + 40
        cx1 = self.fb_width - panel_margin - 20
        cy1 = self.fb_height - panel_margin - 20
        d.rectangle([cx0, cy0, cx1, cy1], outline=(60,60,60))
        self._render_tab_content(d, cx0+20, cy0+20, cx1-20, cy1-20)
        self.blit_rgb_image(overlay, 0, 0)

    def _set_active_tab(self, t):
        self.active_settings_tab = t

    def _close_overlay(self):
        self.show_settings_overlay = False

    def _render_tab_content(self, d, x0, y0, x1, y1):
        y = y0
        gap = 12
        btn_w = 240
        btn_h = 50
        def add_toggle(label, value_getter, setter):
            nonlocal y
            d.text((x0, y), label, font=self.status_font, fill=(200,200,200))
            bx = x0 + 320
            self._render_button(d, bx, y-8, btn_w, btn_h, 'On' if value_getter() else 'Off', active=value_getter())
            self._add_button(f"toggle:{label}", (bx, y-8, btn_w, btn_h), lambda: setter(not value_getter()))
            y += btn_h + gap
        def add_selector(label, options, get_idx, set_idx):
            nonlocal y
            d.text((x0, y), label, font=self.status_font, fill=(200,200,200))
            bx = x0 + 320
            self._render_button(d, bx, y-8, 60, btn_h, '<')
            self._add_button(f"sel_prev:{label}", (bx, y-8, 60, btn_h), lambda: set_idx((get_idx()-1) % len(options)))
            val = str(options[get_idx()])
            d.text((bx+80, y), val, font=self.status_font, fill=(200,200,200))
            self._render_button(d, bx+200, y-8, 60, btn_h, '>')
            self._add_button(f"sel_next:{label}", (bx+200, y-8, 60, btn_h), lambda: set_idx((get_idx()+1) % len(options)))
            y += btn_h + gap
        if self.active_settings_tab == 'Display':
            add_toggle('Show seconds', lambda: self.show_seconds, lambda v: setattr(self, 'show_seconds', v))
            add_toggle('Night dimming', lambda: self.dim_at_night, lambda v: setattr(self, 'dim_at_night', v))
            add_toggle('Pixel shift', lambda: self.pixel_shift_enabled, lambda v: setattr(self, 'pixel_shift_enabled', v))
            levels = [0.15, 0.25, 0.35, 0.5]
            def get_idx():
                base = self.color[0] or self.color[1] or self.color[2] or 1
                cur = self.status_color[0]/base
                return min(range(len(levels)), key=lambda i: abs(levels[i]-cur))
            def set_idx(i):
                f = levels[i]
                self.status_color = tuple(int(c * f) for c in self.color)
            add_selector('Status brightness', levels, get_idx, set_idx)
        elif self.active_settings_tab == 'Time':
            add_toggle('12-hour format', lambda: self.format_12h, lambda v: setattr(self, 'format_12h', v))
            d.text((x0, y), f"Timezone (display only): {self.timezone_name}", font=self.status_font, fill=(160,160,160))
            y += btn_h + gap
        elif self.active_settings_tab == 'Status':
            options = [30, 60, 120, 300]
            def get_idx():
                return min(range(len(options)), key=lambda i: abs(options[i]-self.status_position_interval))
            def set_idx(i):
                self.status_position_interval = options[i]
            add_selector('Status position interval (s)', options, get_idx, set_idx)
        elif self.active_settings_tab == 'System':
            d.text((x0, y), f"Network: {self.network_status}", font=self.status_font, fill=(160,160,160))
            y += btn_h
            d.text((x0, y), f"Sync: {self.get_time_since_sync()}", font=self.status_font, fill=(160,160,160))
        else:
            try:
                from utils import format_build_info
                d.text((x0, y), format_build_info(self.build_info), font=self.status_font, fill=(160,160,160))
            except Exception:
                d.text((x0, y), "Version info unavailable", font=self.status_font, fill=(160,160,160))
    
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

    def _send_native(self, line: str):
        # Return True on success, False on failure
        try:
            if self.native_renderer_enabled and self.native_proc:
                # If process died, attempt restart
                if self.native_proc.poll() is not None:
                    return self._restart_native_renderer()
                if self.native_proc.stdin:
                    self.native_proc.stdin.write((line + "\n").encode('utf-8'))
                    self.native_proc.stdin.flush()
                    return True
        except BrokenPipeError:
            # Attempt one restart, then disable
            return self._restart_native_renderer()
        except Exception as e:
            # Throttle error logging
            if not hasattr(self, '_last_native_error') or time.time() - getattr(self, '_last_native_error', 0) > 2:
                logging.error(f"Native send failed: {e}")
                self._last_native_error = time.time()
        return False

    def _restart_native_renderer(self) -> bool:
        now = time.time()
        if now - self._last_native_restart < 2:
            return False
        self._last_native_restart = now
        self._native_restart_attempts += 1
        try:
            if self.native_proc:
                try:
                    self.native_proc.terminate()
                except Exception:
                    pass
            bin_path = os.environ.get('NATIVE_TIME_BIN', str(Path(__file__).parent / 'native' / 'clock_fb_rust' / 'target' / 'release' / 'clock_fb_rust'))
            logging.warning(f"Restarting native renderer (attempt {self._native_restart_attempts}): {bin_path}")
            self.native_proc = subprocess.Popen([bin_path], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Reset attempts after successful start
            self._native_restart_attempts = 0
            return True
        except Exception as e:
            logging.error(f"Native renderer restart failed: {e}")
            if self._native_restart_attempts >= 3:
                logging.error("Disabling native renderer after repeated failures; falling back to PIL rendering")
                self.native_renderer_enabled = False
            return False
    
    def check_network_status(self):
        """Check network connectivity."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.network_status = "Connected"
        except:
            self.network_status = "No Network"
    
    def check_last_ntp_sync(self):
        """Check last NTP synchronization time using multiple methods."""
        # Method 1: Try timedatectl
        try:
            result = subprocess.run(['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip() == 'yes':
                self.last_ntp_sync = datetime.now()
                return
        except:
            pass
        
        # Method 2: Check systemd-timesyncd status
        try:
            result = subprocess.run(['systemctl', 'status', 'systemd-timesyncd'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and 'synchronized' in result.stdout.lower():
                self.last_ntp_sync = datetime.now()
                return
        except:
            pass
        
        # Method 3: Check if chrony or ntpd is running
        try:
            for service in ['chronyd', 'ntpd']:
                result = subprocess.run(['pgrep', service],
                                        capture_output=True, timeout=2)
                if result.returncode == 0:
                    # Service is running, assume sync happened
                    if not self.last_ntp_sync:
                        self.last_ntp_sync = datetime.now()
                    return
        except:
            pass
        
        # Method 4: Use RTC if available
        if self.rtc_manager and self.rtc_manager.available:
            rtc_time = self.rtc_manager.read_time()
            if rtc_time:
                self.last_ntp_sync = rtc_time
                logging.info("Using RTC time as sync reference")
                return
        
        # Fallback: Assume synced if network is available
        if not self.last_ntp_sync and self.network_status == "Connected":
            self.last_ntp_sync = datetime.now()
            logging.debug("Assumed NTP sync based on network connectivity")
    
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
        # Apply pixel shift only at minute boundary to avoid visible tearing
        if now - self.last_pixel_shift > self.pixel_shift_interval and datetime.now().second == 0:
            # Lazy import random only when needed
            import random
            self.pixel_shift_x = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.pixel_shift_y = random.randint(-self.pixel_shift_max, self.pixel_shift_max)
            self.last_pixel_shift = now
            logging.debug(f"Pixel shift applied: x={self.pixel_shift_x:+d}, y={self.pixel_shift_y:+d}")
    
    def update_burn_in_protection(self):
        """Vary font size and characteristics to prevent burn-in."""
        if not self.pixel_shift_enabled:  # Reuse same enable flag
            return
        
        now = time.time()
        # Change font characteristics every 5 minutes
        if not hasattr(self, '_last_font_variation'):
            self._last_font_variation = 0
            self._font_size_offset = 0
        
        if now - self._last_font_variation > 300 and datetime.now().second == 0:  # 5 min
            import random
            # Vary time font size by ±8% (e.g., 280 ± 22px)
            base_size = self.base_time_font_size
            variation = int(base_size * 0.08)
            self._font_size_offset = random.randint(-variation, variation)
            new_size = max(10, int((base_size + self._font_size_offset) * self.display_scale))
            
            try:
                if getattr(self, 'font_file', None):
                    self.time_font = ImageFont.truetype(self.font_file, new_size)
                    self.time_font_size = new_size
                    # Update cache
                    self._font_cache[new_size] = self.time_font
                    logging.debug(f"Font size varied: {new_size}px (offset: {self._font_size_offset:+d}px)")
            except Exception as e:
                logging.warning(f"Font variation failed: {e}")
            
            self._last_font_variation = now
    
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
        if now - self.last_status_check > 120:  # Update every 2 minutes (reduce subprocess overhead)
            self.check_network_status()
            self.check_last_ntp_sync()
            self.last_status_check = now
    
    def render(self):
        """Render the clock display using partial updates into shadow buffer."""
        t_start = time.time()
        
        # One-time full clear on first render to remove balena background
        if not hasattr(self, '_initial_clear_done'):
            logging.info("Initial framebuffer clear to remove boot background")
            self.fb_shadow.fill(0)
            self.write_to_framebuffer(None)
            self._initial_clear_done = True
        
        try:
            # If screensaver, write blank and return
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
        
        # Detect pixel shift change and clear old positions to prevent artifacts
        shift_changed = (self.pixel_shift_x != self._prev_pixel_shift_x or 
                        self.pixel_shift_y != self._prev_pixel_shift_y)
        if shift_changed:
            # Full framebuffer clear to eliminate all artifacts
            logging.info(f"Pixel shift: ({self._prev_pixel_shift_x},{self._prev_pixel_shift_y}) → ({self.pixel_shift_x},{self.pixel_shift_y}), clearing screen")
            self.fb_shadow.fill(0)
            # Write the clear immediately before drawing new content
            self.write_to_framebuffer(None)
            # Reset all tracked rects
            self._last_time_rect = None
            self._last_date_rect = None
            self._last_status_rect = None
            if hasattr(self, '_last_weather_rect'):
                self._last_weather_rect = None
            # Update tracking
            self._prev_pixel_shift_x = self.pixel_shift_x
            self._prev_pixel_shift_y = self.pixel_shift_y
        
        # Apply brightness
        display_color = self.apply_brightness(self.color)
        status_color = self.apply_brightness(self.status_color)

        # If native renderer is enabled, send commands; fallback to PIL if any fail
        native_ok = False
        if self.native_renderer_enabled:
            hex_color = f"#{display_color[0]:02X}{display_color[1]:02X}{display_color[2]:02X}"
            ok = True
            ok &= self._send_native(f"COLOR {hex_color}")
            ok &= self._send_native(f"BRIGHT {self.current_brightness:.3f}")
            ok &= self._send_native(f"SHIFT {self.pixel_shift_x} {self.pixel_shift_y}")
            ok &= self._send_native(f"TIME {time_str}")
            # Send DATE only when it changes (reduce flicker and overlap clears)
            if self._last_date_sent != date_str:
                ok &= self._send_native(f"DATE {date_str}")
                if ok:
                    self._last_date_sent = date_str
            if ok:
                native_ok = True
            else:
                logging.warning("Native renderer send failed; rendering with PIL fallback")
        
        t_prep = time.time()
        
        # If native path succeeded, draw only the status bar via PIL and write partial
        if native_ok:
            if self.show_status_bar:
                # Build status items
                status_items = []
                if self.network_status:
                    if "Connected" in self.network_status:
                        status_items.append(("network", self.network_status))
                    else:
                        status_items.append(("error", self.network_status))
                if self.timezone_name:
                    status_items.append(("timezone", f"TZ:{self.timezone_name}"))
                sync_time = self.get_time_since_sync()
                if sync_time == "Just now" or "m ago" in sync_time:
                    status_items.append(("sync_ok", f"Sync: {sync_time}"))
                else:
                    status_items.append(("sync_old", f"Sync: {sync_time}"))
                if self.build_info:
                    ver = self.build_info.get("git_version") or ""
                    sha = self.build_info.get("git_sha") or ""
                    short_sha = sha[:7] if isinstance(sha, str) and sha else ""
                    parts = []
                    if ver: parts.append(ver)
                    if short_sha: parts.append(short_sha)
                    if parts:
                        status_items.append(("version", " ".join(parts)))
                status_items.append(("settings", "Settings"))

                # Use fixed status bar position
                margin = int(30 * self.display_scale)
                position_name = self.status_bar_position

                # Measure and draw status into small image
                if not self._temp_draw:
                    self._temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
                status_w = 0
                status_h = 0
                min_y_offset = 0
                for idx, (name, label) in enumerate(status_items):
                    if name in ['network', 'error', 'sync_ok', 'sync_old', 'settings']:
                        status_w += 12
                    lb = self._temp_draw.textbbox((0,0), label, font=self.status_font)
                    status_w += lb[2] - lb[0]
                    status_h = max(status_h, lb[3] - lb[1])
                    min_y_offset = min(min_y_offset, lb[1])
                    if idx < len(status_items) - 1:
                        sep = self._temp_draw.textbbox((0,0), " | ", font=self.status_font)
                        status_w += sep[2] - sep[0]
                v_pad = max(5, -min_y_offset + 3)
                status_h += v_pad
                if position_name == 'bottom-left':
                    status_x = margin
                    status_y = self.fb_height - status_h - margin
                elif position_name == 'bottom-right':
                    status_x = self.fb_width - status_w - margin
                    status_y = self.fb_height - status_h - margin
                elif position_name == 'top-left':
                    status_x = margin
                    status_y = margin
                else:
                    status_x = self.fb_width - status_w - margin
                    status_y = margin
                status_img = Image.new('RGB', (status_w, status_h), (0,0,0))
                status_draw = ImageDraw.Draw(status_img)
                cursor_x = 0
                text_y = -min_y_offset if min_y_offset < 0 else 0
                s_color = status_color
                for idx, (name, label) in enumerate(status_items):
                    if name in ['network', 'error', 'sync_ok', 'sync_old', 'settings']:
                        self._draw_icon(status_draw, cursor_x, text_y, name, s_color)
                        cursor_x += 12
                    status_draw.text((cursor_x, text_y), label, font=self.status_font, fill=s_color)
                    lb = self._temp_draw.textbbox((0,0), label, font=self.status_font)
                    cursor_x += lb[2] - lb[0]
                    if idx < len(status_items) - 1:
                        status_draw.text((cursor_x, 0), " | ", font=self.status_font, fill=s_color)
                        sep = self._temp_draw.textbbox((0,0), " | ", font=self.status_font)
                        cursor_x += sep[2] - sep[0]
                self.blit_rgb_image(status_img, status_x, status_y, clear_last_rect_attr='_last_status_rect', skip_write=True)
                self.write_to_framebuffer(None)  # Write once for native path
            return

        # Calculate center position with pixel shift (full resolution)
        center_x = self.fb_width // 2 + self.pixel_shift_x
        # Time should stay strictly centered horizontally unless explicitly enabled
        center_x_time = self.fb_width // 2 + (self.pixel_shift_x if self.pixel_shift_time_enabled else 0)
        center_y = self.fb_height // 2 + self.pixel_shift_y
        
        # Dynamic margins and offsets (use cached scale)
        margin = int(30 * self.display_scale)
        time_offset_y = int(60 * self.display_scale)
        date_offset_y = int(100 * self.display_scale)
        
        # Render time using pre-rendered sprite cache (7-15x faster)
        t_cache_start = time.time()
        time_img = self._composite_time_from_cache(time_str, display_color)
        cache_time_ms = (time.time() - t_cache_start) * 1000
        
        if time_img:
            # Center the composite image
            time_x = max(margin, min(self.fb_width - margin - time_img.width, center_x_time - (time_img.width // 2)))
            time_y = max(margin, min(self.fb_height - margin - time_img.height, center_y - time_offset_y - (time_img.height // 2)))
            self.blit_rgb_image(time_img, time_x, time_y, clear_last_rect_attr='_last_time_rect', skip_write=True)
            if not hasattr(self, '_cache_hit_logged'):
                logging.info(f"Sprite cache HIT: rendered time in {cache_time_ms:.1f}ms (vs 750ms direct)")
                self._cache_hit_logged = True
        else:
            # Fallback to direct rendering if cache fails (shouldn't happen)
            logging.warning(f"Sprite cache MISS for time_str='{time_str}', falling back to direct rendering")
            if not self._temp_draw:
                self._temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
            time_bbox = self._temp_draw.textbbox((0,0), time_str, font=self.time_font)
            text_w = time_bbox[2] - time_bbox[0]
            text_h = time_bbox[3] - time_bbox[1]
            t_pad = max(40, int(self.time_font_size * 0.15))
            time_img = Image.new('RGB', (text_w + 2*t_pad, text_h + 2*t_pad), (0,0,0))
            ImageDraw.Draw(time_img).text((t_pad - time_bbox[0], t_pad - time_bbox[1]), time_str, font=self.time_font, fill=display_color)
            time_x = max(margin, min(self.fb_width - margin - time_img.width, center_x_time - (time_img.width // 2)))
            time_y = max(margin, min(self.fb_height - margin - time_img.height, center_y - time_offset_y - (time_img.height // 2)))
            self.blit_rgb_image(time_img, time_x, time_y, clear_last_rect_attr='_last_time_rect', skip_write=True)
        
        # Render date with generous padding - try sprite cache first
        t_date_start = time.time()
        date_img = self._composite_date_from_cache(date_str, display_color)
        date_cache_ms = (time.time() - t_date_start) * 1000
        
        if date_img:
            # Center the cached date composite
            date_x = max(margin, min(self.fb_width - margin - date_img.width, center_x - (date_img.width // 2)))
            date_y = max(margin, min(self.fb_height - margin - date_img.height, center_y + date_offset_y))
            self.blit_rgb_image(date_img, date_x, date_y, clear_last_rect_attr='_last_date_rect', skip_write=True)
            if not hasattr(self, '_date_cache_hit_logged'):
                logging.info(f"Date sprite cache HIT: rendered '{date_str}' in {date_cache_ms:.1f}ms")
                self._date_cache_hit_logged = True
        else:
            # Fallback to direct rendering (slow path)
            if not hasattr(self, '_date_cache_miss_logged'):
                logging.warning(f"Date sprite cache MISS for '{date_str}', using slow direct rendering")
                self._date_cache_miss_logged = True
            if not self._temp_draw:
                self._temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
            date_bbox = self._temp_draw.textbbox((0,0), date_str, font=self.date_font)
            date_w = date_bbox[2] - date_bbox[0]
            date_h = date_bbox[3] - date_bbox[1]
            d_pad_left = max(40, int(self.date_font_size * 0.4))
            d_pad_right = max(40, int(self.date_font_size * 0.4))
            d_pad_top = max(20, int(self.date_font_size * 0.2))
            d_pad_bottom = max(20, int(self.date_font_size * 0.2))
            date_canvas_w = date_w + d_pad_left + d_pad_right
            date_canvas_h = date_h + d_pad_top + d_pad_bottom
            date_x = max(margin, min(self.fb_width - margin - date_canvas_w, center_x - date_canvas_w // 2))
            date_y = max(margin, min(self.fb_height - margin - date_canvas_h, center_y + date_offset_y))
            date_img = Image.new('RGB', (date_canvas_w, date_canvas_h), (0,0,0))
            ImageDraw.Draw(date_img).text((d_pad_left - date_bbox[0], d_pad_top - date_bbox[1]), date_str, font=self.date_font, fill=display_color)
            self.blit_rgb_image(date_img, date_x, date_y, clear_last_rect_attr='_last_date_rect', skip_write=True)
        
        # Draw weather if available (measure, pad, and blit like time/date)
        if self.weather_text:
            if not self._temp_draw:
                self._temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
            wb = self._temp_draw.textbbox((0, 0), self.weather_text, font=self.weather_font)
            ww = wb[2] - wb[0]
            wh = wb[3] - wb[1]
            w_pad_left = max(12, int(self.weather_font_size * 0.2))
            w_pad_right = max(12, int(self.weather_font_size * 0.2))
            w_pad_top = max(6, int(self.weather_font_size * 0.12))
            w_pad_bottom = max(6, int(self.weather_font_size * 0.12))
            weather_img = Image.new('RGB', (ww + w_pad_left + w_pad_right, wh + w_pad_top + w_pad_bottom), (0,0,0))
            ImageDraw.Draw(weather_img).text((w_pad_left - wb[0], w_pad_top - wb[1]), self.weather_text, font=self.weather_font, fill=display_color)
            weather_x = center_x - (weather_img.width // 2)
            weather_y = center_y + int(120 * self.display_scale)
            self.blit_rgb_image(weather_img, weather_x, weather_y, clear_last_rect_attr='_last_weather_rect', skip_write=True)
        
        # Draw status bar
        if self.show_status_bar:
            status_items = []  # list of (name, label)
            # Network with icon
            if self.network_status:
                if "Connected" in self.network_status:
                    status_items.append(("network", self.network_status))
                else:
                    status_items.append(("error", self.network_status))
            # Timezone
            if self.timezone_name:
                status_items.append(("timezone", f"TZ:{self.timezone_name}"))
            # Sync status
            sync_time = self.get_time_since_sync()
            if sync_time == "Just now" or "m ago" in sync_time:
                status_items.append(("sync_ok", f"Sync: {sync_time}"))
            else:
                status_items.append(("sync_old", f"Sync: {sync_time}"))
            
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
                    status_items.append(("version", " ".join(parts)))
            # Always append settings item for overlay access
            status_items.append(("settings", "Settings"))
            
            status_text = " | ".join([label for _, label in status_items])
            
            # Status bar position is now fixed to avoid artifacts
            # Rotation disabled - pixel shift still provides burn-in protection
            # Render status bar using consolidated method
            self._render_status_bar(status_items, status_color, margin)
        
        t_draw = time.time()
        # Render settings overlay if active
        if self.show_settings_overlay:
            self._render_settings_overlay()
        # Optional pointer cursor (visible when input present)
        if getattr(self, 'input_devices', None):
            cur_size = 8
            cur_img = Image.new('RGB', (cur_size, cur_size), (0,0,0))
            cd = ImageDraw.Draw(cur_img)
            cd.ellipse((1,1,cur_size-2,cur_size-2), outline=(255,255,255))
            px = max(0, min(self.fb_width - cur_size, self.pointer_x))
            py = max(0, min(self.fb_height - cur_size, self.pointer_y))
            self.blit_rgb_image(cur_img, px, py, clear_last_rect_attr='_last_cursor_rect', skip_write=True)
        # Write shadow buffer to framebuffer ONCE at the end
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
        """Write image directly to framebuffer device.
        If using 16bpp shadow buffer, write only dirty rectangles.
        """
        try:
            # For partial-update path, write only dirty rects if present
            if self.fb_bpp == 16 and isinstance(self.fb_shadow, np.ndarray):
                if getattr(self, '_dirty_rects', None):
                    if self.fb_mmap:
                        # Use memory map for fast row copies
                        for (rx, ry, rw, rh) in self._dirty_rects:
                            if rw <= 0 or rh <= 0:
                                continue
                            rx = max(0, min(self.fb_width - 1, rx))
                            ry = max(0, min(self.fb_height - 1, ry))
                            rw = max(0, min(self.fb_width - rx, rw))
                            rh = max(0, min(self.fb_height - ry, rh))
                            if rw == 0 or rh == 0:
                                continue
                            for row in range(rh):
                                offset = ((ry + row) * self._fb_stride_bytes) + (rx * 2)
                                slice_row = self.fb_shadow[ry + row, rx:rx+rw]
                                self.fb_mmap[offset:offset + (rw * 2)] = slice_row.astype('<u2').tobytes()
                        self._dirty_rects.clear()
                    else:
                        # Fallback to file writes with seek
                        with open(self.fb_device, 'r+b') as fb:
                            stride_bytes = self.fb_width * 2
                            for (rx, ry, rw, rh) in self._dirty_rects:
                                if rw <= 0 or rh <= 0:
                                    continue
                                rx = max(0, min(self.fb_width - 1, rx))
                                ry = max(0, min(self.fb_height - 1, ry))
                                rw = max(0, min(self.fb_width - rx, rw))
                                rh = max(0, min(self.fb_height - ry, rh))
                                if rw == 0 or rh == 0:
                                    continue
                                for row in range(rh):
                                    offset = ((ry + row) * stride_bytes) + (rx * 2)
                                    fb.seek(offset)
                                    slice_row = self.fb_shadow[ry + row, rx:rx+rw]
                                    fb.write(slice_row.astype('<u2').tobytes())
                            self._dirty_rects.clear()
                else:
                    # No dirty rects tracked; fallback to full shadow write
                    if self.fb_mmap:
                        # Copy entire shadow into mmap in chunks to avoid huge temporary buffers
                        for row in range(self.fb_height):
                            offset = (row * self._fb_stride_bytes)
                            slice_row = self.fb_shadow[row, :]
                            self.fb_mmap[offset:offset + self._fb_stride_bytes] = slice_row.astype('<u2').tobytes()
                    else:
                        with open(self.fb_device, 'wb') as fb:
                            fb.write(self.fb_shadow.astype('<u2').tobytes())
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

    def blit_rgb_image(self, img: Image.Image, x: int, y: int, clear_last_rect_attr: str, skip_write: bool = False):
        """Convert a small RGB888 PIL image to RGB565 and blit into shadow buffer at (x,y).
        Clears previous rect stored in the attribute to avoid trails.
        If skip_write=True, don't write to framebuffer yet (batch writes).
        """
        if self.fb_bpp != 16 or not isinstance(self.fb_shadow, np.ndarray):
            # Fallback: draw onto a full-size image (rare path)
            full = Image.new('RGB', (self.fb_width, self.fb_height), self.bg_color)
            full.paste(img, (x, y))
            if not skip_write:
                self.write_to_framebuffer(full)
            return
        # Clear previous rect with padding to eliminate artifacts from width changes
        last_rect = getattr(self, clear_last_rect_attr, None)
        if last_rect:
            lx, ly, lw, lh = last_rect
            # Add 50px padding (large 280pt font needs wide coverage)
            clear_pad = 50
            lx_clear = max(0, lx - clear_pad)
            ly_clear = max(0, ly - clear_pad)
            lx2_clear = min(self.fb_width, lx + lw + clear_pad)
            ly2_clear = min(self.fb_height, ly + lh + clear_pad)
            self.fb_shadow[ly_clear:ly2_clear, lx_clear:lx2_clear].fill(0)
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
        rect = (x, y, w, h)
        setattr(self, clear_last_rect_attr, rect)
        # Track dirty rect for partial writes
        if hasattr(self, '_dirty_rects'):
            self._dirty_rects.append(rect)
    
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
        title_text = ">> SETTINGS MENU <<"
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
        last_minute = -1  # Track minute too to ensure we never skip
        loop_count = 0
        
        try:
            while self.running:
                loop_count += 1
                # Poll input (non-blocking)
                self._poll_input()
                
                # Check if second has changed (also check minute to handle sleep overshoots)
                current_second = datetime.now().second
                current_minute = datetime.now().minute
                
                # Decide whether to render this loop
                if self.show_seconds:
                    render_due = (current_second != last_second) or (current_minute != last_minute)
                else:
                    # Throttle: when seconds are hidden, redraw on minute change (reduces CPU)
                    render_due = (current_minute != last_minute)

                if render_due:
                    # Skip expensive updates if overlay is showing
                    if not self.show_settings_overlay:
                        # Update weather periodically
                        self.update_weather()
                        
                        # Update status information
                        self.update_status()
                        
                        # Update pixel shift
                        self.update_pixel_shift()
                        
                        # Update burn-in protection: vary font size and font family
                        self.update_burn_in_protection()
                    
                    # Render
                    self.render()
                    
                    last_second = current_second
                    last_minute = current_minute
                    frame_count += 1
                    
                    if frame_count % 300 == 0:  # Log every 5 minutes (reduce I/O)
                        avg_loops = loop_count / frame_count if frame_count > 0 else 0
                        logging.info(f"Clock stats: {frame_count} renders, {loop_count} loops, {avg_loops:.1f} loops/render")
                
                # Check for restart flag
                if os.path.exists('/tmp/restart_clock'):
                    logging.info("Restart flag detected - exiting")
                    os.remove('/tmp/restart_clock')
                    break
                
                # Align sleep based on mode:
                # - With overlay shown: sleep a short interval for snappy UI
                # - With seconds shown: align to next second to avoid skips
                # - With seconds hidden and no overlay: align to next minute for lower CPU
                if self.show_settings_overlay:
                    hz = getattr(self, 'overlay_refresh_hz', 10.0)
                    interval = 1.0 / max(1.0, float(hz))
                    time.sleep(interval)
                elif not self.show_seconds and not self.show_settings_overlay:
                    now_ts = time.time()
                    next_minute = (math.floor(now_ts / 60.0) * 60.0) + 60.0
                    delay = max(0.0, next_minute - now_ts)
                else:
                    now_ts = time.time()
                    next_second = math.floor(now_ts) + 1.0
                    delay = max(0.0, next_second - now_ts)
                # Sleep until next boundary (if not already slept for overlay cadence)
                if not self.show_settings_overlay:
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            logging.info("Clock interrupted by user")
        except Exception as e:
            logging.error(f"Error in clock loop: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        logging.info("Framebuffer clock stopped")
        # Terminate native renderer if running
        try:
            if getattr(self, 'native_renderer_enabled', False) and self.native_proc and self.native_proc.stdin:
                # Ask daemon to exit gracefully
                self._send_native("QUIT")
                time.sleep(0.2)
            if getattr(self, 'native_proc', None):
                self.native_proc.terminate()
        except Exception:
            pass
        try:
            if getattr(self, 'fb_mmap', None):
                self.fb_mmap.close()
            if getattr(self, '_fb_file', None):
                self._fb_file.close()
        except Exception:
            pass


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

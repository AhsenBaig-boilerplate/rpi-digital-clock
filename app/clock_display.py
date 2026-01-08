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
import time
from datetime import datetime
from pathlib import Path
import yaml

# Import weather service
try:
    from weather import WeatherService
except ImportError:
    WeatherService = None

# Import RTC module (optional hardware)
try:
    from rtc import RTCManager
except ImportError:
    RTCManager = None


class PygameClock:
    """Pygame-based digital clock display."""
    
    def __init__(self, config: dict):
        """Initialize pygame clock."""
        self.config = config
        self.running = True
        
        # Initialize pygame (disable audio mixer to prevent ALSA errors)
        pygame.init()
        pygame.mixer.quit()  # We don't need audio for a clock display
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
        
        # Calculate font scaling based on screen resolution
        # Base sizes designed for 1920x1200, scale proportionally for other resolutions
        base_width = 1920
        base_height = 1200
        scale_factor = min(self.screen_width / base_width, self.screen_height / base_height)
        
        logging.info(f"Font scale factor: {scale_factor:.2f} (based on {self.screen_width}x{self.screen_height})")
        
        # Font sizes - scale based on resolution for optimal space usage
        # Large defaults for distance visibility (use 70-80% of screen height for time)
        base_time_size = display_config.get('time_font_size', 380)
        base_date_size = display_config.get('date_font_size', 110)
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
        self.network_offline_since = None  # Track when network went offline
        self.network_was_connected = False  # Track previous connection state
        # Prefer TIMEZONE env var, fallback to TZ, else system default
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
            logging.info(f"Pixel shift enabled: +/-{self.pixel_shift_max}px every {display_config.get('pixel_shift_interval_seconds', 30)}s (disabled {self.pixel_shift_disable_start:02d}:00-{self.pixel_shift_disable_end:02d}:00)")
        
        # Weather service
        self.weather_service = None
        if config.get('weather', {}).get('enabled', False):
            api_key = os.environ.get('WEATHER_API_KEY') or config.get('weather', {}).get('api_key', '')
            if api_key and WeatherService:
                self.weather_service = WeatherService(config.get('weather', {}))
        
        # RTC module (optional hardware support)
        self.rtc = None
        rtc_enabled = os.environ.get('RTC_ENABLED', '').lower() == 'true' or config.get('time', {}).get('rtc_enabled', False)
        if rtc_enabled and RTCManager:
            self.rtc = RTCManager(enabled=True)
            if self.rtc.available:
                logging.info("DS3231 RTC available - will sync system time from RTC if network unavailable")
                # Try to sync from RTC on startup if network is down
                if self.network_status in ["No Network", "Unknown"]:
                    self.rtc.sync_system_from_rtc()
            else:
                logging.warning("RTC enabled but hardware not detected")
                self.rtc = None
        
        # Clock for FPS
        self.clock = pygame.time.Clock()
        
        # Weather update tracking
        self.last_weather_update = 0
        self.weather_text = ""
        
        # Get initial NTP sync time
        self.check_last_ntp_sync()
        
        # Load emoji PNG icons (lightweight alternative to emoji fonts)
        self.emoji_icons = self.load_emoji_icons()
        
        # Log pixel shift status
        if self.pixel_shift_enabled:
            logging.info(f"Pixel shift enabled: +/-{self.pixel_shift_max}px every {display_config.get('pixel_shift_interval_seconds', 30)}s")
        else:
            logging.info("Pixel shift disabled")
        
        # Startup runtime summary
        pygame_ver = getattr(pygame, '__version__', 'unknown')
        icon_mode = f"PNG ({len(self.emoji_icons)} icons)" if self.emoji_icons else "ASCII"
        rtc_mode = "Active" if (self.rtc and self.rtc.available) else "Disabled"
        logging.info(f"Runtime summary: pygame {pygame_ver} | Icons: {icon_mode} | RTC: {rtc_mode}")
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
    
    def load_emoji_icons(self) -> dict:
        """
        Load emoji PNG icons from assets/emojis/ directory.
        Returns dict mapping icon names to pygame surfaces.
        Falls back gracefully if icons not found.
        """
        icons = {}
        emoji_dir = Path(__file__).parent / "assets" / "emojis"
        
        # Icon files to load (16x16 or 24x24 PNGs work well)
        icon_files = {
            'wifi': 'wifi.png',
            'ethernet': 'ethernet.png',
            'network_error': 'network_error.png',
            'globe': 'globe.png',
            'sync': 'sync.png',
            'clock': 'clock.png',
        }
        
        if not emoji_dir.exists():
            logging.info("Emoji icons directory not found, using ASCII fallback")
            return icons
        
        # Load each icon
        for name, filename in icon_files.items():
            icon_path = emoji_dir / filename
            if icon_path.exists():
                try:
                    # Load and scale icon to appropriate size (24x24 for status bar)
                    icon = pygame.image.load(str(icon_path))
                    icon = pygame.transform.smoothscale(icon, (24, 24))
                    icons[name] = icon
                    logging.debug(f"Loaded emoji icon: {name}")
                except Exception as e:
                    logging.debug(f"Failed to load emoji icon {name}: {e}")
        
        if icons:
            logging.info(f"Loaded {len(icons)} emoji PNG icons")
            try:
                names = ", ".join(sorted(icons.keys()))
                logging.info(f"Emoji icons available: {names}")
            except Exception:
                pass
        else:
            logging.info("No emoji icons loaded, using ASCII fallback")
        
        return icons
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def format_time(self, now):
        """Format time string."""
        if self.format_12h:
            if self.show_seconds:
                # Use %-I to remove leading zero (6:56:06 AM instead of 06:56:06 AM)
                return now.strftime("%-I:%M:%S %p")
            else:
                return now.strftime("%-I:%M %p")
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
        """Check network/WiFi connectivity with detailed status."""
        try:
            # Try to connect to Google DNS to verify internet connectivity (0.5s timeout to avoid blocking)
            socket.create_connection(("8.8.8.8", 53), timeout=0.5)
            
            # Check WiFi status and signal strength
            try:
                result = subprocess.run(
                    ['iwconfig'], 
                    capture_output=True, 
                    text=True, 
                    timeout=2
                )
                
                # Look for active WiFi interface
                if 'ESSID:' in result.stdout and 'off/any' not in result.stdout.lower():
                    # Extract signal quality and level
                    for line in result.stdout.split('\n'):
                        if 'Link Quality' in line:
                            # Parse: Link Quality=65/70  Signal level=-45 dBm
                            try:
                                quality_part = line.split('Link Quality=')[1].split()[0]
                                current, maximum = quality_part.split('/')
                                percentage = int((int(current) / int(maximum)) * 100)
                                
                                # Get signal level if available
                                if 'Signal level=' in line:
                                    signal = line.split('Signal level=')[1].split()[0]
                                    self.network_status = f"WiFi {percentage}% ({signal}dBm)"
                                else:
                                    self.network_status = f"WiFi {percentage}%"
                                return
                            except:
                                # Fallback if parsing fails
                                self.network_status = f"WiFi Connected"
                                return
                    
                    # WiFi interface active but couldn't parse quality
                    self.network_status = "WiFi Active"
                    return
            except:
                pass
            
            # Check if we have Ethernet connection
            try:
                result = subprocess.run(
                    ['ip', 'link', 'show'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                # Look for eth0 or similar Ethernet interfaces that are UP
                for line in result.stdout.split('\n'):
                    if ('eth' in line.lower() or 'enp' in line.lower()) and 'state UP' in line:
                        # Try to get link speed
                        try:
                            iface = line.split(':')[1].strip().split('@')[0]
                            speed_result = subprocess.run(
                                ['ethtool', iface],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if 'Speed:' in speed_result.stdout:
                                speed = speed_result.stdout.split('Speed:')[1].split('\n')[0].strip()
                                self.network_status = f"Ethernet {speed}"
                                return
                        except:
                            pass
                        
                        self.network_status = "Ethernet"
                        return
            except:
                pass
            
            # Has internet but couldn't identify interface type
            self.network_status = "Connected"
            self.network_was_connected = True
            self.network_offline_since = None  # Reset offline timer
            
        except socket.timeout:
            self._handle_network_offline("No Internet")
        except:
            self._handle_network_offline("Offline")
    
    def _handle_network_offline(self, base_status):
        """Handle network offline state with duration tracking."""
        # Start tracking offline time if we just went offline
        if self.network_was_connected or self.network_offline_since is None:
            self.network_offline_since = time.time()
            self.network_was_connected = False
            self.network_status = base_status
            return
        
        # Calculate offline duration
        offline_duration = time.time() - self.network_offline_since
        
        # Format duration
        if offline_duration < 60:
            duration_str = f"{int(offline_duration)}s"
        elif offline_duration < 3600:
            minutes = int(offline_duration / 60)
            seconds = int(offline_duration % 60)
            duration_str = f"{minutes}m {seconds}s"
        else:
            hours = int(offline_duration / 3600)
            minutes = int((offline_duration % 3600) / 60)
            duration_str = f"{hours}h {minutes}m"
        
        self.network_status = f"{base_status} {duration_str}"
    
    def check_last_ntp_sync(self):
        """Check last NTP synchronization time."""
        # Prefer parsing systemd-timesyncd journal for last sync event
        try:
            result = subprocess.run(
                ['journalctl', '-u', 'systemd-timesyncd', '--since', '24 hours ago', '--no-pager', '--output', 'short-iso'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0 and result.stdout:
                for line in reversed(result.stdout.splitlines()):
                    if 'Synchronized' in line or 'System clock synchronized' in line:
                        # short-iso format: YYYY-MM-DD HH:MM:SS[.ms] 
                        ts = line.split()[0] + ' ' + line.split()[1]
                        ts = ts.split('.')[0]  # drop milliseconds if present
                        try:
                            self.last_ntp_sync = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                            return
                        except Exception:
                            # If parsing fails, just set to now
                            self.last_ntp_sync = datetime.now()
                            return
        except Exception:
            pass
        
        # Fallback: timedatectl synchronized flag
        try:
            result = subprocess.run(
                ['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip() == 'yes':
                self.last_ntp_sync = datetime.now()
                return
        except Exception:
            pass
        
        # Last resort: assume synced at startup
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
        self.check_last_ntp_sync()
        self.last_status_check = current_time
        
        # Periodic RTC sync: save system time to RTC every 30s if network available
        if self.rtc and self.rtc.available and self.network_status in ["WiFi", "Ethernet"]:
            self.rtc.write_time()
    
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
        
        # Check screensaver
        if not self.should_show_display():
            pygame.display.flip()
            return
        
        # Update brightness
        self.update_brightness()
        
        # Get current time
        now = datetime.now()
        
        # Format strings
        time_str = self.format_time(now)
        date_str = self.format_date(now)
        
        # Apply brightness to colors
        display_color = self.apply_brightness(self.color)
        status_color = self.apply_brightness(self.status_color)
        
        # Render text surfaces with brightness applied
        time_surface = self.time_font.render(time_str, True, display_color)
        date_surface = self.date_font.render(date_str, True, display_color)
        
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
        
        # Update display
        pygame.display.flip()
    
    def render_status_bar(self, status_color):
        """Render status bar with system information using PNG icons or ASCII fallback."""
        # Check if we have PNG emoji icons loaded
        use_png_icons = bool(self.emoji_icons) and (os.environ.get('USE_EMOJI', 'true').lower() == 'true')
        
        # Starting X position for left-aligned status items
        x_pos = 10
        y_pos = self.screen_height - 30
        spacing = 5  # Space between icon and text
        item_gap = 20  # Gap between status items
        
        # Network status
        if self.network_status:
            if "WiFi" in self.network_status:
                icon_key = 'wifi'
                text = self.network_status
            elif "Ethernet" in self.network_status:
                icon_key = 'ethernet'
                text = self.network_status
            else:
                icon_key = 'network_error'
                text = self.network_status
        else:
            icon_key = 'network_error'
            text = "No Network"
        
        # Render network status
        if use_png_icons and icon_key in self.emoji_icons:
            self.screen.blit(self.emoji_icons[icon_key], (x_pos, y_pos))
            x_pos += 24 + spacing
        else:
            # ASCII fallback
            prefix = "WiFi:" if "WiFi" in text else ("Net:" if "Ethernet" in text else "X")
            text_surface = self.status_font.render(f"{prefix} {text}", True, status_color)
            self.screen.blit(text_surface, (x_pos, y_pos))
            x_pos += text_surface.get_width() + item_gap
            text = ""  # Already included in prefix
        
        if text:
            text_surface = self.status_font.render(text, True, status_color)
            self.screen.blit(text_surface, (x_pos, y_pos))
            x_pos += text_surface.get_width() + item_gap
        
        # Separator
        sep_surface = self.status_font.render("|", True, status_color)
        self.screen.blit(sep_surface, (x_pos, y_pos))
        x_pos += sep_surface.get_width() + item_gap
        
        # Timezone with abbreviation
        try:
            tz_abbr = time.strftime('%Z')
        except Exception:
            tz_abbr = "TZ"
        
        if use_png_icons and 'globe' in self.emoji_icons:
            self.screen.blit(self.emoji_icons['globe'], (x_pos, y_pos))
            x_pos += 24 + spacing
            tz_text = f"{tz_abbr} ({self.timezone_name})" if self.timezone_name else tz_abbr
        else:
            tz_text = f"TZ: {tz_abbr} ({self.timezone_name})" if self.timezone_name else f"TZ: {tz_abbr}"
        
        tz_surface = self.status_font.render(tz_text, True, status_color)
        self.screen.blit(tz_surface, (x_pos, y_pos))
        x_pos += tz_surface.get_width() + item_gap
        
        # Separator
        self.screen.blit(sep_surface, (x_pos, y_pos))
        x_pos += sep_surface.get_width() + item_gap
        
        # Last sync
        sync_time = self.get_time_since_sync()
        if use_png_icons and 'sync' in self.emoji_icons:
            self.screen.blit(self.emoji_icons['sync'], (x_pos, y_pos))
            x_pos += 24 + spacing
            sync_text = sync_time
        else:
            sync_text = f"Sync: {sync_time}"
        
        sync_surface = self.status_font.render(sync_text, True, status_color)
        self.screen.blit(sync_surface, (x_pos, y_pos))
        x_pos += sync_surface.get_width() + item_gap
        
        # RTC status if available
        if self.rtc and self.rtc.available:
            # Separator
            self.screen.blit(sep_surface, (x_pos, y_pos))
            x_pos += sep_surface.get_width() + item_gap
            
            if use_png_icons and 'clock' in self.emoji_icons:
                self.screen.blit(self.emoji_icons['clock'], (x_pos, y_pos))
                x_pos += 24 + spacing
                rtc_text = "Active"
            else:
                rtc_text = "RTC: Active"
            
            rtc_surface = self.status_font.render(rtc_text, True, status_color)
            self.screen.blit(rtc_surface, (x_pos, y_pos))
    
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
        in_screensaver = False
        
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

                # Check if we're entering/exiting screensaver mode
                should_show = self.should_show_display()
                if not should_show and not in_screensaver:
                    # Entering screensaver mode
                    in_screensaver = True
                    logging.info("Entering screensaver mode")
                elif should_show and in_screensaver:
                    # Exiting screensaver mode - reset pygame clock to prevent drift
                    in_screensaver = False
                    self.clock = pygame.time.Clock()
                    logging.info("Exiting screensaver mode - clock reset")

                
                # Render
                self.render()
                
                # Limit to 10 FPS for smooth second updates (updates every 0.1 seconds)
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
    
    # Log environment variables (mask sensitive values)
    def mask(name: str, value: str) -> str:
        if value is None:
            return ""
        upper = name.upper()
        if any(s in upper for s in ["KEY", "TOKEN", "SECRET", "PASSWORD"]):
            return "****"
        return value
    
    env_names = [
        # Weather
        "WEATHER_API_KEY", "BALENA_WEATHER_API_KEY",
        "WEATHER_LOCATION", "BALENA_WEATHER_LOCATION",
        "WEATHER_UNITS", "BALENA_WEATHER_UNITS",
        "WEATHER_ENABLED", "BALENA_WEATHER_ENABLED",
        # Time / logging / display
        "TIMEZONE", "BALENA_TIMEZONE", "TZ",
        "RTC_ENABLED", "BALENA_RTC_ENABLED",
        "LOG_LEVEL", "BALENA_LOG_LEVEL",
        "DISPLAY_ORIENTATION", "BALENA_DISPLAY_ORIENTATION",
        "DISPLAY_COLOR", "BALENA_DISPLAY_COLOR",
        "FONT_FAMILY", "BALENA_FONT_FAMILY",
        "TIME_FONT_SIZE", "BALENA_TIME_FONT_SIZE",
        "TIME_FORMAT_12H", "BALENA_TIME_FORMAT_12H",
        "SHOW_SECONDS", "BALENA_SHOW_SECONDS",
        "DATE_FORMAT", "BALENA_DATE_FORMAT",
        # Burn-in prevention
        "SCREENSAVER_ENABLED", "BALENA_SCREENSAVER_ENABLED",
        "SCREENSAVER_START_HOUR", "BALENA_SCREENSAVER_START_HOUR",
        "SCREENSAVER_END_HOUR", "BALENA_SCREENSAVER_END_HOUR",
        "PIXEL_SHIFT_ENABLED", "BALENA_PIXEL_SHIFT_ENABLED",
        "PIXEL_SHIFT_INTERVAL_SECONDS", "BALENA_PIXEL_SHIFT_INTERVAL_SECONDS",
        "PIXEL_SHIFT_DISABLE_START_HOUR", "BALENA_PIXEL_SHIFT_DISABLE_START_HOUR",
        "PIXEL_SHIFT_DISABLE_END_HOUR", "BALENA_PIXEL_SHIFT_DISABLE_END_HOUR",
        "DIM_AT_NIGHT", "BALENA_DIM_AT_NIGHT",
        "NIGHT_BRIGHTNESS", "BALENA_NIGHT_BRIGHTNESS",
        "NIGHT_START_HOUR", "BALENA_NIGHT_START_HOUR",
        "NIGHT_END_HOUR", "BALENA_NIGHT_END_HOUR",
    ]
    service_name = os.environ.get("BALENA_SERVICE_NAME", "unknown")
    logging.info(f"Service context: {service_name}")
    logging.info("Environment variables (masked where sensitive):")
    
    # Log balena device/fleet metadata for visibility
    logging.info("Device metadata (balena environment):")
    device_envs = [
        "BALENA_DEVICE_NAME",
        "BALENA_DEVICE_TYPE",
        "BALENA_DEVICE_UUID",
        "BALENA_DEVICE_ARCH",
        "BALENA_HOST_OS_VERSION",
        "BALENA_SUPERVISOR_VERSION",
        "BALENA_SUPERVISOR_ADDRESS",
        "BALENA_SUPERVISOR_API_KEY",
        "BALENA_APP_NAME",
        "BALENA_APP_ID",
        "BALENA_APP_COMMIT",
        "BALENA_FLEET_SLUG",
        "BALENA_SERVICE_NAME",
    ]
    for name in device_envs:
        if name in os.environ:
            value = mask(name, os.environ.get(name))
            logging.info(f"  [Device] {name}={value}")
    
    def scope_label(var_name: str) -> str:
        # Treat BALENA_ prefixed as Global; others as Service-scoped to current service
        return "Global" if var_name.startswith("BALENA_") else f"Service({service_name})"
    
    for name in env_names:
        if name in os.environ:
            value = mask(name, os.environ.get(name))
            scope = scope_label(name)
            logging.info(f"  [{scope}] {name}={value}")
    
    # Create and run clock
    clock = PygameClock(config)
    clock.run()


if __name__ == '__main__':
    main()

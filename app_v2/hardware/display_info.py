"""
Display Info - Screen resolution and display detection
"""
import tkinter as tk
from typing import Tuple, Optional, Dict


class DisplayInfo:
    """
    Display information and screen resolution detection.
    """
    
    def __init__(self):
        """Initialize display info detector"""
        self._screen_width: Optional[int] = None
        self._screen_height: Optional[int] = None
        self._detected: bool = False
    
    def detect(self) -> Tuple[int, int]:
        """
        Detect screen resolution using Tkinter.
        
        Returns:
            Tuple of (width, height) in pixels
        """
        if self._detected and self._screen_width and self._screen_height:
            return (self._screen_width, self._screen_height)
        
        try:
            # Create temporary root window to query screen size
            root = tk.Tk()
            root.withdraw()  # Hide window
            
            self._screen_width = root.winfo_screenwidth()
            self._screen_height = root.winfo_screenheight()
            
            root.destroy()
            self._detected = True
            
            return (self._screen_width, self._screen_height)
            
        except Exception as e:
            print(f"Display detection failed: {e}")
            # Fallback to common RPi display sizes
            return (800, 480)
    
    def get_dimensions(self) -> Tuple[int, int]:
        """
        Get display dimensions.
        
        Returns:
            Tuple of (width, height)
        """
        if not self._detected:
            return self.detect()
        return (self._screen_width or 800, self._screen_height or 480)
    
    def get_width(self) -> int:
        """Get screen width"""
        width, _ = self.get_dimensions()
        return width
    
    def get_height(self) -> int:
        """Get screen height"""
        _, height = self.get_dimensions()
        return height
    
    def get_aspect_ratio(self) -> float:
        """
        Calculate screen aspect ratio.
        
        Returns:
            Aspect ratio (width / height)
        """
        width, height = self.get_dimensions()
        return width / height if height > 0 else 1.0
    
    def is_landscape(self) -> bool:
        """Check if display is landscape orientation"""
        return self.get_aspect_ratio() > 1.0
    
    def is_portrait(self) -> bool:
        """Check if display is portrait orientation"""
        return self.get_aspect_ratio() < 1.0
    
    def get_info(self) -> Dict[str, any]:
        """
        Get comprehensive display information.
        
        Returns:
            Dictionary with display details
        """
        width, height = self.get_dimensions()
        aspect = self.get_aspect_ratio()
        
        # Detect common display types
        display_type = 'Unknown'
        if (width, height) == (800, 480):
            display_type = '7" RPi Touchscreen (800x480)'
        elif (width, height) == (1024, 600):
            display_type = '7" HDMI Display (1024x600)'
        elif (width, height) == (1920, 1080):
            display_type = 'Full HD (1920x1080)'
        elif (width, height) == (1280, 720):
            display_type = 'HD (1280x720)'
        
        return {
            'width': width,
            'height': height,
            'aspect_ratio': round(aspect, 2),
            'orientation': 'landscape' if self.is_landscape() else 'portrait',
            'display_type': display_type,
            'detected': self._detected
        }
    
    def __str__(self) -> str:
        """String representation"""
        width, height = self.get_dimensions()
        return f"{width}x{height}"
    
    def __repr__(self) -> str:
        """Developer representation"""
        info = self.get_info()
        return f"DisplayInfo(width={info['width']}, height={info['height']}, type='{info['display_type']}')"

"""
Layout - Grid layout manager for clock UI components
"""
from typing import Dict, Tuple, Optional
from .theme import Theme


class Layout:
    """
    Manages layout calculations and positioning for UI components.
    """
    
    def __init__(self, width: int, height: int):
        """
        Initialize layout manager.
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self._width = width
        self._height = height
        
        # Define regions as percentages
        self._regions = {
            'time': {'x': 0.0, 'y': 0.2, 'width': 1.0, 'height': 0.4},
            'date': {'x': 0.0, 'y': 0.6, 'width': 1.0, 'height': 0.15},
            'weather': {'x': 0.0, 'y': 0.8, 'width': 1.0, 'height': 0.2},
        }
    
    def get_region(self, name: str) -> Dict[str, int]:
        """
        Get pixel coordinates for named region.
        
        Args:
            name: Region name ('time', 'date', 'weather')
        
        Returns:
            Dictionary with x, y, width, height in pixels
        """
        if name not in self._regions:
            raise ValueError(f"Unknown region: {name}")
        
        region = self._regions[name]
        
        return {
            'x': int(region['x'] * self._width),
            'y': int(region['y'] * self._height),
            'width': int(region['width'] * self._width),
            'height': int(region['height'] * self._height),
        }
    
    def get_center_position(self, region: str) -> Tuple[int, int]:
        """
        Get center coordinates of a region.
        
        Args:
            region: Region name
        
        Returns:
            Tuple of (x, y) center coordinates
        """
        r = self.get_region(region)
        center_x = r['x'] + r['width'] // 2
        center_y = r['y'] + r['height'] // 2
        return (center_x, center_y)
    
    def calculate_font_size(self, region: str, text_length: int, base_size: int) -> int:
        """
        Calculate optimal font size for text in region.
        
        Args:
            region: Region name
            text_length: Number of characters
            base_size: Starting font size
        
        Returns:
            Adjusted font size
        """
        r = self.get_region(region)
        available_width = r['width'] - (Theme.PADDING_LARGE * 2)
        
        # Rough estimate: character width is ~0.6 * font_size
        char_width = base_size * 0.6
        required_width = text_length * char_width
        
        if required_width > available_width:
            # Scale down font to fit
            scale = available_width / required_width
            return int(base_size * scale)
        
        return base_size
    
    def get_time_layout(self) -> Dict[str, any]:
        """
        Get layout configuration for time display.
        
        Returns:
            Layout dictionary with position and sizing
        """
        region = self.get_region('time')
        center_x, center_y = self.get_center_position('time')
        
        # Estimate time string length (e.g., "12:34:56")
        time_length = 8
        font_size = self.calculate_font_size('time', time_length, Theme.FONT_SIZE_HUGE)
        
        return {
            'x': center_x,
            'y': center_y,
            'font': Theme.get_time_font(font_size),
            'anchor': 'center',
            'color': Theme.FG_PRIMARY,
        }
    
    def get_date_layout(self) -> Dict[str, any]:
        """
        Get layout configuration for date display.
        
        Returns:
            Layout dictionary with position and sizing
        """
        region = self.get_region('date')
        center_x, center_y = self.get_center_position('date')
        
        # Estimate date string length (e.g., "Monday, January 15, 2024")
        date_length = 30
        font_size = self.calculate_font_size('date', date_length, Theme.FONT_SIZE_LARGE)
        
        return {
            'x': center_x,
            'y': center_y,
            'font': Theme.get_date_font(font_size),
            'anchor': 'center',
            'color': Theme.FG_SECONDARY,
        }
    
    def get_weather_layout(self) -> Dict[str, any]:
        """
        Get layout configuration for weather display.
        
        Returns:
            Layout dictionary with position and sizing
        """
        region = self.get_region('weather')
        center_x, center_y = self.get_center_position('weather')
        
        # Weather display is typically shorter
        weather_length = 25
        font_size = self.calculate_font_size('weather', weather_length, Theme.FONT_SIZE_MEDIUM)
        
        return {
            'x': center_x,
            'y': center_y,
            'font': Theme.get_weather_font(font_size),
            'anchor': 'center',
            'color': Theme.FG_TERTIARY,
        }
    
    def get_full_layout(self) -> Dict[str, Dict[str, any]]:
        """
        Get complete layout configuration for all components.
        
        Returns:
            Dictionary mapping component names to layout configs
        """
        return {
            'time': self.get_time_layout(),
            'date': self.get_date_layout(),
            'weather': self.get_weather_layout(),
        }
    
    def update_dimensions(self, width: int, height: int) -> None:
        """
        Update display dimensions and recalculate layout.
        
        Args:
            width: New display width
            height: New display height
        """
        self._width = width
        self._height = height
    
    @property
    def width(self) -> int:
        """Get display width"""
        return self._width
    
    @property
    def height(self) -> int:
        """Get display height"""
        return self._height
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Get display dimensions as tuple"""
        return (self._width, self._height)

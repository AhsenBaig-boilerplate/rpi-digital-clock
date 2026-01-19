"""
Theme - Dark theme with colors, fonts, and styling constants
"""
from typing import Dict, Tuple


class Theme:
    """
    Dark theme configuration for clock display.
    """
    
    # Color Palette
    BG_PRIMARY = '#000000'        # Pure black background
    BG_SECONDARY = '#1a1a1a'      # Slightly lighter black for panels
    
    FG_PRIMARY = '#ffffff'        # White for main text
    FG_SECONDARY = '#cccccc'      # Light gray for secondary text
    FG_TERTIARY = '#999999'       # Medium gray for tertiary text
    FG_DIM = '#666666'            # Dim gray for subtle elements
    
    ACCENT_PRIMARY = '#00aaff'    # Bright blue accent
    ACCENT_SECONDARY = '#00ffaa'  # Teal accent
    
    # Weather condition colors
    WEATHER_SUNNY = '#ffaa00'     # Orange
    WEATHER_CLOUDY = '#aaaaaa'    # Gray
    WEATHER_RAINY = '#0088ff'     # Blue
    WEATHER_SNOWY = '#ffffff'     # White
    
    # Status colors
    STATUS_SUCCESS = '#00ff00'    # Green
    STATUS_WARNING = '#ffaa00'    # Orange
    STATUS_ERROR = '#ff0000'      # Red
    
    # Font Configuration
    FONT_FAMILY = 'Helvetica'     # Default font family
    FONT_FAMILY_MONO = 'Courier'  # Monospace for digital display
    
    FONT_SIZE_HUGE = 120          # Main clock time
    FONT_SIZE_LARGE = 48          # Date, weather temp
    FONT_SIZE_MEDIUM = 24         # Weather details
    FONT_SIZE_SMALL = 16          # Status, labels
    FONT_SIZE_TINY = 12           # Fine print
    
    FONT_WEIGHT_BOLD = 'bold'
    FONT_WEIGHT_NORMAL = 'normal'
    
    # Spacing and Layout
    PADDING_LARGE = 40
    PADDING_MEDIUM = 20
    PADDING_SMALL = 10
    PADDING_TINY = 5
    
    MARGIN_LARGE = 30
    MARGIN_MEDIUM = 15
    MARGIN_SMALL = 8
    
    # Component Dimensions
    WEATHER_ICON_SIZE = 64
    BORDER_WIDTH = 2
    BORDER_RADIUS = 8
    
    @staticmethod
    def get_time_font(size: int = None) -> Tuple[str, int, str]:
        """
        Get font configuration for time display.
        
        Args:
            size: Font size (default: FONT_SIZE_HUGE)
        
        Returns:
            Tuple of (family, size, weight)
        """
        if size is None:
            size = Theme.FONT_SIZE_HUGE
        return (Theme.FONT_FAMILY, size, Theme.FONT_WEIGHT_BOLD)
    
    @staticmethod
    def get_date_font(size: int = None) -> Tuple[str, int, str]:
        """
        Get font configuration for date display.
        
        Args:
            size: Font size (default: FONT_SIZE_LARGE)
        
        Returns:
            Tuple of (family, size, weight)
        """
        if size is None:
            size = Theme.FONT_SIZE_LARGE
        return (Theme.FONT_FAMILY, size, Theme.FONT_WEIGHT_NORMAL)
    
    @staticmethod
    def get_weather_font(size: int = None) -> Tuple[str, int, str]:
        """
        Get font configuration for weather display.
        
        Args:
            size: Font size (default: FONT_SIZE_MEDIUM)
        
        Returns:
            Tuple of (family, size, weight)
        """
        if size is None:
            size = Theme.FONT_SIZE_MEDIUM
        return (Theme.FONT_FAMILY, size, Theme.FONT_WEIGHT_NORMAL)
    
    @staticmethod
    def get_label_font(size: int = None) -> Tuple[str, int, str]:
        """
        Get font configuration for labels.
        
        Args:
            size: Font size (default: FONT_SIZE_SMALL)
        
        Returns:
            Tuple of (family, size, weight)
        """
        if size is None:
            size = Theme.FONT_SIZE_SMALL
        return (Theme.FONT_FAMILY, size, Theme.FONT_WEIGHT_NORMAL)
    
    @staticmethod
    def get_weather_color(condition: str) -> str:
        """
        Get color for weather condition.
        
        Args:
            condition: Weather condition string (e.g., 'Clear', 'Clouds', 'Rain')
        
        Returns:
            Hex color string
        """
        condition_lower = condition.lower()
        
        if 'clear' in condition_lower or 'sun' in condition_lower:
            return Theme.WEATHER_SUNNY
        elif 'cloud' in condition_lower or 'overcast' in condition_lower:
            return Theme.WEATHER_CLOUDY
        elif 'rain' in condition_lower or 'drizzle' in condition_lower:
            return Theme.WEATHER_RAINY
        elif 'snow' in condition_lower or 'sleet' in condition_lower:
            return Theme.WEATHER_SNOWY
        else:
            return Theme.FG_SECONDARY
    
    @staticmethod
    def get_theme_dict() -> Dict[str, str]:
        """
        Get theme as dictionary for easy access.
        
        Returns:
            Dictionary with all theme colors and values
        """
        return {
            'bg_primary': Theme.BG_PRIMARY,
            'bg_secondary': Theme.BG_SECONDARY,
            'fg_primary': Theme.FG_PRIMARY,
            'fg_secondary': Theme.FG_SECONDARY,
            'fg_tertiary': Theme.FG_TERTIARY,
            'fg_dim': Theme.FG_DIM,
            'accent_primary': Theme.ACCENT_PRIMARY,
            'accent_secondary': Theme.ACCENT_SECONDARY,
        }

"""
Configuration Service - Production-grade config management
Loads YAML config with environment variable overrides
"""
import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigService:
    """
    Centralized configuration management with environment overrides.
    
    Priority order:
    1. Environment variables (highest)
    2. YAML config file
    3. Default values (lowest)
    """
    
    _instance: Optional['ConfigService'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        """Singleton pattern for global config access"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize only once"""
        if not self._config:
            self.reload()
    
    def reload(self) -> None:
        """Load config from file and environment"""
        self._config = self._load_yaml_config()
        self._apply_env_overrides()
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_paths = [
            Path("/data/config.yaml"),  # Production path
            Path("config/default.yaml"),  # Development path
            Path("app_v2/config/default.yaml"),  # Relative path
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f) or {}
                        return config
                except Exception as e:
                    print(f"Warning: Failed to load {config_path}: {e}")
        
        # Return defaults if no config file found
        return self._get_defaults()
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # Timezone
        if env_tz := os.environ.get('TIMEZONE'):
            self._config['timezone'] = env_tz
        
        # Weather
        if env_enabled := os.environ.get('WEATHER_ENABLED'):
            self._config.setdefault('weather', {})
            self._config['weather']['enabled'] = env_enabled.lower() in ('true', '1', 'yes')
        
        if env_key := os.environ.get('WEATHER_API_KEY'):
            self._config.setdefault('weather', {})
            self._config['weather']['api_key'] = env_key
        
        if env_location := os.environ.get('WEATHER_LOCATION'):
            self._config.setdefault('weather', {})
            self._config['weather']['location'] = env_location
        
        if env_units := os.environ.get('WEATHER_UNITS'):
            self._config.setdefault('weather', {})
            self._config['weather']['units'] = env_units
        
        # Display
        if env_width := os.environ.get('DISPLAY_WIDTH'):
            self._config.setdefault('display', {})
            self._config['display']['width'] = int(env_width)
        
        if env_height := os.environ.get('DISPLAY_HEIGHT'):
            self._config.setdefault('display', {})
            self._config['display']['height'] = int(env_height)
        
        if env_fullscreen := os.environ.get('DISPLAY_FULLSCREEN'):
            self._config.setdefault('display', {})
            self._config['display']['fullscreen'] = env_fullscreen.lower() in ('true', '1', 'yes')
        
        # Refresh interval
        if env_interval := os.environ.get('REFRESH_INTERVAL_SECONDS'):
            self._config['refresh_interval_seconds'] = int(env_interval)
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'timezone': 'America/Los_Angeles',
            'weather': {
                'enabled': True,
                'api_key': '',
                'location': 'New York',
                'units': 'metric',
                'refresh_interval_minutes': 10
            },
            'display': {
                'width': 800,
                'height': 480,
                'fullscreen': False,
                'theme': 'dark'
            },
            'refresh_interval_seconds': 1,
            'logging': {
                'level': 'INFO',
                'format': 'structured'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value using dot notation
        Example: config.get('weather.enabled')
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dict"""
        return self._config.copy()
    
    def set(self, key: str, value: Any) -> None:
        """
        Set config value using dot notation
        Example: config.set('weather.enabled', True)
        """
        keys = key.split('.')
        target = self._config
        
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        
        target[keys[-1]] = value


# Global instance
config = ConfigService()

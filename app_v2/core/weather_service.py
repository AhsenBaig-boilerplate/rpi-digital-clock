"""
Weather Service - OpenWeatherMap API integration
Handles API calls with caching and graceful fallback
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import time


class WeatherService:
    """
    Weather data service with caching and error handling.
    """
    
    def __init__(self, api_key: str, location: str, units: str = 'imperial', cache_ttl: int = 900):
        """
        Initialize weather service.
        
        Args:
            api_key: OpenWeatherMap API key
            location: City name (e.g., 'Los Angeles, US')
            units: 'imperial' or 'metric'
            cache_ttl: Cache time-to-live in seconds (default 15 minutes)
        """
        self._api_key = api_key
        self._location = location
        self._units = units
        self._cache_ttl = cache_ttl
        
        self._cache: Dict[str, Any] = {}
        self._last_fetch: float = 0
        self._last_error: Optional[str] = None
        
        self._base_url = 'https://api.openweathermap.org/data/2.5/weather'
    
    def get_weather(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get current weather data with caching.
        
        Args:
            force_refresh: Skip cache and fetch fresh data
        
        Returns:
            Weather data dictionary or None on error
        """
        now = time.time()
        
        # Return cached data if still valid
        if not force_refresh and self._cache and (now - self._last_fetch) < self._cache_ttl:
            return self._cache
        
        # Fetch fresh data
        try:
            weather_data = self._fetch_weather()
            if weather_data:
                self._cache = weather_data
                self._last_fetch = now
                self._last_error = None
                return weather_data
        except Exception as e:
            self._last_error = str(e)
            print(f"Weather fetch failed: {e}")
        
        # Return stale cache on error (better than nothing)
        return self._cache if self._cache else None
    
    def _fetch_weather(self) -> Optional[Dict[str, Any]]:
        """
        Fetch weather data from OpenWeatherMap API.
        
        Returns:
            Processed weather data or None on error
        """
        if not self._api_key or self._api_key == 'your_api_key_here':
            return None
        
        params = {
            'q': self._location,
            'appid': self._api_key,
            'units': self._units
        }
        
        try:
            response = requests.get(self._base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_weather_data(data)
        
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Failed to parse weather data: {e}")
            return None
    
    def _parse_weather_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse OpenWeatherMap response into simplified format.
        
        Args:
            raw_data: Raw API response
        
        Returns:
            Simplified weather data dictionary
        """
        main = raw_data.get('main', {})
        weather = raw_data.get('weather', [{}])[0]
        wind = raw_data.get('wind', {})
        
        temp = main.get('temp', 0)
        feels_like = main.get('feels_like', temp)
        humidity = main.get('humidity', 0)
        
        description = weather.get('description', 'Unknown').capitalize()
        icon = weather.get('icon', '01d')
        
        wind_speed = wind.get('speed', 0)
        
        # Temperature unit symbol
        temp_unit = '°F' if self._units == 'imperial' else '°C'
        wind_unit = 'mph' if self._units == 'imperial' else 'm/s'
        
        return {
            'temperature': round(temp),
            'feels_like': round(feels_like),
            'humidity': humidity,
            'description': description,
            'icon': icon,
            'wind_speed': round(wind_speed, 1),
            'location': self._location,
            'temp_unit': temp_unit,
            'wind_unit': wind_unit,
            'timestamp': time.time(),
            'display': {
                'temp': f"{round(temp)}{temp_unit}",
                'feels_like': f"Feels like {round(feels_like)}{temp_unit}",
                'humidity': f"{humidity}%",
                'wind': f"{round(wind_speed, 1)} {wind_unit}",
                'condition': description
            }
        }
    
    def is_cached(self) -> bool:
        """Check if valid cached data exists"""
        if not self._cache:
            return False
        age = time.time() - self._last_fetch
        return age < self._cache_ttl
    
    def get_cache_age(self) -> int:
        """Get age of cached data in seconds"""
        if not self._cache:
            return -1
        return int(time.time() - self._last_fetch)
    
    def update_location(self, location: str) -> None:
        """
        Update location and invalidate cache.
        
        Args:
            location: New city name
        """
        self._location = location
        self._cache = {}
        self._last_fetch = 0
    
    def update_api_key(self, api_key: str) -> None:
        """
        Update API key and invalidate cache.
        
        Args:
            api_key: New OpenWeatherMap API key
        """
        self._api_key = api_key
        self._cache = {}
        self._last_fetch = 0
    
    @property
    def last_error(self) -> Optional[str]:
        """Get last error message"""
        return self._last_error
    
    @property
    def location(self) -> str:
        """Get current location"""
        return self._location

"""
Weather Service Module - Fetches weather data from OpenWeatherMap API.
Includes error handling, caching, and fallback mechanisms.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict


class WeatherService:
    """Service for fetching and caching weather data."""
    
    def __init__(self, weather_config: dict):
        """Initialize weather service with configuration."""
        self.api_key = weather_config.get('api_key', '')
        self.location = weather_config.get('location', '')
        self.units = weather_config.get('units', 'metric')  # metric, imperial, or kelvin
        self.language = weather_config.get('language', 'en')
        
        # API endpoint
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        
        # Cache settings
        self.cache_duration = timedelta(minutes=10)
        self.cached_data = None
        self.last_fetch_time = None
        
        # Validate configuration
        if not self.api_key:
            logging.warning("Weather API key not provided - weather display will be disabled")
        if not self.location:
            logging.warning("Weather location not provided - weather display will be disabled")
        
        logging.info(f"Weather service initialized for location: {self.location}")
    
    def get_weather(self) -> Optional[Dict]:
        """
        Get current weather data. Uses cached data if available and fresh.
        
        Returns:
            Dictionary with weather data or None if fetch fails.
        """
        # Return cached data if still valid
        if self._is_cache_valid():
            logging.debug("Returning cached weather data")
            return self.cached_data
        
        # Fetch fresh data
        try:
            weather_data = self._fetch_weather()
            if weather_data:
                self.cached_data = weather_data
                self.last_fetch_time = datetime.now()
                logging.info("Weather data fetched and cached successfully")
            return weather_data
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}", exc_info=True)
            # Return cached data even if stale, better than nothing
            return self.cached_data
    
    def _is_cache_valid(self) -> bool:
        """Check if cached weather data is still valid."""
        if self.cached_data is None or self.last_fetch_time is None:
            return False
        
        time_since_fetch = datetime.now() - self.last_fetch_time
        return time_since_fetch < self.cache_duration
    
    def _fetch_weather(self) -> Optional[Dict]:
        """
        Fetch weather data from OpenWeatherMap API.
        
        Returns:
            Formatted weather dictionary or None on failure.
        """
        if not self.api_key or not self.location:
            logging.warning("Weather API key or location not configured")
            return None
        
        try:
            # Build API request parameters
            params = {
                'q': self.location,
                'appid': self.api_key,
                'units': self.units,
                'lang': self.language
            }
            
            # Make API request with timeout
            logging.debug(f"Fetching weather for: {self.location}")
            response = requests.get(
                self.base_url,
                params=params,
                timeout=2  # 2 second timeout to avoid blocking the display
            )
            
            # Check response status
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract relevant information
            weather_info = {
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'condition': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'city': data['name'],
                'country': data['sys']['country']
            }
            
            # Add unit symbols
            if self.units == 'metric':
                weather_info['temp_unit'] = '°C'
                weather_info['wind_unit'] = 'm/s'
            elif self.units == 'imperial':
                weather_info['temp_unit'] = '°F'
                weather_info['wind_unit'] = 'mph'
            else:
                weather_info['temp_unit'] = 'K'
                weather_info['wind_unit'] = 'm/s'
            
            logging.info(f"Weather fetched: {weather_info['condition']}, {weather_info['temp']}{weather_info['temp_unit']}")
            return weather_info
            
        except requests.exceptions.Timeout:
            logging.error("Weather API request timed out")
            return None
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logging.error("Invalid weather API key")
            elif response.status_code == 404:
                logging.error(f"Location not found: {self.location}")
            else:
                logging.error(f"Weather API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Weather API request failed: {e}")
            return None
        except (KeyError, ValueError) as e:
            logging.error(f"Error parsing weather API response: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching weather: {e}", exc_info=True)
            return None
    
    def clear_cache(self):
        """Clear cached weather data."""
        self.cached_data = None
        self.last_fetch_time = None
        logging.info("Weather cache cleared")

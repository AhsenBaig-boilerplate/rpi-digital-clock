#!/usr/bin/env python3
"""
Simple web server to serve the clock HTML and provide weather API endpoint.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import logging
from pathlib import Path
import yaml
import os

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config.yaml"

class ClockRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for clock application."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/weather':
            self.send_weather_data()
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/clock.html'
            return super().do_GET()
        else:
            return super().do_GET()
    
    def send_weather_data(self):
        """Send weather data as JSON."""
        try:
            # Load config
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
            
            weather_config = config.get('weather', {})
            
            # Check if weather is enabled and has API key
            if not weather_config.get('enabled', False):
                self.send_json_response({})
                return
            
            api_key = os.environ.get('WEATHER_API_KEY') or weather_config.get('api_key', '')
            if not api_key:
                self.send_json_response({})
                return
            
            # Import weather service
            from weather import WeatherService
            weather_service = WeatherService(weather_config)
            weather_data = weather_service.get_weather()
            
            self.send_json_response(weather_data or {})
            
        except Exception as e:
            logging.error(f"Error fetching weather: {e}")
            self.send_json_response({})
    
    def send_json_response(self, data):
        """Send JSON response."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Log messages using logging module."""
        logging.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))


def start_server(port=8000):
    """Start the web server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ClockRequestHandler)
    logging.info(f"Web server starting on port {port}")
    logging.info(f"Open http://localhost:{port} to view the clock")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Web server stopped")
        httpd.shutdown()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_server()

#!/usr/bin/env python3
"""
Settings UI Server - Web interface for configuring the digital clock
Runs on port 8080 and provides a simple form to update device variables
"""
import os
import logging
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Balena Supervisor API configuration
SUPERVISOR_ADDRESS = os.environ.get('BALENA_SUPERVISOR_ADDRESS', 'http://127.0.0.1:48484')
SUPERVISOR_API_KEY = os.environ.get('BALENA_SUPERVISOR_API_KEY', '')
DEVICE_UUID = os.environ.get('BALENA_DEVICE_UUID', '')

# Configuration options with defaults
CONFIG_OPTIONS = {
    # Weather settings
    'WEATHER_LOCATION': {
        'label': 'Weather Location',
        'type': 'text',
        'default': 'New York',
        'help': 'City name for weather display (e.g., "New York" or "London,UK")'
    },
    'WEATHER_API_KEY': {
        'label': 'OpenWeather API Key',
        'type': 'text',
        'default': '',
        'help': 'Get free API key from openweathermap.org'
    },
    'WEATHER_ENABLED': {
        'label': 'Show Weather',
        'type': 'checkbox',
        'default': 'true',
        'help': 'Display weather information on clock'
    },
    
    # Display settings
    'TIMEZONE': {
        'label': 'Timezone',
        'type': 'select',
        'default': 'America/New_York',
        'options': [
            'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
            'America/Toronto', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
            'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney', 'UTC'
        ],
        'help': 'Local timezone for clock display'
    },
    'DISPLAY_COLOR': {
        'label': 'Time Color',
        'type': 'color',
        'default': '#FFFFFF',
        'help': 'Color for time display'
    },
    'TIME_FORMAT': {
        'label': 'Time Format',
        'type': 'select',
        'default': '12',
        'options': ['12', '24'],
        'help': '12-hour or 24-hour format'
    },
    'DISPLAY_DATE': {
        'label': 'Show Date',
        'type': 'checkbox',
        'default': 'true',
        'help': 'Display date below time'
    },
    
    # Burn-in prevention
    'SHIFT_ENABLED': {
        'label': 'Enable Burn-in Prevention',
        'type': 'checkbox',
        'default': 'true',
        'help': 'Shift display position periodically to prevent burn-in'
    },
    'SHIFT_INTERVAL': {
        'label': 'Shift Interval (seconds)',
        'type': 'number',
        'default': '600',
        'help': 'How often to shift the display'
    },
    'SHIFT_RANGE': {
        'label': 'Shift Range (pixels)',
        'type': 'number',
        'default': '20',
        'help': 'Maximum pixels to shift in any direction'
    },
    
    # Screensaver
    'SCREENSAVER_ENABLED': {
        'label': 'Enable Screensaver',
        'type': 'checkbox',
        'default': 'false',
        'help': 'Turn off display during specified hours'
    },
    'SCREENSAVER_START': {
        'label': 'Screensaver Start Time',
        'type': 'time',
        'default': '23:00',
        'help': 'Time to turn off display (24-hour format)'
    },
    'SCREENSAVER_END': {
        'label': 'Screensaver End Time',
        'type': 'time',
        'default': '07:00',
        'help': 'Time to turn on display (24-hour format)'
    },
}


def get_current_config():
    """Fetch current device environment variables from Balena Supervisor API"""
    try:
        headers = {
            'Authorization': f'Bearer {SUPERVISOR_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get device environment variables
        response = requests.get(
            f'{SUPERVISOR_ADDRESS}/v2/device/name',
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info("Successfully fetched device configuration")
            
            # For now, return defaults - in production would parse from API
            config = {}
            for key, spec in CONFIG_OPTIONS.items():
                config[key] = os.environ.get(key, spec['default'])
            return config
        else:
            logger.warning(f"Failed to fetch config: {response.status_code}")
            return {key: spec['default'] for key, spec in CONFIG_OPTIONS.items()}
            
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        return {key: spec['default'] for key, spec in CONFIG_OPTIONS.items()}


def update_device_variables(updates):
    """Update device environment variables via Balena Supervisor API"""
    try:
        headers = {
            'Authorization': f'Bearer {SUPERVISOR_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Update each variable
        for key, value in updates.items():
            # Convert checkbox values
            if CONFIG_OPTIONS[key]['type'] == 'checkbox':
                value = 'true' if value else 'false'
            
            # Set device environment variable
            payload = {key: str(value)}
            
            response = requests.patch(
                f'{SUPERVISOR_ADDRESS}/v1/device/host-config',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to update {key}: {response.status_code}")
                
        logger.info(f"Updated {len(updates)} device variables")
        return True
        
    except Exception as e:
        logger.error(f"Error updating variables: {e}")
        return False


@app.route('/')
def index():
    """Render the settings form"""
    current_config = get_current_config()
    return render_template('index.html', 
                          config=CONFIG_OPTIONS,
                          current=current_config)


@app.route('/api/config', methods=['GET'])
def get_config():
    """API endpoint to get current configuration"""
    return jsonify(get_current_config())


@app.route('/api/config', methods=['POST'])
def save_config():
    """API endpoint to save configuration"""
    try:
        updates = request.json
        
        # Validate all keys exist in CONFIG_OPTIONS
        for key in updates.keys():
            if key not in CONFIG_OPTIONS:
                return jsonify({'success': False, 'error': f'Invalid key: {key}'}), 400
        
        success = update_device_variables(updates)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Configuration updated. Clock will restart shortly.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update device variables'
            }), 500
            
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting settings UI server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

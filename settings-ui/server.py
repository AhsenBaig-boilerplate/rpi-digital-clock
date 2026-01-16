#!/usr/bin/env python3
"""
Settings UI Server - Web interface for configuring the digital clock
Runs on port 8080 and provides a simple form to update device variables
"""
import os
import logging
import secrets
import requests
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)  # Enable CORS for all routes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Balena Supervisor API configuration
SUPERVISOR_ADDRESS = os.environ.get('BALENA_SUPERVISOR_ADDRESS', 'http://127.0.0.1:48484')
SUPERVISOR_API_KEY = os.environ.get('BALENA_SUPERVISOR_API_KEY', '')
DEVICE_UUID = os.environ.get('BALENA_DEVICE_UUID', '')

# Security configuration
SETTINGS_PASSWORD = os.environ.get('SETTINGS_PASSWORD', '')  # If empty, no authentication required
AUTH_ENABLED = bool(SETTINGS_PASSWORD)

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
        'default': True,
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
        'default': True,
        'help': 'Display date below time'
    },
    
    # Burn-in prevention
    'SHIFT_ENABLED': {
        'label': 'Enable Burn-in Prevention',
        'type': 'checkbox',
        'default': True,
        'help': 'Shift display position periodically to prevent burn-in'
    },
    'SHIFT_INTERVAL': {
        'label': 'Shift Interval (seconds)',
        'type': 'number',
        'default': 600,
        'help': 'How often to shift the display'
    },
    'SHIFT_RANGE': {
        'label': 'Shift Range (pixels)',
        'type': 'number',
        'default': 20,
        'help': 'Maximum pixels to shift in any direction'
    },
    
    # Screensaver
    'SCREENSAVER_ENABLED': {
        'label': 'Enable Screensaver',
        'type': 'checkbox',
        'default': False,
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


def login_required(f):
    """Decorator to require authentication if password is set"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if AUTH_ENABLED and not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_config():
    """Load current configuration from file or environment variables"""
    try:
        import yaml
        config_file = '/data/settings.yaml'
        
        # Try to load from file first
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {config_file}")
            
            # Merge with defaults
            config = {}
            for key, spec in CONFIG_OPTIONS.items():
                config[key] = file_config.get(key, os.environ.get(key, spec['default']))
            return config
        else:
            logger.info("No saved config file, using environment variables and defaults")
            config = {}
            for key, spec in CONFIG_OPTIONS.items():
                config[key] = os.environ.get(key, spec['default'])
            return config
            
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {key: spec['default'] for key, spec in CONFIG_OPTIONS.items()}


def update_device_variables(updates):
    """Save configuration to shared config file"""
    try:
        import yaml
        config_file = '/data/settings.yaml'
        
        # Prepare configuration
        config = {}
        for key, value in updates.items():
            # Convert checkbox values
            if CONFIG_OPTIONS[key]['type'] == 'checkbox':
                value = value if isinstance(value, bool) else (value == 'true' or value == True)
            config[key] = value
        
        # Write to shared volume
        os.makedirs('/data', exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        
        logger.info(f"Successfully saved {len(updates)} settings to {config_file}")
        
        # Trigger clock restart to apply new settings
        # Try multiple approaches to restart the clock service
        restart_success = False
        
        try:
            if SUPERVISOR_ADDRESS and SUPERVISOR_API_KEY:
                # Method 1: Try with BALENA_APP_ID if available and valid
                app_id = os.environ.get("BALENA_APP_ID", "")
                # Ignore placeholder values like "${BALENA_APP_ID}"
                if app_id and not str(app_id).startswith("${"):
                    url = f"{SUPERVISOR_ADDRESS}/v2/applications/{app_id}/restart-service?apikey={SUPERVISOR_API_KEY}"
                    response = requests.post(
                        url,
                        json={'serviceName': 'clock'},
                        timeout=30
                    )
                    if response.status_code == 200:
                        logger.info("Triggered clock service restart via app ID")
                        restart_success = True
                    else:
                        logger.warning(f"Restart via app ID failed: {response.status_code} - {response.text}")
                
                # Method 2: Fallback to restart via v1/restart endpoint (restarts all services in app)
                if not restart_success:
                    # Get the current app state to find the correct app ID
                    state_url = f"{SUPERVISOR_ADDRESS}/v2/applications/state?apikey={SUPERVISOR_API_KEY}"
                    state_response = requests.get(state_url, timeout=10)
                    if state_response.status_code == 200:
                        apps = state_response.json()
                        # Find the first app (should be only one in single-app fleets)
                        for app_name, app_data in apps.items():
                            found_app_id = app_data.get('appId')
                            if found_app_id:
                                restart_url = f"{SUPERVISOR_ADDRESS}/v2/applications/{found_app_id}/restart-service?apikey={SUPERVISOR_API_KEY}"
                                restart_response = requests.post(
                                    restart_url,
                                    json={'serviceName': 'clock'},
                                    timeout=30
                                )
                                if restart_response.status_code == 200:
                                    logger.info(f"Triggered clock service restart via detected app ID: {found_app_id}")
                                    restart_success = True
                                    break
                
                if not restart_success:
                    logger.warning("Could not restart clock service automatically. Please restart manually or changes will apply on next reboot.")
            else:
                logger.warning("Missing supervisor env; skip restart")
        except Exception as e:
            logger.warning(f"Could not restart clock service: {e}")

        
        return True
        
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if not AUTH_ENABLED:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == SETTINGS_PASSWORD:
            session['authenticated'] = True
            logger.info("Successful login attempt")
            return redirect(url_for('index'))
        else:
            logger.warning("Failed login attempt")
            return render_template('login.html', error='Invalid password')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Render the settings form"""
    current_config = get_current_config()
    return render_template('index.html', 
                          config=CONFIG_OPTIONS,
                          current=current_config,
                          auth_enabled=AUTH_ENABLED)


@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """API endpoint to get current configuration"""
    return jsonify(get_current_config())


@app.route('/api/config', methods=['POST'])
@login_required
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


@app.route('/api/restart-clock', methods=['POST'])
@login_required
def restart_clock():
    """Manual endpoint to restart the clock service"""
    try:
        if not SUPERVISOR_ADDRESS or not SUPERVISOR_API_KEY:
            return jsonify({
                'success': False,
                'error': 'Supervisor API not available'
            }), 500
        
        # Try BALENA_APP_ID first if valid
        app_id_env = os.environ.get('BALENA_APP_ID', '')
        if app_id_env and not str(app_id_env).startswith('${'):
            restart_url = f"{SUPERVISOR_ADDRESS}/v2/applications/{app_id_env}/restart-service?apikey={SUPERVISOR_API_KEY}"
            restart_response = requests.post(
                restart_url,
                json={'serviceName': 'clock'},
                timeout=30
            )
            if restart_response.status_code == 200:
                logger.info(f"Manually triggered clock restart for app {app_id_env}")
                return jsonify({'success': True, 'message': 'Clock service restarted successfully'})
        
        # Fallback: Get current app state to determine app ID
        state_url = f"{SUPERVISOR_ADDRESS}/v2/applications/state?apikey={SUPERVISOR_API_KEY}"
        state_response = requests.get(state_url, timeout=10)
        
        if state_response.status_code == 200:
            apps = state_response.json()
            for app_name, app_data in apps.items():
                app_id = app_data.get('appId')
                if app_id:
                    restart_url = f"{SUPERVISOR_ADDRESS}/v2/applications/{app_id}/restart-service?apikey={SUPERVISOR_API_KEY}"
                    restart_response = requests.post(
                        restart_url,
                        json={'serviceName': 'clock'},
                        timeout=30
                    )
                    if restart_response.status_code == 200:
                        logger.info(f"Manually triggered clock restart for app {app_id}")
                        return jsonify({
                            'success': True,
                            'message': 'Clock service restarted successfully'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'Restart failed: {restart_response.text}'
                        }), 500
        
        return jsonify({
            'success': False,
            'error': 'Could not determine app ID'
        }), 500
        
    except Exception as e:
        logger.error(f"Error restarting clock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    if AUTH_ENABLED:
        logger.info(f"Starting settings UI server on port {port} (password protection enabled)")
    else:
        logger.warning(f"Starting settings UI server on port {port} (NO PASSWORD PROTECTION - set SETTINGS_PASSWORD to enable)")
    app.run(host='0.0.0.0', port=port, debug=False)

#!/usr/bin/env python3
"""
Web UI for configuring Raspberry Pi Digital Clock settings.
Simple Flask app for editing config.yaml and environment variables.
"""

import os
import yaml
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Clock Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        label { display: block; margin: 10px 0 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #45a049; }
        .info { background: #e3f2fd; padding: 10px; border-left: 4px solid #2196F3; margin: 10px 0; }
        .success { background: #c8e6c9; padding: 10px; border-left: 4px solid #4CAF50; margin: 10px 0; }
        .env-var { background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>🕐 Digital Clock Settings</h1>
    
    {% if message %}
    <div class="success">{{ message }}</div>
    {% endif %}
    
    <div class="info">
        <strong>Build Info:</strong> {{ build_info }}
    </div>
    
    <form method="POST" action="/save">
        <div class="section">
            <h2>Time Settings</h2>
            <label>Time Format</label>
            <select name="time_format_12h">
                <option value="true" {% if config.time.format_12h %}selected{% endif %}>12-hour (AM/PM)</option>
                <option value="false" {% if not config.time.format_12h %}selected{% endif %}>24-hour</option>
            </select>
            
            <label>Show Seconds</label>
            <select name="display_show_seconds">
                <option value="true" {% if config.display.show_seconds %}selected{% endif %}>Yes</option>
                <option value="false" {% if not config.display.show_seconds %}selected{% endif %}>No</option>
            </select>
        </div>
        
        <div class="section">
            <h2>Display Settings</h2>
            <label>Display Color (hex)</label>
            <input type="text" name="display_color" value="{{ config.display.color }}" placeholder="#00FF00">
            
            <label>Time Font Size</label>
            <input type="number" name="time_font_size" value="{{ config.display.time_font_size }}" min="50" max="500">
            
            <label>Date Font Size</label>
            <input type="number" name="date_font_size" value="{{ config.display.date_font_size }}" min="20" max="200">
            
            <label>Brightness</label>
            <select name="display_brightness">
                <option value="1.0" {% if config.display.brightness == 1.0 %}selected{% endif %}>100%</option>
                <option value="0.8" {% if config.display.brightness == 0.8 %}selected{% endif %}>80%</option>
                <option value="0.6" {% if config.display.brightness == 0.6 %}selected{% endif %}>60%</option>
                <option value="0.4" {% if config.display.brightness == 0.4 %}selected{% endif %}>40%</option>
            </select>
            
            <label>Night Dimming</label>
            <select name="display_dim_at_night">
                <option value="true" {% if config.display.dim_at_night %}selected{% endif %}>Enabled</option>
                <option value="false" {% if not config.display.dim_at_night %}selected{% endif %}>Disabled</option>
            </select>
        </div>
        
        <div class="section">
            <h2>Screensaver</h2>
            <label>Screensaver Enabled</label>
            <select name="screensaver_enabled">
                <option value="true" {% if config.display.screensaver_enabled %}selected{% endif %}>Yes</option>
                <option value="false" {% if not config.display.screensaver_enabled %}selected{% endif %}>No</option>
            </select>
            
            <label>Start Hour (24h format)</label>
            <input type="number" name="screensaver_start_hour" value="{{ config.display.screensaver_start_hour }}" min="0" max="23">
            
            <label>End Hour (24h format)</label>
            <input type="number" name="screensaver_end_hour" value="{{ config.display.screensaver_end_hour }}" min="0" max="23">
        </div>
        
        <div class="section">
            <h2>Weather (via Environment Variables)</h2>
            <div class="env-var">
                <strong>Note:</strong> Weather settings must be configured via Balena Dashboard > Device Variables:
                <ul>
                    <li><code>WEATHER_ENABLED</code> - true/false</li>
                    <li><code>WEATHER_API_KEY</code> - OpenWeatherMap API key</li>
                    <li><code>WEATHER_LOCATION</code> - City name (e.g., "New York,US")</li>
                    <li><code>WEATHER_UNITS</code> - metric/imperial/kelvin</li>
                </ul>
                Current: {{ env_vars }}
            </div>
        </div>
        
        <button type="submit">💾 Save Settings & Restart Clock</button>
    </form>
    
    <div class="section" style="margin-top: 30px;">
        <h2>Current Configuration (config.yaml)</h2>
        <pre style="background: #f8f8f8; padding: 15px; overflow-x: auto; border-radius: 4px;">{{ config_raw }}</pre>
    </div>
</body>
</html>
"""

def load_config():
    """Load current configuration."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        return {"error": str(e)}

def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

def get_build_info():
    """Get build information."""
    try:
        from utils import load_build_info, format_build_info
        info = load_build_info()
        return format_build_info(info)
    except:
        return "Unknown"

def get_env_vars():
    """Get relevant environment variables."""
    return {
        'WEATHER_ENABLED': os.environ.get('WEATHER_ENABLED', 'not set'),
        'WEATHER_API_KEY': '***' if os.environ.get('WEATHER_API_KEY') else 'not set',
        'WEATHER_LOCATION': os.environ.get('WEATHER_LOCATION', 'not set'),
        'TIMEZONE': os.environ.get('TIMEZONE', 'not set'),
    }

@app.route('/')
def index():
    """Main settings page."""
    config = load_config()
    config_raw = yaml.safe_dump(config, default_flow_style=False, sort_keys=False)
    build_info = get_build_info()
    env_vars = get_env_vars()
    message = request.args.get('message', '')
    
    return render_template_string(
        HTML_TEMPLATE,
        config=config,
        config_raw=config_raw,
        build_info=build_info,
        env_vars=env_vars,
        message=message
    )

@app.route('/save', methods=['POST'])
def save():
    """Save configuration and restart clock."""
    config = load_config()
    
    # Update config from form
    config['time']['format_12h'] = request.form.get('time_format_12h') == 'true'
    config['display']['show_seconds'] = request.form.get('display_show_seconds') == 'true'
    config['display']['color'] = request.form.get('display_color', '#00FF00')
    config['display']['time_font_size'] = int(request.form.get('time_font_size', 280))
    config['display']['date_font_size'] = int(request.form.get('date_font_size', 90))
    config['display']['brightness'] = float(request.form.get('display_brightness', 1.0))
    config['display']['dim_at_night'] = request.form.get('display_dim_at_night') == 'true'
    config['display']['screensaver_enabled'] = request.form.get('screensaver_enabled') == 'true'
    config['display']['screensaver_start_hour'] = int(request.form.get('screensaver_start_hour', 2))
    config['display']['screensaver_end_hour'] = int(request.form.get('screensaver_end_hour', 5))
    
    # Save config
    save_config(config)
    
    # Trigger clock restart by touching a restart flag file
    Path('/tmp/restart_clock').touch()
    
    return redirect(url_for('index', message='Settings saved! Clock will restart in a few seconds.'))

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """API endpoint to get current config."""
    return jsonify(load_config())

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """API endpoint to restart clock."""
    Path('/tmp/restart_clock').touch()
    return jsonify({"status": "restart triggered"})

if __name__ == '__main__':
    print("Starting Clock Settings Web UI on port 8080...")
    print(f"Build: {get_build_info()}")
    app.run(host='0.0.0.0', port=8080, debug=False)

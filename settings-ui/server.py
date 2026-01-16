#!/usr/bin/env python3
"""
Settings UI Server - Web interface for configuring the digital clock
Runs on port 8080 and provides a simple form to update device variables
"""
import os
import logging
import threading
import time
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

# Balena Cloud API configuration (for persistent device variables)
BALENA_API_URL = 'https://api.balena-cloud.com'
# Standard Balena convention is API_TOKEN, but also check BALENA_API_KEY for backwards compatibility
API_TOKEN = os.environ.get('API_TOKEN', os.environ.get('BALENA_API_KEY', ''))

# Security configuration
SETTINGS_PASSWORD = os.environ.get('SETTINGS_PASSWORD', '')  # If empty, no authentication required
AUTH_ENABLED = bool(SETTINGS_PASSWORD)

# Auto-prefer WiFi behavior
def _env_bool(name, default):
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).lower() in ('1', 'true', 'yes', 'on')

WIFI_AUTO_PREFER_ENABLED = _env_bool('WIFI_AUTO_PREFER_ENABLED', True)
WIFI_AUTO_PREFER_INTERVAL_SECONDS = int(os.environ.get('WIFI_AUTO_PREFER_INTERVAL_SECONDS', '120'))
WIFI_AUTO_PREFER_MIN_SIGNAL = int(os.environ.get('WIFI_AUTO_PREFER_MIN_SIGNAL', '40'))

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

# WiFi configuration (separate from CONFIG_OPTIONS as it uses device variables)
WIFI_CONFIG = {
    'WIFI_SSID': {
        'label': 'Primary WiFi Network',
        'type': 'text',
        'help': 'WiFi network name (SSID)'
    },
    'WIFI_PSK': {
        'label': 'Primary WiFi Password',
        'type': 'password',
        'help': 'WiFi network password'
    },
    'WIFI_SSID_1': {
        'label': 'Backup WiFi Network 1',
        'type': 'text',
        'help': 'Fallback WiFi network (optional)'
    },
    'WIFI_PSK_1': {
        'label': 'Backup WiFi Password 1',
        'type': 'password',
        'help': 'Backup network password'
    },
    'WIFI_SSID_2': {
        'label': 'Backup WiFi Network 2',
        'type': 'text',
        'help': 'Second fallback WiFi network (optional)'
    },
    'WIFI_PSK_2': {
        'label': 'Backup WiFi Password 2',
        'type': 'password',
        'help': 'Second backup network password'
    },
}


def scan_wifi_networks():
    """Scan for available WiFi networks and return list of SSIDs with signal strength.
    Returns list of dicts with 'ssid', 'signal', 'security' keys.
    """
    try:
        import shutil

        # Ensure nmcli is available
        nmcli_path = shutil.which('nmcli')
        if not nmcli_path:
            logger.warning("nmcli not found in container. Install network-manager and ensure DBus is mounted.")
            logger.warning("Hint: This service requires io.balena.features.dbus and /run/dbus mounted.")
            return []

        # Ensure DBus socket is reachable
        dbus_addr = os.environ.get('DBUS_SYSTEM_BUS_ADDRESS', '')
        dbus_sock = '/host/run/dbus/system_bus_socket'
        if not dbus_addr:
            logger.warning("DBUS_SYSTEM_BUS_ADDRESS not set; cannot query host NetworkManager.")
        if not os.path.exists(dbus_sock):
            logger.warning(f"Host DBus socket not found at {dbus_sock}; WiFi scan may fail.")

        # Use nmcli to scan for WiFi networks
        # Format: SSID:SIGNAL:SECURITY
        cmd = "nmcli -t -f ssid,signal,security dev wifi list"
        result = os.popen(cmd).read().strip()

        if not result:
            logger.warning("WiFi scan returned no results")
            return []

        networks = []
        seen_ssids = set()

        for line in result.split('\n'):
            if not line or line.startswith('--'):
                continue

            parts = line.split(':', 2)
            if len(parts) >= 2:
                ssid = parts[0].strip()
                signal = parts[1].strip() if len(parts) > 1 else '0'
                security = parts[2].strip() if len(parts) > 2 else ''

                # Skip empty SSIDs and duplicates (take strongest signal)
                if ssid and ssid not in seen_ssids:
                    seen_ssids.add(ssid)
                    networks.append({
                        'ssid': ssid,
                        'signal': int(signal) if signal.isdigit() else 0,
                        'security': security
                    })

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: x['signal'], reverse=True)

        logger.info(f"📡 Found {len(networks)} WiFi network(s) in scan")
        for n in networks:
            sec = 'secure' if n.get('security') else 'open'
            logger.info(f"  • {n.get('ssid')}  ({n.get('signal')}%, {sec})")
        return networks

    except Exception as e:
        logger.error(f"Error scanning WiFi networks: {e}")
        return []


def get_wifi_device():
    """Return the first WiFi device name (e.g., wlan0) or None"""
    try:
        output = os.popen('nmcli -t -f DEVICE,TYPE,STATE dev').read().strip()
        for line in output.split('\n'):
            parts = line.split(':')
            if len(parts) >= 3:
                device, dev_type, state = parts[0], parts[1], parts[2]
                if dev_type == 'wifi':
                    return device
        return None
    except Exception:
        return None


def list_nm_wifi_connections():
    """Return a mapping of SSID -> connection NAME for existing WiFi connections."""
    try:
        conns_output = os.popen("nmcli -t -f NAME,TYPE connection show").read().strip()
        ssid_to_name = {}
        for line in conns_output.split('\n'):
            if not line:
                continue
            name, ctype = (line.split(':', 1) + [''])[:2]
            if ctype != 'wifi':
                continue
            ssid = os.popen(f"nmcli -g 802-11-wireless.ssid connection show \"{name}\"").read().strip()
            if ssid:
                ssid_to_name[ssid] = name
        return ssid_to_name
    except Exception as e:
        logger.warning(f"Failed to list NM wifi connections: {e}")
        return {}


def nm_get_wifi_connections_by_name():
    """Return a mapping of connection NAME -> SSID for WiFi connections."""
    try:
        output = os.popen("nmcli -t -f NAME,TYPE connection show").read().strip()
        name_to_ssid = {}
        for line in output.split('\n'):
            if not line:
                continue
            name, ctype = (line.split(':', 1) + [''])[:2]
            if ctype != 'wifi':
                continue
            ssid = os.popen(f"nmcli -g 802-11-wireless.ssid connection show \"{name}\"").read().strip()
            if ssid:
                name_to_ssid[name] = ssid
        return name_to_ssid
    except Exception as e:
        logger.warning(f"Failed to query NM connections: {e}")
        return {}


def nm_add_or_update_wifi_connection(con_name: str, ssid: str, psk: str, priority: int, ifname: str | None = None):
    """Create or update a WiFi connection in NetworkManager with given name/ssid/psk/priority."""
    try:
        ifname = ifname or (get_wifi_device() or 'wlan0')
        existing = os.popen(f"nmcli -t -f NAME connection show | grep -Fx \"{con_name}\"").read().strip()
        if not existing:
            # Create new connection
            cmd_add = f"nmcli connection add type wifi ifname {ifname} con-name \"{con_name}\" ssid \"{ssid}\""
            add_out = os.popen(cmd_add).read().strip()
            logger.debug(f"nmcli add: {add_out}")
        # Ensure security, ssid, autoconnect and priority
        cmds = [
            f"nmcli connection modify \"{con_name}\" 802-11-wireless.ssid \"{ssid}\"",
            f"nmcli connection modify \"{con_name}\" 802-11-wireless.security 'wpa-psk'",
            f"nmcli connection modify \"{con_name}\" wifi-sec.key-mgmt wpa-psk",
            f"nmcli connection modify \"{con_name}\" wifi-sec.psk \"{psk}\"",
            f"nmcli connection modify \"{con_name}\" connection.autoconnect yes",
            f"nmcli connection modify \"{con_name}\" connection.autoconnect-priority {priority}",
        ]
        for cmd in cmds:
            _ = os.popen(cmd).read().strip()
        # Save and reload connections
        _ = os.popen('nmcli connection reload').read().strip()
        return True
    except Exception as e:
        logger.warning(f"Failed to add/update NM connection {con_name}: {e}")
        return False


def nm_delete_wifi_connection(con_name: str):
    try:
        _ = os.popen(f"nmcli connection delete \"{con_name}\"").read().strip()
        return True
    except Exception as e:
        logger.warning(f"Failed to delete NM connection {con_name}: {e}")
        return False


def switch_to_best_available(min_signal: int | None = None):
    """Switch to the highest-priority configured SSID that is currently visible.

    Priorities: primary=100, backup1=90, backup2=80. If already connected
    to the best available, does nothing.
    """
    try:
        import shutil

        nmcli_path = shutil.which('nmcli')
        if not nmcli_path:
            return False, 'nmcli not available'

        device = get_wifi_device()
        if not device:
            return False, 'No WiFi device found'

        # Reload connections so NetworkManager picks up any new/changed files
        reload_result = os.popen('nmcli connection reload').read().strip()
        logger.debug(f'nmcli connection reload: {reload_result}')

        current = get_current_wifi_connection() or ''
        scan = scan_wifi_networks()
        if min_signal is not None:
            scan = [n for n in scan if isinstance(n.get('signal'), int) and n['signal'] >= min_signal]
        visible = {n['ssid'] for n in scan}

        cfg = get_wifi_config()
        # Map SSID -> (priority, filename) so we can call nmcli with the right connection name
        candidates = []
        if cfg.get('WIFI_SSID'):
            candidates.append((cfg['WIFI_SSID'], 100, 'balena-wifi-primary'))
        if cfg.get('WIFI_SSID_1'):
            candidates.append((cfg['WIFI_SSID_1'], 90, 'balena-wifi-backup1'))
        if cfg.get('WIFI_SSID_2'):
            candidates.append((cfg['WIFI_SSID_2'], 80, 'balena-wifi-backup2'))

        # Pick highest priority among those visible
        best = None
        best_filename = None
        for ssid, prio, filename in sorted(candidates, key=lambda x: x[1], reverse=True):
            if ssid and ssid in visible:
                best = ssid
                best_filename = filename
                break

        if not best:
            return False, 'No configured SSIDs are currently visible'

        if current and current == best:
            return True, f'Already connected to best SSID: {best}'

        # Try to bring up an existing NM connection matching the SSID
        ssid_to_name = list_nm_wifi_connections()
        if best in ssid_to_name:
            conn_name = ssid_to_name[best]
            cmd = f'nmcli -w 15 connection up "{conn_name}" ifname {device}'
            logger.info(f'Attempting switch to best SSID: {best} (connection: {conn_name}) on {device}')
            result = os.popen(cmd).read().strip()
        else:
            # Fallback: ask NM to connect by SSID (will use saved secrets if available)
            cmd = f'nmcli -w 20 device wifi connect "{best}" ifname {device}'
            logger.info(f'Attempting switch via direct connect to SSID: {best} on {device}')
            result = os.popen(cmd).read().strip()

        # Re-check current connection
        now = get_current_wifi_connection() or ''
        if now == best:
            logger.info(f'✓ Switched to SSID: {best}')
            return True, f'Switched to SSID: {best}'
        else:
            logger.warning(f'Could not switch to {best}. nmcli output: {result}')
            return False, f'Failed to switch. Output: {result}'

    except Exception as e:
        logger.error(f'Error switching WiFi: {e}')
        return False, str(e)


def _auto_prefer_loop():
    """Background worker to periodically prefer highest-priority visible SSID."""
    if not WIFI_AUTO_PREFER_ENABLED:
        logger.info('Auto-prefer WiFi is disabled via env')
        return
    logger.info(f'Auto-prefer WiFi enabled: interval={WIFI_AUTO_PREFER_INTERVAL_SECONDS}s, min_signal={WIFI_AUTO_PREFER_MIN_SIGNAL}')
    while True:
        try:
            success, msg = switch_to_best_available(min_signal=WIFI_AUTO_PREFER_MIN_SIGNAL)
            # Log only on successful switch or meaningful message
            if success:
                logger.info(f'Auto-prefer: {msg}')
            else:
                # reduce noise; only log when a switch was attempted and failed meaningfully
                if msg.startswith('Failed'):
                    logger.warning(f'Auto-prefer: {msg}')
        except Exception as e:
            logger.warning(f'Auto-prefer loop error: {e}')
        time.sleep(WIFI_AUTO_PREFER_INTERVAL_SECONDS)


def get_current_wifi_connection():
    """Get the currently connected WiFi network SSID"""
    try:
        # Use nmcli to get current WiFi connection
        result = os.popen('nmcli -t -f active,ssid dev wifi | grep "^yes"').read().strip()
        if result:
            # Format is "yes:SSID"
            parts = result.split(':', 1)
            if len(parts) == 2:
                ssid = parts[1]
                logger.info(f"📶 Currently connected to WiFi: {ssid}")
                return ssid
        
        logger.info("📶 No WiFi connection detected (or using Ethernet)")
        return None
    except Exception as e:
        logger.warning(f"Could not determine current WiFi: {e}")
        return None


def login_required(f):
    """Decorator to require authentication if password is set"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if AUTH_ENABLED and not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_wifi_config():
    """Get current WiFi configuration by querying NetworkManager connections.

    We look for our managed connections by name and return their SSIDs.
    Passwords are masked (***).
    """
    try:
        wifi_config = {key: '' for key in WIFI_CONFIG.keys()}
        name_to_ssid = nm_get_wifi_connections_by_name()
        mapping = [
            ('balena-wifi-primary', 'WIFI_SSID', 'WIFI_PSK'),
            ('balena-wifi-backup1', 'WIFI_SSID_1', 'WIFI_PSK_1'),
            ('balena-wifi-backup2', 'WIFI_SSID_2', 'WIFI_PSK_2'),
        ]
        for con_name, ssid_key, psk_key in mapping:
            if con_name in name_to_ssid:
                wifi_config[ssid_key] = name_to_ssid[con_name]
                wifi_config[psk_key] = '***'
                logger.info(f"Found WiFi config: {con_name} (SSID: {wifi_config[ssid_key]})")
        return wifi_config
    except Exception as e:
        logger.error(f"Error loading WiFi config: {e}")
        return {key: '' for key in WIFI_CONFIG.keys()}


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
            
            # Priority: File > Env Vars > Defaults
            config = {}
            for key, spec in CONFIG_OPTIONS.items():
                if key in file_config:
                    # Use file value (highest priority)
                    value = file_config[key]
                elif key in os.environ:
                    # Use env var as fallback
                    value = os.environ[key]
                else:
                    # Use default
                    value = spec['default']
                
                # Type conversion for checkboxes
                if spec['type'] == 'checkbox':
                    if isinstance(value, bool):
                        config[key] = value
                    elif isinstance(value, str):
                        config[key] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        config[key] = bool(value)
                else:
                    config[key] = value
                    
            return config
        else:
            logger.info("No saved config file, using environment variables and defaults")
            config = {}
            for key, spec in CONFIG_OPTIONS.items():
                value = os.environ.get(key, spec['default'])
                
                # Type conversion for checkboxes
                if spec['type'] == 'checkbox':
                    if isinstance(value, bool):
                        config[key] = value
                    elif isinstance(value, str):
                        config[key] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        config[key] = bool(value)
                else:
                    config[key] = value
                    
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


def create_networkmanager_wifi_file(ssid, password, priority, filename):
    """Create a NetworkManager connection file for WiFi.
    
    Args:
        ssid: WiFi network name
        password: WiFi password (PSK)
        priority: Connection priority (higher = preferred)
        filename: File name to create in /mnt/boot/system-connections/
    
    Returns:
        True if successful, False otherwise
    """
    try:
        boot_connections = '/mnt/boot/system-connections'
        if not os.path.exists(boot_connections):
            try:
                os.makedirs(boot_connections, exist_ok=True)
                logger.info(f"Created boot connections directory: {boot_connections}")
            except Exception as e:
                logger.error(f"Could not create boot connections directory {boot_connections}: {e}")
                return False
        
        filepath = os.path.join(boot_connections, filename)
        
        # NetworkManager connection file format
        # See: https://docs.balena.io/reference/OS/network/#wifi-setup
        config_content = f"""[connection]
id={ssid}
type=wifi
autoconnect=true
autoconnect-priority={priority}

[wifi]
mode=infrastructure
ssid={ssid}

[wifi-security]
auth-alg=open
key-mgmt=wpa-psk
psk={password}

[ipv4]
method=auto

[ipv6]
addr-gen-mode=stable-privacy
method=auto
"""
        
        with open(filepath, 'w') as f:
            f.write(config_content)
        
        # Set proper permissions (NetworkManager requires 600)
        os.chmod(filepath, 0o600)
        
        logger.info(f"✓ Created WiFi config: {filename} (SSID: {ssid}, Priority: {priority})")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create WiFi config {filename}: {e}")
        return False


def remove_old_wifi_configs():
    """Remove all WiFi config files from boot partition to ensure clean slate."""
    logger.info("Step 1: Removing old WiFi configuration files...")
    try:
        boot_connections = '/mnt/boot/system-connections'
        if not os.path.exists(boot_connections):
            try:
                os.makedirs(boot_connections, exist_ok=True)
                logger.info(f"Created boot connections directory: {boot_connections}")
                # Nothing to remove since directory was missing
                return True
            except Exception as e:
                logger.error(f"Could not create boot connections directory {boot_connections}: {e}")
                return False
        
        removed = []
        # Remove all files (we'll recreate the ones we need)
        for filename in os.listdir(boot_connections):
            if filename.endswith('.ignore'):
                continue  # Keep sample files
            
            filepath = os.path.join(boot_connections, filename)
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    removed.append(filename)
                    logger.info(f"Removed old WiFi config: {filename}")
                except Exception as e:
                    logger.warning(f"Could not remove {filename}: {e}")
        
        if removed:
            logger.info(f"✓ Removed {len(removed)} old WiFi config file(s)")
            return True
        else:
            logger.info("No old WiFi config files found")
            return False
            
    except Exception as e:
        logger.error(f"Error removing old WiFi configs: {e}")
        return False


def update_wifi_config(wifi_settings):
    """Update WiFi configuration using NetworkManager via nmcli (no reboot required)."""
    logger.info("")
    logger.info("Starting WiFi Configuration Update Process")
    logger.info("-" * 60)
    try:
        logger.info("")
        logger.info("Step 1: Applying WiFi connections in NetworkManager (non-destructive)...")
        created_or_updated = []
        unchanged = []

        current_cfg = get_wifi_config()
        device = get_wifi_device() or 'wlan0'

        def _apply(slot, prio, con_name):
            ssid_key = f"WIFI_SSID{'' if slot == 0 else f'_{slot}'}"
            psk_key = f"WIFI_PSK{'' if slot == 0 else f'_{slot}'}"
            ssid = wifi_settings.get(ssid_key, '').strip()
            psk = wifi_settings.get(psk_key, '').strip()
            if not ssid:
                return
            if psk == '***':
                # If SSID unchanged and password masked, leave as-is
                if ssid == (current_cfg.get(ssid_key) or ''):
                    unchanged.append(f"{ssid} ({'primary' if slot==0 else f'backup {slot}'})")
                    return
                else:
                    raise ValueError(f"Password required when changing SSID for slot {slot}")
            ok = nm_add_or_update_wifi_connection(con_name, ssid, psk, prio, ifname=device)
            if ok:
                created_or_updated.append(f"{ssid} ({'primary' if slot==0 else f'backup {slot}'})")
            else:
                raise RuntimeError(f"Failed to apply connection for {ssid}")

        # Apply in priority order
        _apply(0, 100, 'balena-wifi-primary')
        _apply(1, 90, 'balena-wifi-backup1')
        _apply(2, 80, 'balena-wifi-backup2')

        if not created_or_updated and not unchanged:
            logger.warning("No valid WiFi updates provided (empty fields or masked only)")
            return False, "No WiFi changes detected"

        logger.info("")
        logger.info("✓ WiFi Configuration Summary:")
        logger.info(f"  - Applied {len(created_or_updated)} network configuration(s)")
        for i, config in enumerate(created_or_updated, 1):
            logger.info(f"  {i}. {config}")
        if unchanged:
            logger.info(f"  - Left {len(unchanged)} configuration(s) unchanged")
            for name in unchanged:
                logger.info(f"    • {name}")

        # Prefer highest priority available now
        success, msg = switch_to_best_available()
        if success:
            return True, f"WiFi settings applied. {msg}"
        else:
            return True, "WiFi settings applied. Switching deferred (no preferred SSID visible)."

    except Exception as e:
        logger.error(f"Error updating WiFi config: {e}")
        return False, str(e)


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
    wifi_config = get_wifi_config()
    current_wifi_ssid = get_current_wifi_connection()
    return render_template('index.html', 
                          config=CONFIG_OPTIONS,
                          current=current_config,
                          wifi_config=WIFI_CONFIG,
                          wifi_current=wifi_config,
                          auth_enabled=AUTH_ENABLED,
                          current_wifi_ssid=current_wifi_ssid)


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


@app.route('/api/wifi/scan', methods=['GET'])
@login_required
def scan_wifi():
    """API endpoint to scan and return available WiFi networks"""
    try:
        networks = scan_wifi_networks()
        return jsonify({
            'success': True,
            'networks': networks,
            'count': len(networks)
        })
    except Exception as e:
        logger.error(f"Error in WiFi scan endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'networks': []
        }), 500


@app.route('/api/wifi', methods=['GET'])
@login_required
def get_wifi():
    """API endpoint to get current WiFi configuration"""
    return jsonify(get_wifi_config())


@app.route('/api/wifi/current', methods=['GET'])
@login_required
def get_wifi_current():
    """API endpoint to get current connected WiFi SSID"""
    try:
        ssid = get_current_wifi_connection()
        source = 'unknown'
        priority = None
        device = None
        signal = None
        security = None

        # Determine device
        device = get_wifi_device()

        # Determine if SSID matches our configured networks
        cfg = get_wifi_config() if ssid else {}
        if ssid:
            if ssid == cfg.get('WIFI_SSID'):
                source = 'primary'
                priority = 100
            elif ssid == cfg.get('WIFI_SSID_1'):
                source = 'backup1'
                priority = 90
            elif ssid == cfg.get('WIFI_SSID_2'):
                source = 'backup2'
                priority = 80
            else:
                source = 'unconfigured'

        # Try to enrich with current signal/security from latest scan
        scan = scan_wifi_networks()
        for n in scan:
            if n.get('ssid') == ssid:
                signal = n.get('signal')
                security = n.get('security')
                break

        return jsonify({
            'success': True,
            'ssid': ssid,
            'source': source,
            'priority': priority,
            'device': device,
            'signal': signal,
            'security': security
        })
    except Exception as e:
        logger.error(f"Error getting current WiFi: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wifi/switch-best', methods=['POST'])
@login_required
def api_switch_best_wifi():
    """API endpoint to switch to the highest-priority available SSID"""
    try:
        success, message = switch_to_best_available()
        status = 200 if success else 400
        return jsonify({'success': success, 'message': message}), status
    except Exception as e:
        logger.error(f"Error switching WiFi: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wifi', methods=['POST'])
@login_required
def save_wifi():
    """API endpoint to save WiFi configuration and reboot device"""
    logger.info("="*60)
    logger.info("WiFi Configuration Update Request Received")
    logger.info("="*60)
    try:
        wifi_settings = request.json
        logger.info(f"WiFi settings payload: {wifi_settings.keys() if wifi_settings else 'None'}")
        
        # Validate keys
        for key in wifi_settings.keys():
            if key not in WIFI_CONFIG:
                return jsonify({'success': False, 'error': f'Invalid key: {key}'}), 400
        
        success, message = update_wifi_config(wifi_settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    except Exception as e:
        logger.error(f"Error saving WiFi config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wifi/clear', methods=['POST'])
@login_required
def clear_wifi_configs():
    """Explicitly clear our WiFi NetworkManager connections."""
    logger.info("="*60)
    logger.info("WiFi Configuration CLEAR Request Received")
    logger.info("="*60)
    try:
        ok_primary = nm_delete_wifi_connection('balena-wifi-primary')
        ok_b1 = nm_delete_wifi_connection('balena-wifi-backup1')
        ok_b2 = nm_delete_wifi_connection('balena-wifi-backup2')
        if ok_primary or ok_b1 or ok_b2:
            return jsonify({'success': True, 'message': 'Cleared WiFi connections from NetworkManager'}), 200
        return jsonify({'success': True, 'message': 'No WiFi connections to clear'}), 200
    except Exception as e:
        logger.error(f"Error clearing WiFi configs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/reset', methods=['POST'])
@login_required
def factory_reset():
    """Factory reset: clear clock settings and WiFi configs, optional reboot."""
    logger.info("="*70)
    logger.info("FACTORY RESET REQUEST RECEIVED")
    logger.info("="*70)
    try:
        # Parse options
        payload = request.json or {}
        do_reboot = bool(payload.get('reboot', True))

        # Clear clock settings
        config_file = '/data/settings.yaml'
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
                logger.info(f"✓ Cleared clock settings file: {config_file}")
            except Exception as e:
                logger.warning(f"Could not remove {config_file}: {e}")
        else:
            logger.info("Clock settings file not present; nothing to clear")

        # Clear WiFi configs (NetworkManager connections)
        any_cleared = False
        for name in ('balena-wifi-primary', 'balena-wifi-backup1', 'balena-wifi-backup2'):
            if nm_delete_wifi_connection(name):
                any_cleared = True
        if any_cleared:
            logger.info("✓ Cleared WiFi connections from NetworkManager")
        else:
            logger.info("No WiFi connections found to clear in NetworkManager")

        # Optional reboot
        if do_reboot and SUPERVISOR_ADDRESS and SUPERVISOR_API_KEY:
            reboot_url = f"{SUPERVISOR_ADDRESS}/v1/reboot?apikey={SUPERVISOR_API_KEY}"
            reboot_response = requests.post(reboot_url, timeout=10)
            if reboot_response.status_code == 202:
                logger.info("✓ Device reboot triggered after factory reset")
                return jsonify({'success': True, 'message': 'Factory reset complete. Device rebooting...'}), 200
            else:
                logger.warning(f"Factory reset complete but reboot failed: {reboot_response.status_code}")
                return jsonify({'success': True, 'message': 'Factory reset complete. Please reboot manually.'}), 200

        return jsonify({'success': True, 'message': 'Factory reset complete.'}), 200

    except Exception as e:
        logger.error(f"Error during factory reset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
    
    logger.info("="*70)
    logger.info("SETTINGS-UI STARTING")
    logger.info("="*70)
    
    if AUTH_ENABLED:
        logger.info(f"✓ Password protection ENABLED (port {port})")
    else:
        logger.warning(f"⚠ Password protection DISABLED (port {port}) - set SETTINGS_PASSWORD to enable")
    
    # Log device UUID for reference
    if DEVICE_UUID:
        logger.info(f"✓ Device UUID: {DEVICE_UUID}")
    else:
        logger.warning("⚠ DEVICE_UUID not set")
    
    # Check and log current WiFi connection
    logger.info("")
    logger.info("Current Network Status:")
    logger.info("-" * 70)
    current_wifi = get_current_wifi_connection()
    
    # Log available WiFi configurations
    wifi_config = get_wifi_config()
    configured_networks = [v for k, v in wifi_config.items() if v and 'SSID' in k and v != '***']
    if configured_networks:
        logger.info(f"✓ Found {len(configured_networks)} configured WiFi network(s):")
        for ssid in configured_networks:
            status = "← CONNECTED" if current_wifi and ssid in current_wifi else ""
            logger.info(f"  • {ssid} {status}")
    else:
        logger.info("⚠ No WiFi networks configured (NetworkManager connections)")
    
    logger.info("="*70)
    logger.info("")
    # Start auto-prefer thread
    try:
        t = threading.Thread(target=_auto_prefer_loop, daemon=True)
        t.start()
    except Exception as e:
        logger.warning(f'Could not start auto-prefer thread: {e}')

    app.run(host='0.0.0.0', port=port, debug=False)

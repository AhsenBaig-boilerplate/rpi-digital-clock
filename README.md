# Raspberry Pi Digital Clock for balena.io

A production-ready digital clock display for Raspberry Pi Zero (1st gen) with weather information, designed for HDMI TV displays. Built with Python and PIL with RGB565 optimization for direct framebuffer rendering, deployed via balena.io with comprehensive screen burn-in prevention features.

Note: The container base uses Debian Bookworm with Python 3.11, optimized for Raspberry Pi Zero W (ARMv6). Status icons are drawn as vector graphics for minimal overhead.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Balena](https://img.shields.io/badge/balena-compatible-green.svg)

## ✨ Features

### Core Functionality
- **Large Digital Clock Display** - Easy-to-read time display optimized for TV viewing
- **12/24 Hour Format** - Configurable time format with optional AM/PM display
- **Live Weather Integration** - Real-time weather data from OpenWeatherMap API
- **Date Display** - Customizable date format
- **NTP Time Sync** - Automatic time synchronization on startup
- **Hardware RTC Support** - DS3231 RTC module for accurate time when offline (optional)

### Screen Burn-in Prevention 🛡️
- **Scheduled Screensaver** - Blanks screen during configured hours (e.g., 2:00–5:00)
- **Pixel Shift** - Subtle position changes to prevent burn-in; can be disabled during viewing hours (e.g., 12:00–14:00)
- **Night Dimming** - Automatic brightness reduction during night hours (e.g., 22:00–06:00)
- **Flexible Windows** - All time windows support midnight wraparound

### Production Ready
- **Error Handling** - Comprehensive error handling and recovery
- **Logging** - Detailed logging for debugging and monitoring
- **Config Validation** - Automatic validation of configuration settings
- **Docker Containerized** - Easy deployment via balena.io
- **Environment Variables** - Override config with environment variables
- **Graceful Shutdown** - Proper cleanup on exit

## 🛠️ Runtime & Emoji Icons

- **Python Runtime**: Container uses Debian Bookworm with Python 3.11, optimized for Raspberry Pi Zero W (ARMv6)
- **PIL (Pillow)**: System `python3-pil` with RGB565 optimization
- **Emoji Icons**: PNG sprites loaded from `app/assets/emojis/` for status bar (no font rendering overhead)
  - Provide PNGs (24x24 recommended) named: `wifi.png`, `ethernet.png`, `network_error.png`, `globe.png`, `sync.png`, `clock.png`
  - Set `USE_EMOJI=true` to enable icons; falls back to ASCII if files missing

### Runtime Summary (example startup logs)

On startup, the application logs a concise runtime summary and environment scopes to aid troubleshooting:

```
2026-01-12 21:45:05 - root - INFO - Runtime summary: PIL RGB565 | Icons: Vector | RTC: Disabled
2026-01-12 21:45:05 - root - INFO - Status icons: network, sync_ok, sync_old, error, settings
2026-01-12 21:45:05 - root - INFO - Device metadata (balena environment):
2026-01-12 21:45:05 - root - INFO -   [Device] BALENA_DEVICE_NAME=LivingRoomClock
2026-01-12 21:45:05 - root - INFO -   [Device] BALENA_DEVICE_TYPE=raspberry-pi
2026-01-12 21:45:05 - root - INFO -   [Device] BALENA_DEVICE_UUID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
2026-01-12 21:45:05 - root - INFO -   [Device] BALENA_SERVICE_NAME=clock
2026-01-12 21:45:05 - root - INFO - Environment variables (masked where sensitive):
2026-01-12 21:45:05 - root - INFO -   [Service(clock)] WEATHER_API_KEY=****
2026-01-12 21:45:05 - root - INFO -   [Service(clock)] TIMEZONE=America/Los_Angeles
```

This helps confirm the runtime (PIL with RGB565 optimization), vector icon rendering, RTC status, device context, and scoped variables.

## 📋 Prerequisites

- Raspberry Pi Zero (1st generation)
- MicroSD card (8GB or larger recommended)
- TV with HDMI input
- Mini HDMI to HDMI cable
- Power supply for Raspberry Pi
- [balena.io](https://www.balena.io/) account (free tier available)
- [OpenWeatherMap](https://openweathermap.org/api) API key (free tier available)
- **Optional**: DS3231 RTC module for offline timekeeping ([Amazon](https://www.amazon.com/dp/B08X4H3NBR))

## 🚀 Quick Start

You can one-click-deploy this project to balena using the button below:

[![Deploy with balena](https://www.balena.io/deploy.svg)](https://dashboard.balena-cloud.com/deploy?repoUrl=https://github.com/AhsenBaig-boilerplate/rpi-digital-clock)

### Environment Variables Setup (Global vs Service)

After deployment, you **must** configure variables in your balena dashboard. The application supports both direct variable names and `BALENA_` prefixed versions.

#### How to Add Variables in balena Dashboard:

1. **Fleet-wide Variables (Global)** — applies to all devices:
   - Navigate to: Dashboard → Your Fleet → Variables tab
   - Click "Add variable"
   - Select "All services" or "clock" service
   - Enter variable name and value
   - Click "Add"

2. **Device-specific Variables** — for individual devices:
   - Navigate to: Dashboard → Your Device → Device Variables tab
   - Click "Add variable"
   - Enter variable name and value
   - Click "Add"

#### Required Variables:

| Variable Name | Default | Description |
|--------------|---------|-------------|
| `WEATHER_API_KEY` | `your_api_key_here` | OpenWeatherMap API key ([Get free key](https://openweathermap.org/api)) |
| `WEATHER_LOCATION` | `New York,US` | City name and country code |
| `TIMEZONE` | `America/New_York` | System timezone - **DST automatically handled!** ([List of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |

#### Optional Configuration Variables:

| Variable Name | Default | Description |
|--------------|---------|-------------|
| `WEATHER_UNITS` | `metric` | Temperature units (`metric` or `imperial`) |
| `WEATHER_ENABLED` | `true` | Enable/disable weather display |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DISPLAY_ORIENTATION` | `landscape` | Display orientation (`landscape` or `portrait`) |
| `DISPLAY_COLOR` | `#00FF00` | Clock color in hex format |
| `FONT_FAMILY` | `Helvetica` | Font family name |
| `TIME_FONT_SIZE` | `280` | Time display font size (scaled per resolution) |
| `TIME_FORMAT_12H` | `true` | Use 12-hour format (true/false) |
| `SHOW_SECONDS` | `true` | Show seconds in display |
| `DATE_FORMAT` | `%A, %B %d, %Y` | Python strftime format |
| `SCREENSAVER_ENABLED` | `true` | Enable scheduled screensaver |
| `SCREENSAVER_START_HOUR` | `2` | Screensaver start hour (0–23) |
| `SCREENSAVER_END_HOUR` | `5` | Screensaver end hour (0–23) |
| `PIXEL_SHIFT_ENABLED` | `true` | Enable pixel shifting |
| `PIXEL_SHIFT_INTERVAL_SECONDS` | `30` | Interval between shifts |
| `PIXEL_SHIFT_DISABLE_START_HOUR` | `12` | Disable pixel shift start hour |
| `PIXEL_SHIFT_DISABLE_END_HOUR` | `14` | Disable pixel shift end hour |
| `DIM_AT_NIGHT` | `true` | Dim display at night |
| `NIGHT_BRIGHTNESS` | `0.3` | Night brightness (0.0–1.0) |
| `NIGHT_START_HOUR` | `22` | Night start hour |
| `NIGHT_END_HOUR` | `6` | Night end hour |

#### WiFi Configuration

**Method 1: Dynamic WiFi Change (No Reboot Required)**

Use balenaOS's NetworkManager via D-Bus to change WiFi without rebooting:

```bash
# SSH into device
balena ssh <device-uuid>

# Switch to host OS
balena ssh <device-uuid> host

# Connect to new WiFi network
nmcli device wifi connect "NetworkName" password "password123"

# Or scan and connect
nmcli device wifi list
nmcli device wifi connect "NetworkName" password "password123"
```

**Method 2: WiFi Connect (Captive Portal)**

For user-friendly WiFi setup, use [Balena WiFi Connect](https://github.com/balena-io/wifi-connect) - creates a captive portal when WiFi is unavailable. Add to your fleet:

```yaml
# In docker-compose.yml, add wifi-connect service
wifi-connect:
  image: bh.cr/balenalabs/wifi-connect-arm
  network_mode: host
  labels:
    io.balena.features.dbus: '1'
    io.balena.features.firmware: '1'
  cap_add:
    - NET_ADMIN
  environment:
    DBUS_SYSTEM_BUS_ADDRESS: "unix:path=/host/run/dbus/system_bus_socket"
```

**Method 3: Device Variables (Requires Reboot)**

Set WiFi via device variables (device will reboot to apply):

| Variable Name | Description | Example |
|--------------|-------------|---------|
| `BALENA_HOST_CONFIG_wifi_ssid` | WiFi network name | `MyHomeNetwork` |
| `BALENA_HOST_CONFIG_wifi_ssid_1` | Second network (fallback) | `OfficeNetwork` |
| `BALENA_HOST_CONFIG_wifi_psk` | WiFi password | `mypassword123` |
| `BALENA_HOST_CONFIG_wifi_psk_1` | Second network password | `officepass456` |

**To change WiFi network (Method 3):**
1. Go to Device Variables in Balena dashboard
2. Add/update `BALENA_HOST_CONFIG_wifi_ssid` with your network name
3. Add/update `BALENA_HOST_CONFIG_wifi_psk` with your password
4. Device will reboot and connect to new network

**Multiple WiFi Networks (Automatic Fallback):**

Configure multiple networks by adding `_1`, `_2`, etc. suffixes:

```
BALENA_HOST_CONFIG_wifi_ssid = "HomeNetwork"
BALENA_HOST_CONFIG_wifi_psk = "homepass"
BALENA_HOST_CONFIG_wifi_ssid_1 = "OfficeNetwork"
BALENA_HOST_CONFIG_wifi_psk_1 = "officepass"
BALENA_HOST_CONFIG_wifi_ssid_2 = "MobileHotspot"
BALENA_HOST_CONFIG_wifi_psk_2 = "mobilepass"
```

Device will automatically try networks in order and connect to the first available.

💡 **Recommendation**: Use Method 1 (nmcli) for quick changes, Method 2 (WiFi Connect) for user-friendly setup, Method 3 for pre-configured deployments.

💡 **Multi-Device Setup:** Use Fleet Variables for common settings (like API key) and Device Variables for location-specific settings (like `WEATHER_LOCATION`).

💡 **Variable Prefix:** You can use either `WEATHER_API_KEY` or `BALENA_WEATHER_API_KEY` - both work!

**Where to set variables:**
- **Fleet Variables**: Dashboard → Your Application → Variables (applies to all devices)
- **Device Variables**: Dashboard → Your Device → Variables (device-specific)
- **Service Variables**: Select "clock" service when adding variable

### Manual Deployment

Alternatively, you can manually deploy by following these steps:

#### 1. Setup balena Account

1. Create a free account at [balena.io](https://www.balena.io/)
2. Install balena CLI: https://github.com/balena-io/balena-cli/blob/master/INSTALL.md
3. Login to balena CLI:
   ```bash
   balena login
   ```

#### 2. Create balena Application

1. Go to [balena Dashboard](https://dashboard.balena-cloud.com/)
2. Click "Create application"
3. Choose:
   - **Name**: `rpi-digital-clock` (or your preferred name)
   - **Device type**: Raspberry Pi (v1 / Zero / Zero W)
   - **Application type**: Starter
4. Click "Create new application"

##### 3. Add Your Device

1. In your application dashboard, click "Add device"
2. Select WiFi configuration (if using WiFi)
3. Download the balenaOS image
4. Flash the image to your SD card using [balenaEtcher](https://www.balena.io/etcher/)
5. Insert SD card into Raspberry Pi and power it on
6. Wait for device to appear in your balena dashboard (may take a few minutes)

#### 4. Configure Weather API

1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. In balena dashboard, go to your application
3. Navigate to "Environment variables" or "Device variables"
4. Add the following variables:
   - `WEATHER_API_KEY`: Your OpenWeatherMap API key
   - `WEATHER_LOCATION`: Your city (e.g., "New York,US", "London,GB")

#### 5. Deploy Application

Clone and push this repository to your balena application:

```bash
# Clone this repository
git clone https://github.com/AhsenBaig-boilerplate/rpi-digital-clock.git
cd rpi-digital-clock

# Add balena remote (get this from your balena dashboard)
balena push <YOUR_APP_NAME>
```

Or using git:

```bash
git remote add balena <YOUR_USERNAME>@git.balena-cloud.com:<YOUR_USERNAME>/<YOUR_APP_NAME>.git
git push balena main
```

#### 6. Wait for Build and Deployment

- balena will build the Docker container (takes 10-20 minutes on first build)
- The application will automatically deploy to your Raspberry Pi
- Check logs in balena dashboard to monitor progress

#### 7. Connect to TV

1. Connect Raspberry Pi to TV via HDMI
2. Power on Raspberry Pi
3. Clock should display automatically on TV

## ⚙️ Configuration

The clock can be configured in two ways:

### 🌐 Web Interface (Recommended)

Access the settings UI from any device on the same network:

1. **Find your device IP**: Check your balena dashboard or router
2. **Open settings page**: Navigate to `http://<device-ip>:8080`
3. **Login (if enabled)**: Enter password if `SETTINGS_PASSWORD` is set
4. **Configure settings**: Use the web form to adjust:
   - Weather location and API key
   - Timezone and time format
   - Display colors and date format
   - Burn-in prevention settings
   - Screensaver schedule
   - **WiFi networks** - Configure primary and backup WiFi networks (triggers device reboot)

Clock display settings take effect after the service restarts (automatically triggered). WiFi changes require a device reboot to apply.

#### 🔒 Security (IMPORTANT!)

**By default, the settings page has NO password protection!** Anyone on your WiFi network can access it.

**To enable password protection:**

1. Go to your balena dashboard → Device Variables
2. Add variable: `SETTINGS_PASSWORD` = `your_secure_password`
3. The settings page will now require login

**For persistent WiFi configuration:**

To make WiFi changes persist across reboots and prevent dashboard variables from overwriting them:

1. Go to [Balena Dashboard → Preferences → Access Tokens](https://dashboard.balena-cloud.com/preferences/access-tokens)
2. Create a new API token (read/write permissions)
3. Add Fleet or Device Variable: `BALENA_API_KEY` = `your_api_token`
4. WiFi changes via settings-UI will now be stored persistently in Balena Cloud

Without `BALENA_API_KEY`, WiFi changes are temporary and will be overwritten if you have `BALENA_HOST_CONFIG_wifi_*` variables set in the dashboard.

**Recommendations:**
- ✅ **Set a password** if your WiFi has guests or untrusted users
- ✅ Use a strong password (at least 12 characters)
- ✅ **Set BALENA_API_KEY** for persistent WiFi configuration
- ⚠️ Without a password, anyone on WiFi can change settings
- 💡 Password is optional for private home networks

**Alternative security options:**
- Disable the settings-ui service entirely in [docker-compose.yml](docker-compose.yml)
- Use firewall rules to restrict access to port 8080
- Only enable when needed, then remove the service

### 📝 Configuration File

Alternatively, edit `app/config.yaml` directly:

### Time Settings

```yaml
time:
  format_12h: true                  # true for 12-hour, false for 24-hour
  timezone: "America/New_York"      # Timezone (DST automatically handled!)
  ntp_sync: true                    # Sync time with NTP on startup
  ntp_server: "pool.ntp.org"        # NTP server to use
  rtc_enabled: true                 # Enable DS3231 RTC module support
```

**Timezone & Daylight Saving Time**: When you set a timezone like `America/New_York` or `Europe/London`, the system **automatically handles DST transitions**! No additional configuration needed. The clock will automatically "spring forward" and "fall back" according to your timezone's DST rules.

**RTC Module Setup**: If you have a DS3231 RTC module, see [RTC_SETUP.md](RTC_SETUP.md) for detailed hardware installation and configuration instructions.

### Display Settings

```yaml
display:
  font_family: "Helvetica"      # Font family
  time_font_size: 120           # Time font size in points
  date_font_size: 40            # Date font size in points
  weather_font_size: 30         # Weather font size in points
  color: "#00FF00"              # Display color (hex format)
  show_seconds: true            # Show seconds in time
  date_format: "%A, %B %d, %Y"  # Python strftime format
```

### Screen Burn-in Prevention

```yaml
display:
  # Screensaver
  screensaver_enabled: true
  screensaver_delay_minutes: 60
  
  # Pixel shift
  pixel_shift_enabled: true
  pixel_shift_interval_seconds: 30
  
  # Night dimming
  dim_at_night: true
  night_brightness: 0.3         # 0.0 to 1.0
  night_start_hour: 22          # 24-hour format
  night_end_hour: 6
```

### Weather Settings

```yaml
weather:
  enabled: true
  api_key: ""                   # Or use WEATHER_API_KEY env var
  location: "New York,US"       # Or use WEATHER_LOCATION env var
  units: "metric"               # metric, imperial, or kelvin
  language: "en"                # ISO 639-1 language code
```

### Environment Variables

You can override config.yaml settings using environment variables in balena dashboard. These can be set at three levels:

1. **Fleet Variables** - Apply to all devices in your fleet
2. **Device Variables** - Apply to a specific device only
3. **Service Variables** - Apply to the clock service specifically

To set variables in balena dashboard:
- Go to your application or device page
- Navigate to "Variables" section
- Add or modify the variables below

**Available Variables:**

#### Core Settings

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `WEATHER_API_KEY` | OpenWeatherMap API key | `abc123def456` | _(required)_ |
| `WEATHER_LOCATION` | City for weather | `London,GB` | `New York,US` |
| `WEATHER_UNITS` | Temperature units | `metric`, `imperial`, `kelvin` | `metric` |
| `WEATHER_ENABLED` | Enable/disable weather | `true`, `false` | `true` |
| `TIMEZONE` | System timezone | `America/New_York`, `Europe/London`, `Asia/Tokyo` | `America/New_York` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG`, `INFO`, `WARNING` | `INFO` |

#### Display Settings

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `DISPLAY_ORIENTATION` | Display orientation | `landscape`, `portrait` | `landscape` |
| `DISPLAY_COLOR` | Clock text color (hex) | `#00FF00`, `#FFFFFF` | `#00FF00` |
| `FONT_FAMILY` | Font family name | `Helvetica`, `Arial` | `Helvetica` |
| `TIME_FONT_SIZE` | Time font size (points) | `100`, `150` | `120` |
| `TIME_FORMAT_12H` | Use 12-hour format | `true`, `false` | `true` |
| `SHOW_SECONDS` | Show seconds in time | `true`, `false` | `true` |
| `DATE_FORMAT` | Date format string | `%B %d, %Y` | `%A, %B %d, %Y` |

#### Screen Burn-in Prevention

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `SCREENSAVER_ENABLED` | Enable screensaver | `true`, `false` | `true` |
| `SCREENSAVER_DELAY_MINUTES` | Minutes until screensaver | `30`, `120` | `60` |
| `PIXEL_SHIFT_ENABLED` | Enable pixel shifting | `true`, `false` | `true` |
| `DIM_AT_NIGHT` | Dim display at night | `true`, `false` | `true` |
| `NIGHT_BRIGHTNESS` | Night brightness (0.0-1.0) | `0.5`, `0.2` | `0.3` |

**Using Device Variables:**

Device variables are useful when you have multiple clocks showing different locations or configurations. You can set these via the web interface (recommended) or through the balena dashboard.

**Via Web Interface (Port 8080):**

Navigate to `http://<device-ip>:8080` to access the settings UI where you can configure all options through a user-friendly form.

**Via Balena Dashboard:**

```
Device 1 (Kitchen - New York):
  WEATHER_LOCATION: "New York,US"
  DISPLAY_COLOR: "#00FF00"
  WEATHER_UNITS: "imperial"

Device 2 (Office - London):
  WEATHER_LOCATION: "London,GB"
  DISPLAY_COLOR: "#00FFFF"
  WEATHER_UNITS: "metric"
  TIME_FORMAT: "24"

Device 3 (Bedroom):
  WEATHER_LOCATION: "Tokyo,JP"
  SCREENSAVER_ENABLED: "true"
  SCREENSAVER_START: "23:00"
  SCREENSAVER_END: "07:00"
```

See [balena documentation](https://docs.balena.io/learn/manage/variables/#device-variables) for more details on variable types and precedence.

## 📱 WiFi Configuration

### Method 1: WiFi Connect (Captive Portal)

When the device can't connect to configured WiFi networks, it automatically starts a WiFi Connect captive portal:

1. **Look for WiFi network**: `DigitalClock Setup` (password: `clocksetup`)
2. **Connect to it**: Your phone/computer will show a captive portal
3. **Select your WiFi**: Choose your home network and enter password
4. **Done**: Device will connect and clock starts

The captive portal exits after 5 minutes of inactivity or successful connection.

### Method 2: Dynamic Configuration via NetworkManager

For devices already connected to WiFi, you can change networks remotely:

**Using balena CLI:**
```bash
balena ssh <UUID>

# Switch to a new WiFi network
nmcli device wifi connect "YourNewSSID" password "YourPassword"

# List available networks
nmcli device wifi list
```

**Configure multiple networks with fallback:**

Set device variables (via dashboard):
```
BALENA_HOST_CONFIG_wifi_ssid: "HomeNetwork"
BALENA_HOST_CONFIG_wifi_psk: "homepassword"
BALENA_HOST_CONFIG_wifi_ssid_1: "OfficeNetwork"
BALENA_HOST_CONFIG_wifi_psk_1: "officepassword"
BALENA_HOST_CONFIG_wifi_ssid_2: "MobileHotspot"
BALENA_HOST_CONFIG_wifi_psk_2: "hotspotpassword"
```

**Configure via Settings UI (Port 8080):**

The web interface provides a dedicated WiFi configuration section where you can set:
- Primary WiFi network (SSID and password)
- Up to 2 backup networks for automatic fallback
- Changes trigger an automatic device reboot

Navigate to `http://<device-ip>:8080` → WiFi Configuration section → Enter network details → Click "Save WiFi & Reboot Device"

The device will automatically try each network in order until one connects.

**⚠️ Important for Persistence:**
- **Without `BALENA_API_KEY`**: WiFi changes are temporary and will be overwritten by dashboard variables on next sync
- **With `BALENA_API_KEY`**: WiFi changes are stored in Balena Cloud and persist across reboots
- Set `BALENA_API_KEY` (Fleet or Device Variable) with your [Balena API token](https://dashboard.balena-cloud.com/preferences/access-tokens) for persistent configuration

**Recommendations:**
- **Method 1 (WiFi Connect)** - Best for initial setup or when you can't access the device remotely
- **Method 2 (nmcli)** - Best for quick remote WiFi changes without rebooting
- **Web UI (port 8080)** - Best for persistent WiFi configuration with automatic fallback (requires BALENA_API_KEY)

## 🎨 Customization

### Color Schemes

Popular color options for `display.color`:

- Green: `#00FF00` (default, easy on eyes)
- White: `#FFFFFF` (bright, modern)
- Cyan: `#00FFFF` (cool, futuristic)
- Amber: `#FFBF00` (warm, classic)
- Red: `#FF0000` (bold, attention-grabbing)

### Date Formats

Common `date_format` patterns:

- `"%A, %B %d, %Y"` → Monday, January 06, 2026
- `"%m/%d/%Y"` → 01/06/2026
- `"%d-%m-%Y"` → 06-01-2026
- `"%B %d, %Y"` → January 06, 2026
- `"%a, %b %d"` → Mon, Jan 06

See [Python strftime reference](https://strftime.org/) for more options.

### Timezone & Daylight Saving Time

**How DST Works:**

The clock automatically handles Daylight Saving Time when you set a standard timezone name. No additional configuration needed!

**Examples of timezones with DST:**
- `America/New_York` - Switches between EST and EDT
- `America/Chicago` - Switches between CST and CDT
- `America/Los_Angeles` - Switches between PST and PDT
- `Europe/London` - Switches between GMT and BST
- `Europe/Paris` - Switches between CET and CEST

**Examples of timezones WITHOUT DST:**
- `America/Phoenix` - Always MST (Arizona doesn't observe DST)
- `America/Honolulu` - Always HST (Hawaii doesn't observe DST)
- `Asia/Tokyo` - Always JST (Japan doesn't observe DST)
- `Asia/Shanghai` - Always CST (China doesn't observe DST)

**Checking DST Status:**

When the clock starts, it will log whether DST is currently active:
```
System timezone set to: America/New_York
Daylight Saving Time is active (EDT, UTC-4.0)
```

or during standard time:
```
System timezone set to: America/New_York
Standard time is active (EST, UTC-5.0)
DST will be automatically observed when applicable (switches to EDT)
```

**Finding Your Timezone:**

Visit [Wikipedia's List of TZ Database Time Zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) to find your exact timezone name.

### Display Orientation

**Landscape vs Portrait Mode:**

The clock supports both landscape (horizontal) and portrait (vertical) display orientations.

**Landscape Mode (Default):**
- Standard horizontal TV/monitor orientation
- Display is in normal horizontal position
- Set: `DISPLAY_ORIENTATION=landscape`

**Portrait Mode:**
- Vertical display orientation (90° clockwise rotation)
- Useful for portrait-mounted displays or tablets
- Set: `DISPLAY_ORIENTATION=portrait`

**How to Configure:**

1. **Via balena Dashboard** (recommended):
   - Go to Device Variables
   - Add variable: `DISPLAY_ORIENTATION`
   - Set value to: `landscape` or `portrait`

2. **Via config.yaml**:
   ```yaml
   display:
     orientation: "portrait"  # or "landscape"
   ```

**Note:** The display rotation is applied using xrandr at startup. If the rotation doesn't work, your display/driver may not support hardware rotation.

## 🔧 Troubleshooting

### High CPU at Startup (Normal Behavior)

**Expected:** CPU spikes to 60-80% for ~1 second during startup, then drops to 30-40%

**Why this happens:**
- The app pre-renders **14 time character sprites** at startup (0-9, colon, space, AM/PM)
- **Date sprites are lazy-loaded** on first use to minimize startup time
- Each sprite requires RGB565 conversion for fast framebuffer rendering
- This is a **one-time initialization** that eliminates per-frame rendering overhead

**What you'll see in logs:**
```
Pre-rendering time sprite cache (lazy-loading date sprites)...
Generating 14 time sprites at startup...
✓ Time sprite cache complete: 14 sprites in 500ms
  Date sprites will be lazy-loaded on first use
```

**Performance:**
- Startup: ~1 second at 60-80% CPU (was 3-5 seconds at 99%)
- First date render: +50-100ms to load date sprites as needed
- Steady-state: 170ms renders at 30-40% CPU

**If CPU stays high (>50%) after 10 seconds:** Check logs for errors or set `LOG_LEVEL=DEBUG`

### Clock Not Displaying

1. Check balena dashboard logs for errors
2. Verify HDMI cable is connected properly
3. Ensure TV is on correct HDMI input
4. Check that device is online in balena dashboard

### Weather Not Showing

1. Verify `WEATHER_API_KEY` is set correctly
2. Check `WEATHER_LOCATION` format (City,CountryCode)
3. Ensure device has internet connection
4. Check logs for API error messages
5. Verify OpenWeatherMap API key is active (can take a few hours after signup)

### Time Not Syncing

1. Check internet connection
2. Verify NTP server is accessible
3. Check logs for NTP sync errors
4. Try setting `ntp_server: "time.google.com"` in config.yaml
5. If using RTC module, see [RTC_SETUP.md](RTC_SETUP.md) for troubleshooting

### Display Issues

1. Set `LOG_LEVEL=DEBUG` in environment variables
2. Check balena logs for errors
3. Verify Raspberry Pi has enough power (use quality power supply)
4. Try reducing font sizes if display is cut off

## 📊 Monitoring

View real-time logs in balena dashboard:

1. Go to your device in balena dashboard
2. Click on the device
3. View logs in the terminal section
4. Filter by service or search for specific errors

## 🔄 Updates

To update the application:

```bash
# Make changes to code
git add .
git commit -m "Update: description of changes"

# Push to balena
balena push <YOUR_APP_NAME>
# or
git push balena main
```

balena will automatically rebuild and deploy the updated application.

## � Build Tracking & Versioning

This project includes comprehensive build tracking to help you identify exactly which version is running on your device.

### CI/CD Integration

Every deployment via GitHub Actions records:
- **GitHub commit SHA** and branch/tag
- **Balena release ID** and commit
- **Build timestamp** and workflow run URL
- **Version string** (git tag or `tag+revN`)

### Required GitHub Secrets

To enable automated deployment, configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description |
|------------|-------------|
| `BALENA_TOKEN` | Balena API token ([Generate here](https://dashboard.balena-cloud.com/preferences/access-tokens)) |
| `BALENA_FLEET` | Your fleet slug (e.g., `yourorg/rpi-digital-clock`) |

### How Build Info Works

1. **Embedded in Image**: `app/build-info.json` is generated during CI and baked into the container
2. **Startup Logs**: Build info is logged when the app starts
3. **Status Bar**: Version and short commit SHA displayed in bottom-left corner
4. **Balena Release Tags**: GitHub metadata automatically tagged on each release
5. **CI Artifacts**: `build-metadata.json` uploaded for every workflow run

### Viewing Build Info

**In logs** (on device or via balena dashboard):
```
2026-01-08 10:15:30 - root - INFO - Build info: commit=abc1234 ref=main version=0.0.0+rev22 built=2026-01-08T10:10:00Z
```

**On device** (via SSH or local balena CLI):
```bash
# Print build info JSON
balena ssh <device-uuid> clock
python3 /app/build_info.py

# Or enable on every startup
balena env add PRINT_BUILD_INFO true --service clock
```

**On screen**: Status bar shows `v0.0.0+rev22 abc1234` in the bottom-right corner

**In CI artifacts**: Download `build-metadata.json` from GitHub Actions run page

**In Balena dashboard**: Release page shows tags: `git.sha`, `git.ref`, `github.run_id`, `github.run_url`

### Example build-info.json

```json
{
  "git_sha": "731a341e6416f617652879a9bbf79bd75211363f",
  "git_ref": "main",
  "repo": "yourusername/rpi-digital-clock",
  "workflow": "Deploy to balena",
  "run_id": "12345678",
  "run_url": "https://github.com/yourusername/rpi-digital-clock/actions/runs/12345678",
  "git_version": "0.0.0+rev22",
  "build_time": "2026-01-08T10:10:00Z",
  "balena_release_id": "2468101",
  "balena_release_commit": "def5678...",
  "balena_release_version": "0.0.0+rev22"
}
```

### Troubleshooting with Build Info

When reporting issues or comparing behaviors between deployments:

1. **Check the status bar** for version/commit displayed on screen
2. **Read startup logs** for full build info line
3. **Download CI artifact** to see exact GitHub ↔ Balena mapping
4. **Compare release tags** in Balena dashboard to identify regressions

This ensures you can always trace a running instance back to the exact source code commit and deployment run.

## � Versioning & Releases

This project follows [Semantic Versioning 2.0.0](https://semver.org/) with Git tags.

### Quick Release

Use normal git workflow:

```bash
# 1. Make your changes and update CHANGELOG.md
git add -A
git commit -m "v1.4.122: Fix description"

# 2. Tag the release
git tag v1.4.122

# 3. Push everything (main + tags)
git push origin main --tags
```

**That's it!** The workflow only triggers on tag pushes, so no duplicate builds.

### How It Works

- Workflow **only triggers on `v*` tag pushes** (not main branch)
- Push to main branch freely without triggering deployments
- Tag when ready to release → automatic deployment to balena
- One tag = one deployment = one workflow run

### Version Format

- **Tagged releases**: `v1.4.0` (shows as "v1.4.0" in UI)
- **Development builds**: `v1.3.0+rev76` (76 commits after v1.3.0 tag)

### Workflow Behavior

The workflow automatically:
- Uses the tag version in balena.yml
- Embeds version in build-info.json
- Shows version in logs and on-screen status bar
- Tags the Balena release with GitHub metadata

### When to Release

- **MAJOR** (2.0.0): Breaking changes (config format, API changes)
- **MINOR** (1.4.0): New features (backward compatible)
- **PATCH** (1.3.1): Bug fixes only

See [VERSIONING.md](VERSIONING.md) for detailed guidelines.

## �🛠️ Development

### Local Testing (Non-Raspberry Pi)

```bash
# Install dependencies
pip install -r requirements.txt

# Edit config.yaml with your settings
cd app
python3 main.py
```

Note: Some features (NTP sync, HDMI output) may not work on non-Raspberry Pi systems.

### Project Structure

```
rpi-digital-clock/
├── .github/
│   └── workflows/
│       └── balena-deploy.yml  # CI/CD pipeline with build tracking
├── app/
│   ├── framebuffer_clock.py   # PIL RGB565 renderer (optimized)
│   ├── main.py                # Application entry point
│   ├── build_info.py          # CLI to print build metadata
│   ├── start.sh               # Framebuffer startup script
│   ├── weather.py             # Weather API integration
│   ├── rtc.py                 # RTC hardware module support
│   ├── clock_ui.py            # Settings UI manager
│   ├── utils.py               # Helper functions (includes build info loaders)
│   ├── config.yaml            # Configuration file
│   └── build-info.json        # Build metadata (generated by CI)
├── Dockerfile.template        # balena Dockerfile
├── docker-compose.yml         # balena service definition
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Inspired by [rpiclock](https://github.com/bkrajendra/rpiclock) by bkrajendra
- Built for deployment on [balena.io](https://www.balena.io/)
- Weather data provided by [OpenWeatherMap](https://openweathermap.org/)

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check balena forums: https://forums.balena.io/
- Check OpenWeatherMap documentation: https://openweathermap.org/api

## 🔮 Future Enhancements

- [ ] Multiple timezone support
- [ ] Calendar integration
- [ ] Custom background images
- [ ] Multiple clock face styles
- [ ] Motion sensor integration for automatic wake/sleep
- [ ] Web-based configuration interface
- [ ] Custom weather icon display
- [ ] Multi-language support

---

**Made with ❤️ for Raspberry Pi Zero**

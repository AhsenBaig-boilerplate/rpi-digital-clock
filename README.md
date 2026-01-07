# Raspberry Pi Digital Clock for balena.io

A production-ready digital clock display for Raspberry Pi Zero (1st gen) with weather information, designed for HDMI TV displays. Built with Python and Tkinter, deployed via balena.io with comprehensive screen burn-in prevention features.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Balena](https://img.shields.io/badge/balena-compatible-green.svg)

## ✨ Features

### Core Functionality
- **Large Digital Clock Display** - Easy-to-read time display optimized for TV viewing
- **12/24 Hour Format** - Configurable time format with optional AM/PM display
- **Live Weather Integration** - Real-time weather data from OpenWeatherMap API
- **Date Display** - Customizable date format
- **NTP Time Sync** - Automatic time synchronization on startup
- **Hardware RTC Support** - DS3231 RTC module for accurate time when offline

### Screen Burn-in Prevention 🛡️
- **Automatic Screensaver** - Blanks screen after configurable inactivity period
- **Pixel Shift** - Subtle automatic position changes to prevent static image burn-in
- **Night Dimming** - Automatic brightness reduction during night hours
- **Configurable Intervals** - Fully customizable timing for all burn-in prevention features

### Production Ready
- **Error Handling** - Comprehensive error handling and recovery
- **Logging** - Detailed logging for debugging and monitoring
- **Config Validation** - Automatic validation of configuration settings
- **Docker Containerized** - Easy deployment via balena.io
- **Environment Variables** - Override config with environment variables
- **Graceful Shutdown** - Proper cleanup on exit

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

### Environment Variables Setup

After deployment, you **must** configure variables in your balena dashboard. The application supports both direct variable names and `BALENA_` prefixed versions.

#### How to Add Variables in balena Dashboard:

1. **Fleet-wide Variables** (applies to all devices):
   - Navigate to: Dashboard → Your Fleet → Variables tab
   - Click "Add variable"
   - Select "All services" or "clock" service
   - Enter variable name and value
   - Click "Add"

2. **Device-specific Variables** (for individual devices):
   - Navigate to: Dashboard → Your Device → Device Variables tab
   - Click "Add variable"
   - Enter variable name and value
   - Click "Add"

#### Required Variables:

| Variable Name | Example Value | Description |
|--------------|---------------|-------------|
| `WEATHER_API_KEY` | `your_api_key_here` | OpenWeatherMap API key ([Get free key](https://openweathermap.org/api)) |
| `WEATHER_LOCATION` | `New York,US` | City name and country code |

#### Optional Configuration Variables:

| Variable Name | Default | Description |
|--------------|---------|-------------|
| `WEATHER_UNITS` | `metric` | Temperature units (`metric` or `imperial`) |
| `WEATHER_ENABLED` | `true` | Enable/disable weather display |
| `TIMEZONE` | `America/New_York` | Timezone ([List of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DISPLAY_COLOR` | `#00FF00` | Clock color in hex format |
| `FONT_FAMILY` | `Helvetica` | Font family name |
| `TIME_FONT_SIZE` | `120` | Time display font size |
| `TIME_FORMAT_12H` | `true` | Use 12-hour format (true/false) |
| `SHOW_SECONDS` | `true` | Show seconds in display |
| `DATE_FORMAT` | `%A, %B %d, %Y` | Python strftime format |
| `SCREENSAVER_ENABLED` | `true` | Enable screensaver |
| `SCREENSAVER_DELAY_MINUTES` | `60` | Minutes before screensaver activates |
| `PIXEL_SHIFT_ENABLED` | `true` | Enable pixel shifting |
| `DIM_AT_NIGHT` | `true` | Dim display at night |
| `NIGHT_BRIGHTNESS` | `0.3` | Night brightness (0.0-1.0) |

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

Edit `app/config.yaml` to customize the clock:

### Time Settings

```yaml
time:
  format_12h: true              # true for 12-hour, false for 24-hour
  ntp_sync: true                # Sync time with NTP on startup
  ntp_server: "pool.ntp.org"    # NTP server to use
  rtc_enabled: true             # Enable DS3231 RTC module support
```

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

Device variables are useful when you have multiple clocks showing different locations or configurations:

```
Device 1 (Kitchen - New York):
  WEATHER_LOCATION: "New York,US"
  DISPLAY_COLOR: "#00FF00"
  WEATHER_UNITS: "imperial"

Device 2 (Office - London):
  WEATHER_LOCATION: "London,GB"
  DISPLAY_COLOR: "#00FFFF"
  WEATHER_UNITS: "metric"
  TIME_FORMAT_12H: "false"

Device 3 (Bedroom):
  WEATHER_LOCATION: "Tokyo,JP"
  DIM_AT_NIGHT: "true"
  NIGHT_BRIGHTNESS: "0.2"
  SCREENSAVER_DELAY_MINUTES: "30"
```

See [balena documentation](https://docs.balena.io/learn/manage/variables/#device-variables) for more details on variable types and precedence.

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

## 🔧 Troubleshooting

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

## 🛠️ Development

### Local Testing (Non-Raspberry Pi)

```bash
# Install dependencies
pip install -r requirements.txt

# Edit config.yaml with your settings
cd app
python main.py
```

Note: Some features (NTP sync, HDMI output) may not work on non-Raspberry Pi systems.

### Project Structure

```
rpi-digital-clock/
├── app/
│   ├── main.py          # Application entry point
│   ├── clock_ui.py      # UI and display logic
│   ├── weather.py       # Weather API integration
│   ├── utils.py         # Helper functions
│   └── config.yaml      # Configuration file
├── Dockerfile.template  # balena Dockerfile
├── docker-compose.yml   # balena service definition
├── requirements.txt     # Python dependencies
└── README.md           # This file
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

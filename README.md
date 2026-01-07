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

### 1. Setup balena Account

1. Create a free account at [balena.io](https://www.balena.io/)
2. Install balena CLI: https://github.com/balena-io/balena-cli/blob/master/INSTALL.md
3. Login to balena CLI:
   ```bash
   balena login
   ```

### 2. Create balena Application

1. Go to [balena Dashboard](https://dashboard.balena-cloud.com/)
2. Click "Create application"
3. Choose:
   - **Name**: `rpi-digital-clock` (or your preferred name)
   - **Device type**: Raspberry Pi (v1 / Zero / Zero W)
   - **Application type**: Starter
4. Click "Create new application"

### 3. Add Your Device

1. In your application dashboard, click "Add device"
2. Select WiFi configuration (if using WiFi)
3. Download the balenaOS image
4. Flash the image to your SD card using [balenaEtcher](https://www.balena.io/etcher/)
5. Insert SD card into Raspberry Pi and power it on
6. Wait for device to appear in your balena dashboard (may take a few minutes)

### 4. Configure Weather API

1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. In balena dashboard, go to your application
3. Navigate to "Environment variables" or "Device variables"
4. Add the following variables:
   - `WEATHER_API_KEY`: Your OpenWeatherMap API key
   - `WEATHER_LOCATION`: Your city (e.g., "New York,US", "London,GB")

### 5. Deploy Application

Clone and push this repository to your balena application:

```bash
# Clone this repository
git clone https://github.com/yourusername/rpi-digital-clock.git
cd rpi-digital-clock

# Add balena remote (get this from your balena dashboard)
balena push <YOUR_APP_NAME>
```

Or using git:

```bash
git remote add balena <YOUR_USERNAME>@git.balena-cloud.com:<YOUR_USERNAME>/<YOUR_APP_NAME>.git
git push balena main
```

### 6. Wait for Build and Deployment

- balena will build the Docker container (takes 10-20 minutes on first build)
- The application will automatically deploy to your Raspberry Pi
- Check logs in balena dashboard to monitor progress

### 7. Connect to TV

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

You can override config.yaml settings using environment variables in balena dashboard:

| Variable | Description | Example |
|----------|-------------|---------|
| `WEATHER_API_KEY` | OpenWeatherMap API key | `abc123def456` |
| `WEATHER_LOCATION` | City for weather | `London,GB` |
| `LOG_LEVEL` | Logging verbosity | `INFO` or `DEBUG` |

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
#   r p i - d i g i t a l - c l o c k 
 
 
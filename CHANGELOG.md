# Changelog

All notable changes to the Raspberry Pi Digital Clock project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-06

### Added
- Initial release of Raspberry Pi Digital Clock
- Digital clock display with customizable fonts and colors
- 12/24 hour format support with AM/PM display
- Real-time weather integration via OpenWeatherMap API
- Customizable date display with multiple format options
- NTP time synchronization on startup
- **DS3231 RTC module support** for offline timekeeping
  - Automatic fallback to RTC when internet unavailable
  - RTC syncing from NTP when online
  - Built-in temperature sensor reading
  - Battery backup support
- Screen burn-in prevention features:
  - Automatic screensaver with configurable timeout
  - Pixel shift to prevent static image burn-in
  - Night dimming for reduced brightness during night hours
- Production-ready error handling and logging
- Configuration validation
- balena.io deployment support with Docker
- Environment variable overrides for sensitive configuration
- Comprehensive documentation in README.md
- MIT License

### Features
- Fullscreen display optimized for TV viewing
- Weather caching to reduce API calls
- Graceful shutdown handling
- Automatic screen blanking and power management
- Cursor hiding for clean display
- Configurable update intervals
- Support for multiple weather units (metric, imperial, kelvin)
- Multi-language weather descriptions

### Technical
- Python 3.9+ compatible
- Tkinter-based GUI
- Docker containerized application
- balena.io fleet management ready
- Comprehensive logging system
- Config file validation
- Internet connectivity checks
- Display resolution detection

### Documentation
- Complete setup guide
- Troubleshooting section
- Configuration examples
- Environment variable documentation
- Development setup instructions
- Contributing guidelines

## Future Roadmap

### Planned for v1.1.0
- [ ] Multiple timezone support
- [ ] Web-based configuration interface
- [ ] Calendar integration
- [ ] Custom background images

### Planned for v1.2.0
- [ ] Multiple clock face styles
- [ ] Motion sensor integration
- [ ] Custom weather icon display
- [ ] Extended weather forecast display

### Planned for v2.0.0
- [ ] Plugin system for extensions
- [ ] Multi-screen support
- [ ] Voice control integration
- [ ] Mobile app for remote control

[1.0.0]: https://github.com/yourusername/rpi-digital-clock/releases/tag/v1.0.0

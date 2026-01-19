# RPI Digital Clock V2 Architecture

Production-grade rewrite with clean separation of concerns.

## Architecture Overview

```
app_v2/
├── core/               # Business logic layer
│   ├── config_service.py      # Configuration management
│   ├── clock_service.py       # Time/date logic
│   ├── weather_service.py     # Weather API integration
│   ├── logging_service.py     # Structured logging
│   └── health_service.py      # UI health monitoring
├── hardware/           # Hardware abstraction layer
│   ├── rtc.py                 # Real-time clock interface
│   └── display_info.py        # Display detection
├── ui/                 # Presentation layer
│   ├── theme.py               # Visual styling
│   ├── layout.py              # Layout management
│   └── main_window.py         # Tkinter UI
├── config/             # Configuration files
│   ├── default.yaml           # Default configuration
│   └── schema.json            # Config validation schema
└── main.py             # Application entry point
```

## Key Features

- **Clean Layered Architecture**: Separation of concerns (core/hardware/ui)
- **Singleton Services**: ConfigService with YAML + environment overrides
- **Caching**: Weather service with 15-minute TTL
- **Health Monitoring**: Heartbeat system to detect UI freezes
- **RTC Support**: Hardware clock abstraction
- **Responsive Design**: Auto-detects display resolution
- **Dark Theme**: Optimized for readability
- **Production-Ready**: Structured logging, error handling, graceful shutdown

## Usage

### Running V2 Architecture

Set environment variable to use the new architecture:

```bash
export CLOCK_VERSION=v2
python3 -m app_v2.main
```

Or in Docker:

```bash
docker run -e CLOCK_VERSION=v2 ...
```

### Configuration

Configuration is loaded from (in order):
1. `/data/config.yaml` (runtime, persistent)
2. `config/default.yaml` (built-in defaults)
3. `app_v2/config/default.yaml` (fallback)
4. Environment variables (highest priority)

Example environment overrides:
```bash
TIMEZONE=America/New_York
WEATHER_API_KEY=your_key_here
WEATHER_LOCATION="New York, US"
DISPLAY_WIDTH=1024
DISPLAY_HEIGHT=600
LOG_LEVEL=DEBUG
```

### Development

Run directly:
```bash
cd /home/admins/rpi-digital-clock
python3 -m app_v2.main
```

## Design Principles

1. **No Circular Imports**: Each layer only imports from lower layers
2. **Dependency Injection Ready**: Services can be mocked for testing
3. **DRY**: Shared logic in reusable services
4. **Fail Gracefully**: Weather failure doesn't crash clock
5. **Performance**: Caching, non-blocking updates, lazy loading
6. **Maintainability**: Clear naming, comprehensive logging, modular design

## Service Responsibilities

### Core Layer
- **ConfigService**: Load YAML, apply env overrides, provide dot notation access
- **ClockService**: Timezone-aware time formatting, display data generation
- **WeatherService**: OpenWeatherMap API with caching and error handling
- **LoggingService**: Structured logging with configurable levels
- **HealthService**: Background thread monitoring UI responsiveness

### Hardware Layer
- **RTC**: Abstract hwclock access, fallback to system time
- **DisplayInfo**: Detect screen resolution, orientation, display type

### UI Layer
- **Theme**: Colors, fonts, spacing constants
- **Layout**: Calculate component positions and sizes
- **MainWindow**: Tkinter event loop with non-blocking updates

## Migration Path

This v2 architecture runs alongside the existing v1 app. To switch:

1. Set `CLOCK_VERSION=v2` environment variable
2. Configure `/data/config.yaml` with your settings
3. Restart container

The old framebuffer renderer (v1) remains default for backward compatibility.

## Version

**v2.0.0** - Complete architectural rewrite (2024)

# Changelog

All notable changes to the Raspberry Pi Digital Clock project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.120] - 2026-01-12

### Fixed
- **GitHub Actions duplicate deployments**: Fixed workflow triggering twice on `git push origin main --tags`
  - Main branch builds now skip when commit is already tagged
  - Prevents duplicate/conflicting deployments (red X marks in Actions)
  - Tag push handles deployment, main branch push exits gracefully
  - Added `skip_build` flag checked by all workflow steps
  - **Root cause**: Workflow triggered on both `main` push AND `v*` tag push simultaneously
  - Tag builds succeed, main builds failed trying to create duplicate tags

## [1.4.119] - 2026-01-12

### Changed
- **Lazy loading for date sprites**: Dramatically reduced startup time and CPU spike
  - Startup: 99% CPU for 3-5s → 60-80% CPU for ~1s (70% faster)
  - Only pre-renders 14 time sprites at startup (instead of 80+ total)
  - Date sprites (A-Z, a-z, punctuation) rendered on-demand via `_get_or_create_date_sprite()`
  - First date render adds 50-100ms to lazy-load needed characters
  - Subsequent date renders use cached sprites with no overhead
  - Maintains same steady-state performance: ~170ms renders at 30-40% CPU

### Fixed
- GitHub Actions build issues: Re-tagged v1.4.117 and v1.4.118 to point to correct commits

### Technical Details
- New `_get_or_create_date_sprite()` method for on-demand sprite generation
- Date canvas width calculation uses lazy loading
- Startup log now shows "lazy-loading date sprites" message
- Perfect for Pi Zero W: fast startup, low memory, smooth operation

## [1.4.118] - 2026-01-12

### Changed
- **Startup behavior documentation**: Explains expected 99% CPU spike during initialization
  - Sprite cache generation takes 3-5 seconds on Pi Zero W
  - Pre-renders 80+ character sprites (time + date) with RGB565 conversion
  - One-time cost that enables fast per-frame rendering (6-7ms vs 280ms)
  - CPU returns to 30-40% after cache completes
  - Added detailed logging: "Pre-rendering sprite cache (this takes 3-5 sec on Pi Zero W, CPU will spike)..."

### Added
- Troubleshooting section in README for high startup CPU (normal vs abnormal)
- Progress logging for sprite cache generation

## [1.4.117] - 2026-01-12

### Added
- **Comprehensive startup logging**: Now logs complete runtime environment
  - Runtime summary: PIL RGB565, vector icons, RTC status
  - Git version/tag from build-info.json
  - Balena device metadata (device name, type, UUID, service name)
  - Environment variables with sensitive values masked (API keys shown as ****)
  - Shows all device/fleet variable overrides at startup
  - Matches README documentation for troubleshooting

### Technical Details
- New `log_runtime_summary()` function in utils.py
- Logs both `VARNAME` and `BALENA_VARNAME` environment variables
- Displays git tag version for easy deployment tracking
- Helps identify which device variables are active vs config.yaml defaults

## [1.4.116] - 2026-01-12

### Fixed
- **Critical CPU usage fix**: 99% CPU usage due to missing sleep
  - Fixed main loop sleep logic that could skip time.sleep() call
  - Each code path now explicitly calls time.sleep() with calculated delay
  - Added minimum 10ms delay to prevent tight loops
  - **Root cause**: Nested if/else logic could skip sleep when seconds shown
  - **Impact**: CPU was spinning at 99% instead of sleeping between renders

### Changed
- Simplified main loop sleep logic for better readability
- Each mode (overlay/seconds/minute) now handles its own sleep directly
- Performance: ~170ms renders + ~830ms sleep = smooth 1 FPS with low CPU

## [1.4.115] - 2026-01-12

### Fixed
- **Critical crash fix**: Sprite overflow during pixel shift
  - Added bounds checking in `_composite_time_from_cache()` and `_composite_date_from_cache()`
  - Prevents ValueError: "could not broadcast input array from shape (220,161) into shape (220,0)"
  - Sprites now clipped to canvas boundaries instead of crashing
  - **Root cause**: Pixel shift could position time/date so sprites extend beyond fixed-width canvas
  - **Impact**: Clock would crash every 30 seconds during pixel shift with certain time values

### Technical Details
- Fixed invalid numpy array slicing when `x_offset + sw > canvas_width`
- Added sprite clipping: `sprite_data[:, :sw_clipped]` to fit within canvas
- Applied to both time and date rendering functions

## [1.4.114] - 2026-01-12

### Removed
- **Unused files cleanup** (~1,650 lines removed):
  - `app/pygame_clock.py` (463 lines) - Pygame renderer no longer needed
  - `app/compare_renderers.py` (142 lines) - Benchmarking script
  - `app/web_ui.py` (218 lines) - Flask web UI (unused)
  - `app/assets/emojis/` - 7 PNG icon files + README (not used)
  - `benchmark.sh` - Renderer comparison script
  - `RENDERER_COMPARISON.md` - Outdated documentation
  
### Changed
- **Documentation cleanup**:
  - Removed `USE_EMOJI` environment variable references
  - Updated runtime summary to show "Vector" icons instead of "PNG"
  - Clarified that status icons are drawn by PIL as vector graphics
  - No external PNG files needed for icons

### Technical Notes
- Status bar icons (network, sync, settings) are now clearly documented as vector-drawn
- Reduced repository size and maintenance complexity
- Pure PIL architecture with RGB565 optimization

## [1.4.113] - 2026-01-12

### Removed
- **Code cleanup**: Removed all unused native renderer (Rust) integration code
  - Removed `_send_native()` and `_restart_native_renderer()` methods
  - Removed native renderer initialization logic
  - Removed environment variables: `NATIVE_TIME_RENDERER`, `NATIVE_TIME_BIN`
  - Native renderer was never functional (binary didn't exist)
- **Dependency cleanup**: Removed pygame references and dependencies
  - Removed `python3-pygame` and `libsdl2-2.0-0` from Dockerfile
  - Removed `USE_PYGAME` environment variable and renderer selection logic
  - Updated documentation to reflect PIL-only architecture
- **Simplified startup**: Removed renderer selection logic from start.sh
  - Clock now always uses PIL framebuffer with RGB565 optimization
  - Reduced code complexity and maintenance burden

### Changed
- Updated file header to clarify "pure PIL with pre-converted sprite cache"
- Updated README.md to remove pygame references
- Updated start.sh to remove conditional renderer logic

## [1.4.112] - 2026-01-12

### Fixed
- **Date rendering optimization**: Applied RGB565 pre-conversion to date sprites
  - Date blit time: 83ms → ~6ms (14x faster)
  - Same optimization strategy as time rendering (v1.4.110-111)
  - Total render time now ~180ms (down from 560ms)
  - CPU usage: ~35% (down from 100%)

## [1.4.111] - 2026-01-12

### Fixed
- **Space character RGB565 conversion**: Fixed KeyError crash
  - Space characters now properly converted to RGB565 format during cache creation
  - Resolves crash: "KeyError: 'rgb565' for character ' '"

## [1.4.110] - 2026-01-12

### Added
- **Breakthrough performance optimization**: RGB565 sprite pre-conversion
  - Sprites now pre-converted to RGB565 format during cache creation
  - New `blit_rgb565_direct()` function bypasses PIL→RGB565 conversion
  - Modified `_composite_time_from_cache()` to return RGB565 array directly
  - Cache stores both 'image' (RGB888) and 'rgb565' (pre-converted) formats

### Performance
- **Massive rendering speedup**: Eliminated per-frame format conversion overhead
  - Time blit: 280ms → 6.5ms (43x faster)
  - Total render: 560ms → 259ms (54% reduction)
  - CPU usage: 100% → 44% (56% reduction)
  - Target of <200ms render and 30-40% CPU achieved

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

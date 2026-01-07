# Quick Reference Guide

## Common Configurations

### 1. Simple Green Clock (Default)
```yaml
display:
  color: "#00FF00"
  time_font_size: 120
  screensaver_enabled: true
  pixel_shift_enabled: true
```

### 2. White Modern Clock
```yaml
display:
  color: "#FFFFFF"
  font_family: "Arial"
  time_font_size: 140
  show_seconds: false
  screensaver_delay_minutes: 30
```

### 3. Retro Amber Clock
```yaml
display:
  color: "#FFBF00"
  font_family: "Courier"
  time_font_size: 110
  date_format: "%m/%d/%Y"
```

### 4. Minimalist Clock (No Weather)
```yaml
time:
  format_12h: false  # 24-hour format
display:
  color: "#00FFFF"
  time_font_size: 150
  show_seconds: false
weather:
  enabled: false
```

### 5. Power Saver Configuration
```yaml
display:
  screensaver_enabled: true
  screensaver_delay_minutes: 15
  pixel_shift_enabled: true
  pixel_shift_interval_seconds: 20
  dim_at_night: true
  night_brightness: 0.2
  night_start_hour: 20
  night_end_hour: 7
```

## Screen Burn-in Prevention Settings

### Aggressive Protection
- Screensaver after 15 minutes
- Pixel shift every 15 seconds
- Maximum night dimming
```yaml
display:
  screensaver_delay_minutes: 15
  pixel_shift_interval_seconds: 15
  night_brightness: 0.2
```

### Balanced Protection (Recommended)
- Screensaver after 60 minutes
- Pixel shift every 30 seconds
- Moderate night dimming
```yaml
display:
  screensaver_delay_minutes: 60
  pixel_shift_interval_seconds: 30
  night_brightness: 0.3
```

### Minimal Protection
- Screensaver after 2 hours
- Pixel shift every 60 seconds
- Light night dimming
```yaml
display:
  screensaver_delay_minutes: 120
  pixel_shift_interval_seconds: 60
  night_brightness: 0.5
```

## Color Schemes

| Style | Color Code | Description |
|-------|-----------|-------------|
| Matrix Green | `#00FF00` | Classic green, easy on eyes |
| Pure White | `#FFFFFF` | Bright, modern |
| Cyan Blue | `#00FFFF` | Cool, futuristic |
| Amber | `#FFBF00` | Warm, retro |
| Red | `#FF0000` | Bold, attention-grabbing |
| Purple | `#9D00FF` | Unique, vibrant |
| Yellow | `#FFFF00` | Bright, cheerful |
| Orange | `#FF8C00` | Warm, inviting |

## Date Format Examples

| Format | Output Example |
|--------|---------------|
| `"%A, %B %d, %Y"` | Monday, January 06, 2026 |
| `"%m/%d/%Y"` | 01/06/2026 |
| `"%d-%m-%Y"` | 06-01-2026 |
| `"%B %d, %Y"` | January 06, 2026 |
| `"%a, %b %d"` | Mon, Jan 06 |
| `"%d %B %Y"` | 06 January 2026 |
| `"%Y-%m-%d"` | 2026-01-06 |

## Weather Location Examples

| Location | Format |
|----------|--------|
| New York | `New York,US` |
| London | `London,GB` |
| Tokyo | `Tokyo,JP` |
| Paris | `Paris,FR` |
| Sydney | `Sydney,AU` |
| Toronto | `Toronto,CA` |
| Berlin | `Berlin,DE` |

## Troubleshooting Quick Fixes

### Clock Too Large/Small
```yaml
display:
  time_font_size: 120  # Adjust this value (60-200)
```

### Weather Not Showing
1. Check API key in environment variables
2. Verify location format: `City,CountryCode`
3. Set `LOG_LEVEL=DEBUG` to see API errors

### Screen Staying On Too Long
```yaml
display:
  screensaver_delay_minutes: 15  # Reduce this value
```

### Text Too Bright at Night
```yaml
display:
  night_brightness: 0.2  # Lower value = dimmer
  night_start_hour: 20   # Earlier start time
  night_end_hour: 8      # Later end time
```

### Display Flickering
```yaml
display:
  pixel_shift_interval_seconds: 60  # Increase interval
  # or disable completely:
  pixel_shift_enabled: false
```

## Environment Variables Quick Reference

Set these in balena dashboard under "Environment Variables":

```
WEATHER_API_KEY=your_api_key_here
WEATHER_LOCATION=New York,US
LOG_LEVEL=INFO
```

## Font Sizes by Display

| TV Size | Recommended Time Font | Date Font | Weather Font |
|---------|----------------------|-----------|--------------|
| 24"-32" | 80-100 | 30 | 20 |
| 40"-50" | 120-140 | 40 | 30 |
| 55"-65" | 150-180 | 50 | 35 |
| 70"+ | 200-240 | 60 | 40 |

## balena CLI Commands

```bash
# View logs
balena logs YOUR_APP_NAME

# Push updates
balena push YOUR_APP_NAME

# SSH into device
balena ssh YOUR_DEVICE_UUID

# Restart application
balena restart YOUR_DEVICE_UUID
```

## Useful Log Commands

```bash
# View live logs
balena logs YOUR_APP_NAME --tail

# View specific service
balena logs YOUR_APP_NAME --service clock

# Filter for errors
balena logs YOUR_APP_NAME | grep ERROR
```

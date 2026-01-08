# Emoji PNG Icons

This directory contains optional PNG emoji icons for the status bar display.

## Icon Requirements

- **Format:** PNG with transparency
- **Size:** 16x16 or 24x24 pixels (will be scaled to 24x24)
- **Color:** Match your clock color theme or use standard emoji colors

## Required Icons

Place these PNG files in this directory to enable icon display:

| Filename | Purpose | Fallback ASCII |
|----------|---------|----------------|
| `wifi.png` | WiFi connection indicator | `WiFi:` |
| `ethernet.png` | Ethernet connection indicator | `Net:` |
| `network_error.png` | No network / error indicator | `X` |
| `globe.png` | Timezone indicator | `TZ:` |
| `sync.png` | NTP sync time indicator | `Sync:` |
| `clock.png` | RTC hardware active indicator | `RTC:` |

## Recommended Icon Sources

### 1. **Twemoji** (Recommended - MIT License)
Free, high-quality emoji PNGs from Twitter:
- Website: https://twemoji.twitter.com/
- GitHub: https://github.com/twitter/twemoji
- License: MIT (free for commercial use)

**Quick Download:**
```bash
# Navigate to this directory
cd /home/admins/rpi-digital-clock/app/assets/emojis

# Download Twemoji icons (using Unicode codepoints)
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4f6.png -O wifi.png      # 📶
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f310.png -O ethernet.png  # 🌐
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/274c.png -O network_error.png # ❌
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f30d.png -O globe.png     # 🌍
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f504.png -O sync.png      # 🔄
wget https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f570.png -O clock.png     # 🕰️
```

### 2. **OpenMoji** (Alternative - CC BY-SA 4.0)
Open-source emoji icons:
- Website: https://openmoji.org/
- License: CC BY-SA 4.0

### 3. **Noto Color Emoji** (Google)
Google's emoji font as PNGs:
- GitHub: https://github.com/googlefonts/noto-emoji
- License: Apache 2.0

### 4. **Custom Icons**
Create your own 24x24 PNG icons matching your clock theme.

## Installation

1. Download or create PNG icons
2. Place them in this directory (`app/assets/emojis/`)
3. Ensure filenames match the table above
4. Icons will be automatically loaded on next startup

## Disable Icons

To use ASCII fallback instead of icons, set:
```bash
USE_EMOJI=false
```

## Performance

PNG icons are lightweight sprites that:
- Load once at startup
- Render as fast as text
- Work perfectly on Raspberry Pi Zero W
- No emoji font rendering overhead

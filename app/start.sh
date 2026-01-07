#!/bin/bash
# Startup script for Raspberry Pi Digital Clock
# Ensures proper X server initialization and application launch

echo "Starting Raspberry Pi Digital Clock..."

# Set timezone if provided via environment variable
if [ -n "$TIMEZONE" ]; then
    echo "Setting timezone to: $TIMEZONE"
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime || echo "Warning: Could not set timezone"
    echo "$TIMEZONE" > /etc/timezone 2>/dev/null || true
fi

# Wait for udev to settle
sleep 2

# Set up display environment
export DISPLAY=:0
export XAUTHORITY=/root/.Xauthority

# Create Xauthority file if it doesn't exist
touch /root/.Xauthority
chmod 600 /root/.Xauthority

# Remove stale X server lock files
rm -f /tmp/.X0-lock
rm -f /tmp/.X11-unix/X0

# Kill any existing X server
killall X 2>/dev/null || true
killall Xorg 2>/dev/null || true
sleep 2

# Start dbus for X server (needed for some X features)
echo "Starting D-Bus..."
mkdir -p /run/dbus
rm -f /run/dbus/pid
dbus-daemon --system --fork 2>/dev/null || echo "D-Bus already running or not available"

# Start X server in background with simpler configuration
echo "Starting X server..."
X :0 -nolisten tcp vt1 -nocursor &
X_PID=$!

# Wait for X server to be ready - check for X socket instead of using xdpyinfo
echo "Waiting for X server..."
X_READY=false
for i in {1..30}; do
    # Check if X server socket exists and process is running
    if [ -S /tmp/.X11-unix/X0 ] && kill -0 $X_PID 2>/dev/null; then
        # Try a simple X connection test
        if DISPLAY=:0 xset q >/dev/null 2>&1 || DISPLAY=:0 xdpyinfo >/dev/null 2>&1; then
            echo "X server is ready (attempt $i)"
            X_READY=true
            break
        fi
    fi
    
    # Check if X process died
    if ! kill -0 $X_PID 2>/dev/null; then
        echo "ERROR: X server process died!"
        break
    fi
    
    echo "Waiting for X server... (attempt $i/30)"
    sleep 1
done

if [ "$X_READY" = false ]; then
    echo "ERROR: X server failed to start properly"
    echo "=== Checking X server process ==="
    ps aux | grep -E 'X|Xorg' | grep -v grep
    echo "=== Last 50 lines of Xorg log ==="
    tail -n 50 /var/log/Xorg.0.log 2>/dev/null || echo "No Xorg log found"
    exit 1
fi

# Give X server extra time to fully initialize
sleep 3

# Disable screen blanking and power management
if command -v xset &> /dev/null; then
    DISPLAY=:0 xset s off 2>/dev/null || true
    DISPLAY=:0 xset -dpms 2>/dev/null || true
    DISPLAY=:0 xset s noblank 2>/dev/null || true
    echo "Screen blanking disabled"
fi

# Set display orientation if specified
if [ -n "$DISPLAY_ORIENTATION" ]; then
    echo "Setting display orientation to: $DISPLAY_ORIENTATION"
    if [ "$DISPLAY_ORIENTATION" = "portrait" ]; then
        # Rotate display 90 degrees clockwise for portrait mode
        DISPLAY=:0 xrandr --output HDMI-1 --rotate right 2>/dev/null || \
        DISPLAY=:0 xrandr --output HDMI-0 --rotate right 2>/dev/null || \
        echo "Warning: Could not rotate display (xrandr might not support this output)"
    elif [ "$DISPLAY_ORIENTATION" = "landscape" ]; then
        # Normal landscape orientation
        DISPLAY=:0 xrandr --output HDMI-1 --rotate normal 2>/dev/null || \
        DISPLAY=:0 xrandr --output HDMI-0 --rotate normal 2>/dev/null || \
        echo "Display set to normal orientation"
    fi
fi

# Start unclutter to hide cursor
if command -v unclutter &> /dev/null; then
    DISPLAY=:0 unclutter -idle 0 -root &
    echo "Cursor hidden"
fi

# Start web server in background
echo "Starting web server..."
cd /app
python3 web_server.py &
WEB_SERVER_PID=$!
sleep 2

# Build clock URL with parameters from config
CLOCK_URL="http://localhost:8000/clock.html"

# Add URL parameters for customization
PARAMS=""
if [ -n "$DISPLAY_COLOR" ]; then
    PARAMS="${PARAMS}&color=${DISPLAY_COLOR}"
fi
if [ -n "$TIME_FORMAT_12H" ]; then
    PARAMS="${PARAMS}&format12h=${TIME_FORMAT_12H}"
fi
if [ -n "$SHOW_SECONDS" ]; then
    PARAMS="${PARAMS}&showSeconds=${SHOW_SECONDS}"
fi

# Remove leading & if params exist
if [ -n "$PARAMS" ]; then
    CLOCK_URL="${CLOCK_URL}?${PARAMS:1}"
fi

echo "Launching clock in Chromium..."
echo "URL: $CLOCK_URL"

# Launch Chromium in kiosk mode (fullscreen, no UI)
DISPLAY=:0 chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --ozone-platform=wayland \
    --enable-features=OverlayScrollbar \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --disable-features=TranslateUI \
    --disk-cache-dir=/dev/null \
    --password-store=basic \
    "$CLOCK_URL" &

CHROMIUM_PID=$!

echo "Clock application started (PID: $CHROMIUM_PID)"
echo "Web server running (PID: $WEB_SERVER_PID)"

# Wait for Chromium process
wait $CHROMIUM_PID

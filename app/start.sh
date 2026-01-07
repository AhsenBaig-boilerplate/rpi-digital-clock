#!/bin/bash
# Startup script for Raspberry Pi Digital Clock
# Ensures proper X server initialization and application launch

set -e

echo "Starting Raspberry Pi Digital Clock..."

# Wait for udev to settle
sleep 2

# Set up display environment
export DISPLAY=:0
export XAUTHORITY=/root/.Xauthority

# Create Xauthority file if it doesn't exist
touch /root/.Xauthority

# Remove stale X server lock files
rm -f /tmp/.X0-lock
rm -f /tmp/.X11-unix/X0

# Kill any existing X server
killall X 2>/dev/null || true
killall Xorg 2>/dev/null || true
sleep 2

# Start X server in background with proper configuration
echo "Starting X server..."
startx /usr/bin/unclutter -idle 0 -root -- :0 vt1 -nocursor -s 0 -dpms 2>&1 | grep -v "hostname:" &

X_PID=$!

# Wait for X server to be ready with more robust checking
echo "Waiting for X server..."
X_READY=false
for i in {1..30}; do
    if xdpyinfo -display :0 >/dev/null 2>&1; then
        echo "X server is ready (attempt $i)"
        X_READY=true
        break
    fi
    echo "Waiting for X server... (attempt $i/30)"
    sleep 1
done

if [ "$X_READY" = false ]; then
    echo "ERROR: X server failed to start properly"
    exit 1
fi

# Give X server extra time to fully initialize
sleep 3

# Disable screen blanking and power management
if command -v xset &> /dev/null; then
    xset -display :0 s off 2>/dev/null || true
    xset -display :0 -dpms 2>/dev/null || true
    xset -display :0 s noblank 2>/dev/null || true
    echo "Screen blanking disabled"
fi

# Start the Python application
echo "Launching clock application..."
cd /app
exec python3 main.py

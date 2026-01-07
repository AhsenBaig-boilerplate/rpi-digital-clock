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

# Kill any existing X server
killall X 2>/dev/null || true
killall Xorg 2>/dev/null || true
sleep 1

# Start X server in background
echo "Starting X server..."
startx /usr/bin/unclutter -idle 0 -root -- -nocursor -s 0 -dpms &

# Wait for X server to be ready
echo "Waiting for X server..."
for i in {1..30}; do
    if xdpyinfo -display :0 >/dev/null 2>&1; then
        echo "X server is ready"
        break
    fi
    echo "Waiting for X server... ($i/30)"
    sleep 1
done

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

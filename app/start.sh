#!/bin/bash
# Startup script for Raspberry Pi Digital Clock
# Ensures proper X server initialization and application launch

set -e

echo "Starting Raspberry Pi Digital Clock..."

# Set up display
export DISPLAY=:0

# Disable screen blanking and power management
if command -v xset &> /dev/null; then
    xset -display :0 s off 2>/dev/null || true
    xset -display :0 -dpms 2>/dev/null || true
    xset -display :0 s noblank 2>/dev/null || true
    echo "Screen blanking disabled"
fi

# Hide cursor
if command -v unclutter &> /dev/null; then
    unclutter -display :0 -idle 0 &
fi

# Start the Python application
echo "Launching clock application..."
cd /app
exec python3 main.py

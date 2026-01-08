#!/bin/bash
# Startup script for Raspberry Pi Digital Clock (Framebuffer mode)
# Direct framebuffer rendering - no X server needed

echo "Starting Raspberry Pi Digital Clock (Framebuffer mode)..."

# Set timezone if provided via environment variable
if [ -n "$TIMEZONE" ]; then
    echo "Setting timezone to: $TIMEZONE"
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime || echo "Warning: Could not set timezone"
    echo "$TIMEZONE" > /etc/timezone 2>/dev/null || true
fi

# Launch framebuffer clock application (no X11 required)
echo "Launching framebuffer clock application..."
cd /app
if [ "${PRINT_BUILD_INFO}" = "true" ]; then
  echo "Printing build info before launch..."
  python3 build_info.py || true
fi
exec python3 framebuffer_clock.py


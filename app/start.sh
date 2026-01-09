#!/bin/bash
# Startup script for Raspberry Pi Digital Clock (Pygame SDL FBDEV mode)
# SDL framebuffer rendering - no X server needed

echo "Starting Raspberry Pi Digital Clock (Pygame SDL FBDEV mode)..."

# Set timezone if provided via environment variable
if [ -n "$TIMEZONE" ]; then
    echo "Setting timezone to: $TIMEZONE"
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime || echo "Warning: Could not set timezone"
    echo "$TIMEZONE" > /etc/timezone 2>/dev/null || true
fi

# Launch pygame clock application (SDL FBDEV mode - no X11 required)
echo "Launching pygame clock application (SDL framebuffer mode)..."
cd /app
if [ "${PRINT_BUILD_INFO}" = "true" ]; then
  echo "Printing build info before launch..."
  python3 build_info.py || true
fi

# Monitor for restart flag and reload clock when settings change
while true; do
    python3 clock_display.py &
    CLOCK_PID=$!
    
    # Wait for either clock to exit or restart flag
    while kill -0 $CLOCK_PID 2>/dev/null; do
        if [ -f /tmp/restart_clock ]; then
            echo "Restart requested, reloading configuration..."
            rm /tmp/restart_clock
            kill $CLOCK_PID 2>/dev/null
            sleep 2
            break
        fi
        sleep 1
    done
    
    # If clock exited on its own (error), wait before restarting
    if [ ! -f /tmp/restart_clock ]; then
        echo "Clock exited unexpectedly, restarting in 5 seconds..."
        sleep 5
    fi
done


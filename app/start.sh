#!/bin/bash
# Startup script for Raspberry Pi Digital Clock
# Direct framebuffer rendering with PIL RGB565 optimization

echo "Starting Raspberry Pi Digital Clock (Framebuffer mode)..."

# Set timezone if provided via environment variable
if [ -n "$TIMEZONE" ]; then
    echo "Setting timezone to: $TIMEZONE"
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime || echo "Warning: Could not set timezone"
    echo "$TIMEZONE" > /etc/timezone 2>/dev/null || true
fi

# Launch clock application
echo "Launching clock application..."
cd /app
if [ "${PRINT_BUILD_INFO}" = "true" ]; then
  echo "Printing build info before launch..."
  python3 build_info.py || true
fi

CLOCK_APP="framebuffer_clock.py"
echo "=========================================="
echo "Using PIL framebuffer renderer with RGB565 optimization"
echo "========================================="

echo "Launching: python3 $CLOCK_APP"

# Monitor for restart flag and reload clock when settings change
while true; do
    python3 $CLOCK_APP &
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


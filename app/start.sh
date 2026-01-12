#!/bin/bash
# Startup script for Raspberry Pi Digital Clock (Pygame SDL FBDEV mode)
# SDL framebuffer rendering - no X server needed

echo "Starting Raspberry Pi Digital Clock (Framebuffer mode)..."

# Set timezone if provided via environment variable
if [ -n "$TIMEZONE" ]; then
    echo "Setting timezone to: $TIMEZONE"
    ln -sf /usr/share/zoneinfo/$TIMEZONE /etc/localtime || echo "Warning: Could not set timezone"
    echo "$TIMEZONE" > /etc/timezone 2>/dev/null || true
fi

# Launch clock application - pygame or PIL framebuffer
echo "Launching clock application..."
cd /app
if [ "${PRINT_BUILD_INFO}" = "true" ]; then
  echo "Printing build info before launch..."
  python3 build_info.py || true
fi

# Choose renderer based on environment variable
if [ "${USE_PYGAME}" = "true" ]; then
    CLOCK_APP="pygame_clock.py"
    echo "=========================================="
    echo "Using Pygame renderer (hardware-accelerated)"
    echo "=========================================="
    # Verify pygame is available
    python3 -c "import pygame; print('Pygame version:', pygame.version.ver)" || echo "WARNING: Pygame import failed!"
else
    CLOCK_APP="framebuffer_clock.py"
    echo "=========================================="
    echo "Using PIL framebuffer renderer (current)"
    echo "=========================================="
fi

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


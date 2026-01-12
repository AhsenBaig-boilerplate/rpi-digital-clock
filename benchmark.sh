#!/bin/bash
# Local benchmark script - compares PIL framebuffer vs Pygame approaches

echo "=== Digital Clock Performance Benchmark ==="
echo ""

# Check if pygame is installed
if ! python3 -c "import pygame" 2>/dev/null; then
    echo "Installing pygame..."
    pip3 install pygame
fi

echo "Starting Pygame clock benchmark (30 seconds)..."
timeout 30 python3 app/pygame_clock.py 2>&1 | tee /tmp/pygame_bench.log &
PYGAME_PID=$!

sleep 30
kill $PYGAME_PID 2>/dev/null || true

echo ""
echo "=== Pygame Results ==="
grep "Render timing" /tmp/pygame_bench.log | tail -5

echo ""
echo "=== Current PIL Framebuffer Results ==="
echo "From your logs:"
echo "  Average: 800-1611ms per frame"
echo "  Draw time: 645-1342ms (PIL text rendering)"
echo "  Write time: 123-264ms (framebuffer write)"

echo ""
echo "=== Analysis ==="
echo "Expected Pygame performance: 5-30ms per frame (50-200x faster)"
echo "Pygame uses GPU-accelerated blitting and pre-rendered sprites."

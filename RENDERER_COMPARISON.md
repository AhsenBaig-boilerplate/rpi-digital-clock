# Renderer Performance Comparison

## Quick Test on Pi Zero W

Two renderer implementations are now available:

### 1. PIL Framebuffer (Current - Slow)
- Direct PIL text rendering every frame
- 800-1600ms render time on your device
- High CPU usage

### 2. Pygame with Sprite Cache (New - Fast)
- Pre-rendered character sprites
- GPU-accelerated blitting
- Expected <50ms render time

## How to Test

### Method 1: Toggle via Environment Variable

In Balena Cloud dashboard, set device environment variable:
```
USE_PYGAME=true
```

Restart the service and monitor logs for "Render timing" entries.

### Method 2: Run Comparison Script (SSH)

SSH into device:
```bash
balena ssh <device-uuid>
cd /app
python3 compare_renderers.py
```

This runs both renderers for 60 seconds each and shows comparison.

### Method 3: Quick Manual Test

SSH into device and run directly:
```bash
# Test current PIL version
python3 /app/framebuffer_clock.py
# (Press Ctrl+C after observing timing logs)

# Test Pygame version  
python3 /app/pygame_clock.py
# (Press Ctrl+C after observing timing logs)
```

## Expected Results

**PIL (Current):**
- Render timing: 800-1600ms
- High CPU usage (~38-100%)
- Date artifacts on updates

**Pygame (New):**
- Render timing: <50ms (15-30x faster)
- Low CPU usage (<5%)
- No artifacts (proper sprite caching)

## Architecture Differences

### PIL Approach (Slow)
1. Create new Image(1920x1200) every frame
2. ImageDraw.text() renders 280pt font from scratch
3. Convert RGB888 → RGB565
4. Write full buffer to /dev/fb0

### Pygame Approach (Fast)
1. Pre-render all digits/chars once at startup (0-9, :, A, M, P)
2. Every frame: blit cached sprites from GPU memory
3. SDL2 handles framebuffer writes efficiently
4. Hardware-accelerated on Pi's VideoCore GPU

## Migration Path

If Pygame proves faster on real hardware:
1. Set `USE_PYGAME=true` by default in balena.yml
2. Remove PIL framebuffer code
3. Simplify to single renderer
4. Further optimize sprite cache if needed

## Notes

- Both renderers share same config.yaml
- Both support all features (burn-in, dimming, screensaver)
- Pygame uses Pi's VideoCore GPU automatically
- No X11 required - works on bare framebuffer

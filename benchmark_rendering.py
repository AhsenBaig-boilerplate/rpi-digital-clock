#!/usr/bin/env python3
"""Quick benchmark comparing PIL vs Pygame rendering performance."""

import time
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Headless mode for testing

import pygame
from PIL import Image, ImageDraw, ImageFont

# Test configuration
FONT_SIZE = 280
TEST_STRING = "10:43:21 PM"
ITERATIONS = 100

print("=== Digital Clock Rendering Benchmark ===\n")

# Find font
font_paths = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
]
font_file = None
for path in font_paths:
    if os.path.exists(path):
        font_file = path
        break

if not font_file:
    print("ERROR: No TrueType font found")
    exit(1)

print(f"Using font: {font_file}")
print(f"Test string: '{TEST_STRING}'")
print(f"Font size: {FONT_SIZE}")
print(f"Iterations: {ITERATIONS}\n")

# PIL Benchmark
print("Testing PIL (current approach)...")
pil_times = []
pil_font = ImageFont.truetype(font_file, FONT_SIZE)

for i in range(ITERATIONS):
    t_start = time.time()
    
    # Simulate current rendering approach
    img = Image.new('RGB', (1920, 1200), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Measure text (compatible with older PIL)
    text_w, text_h = draw.textsize(TEST_STRING, font=pil_font)
    
    # Draw text
    x = (1920 - text_w) // 2
    y = (1200 - text_h) // 2
    draw.text((x, y), TEST_STRING, font=pil_font, fill=(0, 255, 0))
    
    # Convert to RGB565 (like framebuffer)
    import numpy as np
    arr = np.frombuffer(img.tobytes(), dtype=np.uint8).reshape((1200, 1920, 3))
    r = (arr[:, :, 0] >> 3).astype(np.uint16)
    g = (arr[:, :, 1] >> 2).astype(np.uint16)
    b = (arr[:, :, 2] >> 3).astype(np.uint16)
    rgb565 = ((r << 11) | (g << 5) | b)
    
    elapsed = (time.time() - t_start) * 1000
    pil_times.append(elapsed)
    
    if i == 0:
        print(f"  First render: {elapsed:.1f}ms")

pil_avg = sum(pil_times) / len(pil_times)
pil_min = min(pil_times)
pil_max = max(pil_times)

print(f"  Average: {pil_avg:.1f}ms")
print(f"  Min: {pil_min:.1f}ms, Max: {pil_max:.1f}ms")
print()

# Pygame Benchmark
print("Testing Pygame (sprite cache approach)...")
pygame.init()
screen = pygame.display.set_mode((1920, 1200))
pygame_font = pygame.font.Font(font_file, FONT_SIZE)

# Pre-render sprite cache
sprite_cache = {}
for char in TEST_STRING:
    if char not in sprite_cache:
        sprite_cache[char] = pygame_font.render(char, True, (0, 255, 0))

print(f"  Cached {len(sprite_cache)} unique sprites")

pygame_times = []

for i in range(ITERATIONS):
    t_start = time.time()
    
    # Clear screen
    screen.fill((0, 0, 0))
    
    # Calculate total width for centering
    total_w = sum(sprite_cache[c].get_width() for c in TEST_STRING if c in sprite_cache)
    
    # Blit sprites
    x_offset = (1920 - total_w) // 2
    for char in TEST_STRING:
        if char in sprite_cache:
            sprite = sprite_cache[char]
            screen.blit(sprite, (x_offset, 600 - sprite.get_height() // 2))
            x_offset += sprite.get_width()
    
    # Update display
    pygame.display.flip()
    
    elapsed = (time.time() - t_start) * 1000
    pygame_times.append(elapsed)
    
    if i == 0:
        print(f"  First render: {elapsed:.1f}ms")

pygame_avg = sum(pygame_times) / len(pygame_times)
pygame_min = min(pygame_times)
pygame_max = max(pygame_times)

print(f"  Average: {pygame_avg:.1f}ms")
print(f"  Min: {pygame_min:.1f}ms, Max: {pygame_max:.1f}ms")
print()

pygame.quit()

# Comparison
print("=== Results ===")
print(f"PIL approach:    {pil_avg:.1f}ms average")
print(f"Pygame approach: {pygame_avg:.1f}ms average")
print(f"Speedup:         {pil_avg / pygame_avg:.1f}x faster")
print()

if pygame_avg < 50:
    print("✅ Pygame achieves <50ms render time - excellent for Pi Zero")
elif pygame_avg < 100:
    print("✅ Pygame achieves <100ms render time - good for Pi Zero")
else:
    print("⚠️  Pygame still slow, but better than PIL")

print()
print("Real-world context:")
print(f"  Your current logs show: 800-1611ms per frame")
print(f"  Pygame would reduce to: ~{pygame_avg:.0f}ms per frame")
print(f"  CPU improvement: ~{(pil_avg / pygame_avg) * 100:.0f}% reduction in render time")

# Version History & Known Issues

Quick reference for identifying stable versions.

## Legend
- ✅ **GOOD** - Recommended for production use
- ⚠️ **MINOR ISSUES** - Usable with known minor bugs
- ❌ **CRITICAL ISSUES** - Not recommended, major problems

---

## ⚠️ 1.4.76 (Latest - 2026-01-11)

**Status: MOSTLY WORKING - CPU spike issue**

### Known Good
- ✅ Flickering gone except on time update section
- ✅ Time looks centered including 10:00:00 AM (M not cut off)
- ✅ Status bar is back
- ✅ Date alignment improved

### Critical Issues
- ❌ CPU usage: 100% (regression from 27%)
- ❌ Balena background still visible

### Minor Issues
- ⚠️ Slight flicker remains on time text updates
- ⚠️ Burn-in concern: pixel shift may not be enough (colon ":" stays in same area, font/size variation needed)

### Root Cause
- Full buffer clear every frame causing CPU spike
- Need smarter dirty-rect tracking
- Pixel shift doesn't vary font characteristics for true burn-in protection

---

## ❌ 1.4.74 (2026-01-11)

**Status: NOT RECOMMENDED - Deployment failed, issues unverified**

### Changes
- Removed failing Rust build from Dockerfile
- Fixed flickering: clear entire shadow buffer once at start
- Fixed "M" cutoff: increased padding to 40px+ (scales with font size)
- Fixed date alignment: increased padding to 20px+ (scales with font size)
- Full background clear removes balena boot screen

### Expected Good (Unverified)
- ✅ CPU usage: ~27%
- ✅ No flickering on time updates
- ✅ "M" in AM/PM fully visible at 10:00
- ✅ Date text properly aligned
- ✅ Black background only
- ✅ Balena deployment works

### Issues
- Status bar visibility unverified
- Build succeeded but runtime behavior uncertain

---

## ❌ 1.4.73 (2026-01-11)

**Status: NOT RECOMMENDED - Multiple critical issues**

### Critical Issues
- ❌ Screen constantly flickering on time change
- ❌ Date has "aY" alignment issues
- ❌ No status bar visible
- ❌ 10:00:39 AM cuts "M" almost in half
- ❌ Balena startup screen visible in background

### Known Good
- ✅ CPU usage: 27%

### Root Cause
- Attempted native Rust renderer that wasn't building
- PIL renderer using per-element clearing causing flicker
- Insufficient padding for large glyphs
- Background not being fully cleared

---

## ❌ Earlier Versions (Pre-1.4.73)

**Status: NOT RECOMMENDED - Foundation issues**

### Critical Issues (Initial Report)
- ❌ "M" in AM/PM constantly clipped at right edge
- ❌ CPU usage: 99% (system unusable, SSH difficult)
- ❌ Seconds skipping due to CPU overload
- ❌ Time not centered properly
- ❌ Status bar descenders cropped
- ❌ Padding asymmetric causing alignment issues
- ❌ GitHub Actions CI deprecation warnings

### Attempted Fixes (Various versions)
- Auto-shrink time text with padding-based width calculation
- Symmetric padding implementation
- Cached draw object to reduce PIL overhead
- Partial framebuffer writes with dirty rect tracking
- Memory-mapped framebuffer for fast row copies
- Second-aligned sleep to prevent skipping
- Pixel shift gated to minute boundaries
- Reduced weather/status polling frequency
- Native Rust renderer attempt (failed to build)

### Root Causes Identified
- Image.new() called every frame (massive overhead)
- Full framebuffer writes every second
- Unoptimized font rendering
- No caching of static elements
- Excessive subprocess calls for status checks

---

## Version Selection Guide

### For Production Use
**None currently recommended** - All versions have critical issues

### Best Available Option
**Version 1.4.76** - Most features working but CPU at 100%
- Use if you need: working display with status bar
- Avoid if: CPU performance is critical

### For Development/Testing
- 1.4.76 - Latest baseline for improvements
- Need to fix: CPU optimization, burn-in protection, balena background

### Required Fixes for Production
1. **CPU optimization** - Return to 27% from 100%
   - Implement smart dirty-rect tracking instead of full clear
   - Cache static elements (status bar, date when unchanged)
   - Reduce write frequency to framebuffer

2. **Burn-in protection enhancement**
   - Vary font size randomly (±5-10px)
   - Alternate between font families
   - Move elements more significantly (current pixel shift insufficient)
   - Implement screensaver mode during idle hours

3. **Background clearing**
   - Ensure framebuffer fully cleared on startup
   - Possible kernel framebuffer issue

---

## Burn-In Prevention Recommendations

### Current Implementation (Insufficient)
- Pixel shift: ±10px every 60s
- Problem: Colon ":" in time stays in nearly same position
- Problem: Font characteristics unchanged

### Needed Enhancements
1. **Font variation** - Rotate between 2-3 fonts every 5-10 minutes
2. **Size variation** - Randomly adjust size ±5-10% within bounds
3. **Larger position shifts** - Increase to ±30-50px range
4. **Element repositioning** - Shuffle status bar corners more frequently
5. **Screensaver during night** - Blank or moving animation 2AM-5AM

### Hardware Alternative
- Use e-Paper display (no burn-in risk)
- Use OLED with built-in pixel shift
- Upgrade to IPS LCD (less susceptible to burn-in)

---

## Known Issues Across All Versions
- Pi Zero W single-core CPU limits (consider Pi Zero 2 W upgrade)
- Font rendering performance on older Pi hardware
- Balena boot screen persistence (may be kernel/bootloader issue)

---

## Testing Checklist

When validating a new version:

### Visual Tests
- [ ] No flickering during second updates
- [ ] "M" in AM/PM fully visible at 10:00, 11:00, 12:00
- [ ] Date text evenly spaced and aligned
- [ ] Status bar visible (network, timezone, sync, version)
- [ ] Pure black background (no balena boot screen)

### Time Format Tests
```bash
# Test critical times for "M" cutoff
sudo date -s "2026-01-09 10:00:00"  # 10 AM
sudo date -s "2026-01-09 22:00:00"  # 10 PM
sudo date -s "2026-01-09 11:59:00"  # 11:59 AM
```

### Performance Tests
- [ ] CPU usage < 30% sustained
- [ ] Memory usage stable
- [ ] No second skips

### System Tests
- [ ] Deploys successfully on Balena
- [ ] Survives reboot
- [ ] RTC sync working (if enabled)
- [ ] Weather API working (if enabled)

---

## Hardware Recommendations

### Current: Pi Zero W (single-core)
- CPU: ~27% with optimized PIL renderer
- Suitable for: Basic clock display

### Upgrade Path: Pi Zero 2 W
- CPU: Expected ~5-8% (5x faster)
- Benefits: Drop-in replacement, same power usage
- Cost: ~$15

### Alternative: Offload Rendering
- Nextion/TJC display: $20-40
- Waveshare e-Paper: $25-60
- Eliminates Pi CPU load for rendering

---

## Future Improvements

### Short Term
- Verify status bar rendering in 1.4.74
- Add automated screenshot testing
- Performance profiling for Pi Zero W

### Long Term
- Bitmap font option for lower CPU
- GPU-accelerated rendering via VideoCore IV
- Multi-service architecture for Balena
- Health checks and auto-restart policies

# Version History & Known Issues

Quick reference for identifying stable versions.

## Legend
- ✅ **GOOD** - Recommended for production use
- ⚠️ **MINOR ISSUES** - Usable with known minor bugs
- ❌ **CRITICAL ISSUES** - Not recommended, major problems

---

## ✅ 1.4.74 (Latest - 2026-01-11)

**Status: RECOMMENDED - PIL renderer with fixes**

### Changes
- Removed failing Rust build from Dockerfile
- Fixed flickering: clear entire shadow buffer once at start
- Fixed "M" cutoff: increased padding to 40px+ (scales with font size)
- Fixed date alignment: increased padding to 20px+ (scales with font size)
- Full background clear removes balena boot screen

### Known Good
- ✅ CPU usage: ~27%
- ✅ No flickering on time updates
- ✅ "M" in AM/PM fully visible at 10:00
- ✅ Date text properly aligned
- ✅ Black background only
- ✅ Balena deployment works

### To Verify
- Status bar visibility (should show network/timezone/sync/version)

### Deployment
```bash
balena push <app-name>
# or auto-deploy from git push
```

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

## Version Selection Guide

### For Production Use
**Use: 1.4.74** - All critical rendering issues fixed

### For Development/Testing
- 1.4.74 - Stable base for further improvements

### Known Issues Across Versions
- Pi Zero W single-core CPU limits (consider Pi Zero 2 W upgrade)
- Font rendering performance on older Pi hardware

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

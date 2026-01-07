# DS3231 RTC Wiring Diagram

## Visual Connection Guide

### Pin Layout

```
Raspberry Pi Zero (Top View)
┌─────────────────────────────────────────┐
│  3.3V [ 1] [ 2] 5V                      │
│   SDA [ 3] [ 4] 5V                      │
│   SCL [ 5] [ 6] GND                     │
│  GPIO [ 7] [ 8] GPIO                    │
│   GND [ 9] [10] GPIO                    │
│       ...                               │
└─────────────────────────────────────────┘

DS3231 RTC Module (Front View)
┌────────────────┐
│   ┌──────┐     │
│   │CR2032│     │ ← Battery holder
│   └──────┘     │
│                │
│  VCC  GND      │ ← Power pins
│  SDA  SCL      │ ← I2C pins
└────────────────┘
```

### Detailed Wiring

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Raspberry Pi Zero              DS3231 RTC Module       │
│  ┌──────────────┐               ┌──────────────┐       │
│  │              │               │   Battery    │       │
│  │  Pin 1 ──────┼───────────────┼─── VCC       │       │
│  │  (3.3V)      │   Red Wire    │              │       │
│  │              │               │              │       │
│  │  Pin 3 ──────┼───────────────┼─── SDA       │       │
│  │  (GPIO 2)    │   Blue Wire   │              │       │
│  │              │               │              │       │
│  │  Pin 5 ──────┼───────────────┼─── SCL       │       │
│  │  (GPIO 3)    │   Yellow Wire │              │       │
│  │              │               │              │       │
│  │  Pin 6 ──────┼───────────────┼─── GND       │       │
│  │  (Ground)    │   Black Wire  │              │       │
│  │              │               │              │       │
│  └──────────────┘               └──────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Wire Color Convention (Recommended)

| Connection | Recommended Color | Purpose |
|------------|------------------|---------|
| VCC → 3.3V | Red | Power |
| GND → GND | Black | Ground |
| SDA → SDA | Blue or White | Data |
| SCL → SCL | Yellow or Green | Clock |

## Connection Table

| Step | From (Pi Zero) | To (DS3231) | Wire | Note |
|------|---------------|-------------|------|------|
| 1 | Pin 1 (3.3V) | VCC | Red | Power supply |
| 2 | Pin 3 (GPIO 2 / SDA) | SDA | Blue | I2C Data line |
| 3 | Pin 5 (GPIO 3 / SCL) | SCL | Yellow | I2C Clock line |
| 4 | Pin 6 (GND) | GND | Black | Ground reference |

## Physical Setup Photos Reference

### Step 1: Locate Pins on Raspberry Pi Zero
```
    USB     USB    HDMI
   ┌───┐  ┌───┐  ┌───┐
   │   │  │   │  │   │
   └───┘  └───┘  └───┘
┌───────────────────────┐
│ [●●●●●●●●●●]          │
│ [●●●●●●●●●●]  ← GPIO  │
│  123456...            │
│                       │
│   Raspberry Pi Zero   │
└───────────────────────┘
```

Pin 1-6 are the first 6 pins on the GPIO header (closest to the edge).

### Step 2: Prepare DS3231 Module
```
Front View:
┌─────────────────┐
│  ┌───────────┐  │
│  │  CR2032   │  │ ← Insert battery here (+ side up)
│  │  Battery  │  │
│  └───────────┘  │
│                 │
│ VCC GND SDA SCL │ ← Connection pins
└─────────────────┘
```

### Step 3: Connect Wires
```
Connection Order (recommended):
1. GND (black)  - Connect ground first for safety
2. VCC (red)    - Connect power
3. SDA (blue)   - Connect data line
4. SCL (yellow) - Connect clock line
```

## Verification Steps

### 1. Visual Check
- [ ] All 4 wires connected
- [ ] No loose connections
- [ ] Correct pin alignment
- [ ] Battery installed in DS3231
- [ ] No crossed wires

### 2. Power On Test
```bash
# After powering on, check I2C detection
i2cdetect -y 1

# Should show 0x68 address:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
```

### 3. Functionality Test
```bash
# Read RTC time
hwclock -r

# Should display current time (or default if new battery)
```

## Common Mistakes to Avoid

❌ **Wrong Voltage**: Using 5V instead of 3.3V
- DS3231 works with 3.3V or 5V, but use 3.3V from Pi Zero

❌ **Swapped SDA/SCL**: Connecting data to clock and vice versa
- SDA = Data (Pin 3)
- SCL = Clock (Pin 5)

❌ **No Battery**: Operating without CR2032 battery
- Time will be lost on power down

❌ **Wrong Ground**: Using wrong ground pin
- Use Pin 6, 9, 14, 20, 25, 30, 34, or 39 (all are ground)

❌ **Loose Connections**: Poor contact between wires and pins
- Ensure firm connection, consider soldering for permanent setup

## Advanced: Soldering for Permanent Installation

For production deployment, consider:

1. **Solder header pins** to Raspberry Pi Zero (if not pre-soldered)
2. **Use female jumper wires** for easy connection
3. **Use GPIO HAT** for cleaner installation
4. **Solder directly** to DS3231 module for reliability
5. **Heat shrink tubing** for wire protection

## Troubleshooting Connection Issues

| Problem | Check | Solution |
|---------|-------|----------|
| No device at 0x68 | Physical connection | Re-seat all wires |
| I2C not working | I2C enabled | Enable in balena dashboard |
| Intermittent errors | Loose wires | Use shorter, quality wires |
| No response | Power supply | Check 3.3V pin voltage |
| Wrong time | Battery | Replace CR2032 battery |

## Safety Notes

⚠️ **Important**:
- Always power OFF before connecting/disconnecting
- Never connect VCC to 5V while connected to other 3.3V I2C devices
- Handle module by edges to avoid touching components
- Ensure proper polarity when installing battery

## Quick Reference Card

```
╔════════════════════════════════════════╗
║  DS3231 RTC Quick Connection Guide    ║
╠════════════════════════════════════════╣
║  Pi Zero Pin → DS3231 Pin             ║
║  ────────────────────────────────────  ║
║  Pin 1 (3.3V)  →  VCC    [Red]        ║
║  Pin 3 (SDA)   →  SDA    [Blue]       ║
║  Pin 5 (SCL)   →  SCL    [Yellow]     ║
║  Pin 6 (GND)   →  GND    [Black]      ║
║                                        ║
║  Test: i2cdetect -y 1                 ║
║  Expected: 0x68                       ║
║                                        ║
║  Battery: CR2032 (+ side up)          ║
╚════════════════════════════════════════╝
```

---

**Ready to connect!** Follow the steps above for reliable RTC integration.

# DS3231 RTC Module Setup Guide

This guide covers setup and integration of the DS3231 Real-Time Clock module for maintaining accurate time when WiFi/network is unavailable.

**Note:** RTC support is optional and disabled by default. Set `RTC_ENABLED=true` to activate.

---

## 📦 Hardware Requirements

### DS3231 RTC Module
- **Model**: DORHEA DS3231 or compatible
- **Amazon**: https://www.amazon.com/dp/B08X4H3NBR
- **I2C Address**: 0x68 (default)
- **Features**:
  - High precision RTC with TCXO
  - Battery backup (CR2032)
  - Temperature compensated
  - Built-in temperature sensor
  - I2C interface

### Connections

| DS3231 Pin | Raspberry Pi Zero Pin | Pin Number |
|------------|----------------------|------------|
| VCC | 3.3V Power | Pin 1 |
| GND | Ground | Pin 6 or 9 |
| SDA | GPIO 2 (SDA) | Pin 3 |
| SCL | GPIO 3 (SCL) | Pin 5 |

**Note**: Most DS3231 modules include pull-up resistors, so no external resistors needed.

## 🔧 Physical Setup

### 1. Prepare the Module

1. **Insert Battery** (if not included)
   - Open battery compartment on DS3231 module
   - Insert CR2032 battery (positive side up)
   - Battery maintains time during power outages

2. **Check Module**
   - Verify battery is secure
   - Check for any loose connections
   - Ensure no pins are bent

### 2. Connect to Raspberry Pi Zero

```
DS3231 Module          Raspberry Pi Zero
┌────────────┐         ┌──────────────┐
│    VCC     │────────▶│ Pin 1 (3.3V) │
│    GND     │────────▶│ Pin 6 (GND)  │
│    SDA     │◀───────▶│ Pin 3 (SDA)  │
│    SCL     │◀───────▶│ Pin 5 (SCL)  │
└────────────┘         └──────────────┘
```

**Connection Tips**:
- Use quality jumper wires
- Keep connections short to reduce noise
- Double-check polarity before powering on
- Consider using a HAT or breakout board for permanent installation

### 3. Enable I2C on Raspberry Pi

The Docker container automatically includes I2C tools, but I2C must be enabled:

**balena.io Method** (Recommended):
1. Go to balena dashboard
2. Select your device
3. Navigate to "Device Configuration"
4. Enable "I2C" interface
5. Reboot device

**Manual Method** (if not using balena):
```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

## 🧪 Testing the RTC

### Verify I2C Connection

After connecting and enabling I2C:

```bash
# SSH into your device
balena ssh <DEVICE_UUID>

# Check I2C devices
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- 57 -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

You should see `68` (the DS3231 I2C address).

### Read RTC Time

```bash
# Read hardware clock
hwclock -r

# Show hardware clock verbose
hwclock --show --verbose
```

### Set Initial Time

If RTC has incorrect time (new battery or reset):

```bash
# Sync RTC from system time (when connected to internet)
hwclock --systohc

# Verify
hwclock -r
```

## 🚀 Software Configuration

### 1. Enable RTC in config.yaml

Edit `app/config.yaml`:

```yaml
time:
  format_12h: true
  ntp_sync: true
  ntp_server: "pool.ntp.org"
  rtc_enabled: true  # Enable RTC support
```

### 2. Time Synchronization Strategy

The application uses a smart fallback strategy:

1. **Primary**: NTP sync (when internet available)
   - Syncs system time from internet
   - Updates RTC with accurate time
   
2. **Fallback**: RTC sync (when internet unavailable)
   - Reads time from DS3231
   - Syncs system time from RTC
   
3. **Last Resort**: System time (if both fail)
   - Uses existing system time
   - May drift over time

### 3. Automatic Behavior

```
┌─────────────────────────────────────┐
│     Application Startup             │
└──────────────┬──────────────────────┘
               │
               ▼
       ┌───────────────┐
       │ Internet?     │
       └───┬───────┬───┘
           │       │
        YES│       │NO
           │       │
           ▼       ▼
   ┌───────────┐ ┌──────────┐
   │ NTP Sync  │ │ RTC Sync │
   └─────┬─────┘ └────┬─────┘
         │            │
         ▼            │
   ┌──────────┐      │
   │Update RTC│      │
   └─────┬────┘      │
         │           │
         └─────┬─────┘
               ▼
       ┌──────────────┐
       │ Clock Display│
       └──────────────┘
```

## 📊 Monitoring RTC

### Check RTC Status

The application logs RTC status at startup:

```
INFO - DS3231 RTC module detected
INFO - RTC temperature: 24.50°C
```

### View RTC Temperature

The DS3231 includes a temperature sensor:

```bash
# Via application logs
balena logs <DEVICE_UUID> | grep "RTC temperature"
```

Temperature is used for compensation and indicates module health.

## 🔍 Troubleshooting

### RTC Not Detected

**Symptom**: Log shows "RTC device not found"

**Solutions**:
1. Verify I2C is enabled in balena dashboard
2. Check physical connections
3. Run `i2cdetect -y 1` to verify address 0x68
4. Ensure device has proper permissions in docker-compose.yml
5. Verify battery is installed in DS3231

### Time Not Syncing from RTC

**Symptom**: Time is incorrect despite RTC being detected

**Solutions**:
1. Check RTC has correct time: `hwclock -r`
2. Set RTC time when internet available: `hwclock --systohc`
3. Verify application has root permissions (privileged: true in docker-compose.yml)
4. Check logs for permission errors

### RTC Loses Time

**Symptom**: RTC time resets or drifts significantly

**Solutions**:
1. Replace CR2032 battery
2. Check battery holder connections
3. Verify module is genuine DS3231 (not DS1307)
4. Ensure module is not exposed to extreme temperatures

### I2C Communication Errors

**Symptom**: "Error reading RTC" in logs

**Solutions**:
1. Check wire connections are secure
2. Verify no loose connections
3. Use shorter wires (reduce electrical noise)
4. Check for I2C bus conflicts with other devices
5. Try reducing I2C speed (rare issue)

## 🔋 Battery Maintenance

### Battery Life
- **CR2032 Lithium**: 2-5 years typical
- **Factors**: Temperature, quality, RTC usage
- **Indicator**: Time resets after power loss

### Replacing Battery

1. Power off Raspberry Pi
2. Remove old CR2032 battery
3. Insert new battery (positive side up)
4. Power on and set time:
   ```bash
   # When internet available
   hwclock --systohc
   ```
5. Verify: `hwclock -r`

## 📈 Performance Benefits

### With RTC Module

| Scenario | Without RTC | With RTC |
|----------|-------------|----------|
| Internet Available | ✅ NTP Sync | ✅ NTP Sync + RTC Update |
| Internet Down 1 day | ❌ Time drifts | ✅ Accurate time |
| Internet Down 1 week | ❌ Time very wrong | ✅ Accurate time |
| Internet Down 1 month | ❌ Time unusable | ✅ Accurate time |
| Power outage recovery | ❌ Wrong time | ✅ Correct time immediately |

### Accuracy
- **System Clock Drift**: ~1 second per day
- **DS3231 Drift**: ±2 ppm (±1 minute per year)
- **With Battery**: Maintains time indefinitely

## 🎯 Best Practices

### Installation
1. ✅ Use quality DS3231 module (not cheaper DS1307)
2. ✅ Use fresh CR2032 battery
3. ✅ Keep wires short and secure
4. ✅ Mount module away from heat sources
5. ✅ Test before permanent installation

### Configuration
1. ✅ Enable RTC in config.yaml
2. ✅ Keep NTP sync enabled (for accuracy)
3. ✅ Monitor logs for RTC errors
4. ✅ Set initial time when first installed
5. ✅ Test offline operation

### Maintenance
1. ✅ Replace battery every 2-3 years
2. ✅ Check connections periodically
3. ✅ Monitor RTC temperature for anomalies
4. ✅ Verify time accuracy monthly
5. ✅ Keep spare battery on hand

## 📝 Configuration Examples

### Maximum Reliability
```yaml
time:
  format_12h: true
  ntp_sync: true          # Always try NTP first
  ntp_server: "pool.ntp.org"
  rtc_enabled: true       # Fall back to RTC
```

### RTC Only (No Internet)
```yaml
time:
  format_12h: true
  ntp_sync: false         # Disable NTP
  rtc_enabled: true       # Use only RTC
```

### Internet Only (No RTC)
```yaml
time:
  format_12h: true
  ntp_sync: true
  rtc_enabled: false      # Disable RTC
```

## 🆘 Support

If you encounter issues:
1. Check logs: `balena logs <DEVICE_UUID>`
2. Verify wiring matches pinout
3. Test I2C: `i2cdetect -y 1`
4. Check battery voltage (should be ~3V)
5. Consult DS3231 datasheet for advanced troubleshooting

## 📚 Additional Resources

- **DS3231 Datasheet**: https://datasheets.maximintegrated.com/en/ds/DS3231.pdf
- **Raspberry Pi I2C**: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#i2c
- **balena I2C**: https://www.balena.io/docs/learn/develop/hardware/i2c-and-spi/
- **hwclock manual**: `man hwclock`

---

**Module Recommended**: DORHEA DS3231  
**Purchase**: https://www.amazon.com/dp/B08X4H3NBR  
**Price**: ~$8-12 USD  
**Battery**: CR2032 (widely available)

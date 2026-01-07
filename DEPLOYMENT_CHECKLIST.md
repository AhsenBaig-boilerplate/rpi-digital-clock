# Deployment Checklist

Use this checklist to ensure a smooth deployment of your Raspberry Pi Digital Clock.

## ☑️ Pre-Deployment

### Hardware Setup
- [ ] Raspberry Pi Zero (1st gen) ready
- [ ] MicroSD card (8GB+) available
- [ ] Mini HDMI to HDMI cable acquired
- [ ] Quality power supply (5V 2A minimum)
- [ ] TV with available HDMI input
- [ ] Internet connection available (WiFi or Ethernet adapter)

### Account Setup
- [ ] Created free balena.io account
- [ ] Created free OpenWeatherMap account
- [ ] Obtained OpenWeatherMap API key (activated)
- [ ] Verified API key works (test at openweathermap.org)

### Software Prerequisites
- [ ] Installed balena CLI on computer
- [ ] Installed balenaEtcher for flashing SD cards
- [ ] Logged into balena CLI: `balena login`
- [ ] Git installed (for code deployment)

## ☑️ balena Application Setup

### Create Application
- [ ] Logged into balena dashboard
- [ ] Created new application
- [ ] Selected device type: Raspberry Pi (v1 / Zero / Zero W)
- [ ] Named application (e.g., "rpi-digital-clock")
- [ ] Noted application name for CLI commands

### Add Device
- [ ] Clicked "Add device" in application
- [ ] Selected WiFi configuration (if applicable)
- [ ] Entered WiFi credentials
- [ ] Downloaded balenaOS image
- [ ] Verified download completed successfully

### Flash Device
- [ ] Inserted SD card into computer
- [ ] Opened balenaEtcher
- [ ] Selected downloaded balenaOS image
- [ ] Selected SD card as target
- [ ] Flashed image to SD card
- [ ] Verified flash completed successfully
- [ ] Safely ejected SD card

## ☑️ Configuration

### Environment Variables
In balena dashboard, add these variables:

- [ ] `WEATHER_API_KEY` = (your OpenWeatherMap API key)
- [ ] `WEATHER_LOCATION` = (your city, e.g., "New York,US")
- [ ] `LOG_LEVEL` = INFO (or DEBUG for troubleshooting)

### Configuration File (Optional)
If customizing beyond defaults:

- [ ] Reviewed `app/config.yaml`
- [ ] Adjusted time format (12/24 hour)
- [ ] Set preferred colors
- [ ] Configured font sizes
- [ ] Set burn-in prevention preferences
- [ ] Configured night dimming hours
- [ ] Selected date format

## ☑️ Code Deployment

### Repository Setup
- [ ] Cloned repository or created from scratch
- [ ] Reviewed all configuration files
- [ ] Verified `requirements.txt` is present
- [ ] Verified `Dockerfile.template` is present
- [ ] Verified `docker-compose.yml` is present

### Deploy to balena
Choose one method:

**Method A: balena CLI**
- [ ] Navigated to project directory in terminal
- [ ] Ran: `balena push YOUR_APP_NAME`
- [ ] Waited for build to complete (10-20 minutes first time)
- [ ] Verified "Successfully built" message

**Method B: Git Remote**
- [ ] Added balena git remote
- [ ] Ran: `git push balena main`
- [ ] Waited for build to complete
- [ ] Verified successful deployment

## ☑️ Device Setup

### Physical Installation
- [ ] Inserted flashed SD card into Raspberry Pi
- [ ] Connected Mini HDMI cable to Pi
- [ ] Connected HDMI cable to TV
- [ ] Connected power supply to Pi
- [ ] Powered on Raspberry Pi

### Initial Boot
- [ ] Waited for device to boot (2-3 minutes)
- [ ] Verified device appears in balena dashboard
- [ ] Checked device status is "Online"
- [ ] Verified application is downloading/installing

## ☑️ Verification

### balena Dashboard Checks
- [ ] Device showing as "Online"
- [ ] Application status is "Running"
- [ ] No error messages in logs
- [ ] Environment variables correctly set
- [ ] Device metrics showing normal CPU/memory

### Display Checks
- [ ] Turned on TV
- [ ] Selected correct HDMI input
- [ ] Clock display visible on TV
- [ ] Time showing correctly
- [ ] Date displaying properly
- [ ] Weather information visible (if enabled)
- [ ] Display is centered and properly sized

### Functionality Tests
- [ ] Time updates every second/minute as configured
- [ ] Weather updates periodically
- [ ] No errors in balena logs
- [ ] Display color is as expected
- [ ] Font size is readable from viewing distance

## ☑️ Burn-in Prevention Verification

### Test Screensaver (if enabled)
- [ ] Noted screensaver delay setting
- [ ] Waited for screensaver activation
- [ ] Verified screen blanked as expected
- [ ] Touched keyboard/mouse to wake (if accessible)
- [ ] Verified display restored

### Test Pixel Shift (if enabled)
- [ ] Observed display for pixel shift interval
- [ ] Noted subtle position changes
- [ ] Verified shift is not too jarring
- [ ] Adjusted interval if needed

### Test Night Dimming (if enabled)
- [ ] Checked night hour configuration
- [ ] Waited until night hours (or adjusted for testing)
- [ ] Verified display dimmed as expected
- [ ] Verified brightness restored in morning

## ☑️ Post-Deployment

### Documentation
- [ ] Noted device UUID for reference
- [ ] Saved balena application URL
- [ ] Documented any custom configurations
- [ ] Created backup of config.yaml
- [ ] Noted WiFi credentials used

### Monitoring Setup
- [ ] Bookmarked balena dashboard
- [ ] Setup email notifications (optional)
- [ ] Tested SSH access if needed
- [ ] Verified can access logs remotely

### Optimization (Optional)
- [ ] Measured viewing distance
- [ ] Adjusted font sizes if needed
- [ ] Tweaked colors for room lighting
- [ ] Optimized screensaver timing
- [ ] Adjusted night dimming hours
- [ ] Fine-tuned pixel shift interval

## ☑️ Final Checks

### 24-Hour Test
- [ ] Device ran for 24 hours without issues
- [ ] No crashes or restarts
- [ ] Weather updated correctly
- [ ] Time stayed accurate
- [ ] Burn-in prevention features working
- [ ] No overheating issues

### Stability Verification
- [ ] Checked logs for any errors
- [ ] Verified memory usage stable
- [ ] Confirmed CPU usage reasonable
- [ ] Tested power interruption recovery
- [ ] Verified auto-restart on failure

## ☑️ Maintenance Plan

### Regular Checks
- [ ] Weekly log review scheduled
- [ ] Monthly configuration review
- [ ] Quarterly update check
- [ ] Annual hardware inspection

### Update Strategy
- [ ] Decided on update frequency
- [ ] Tested updates in staging (if applicable)
- [ ] Documented update procedure
- [ ] Setup backup/rollback plan

## 🎉 Deployment Complete!

- [ ] All checks passed
- [ ] Clock displaying correctly
- [ ] Documentation complete
- [ ] Stakeholders notified (if applicable)
- [ ] Ready for production use

---

## 📝 Notes

Use this section to record any deployment-specific information:

**Device UUID:** ________________________________

**Application Name:** ________________________________

**Deployment Date:** ________________________________

**Custom Settings:**
- 
- 
- 

**Issues Encountered:**
- 
- 
- 

**Resolutions:**
- 
- 
- 

---

## 🆘 Troubleshooting Reference

If issues arise, refer to:
1. README.md - Troubleshooting section
2. QUICK_REFERENCE.md - Common fixes
3. balena logs - Error messages
4. OpenWeatherMap API status

---

**Pro Tip:** Keep this checklist for future deployments or device additions!

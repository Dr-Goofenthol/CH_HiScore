# Changelog - v2.4.11

## Release Date
November 26, 2025

## Summary

Version 2.4.11 brings **matched version numbers** across both client and bot, along with security and UX improvements for debug mode password handling.

## Changes

### Client Updates

**Hidden Debug Password Input**

When entering debug mode, the password is now hidden from view for better security.

- **What Changed**: Password input now uses `getpass` module
- **User Experience**: Password is completely hidden while typing (no asterisks visible)
- **Security**: Prevents shoulder-surfing and accidental exposure

**Files Modified:**
- `clone_hero_client.py` - Added `import getpass` and changed `input()` to `getpass.getpass()`

**Version Update:**
- Client: `2.4.9` → `2.4.11`

---

### Bot Launcher Enhancement

**Added Debug Password to First-Time Setup**

Users can now set their debug password during the bot's first-time setup wizard, instead of it defaulting to `admin123`.

#### What Changed:

1. **New Setup Step (Step 5)**: Client Debug Password
   - Users can set a custom password
   - Defaults to `admin123` if left blank
   - Security tip shown for public bots
   - Password is masked in configuration summary

2. **Environment Variable**: `DEBUG_PASSWORD` now passed from launcher config to bot

3. **User-Facing Benefits**:
   - More secure: Users can choose strong passwords
   - Better UX: No need to manually edit .env files
   - Clear setup: Users understand what the password is for

#### Files Modified:
- `bot_launcher.py` - Added Debug Password step to setup wizard
  - Updated welcome instructions to mention debug password
  - Added Step 5: Debug Password input
  - Updated configuration summary to show masked password
  - Updated `setup_environment()` to pass DEBUG_PASSWORD to bot

#### Version Update:
- Bot Launcher: `2.4.10` → `2.4.11`

#### Backwards Compatibility:
- ✅ Fully backwards compatible
- Existing configs without DEBUG_PASSWORD will default to `admin123`
- No migration required

---

## What is the Debug Password?

The debug password is required when clients want to enter **debug mode**. Debug mode allows:
- Testing score submissions with `send_test_score`
- Testing OCR functionality with `testocr`
- Viewing system information
- Other debugging features

**Security Note:** If your bot server is publicly accessible, use a strong debug password to prevent unauthorized access to debug features.

---

## User Instructions

### For New Users:
During first-time setup (Step 5), you'll be prompted to enter a debug password:

```
--------------------------------------------------
STEP 5: Client Debug Password
--------------------------------------------------
This password is required when clients want to enter debug mode.
Debug mode allows testing features like sending test scores.

Security tip: Use a strong password if your bot is public!

Enter debug password [admin123]:
```

- Enter a custom password, or
- Press Enter to use the default (`admin123`)

### For Existing Users:

**Option 1: Edit Config Manually**
1. Navigate to: `%APPDATA%\CloneHeroScoreBot\bot_config.json`
2. Add this line:
   ```json
   "DEBUG_PASSWORD": "your_custom_password_here",
   ```
3. Save and restart the bot

**Option 2: Re-run Setup**
1. Delete: `%APPDATA%\CloneHeroScoreBot\bot_config.json`
2. Run `CloneHeroScoreBot_v2.4.11.exe`
3. Complete the setup wizard with your custom password

---

## Configuration Summary Example

After setup, users will see:

```
==============================================================
CONFIGURATION SUMMARY
==============================================================
  Discord App ID: 1441222250023092304
  Discord Token: ********************...
  Guild ID: 1441226499989573774 (fast command sync)
  Channel ID: 1441226539768352768
  Debug Password: **********
  API Port: 8080
==============================================================
```

---

## Complete Setup Flow (v2.4.11)

1. **STEP 1**: Discord Bot Token
2. **STEP 2**: Discord Application ID
3. **STEP 3**: Discord Server ID (Guild ID) - OPTIONAL *(added in v2.4.10)*
4. **STEP 4**: Announcement Channel ID
5. **STEP 5**: Client Debug Password *(NEW in v2.4.11)*
6. **STEP 6**: API Port
7. **STEP 7**: External URL (Optional)

---

## Build Information

**Built with:**
- Python 3.14.0
- PyInstaller 6.16.0
- Colorama 0.4.6 (with hiddenimports fix from v2.4.9)

**Output:**
- `dist/CloneHeroScoreTracker_v2.4.11.exe` (~19 MB) - Client with hidden password input
- `dist/CloneHeroScoreBot_v2.4.11.exe` (~14 MB) - Bot with debug password in setup

**Both executables updated** - Version numbers now match at v2.4.11

---

## Version History

- v2.4.9: Added colored console output, /server_status command, debug menu enhancements
- v2.4.10: Added Guild ID to setup wizard for fast command sync
- v2.4.11: Added Debug Password to setup wizard for better security

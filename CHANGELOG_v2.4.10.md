# Changelog - v2.4.10

## Release Date
November 26, 2025

## Changes

### Bot Launcher Enhancement

**Added Guild ID (Server ID) to First-Time Setup**

Users can now optionally provide their Discord Server ID (Guild ID) during the bot's first-time setup wizard. This significantly improves the Discord slash command sync experience.

#### What Changed:

1. **New Setup Step (Step 3)**: Discord Server ID (Guild ID) - OPTIONAL
   - Clear explanation of why it matters
   - Instructions on how to find it (right-click server icon > Copy Server ID)
   - Can be skipped if user prefers global sync

2. **Environment Variable**: `DISCORD_GUILD_ID` now passed from launcher config to bot

3. **User-Facing Benefits**:
   - **WITH Guild ID**: New slash commands appear **instantly** after bot restart
   - **WITHOUT Guild ID**: New slash commands take **up to 1 hour** to appear (global sync)

#### Files Modified:
- `bot_launcher.py` - Added Guild ID step to setup wizard
  - Updated welcome instructions
  - Added Step 3: Guild ID input (optional)
  - Updated configuration summary to show Guild ID status
  - Updated `setup_environment()` to pass Guild ID to bot
  - Updated startup config display

#### Version Update:
- Bot Launcher: `2.4.9` → `2.4.10`

#### Backwards Compatibility:
- ✅ Fully backwards compatible
- Existing configs without Guild ID continue to work (global sync)
- No migration required

---

## Why This Matters

Previously, users had to manually edit config files or wait up to 1 hour for new Discord commands to appear. Now the setup wizard makes it easy to configure fast command sync from the start.

**Example: When `/server_status` was added in v2.4.9:**
- Users WITHOUT Guild ID: Had to wait up to 1 hour for command to appear
- Users WITH Guild ID: Command appears immediately after bot restart

---

## User Instructions

### For New Users:
During first-time setup, you'll be prompted to enter your Guild ID (Step 3). It's optional but **highly recommended** for faster command updates.

**How to get your Guild ID:**
1. In Discord, go to Settings > Advanced
2. Enable "Developer Mode"
3. Right-click your server icon in the server list
4. Click "Copy Server ID"
5. Paste this when prompted during setup

### For Existing Users:
To add Guild ID to an existing installation:

**Option 1: Edit Config Manually**
1. Navigate to: `%APPDATA%\CloneHeroScoreBot\bot_config.json`
2. Add this line after the Application ID line:
   ```json
   "DISCORD_GUILD_ID": "your_server_id_here",
   ```
3. Save and restart the bot

**Option 2: Re-run Setup**
1. Delete: `%APPDATA%\CloneHeroScoreBot\bot_config.json`
2. Run `CloneHeroScoreBot_v2.4.10.exe`
3. Complete the setup wizard with Guild ID this time

---

## Technical Notes

The Guild ID is used by Discord.py's command tree sync feature:
- If `DISCORD_GUILD_ID` is set: Commands sync to that specific guild (fast)
- If not set: Commands sync globally to all guilds (slow, up to 1 hour)

This is not a bug or limitation of the bot - it's how Discord's slash command system works.

---

## Build Information

**Built with:**
- Python 3.14.0
- PyInstaller 6.16.0
- Colorama 0.4.6 (with hiddenimports fix from v2.4.9)

**Output:**
- `dist/CloneHeroScoreBot_v2.4.10.exe` (~13.3 MB)

**No changes to client executable** - still using v2.4.9

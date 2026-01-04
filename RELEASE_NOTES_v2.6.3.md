# Clone Hero Score Tracker - Release Notes v2.6.3

**Release Date:** January 4, 2026

## Overview

Version 2.6.3 focuses on improving username handling and fixing critical bugs that affected bot stability. This release ensures usernames always stay current when users change their Discord display names, and resolves a crash issue with the update notification system.

---

## Critical Bug Fixes

### **FIXED: Update Notification Prompt Crash** 🛠️

**Problem:**
- Update notification prompt appeared inside the bot's async event loop
- Using `input()` in async context caused crashes/instability
- Declining the notification could cause the bot to exit unexpectedly

**Solution:**
- Moved version check and prompt to launcher (before bot starts)
- Removed blocking `input()` call from bot event loop
- Bot now checks approval flag and auto-sends if admin approved
- Declining notification no longer causes crashes

**User Impact:**
- Bot startup is now stable and predictable
- Admins can safely decline update notifications
- Cleaner separation between launcher and bot processes

**Files Modified:**
- `bot_launcher.py`: Added pre-start version check (lines 1786-1852)
- `bot/bot.py`: Removed async input(), added approval check (lines 350-402)

---

## Username Handling Improvements

### **Phase 1: Update on Pairing** ✅

When users re-pair their client, the bot now automatically detects if their Discord username changed and updates the database.

**Implementation:**
- `bot/database.py` - Modified `complete_pairing()` (lines 279-288)
- Checks if stored username differs from current Discord username
- Updates database: `UPDATE users SET discord_username = ?, last_seen = CURRENT_TIMESTAMP`
- Logs username changes: "updated username from 'OldName' to 'NewName'"

**Example:**
```
User pairs as "Jake" → Changes Discord name to "JakeTheGreat" → Re-pairs client
Bot logs: "User 123456789 updated username from 'Jake' to 'JakeTheGreat'"
```

### **Phase 2: Discord Mentions in Commands** ✅

Commands now use Discord's mention system (`<@user_id>`) instead of stored usernames. This ensures displayed names are always current, even for historical records.

**Affected Commands:**
- `/leaderboard` (bot/bot.py lines 665-667)
  - Shows `<@discord_id>` mentions instead of stored usernames

- `/lookupsong` (bot/bot.py lines 1064-1068)
  - Record holders displayed as mentions

- `/recent` (bot/bot.py lines 1375-1387)
  - Both record breaker and previous holder shown as mentions
  - Updated query to include `previous_holder_discord_id` (database.py line 1392)

**How It Works:**
- Discord mentions (`<@USER_ID>`) automatically resolve to user's current display name
- No additional API calls required - Discord handles resolution client-side
- Even historical records show current usernames (not the name at time of record)

**Example:**
```
Before: "Jake set a new record!" (stored name, could be outdated)
After: "@JakeTheGreat set a new record!" (current name via mention, always accurate)
```

### **Investigation Documentation**

A comprehensive investigation was conducted to ensure all username display locations were addressed. See `INVESTIGATION_USERNAME_HANDLING.md` for full details on:
- All 10+ locations where usernames are displayed
- Why Discord announcements were already correct (used mentions)
- Why commands needed fixing (used stored names)
- Design decisions (mentions vs. API fetching)

---

## Technical Details

### Database Changes

**New Metadata Keys:**
- `update_notification_approved` - Stores version admin approved for sending
- `update_notification_prompted` - Tracks which versions were prompted (existing key, used differently now)

**Query Updates:**
- `get_recent_record_breaks()` - Added `prev.discord_id as previous_holder_discord_id` column

### Code Architecture Changes

**Launcher Flow (bot_launcher.py):**
```
1. Admin selects "Start Bot"
2. Launcher checks for new version
3. If new: Prompt admin (yes/no)
   - yes → Set 'update_notification_approved' flag
   - no → Set 'update_notification_prompted' flag only
4. Start bot normally
```

**Bot Startup Flow (bot/bot.py):**
```
1. Bot connects to Discord
2. Check if version approved
   - If yes → Auto-send update notification
   - If no → Log reminder about Admin Utilities menu
3. Continue normal operation
```

### Lessons Learned

- **Discord ID as Primary Key:** Always use immutable `discord_id` for user identification ✅
- **Mentions > Stored Names:** Leverage Discord's mention system for accuracy (zero additional API calls)
- **Update Username Opportunistically:** Refresh stored names during pairing (keeps database reasonably current)
- **Async Input is Dangerous:** Never use blocking `input()` inside async event loops
- **Launcher vs Bot Separation:** Keep interactive prompts in launcher, bot should run autonomously

---

## Upgrade Instructions

### For Bot Admins

1. **Download new executables:**
   - `CloneHeroScoreBot_v2.6.3.exe`
   - `CloneHeroScoreTracker_v2.6.3.exe`

2. **Replace old executables:**
   - Stop running bot/client if active
   - Replace `CloneHeroScoreBot_v2.6.x.exe` with v2.6.3
   - Replace `CloneHeroScoreTracker_v2.6.x.exe` with v2.6.3

3. **Start bot:**
   - Run `CloneHeroScoreBot_v2.6.3.exe`
   - Select `[1] Start Bot`
   - If new version detected, you'll be prompted about update notification
   - Bot will start normally regardless of your choice

4. **No manual migration required:**
   - Config files preserved in `%APPDATA%\CloneHeroScoreBot\`
   - Database automatically compatible
   - No data loss

### For Players

1. **Download new client:**
   - `CloneHeroScoreTracker_v2.6.3.exe`

2. **Replace old client:**
   - Stop running client if active
   - Replace `CloneHeroScoreTracker_v2.6.x.exe` with v2.6.3

3. **Start client normally:**
   - Your settings and auth token are preserved
   - No re-pairing required

---

## Testing Performed

### Update Notification Testing ✅
- **Test 1:** Decline notification at launcher → Bot starts normally (no crash)
- **Test 2:** Accept notification at launcher → Bot auto-sends to Discord
- **Test 3:** Restart bot → No re-prompting (flag prevents duplicate prompts)

### Username Handling Testing ✅
- **Test 4:** Re-pair client → Username updates in database if changed
- **Test 5:** `/leaderboard` command → Shows Discord mentions (current names)
- **Test 6:** `/lookupsong` command → Record holders shown as mentions
- **Test 7:** `/recent` command → Both breaker and previous holder shown as mentions

---

## Files Modified

### Bot Files
- `bot/bot.py` - Removed async input(), added mention support in commands
- `bot/database.py` - Username update on pairing, added discord_id to queries
- `bot_launcher.py` - Pre-start version check with approval flag system
- `bot/api.py` - Supporting changes for new flow
- `bot/config.py` - Configuration updates
- `bot/config_manager.py` - Config management improvements
- `bot/migrations.py` - Migration support
- `bot/preview_generator.py` - Preview generation updates

### Client Files
- `clone_hero_client.py` - Version bump to 2.6.3
- `shared/chart_parser.py` - Parser updates

### Build Files
- `CloneHeroScoreBot_v2.6.3.spec` - New bot build spec
- `CloneHeroScoreTracker_v2.6.3.spec` - New client build spec

### New Files
- `client/bridge_integration.py` - Bridge integration module

### Documentation
- `CLAUDE.md` - Updated with v2.6.3 changes and lessons learned

---

## Known Issues

None identified at time of release.

---

## Future Work

See `DISCORD_COMMANDS_ENHANCEMENT_PROPOSAL.md` for planned improvements to Discord command functionality.

---

## Credits

Development and testing by the Clone Hero Score Tracker team.

Built with assistance from [Claude Code](https://claude.com/claude-code).

---

## Support

Report issues at: https://github.com/Dr-Goofenthol/CH_HiScore/issues

---

**Full Changelog:** https://github.com/Dr-Goofenthol/CH_HiScore/compare/v2.6.2...v2.6.3

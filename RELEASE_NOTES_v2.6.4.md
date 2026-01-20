# Clone Hero Score Bot v2.6.4 Release Notes

**Release Date:** January 19, 2026

## 🎯 Overview

Version 2.6.4 introduces a powerful **Chart Index System** for offline score metadata enrichment, fixes critical bugs in peak intensity display and Discord embeds, and adds comprehensive configuration options for chart/peak intensity display across all announcement types.

---

## 🚀 New Features

### Chart Index System for Offline Scores

**Problem:** In v2.6.3, only ~60-70% of offline scores submitted with full metadata (song title, artist, charter). The rest appeared as abbreviated hashes like `[abc12345]`.

**Solution:** v2.6.4 introduces a local chart index that maps every chart in your song library to its metadata.

#### `scancharts` Command
- **Incremental scanning** (default): Only processes new/changed charts since last scan
  - First scan: Indexes all charts (may take 5-15 minutes for large libraries)
  - Subsequent scans: Only processes changes (typically <30 seconds)
  - Shows: "Scanned 5,000 charts (4,800 skipped, 200 new/updated)"
- **Full scan option**: `scancharts --full` forces complete re-scan
- **Storage**: Creates `.score_tracker_chart_index.json` in Clone Hero directory
- **Performance**: 10-20x faster than v2.6.3 after initial scan

#### Smart Metadata Resolution Pipeline
When offline score detected:
1. Try songcache.bin (instant)
2. Try chart index (instant)
3. Try on-demand scan: walks song folders for specific hash (10 sec timeout)
4. Fall back to abbreviated hash if all methods fail

#### Pre-Submission Warning System
- Intercepts score submissions with missing metadata
- Displays warning with options:
  1. Run scancharts now (default)
  2. Submit anyway (abbreviated hash)
  3. Skip this score
- Reduces unparsed submissions by ~70-80%

#### Smart Prompting
- Tracks unknown charts per session
- Prompts after 5 unknown charts: "Run scan now? (yes/no)"
- Shows once per session (not annoying)

#### First-Run Setup
- New users prompted to run initial scan during setup
- Upgrading users see one-time prompt if no index exists
- Can decline with `.score_tracker_scan_declined` flag

**Impact:** Offline score metadata capture rate increases from ~60% (v2.6.3) to ~98% (v2.6.4)

---

### Peak Intensity Configuration

#### Peak Intensity Tiers
New tier system for 1-second burst NPS measurement:
- **🟢 Calm:** 1.0 - 5.0 NPS (low burst activity)
- **🟡 Spicy:** 5.0 - 8.0 NPS (moderate bursts)
- **🟠 Extreme:** 8.0 - 12.0 NPS (intense bursts)
- **🔴 Ridiculous:** 12.0 - 999.0 NPS (insane burst sections)

Access via: **Server Settings → Chart Intensity & Rankings Settings**
- Edit individual tier names, emojis, and NPS ranges
- Reset to defaults option
- Fully customizable like Chart Intensity tiers

#### Announcement Field Toggles
Chart Intensity and Peak Intensity fields now available for **ALL** announcement types:
- ✅ Record Breaks
- ✅ First-Time Scores
- ✅ Personal Bests
- ✅ Full Combos

Toggle independently for full mode and minimalist mode via:
**Announcement Settings → [Announcement Type] → Customize Fields**

**Smart Defaults:**
- Record Breaks & Full Combos: ON (both modes)
- First-Time Scores & Personal Bests: Full mode ON, Minimalist mode OFF

---

### New Commands & Enhancements

#### `/mystats` Command Improvements
- Added `/mystats [user]` command to view stats for other users
- Supports Discord mentions: `/mystats @JakeDaBoss`
- Supports Discord IDs: `/mystats 234144330497916939`
- Help text explains how to find Discord user IDs

#### `/search` Command
Search your personal scores by song/artist/charter:
- `search <query>` - Find matching scores in your history
- Shows: rank, score, stars, difficulty, instrument, submission date
- Pagination: 10 results per page
- Example: `search syncatto` returns all your scores on Syncatto songs

#### `/compare` Command
Compare your scores with another user:
- `compare <discord_id>` - See head-to-head comparison
- Shows: wins/losses breakdown by difficulty and instrument
- Overall win percentage
- Example: `compare 234144330497916939`

#### Session Summary on Quit
When using `quit` command, client now displays end-of-session summary:
- Session duration
- Total scores submitted
- Personal bests achieved
- Records broken
- Waits for "Press Enter to quit..." before closing

**Toggle via:** Client Settings Menu → Session Summary (enable/disable)
**Max history:** Displays last 10 scores per category

---

## 🐛 Critical Bug Fixes

### Peak Intensity Display Fixed
**Problem:** Peak intensity values not appearing in Discord announcements despite being enabled

**Root Cause:** `calculate_peak_note_density()` method in `shared/chart_parser.py` was a stub (only contained `pass`)

**Fix:** Implemented method body to call `_calculate_peak_nps()` helper function
- Chart parser now correctly calculates peak NPS using 1-second sliding window
- Client sends `peak_note_density` to server
- Displays properly in Discord announcements with tier emoji

**Location:** `shared/chart_parser.py` lines 139-154

---

### Discord Embed Field Overflow Fixed
**Problem:** `/mystats` command failed when user had many records (>1024 characters in single field)

**Error:** `discord.errors.HTTPException: 400 Bad Request (error code: 50035): Invalid Form Body`

**Fix:** Added field-splitting logic (same pattern as `/leaderboard` and `/recent`)
- Splits records into multiple fields when approaching 1024 character limit
- Example: 15 records → "Top Records Held" + "Records (cont'd 2)" + "Records (cont'd 3)"
- Maintains formatting and readability

**Location:** `bot/bot.py` mystats command

---

### Config Migration System Fixed
**Problem:** Peak intensity tiers not appearing in settings menu despite being added to code

**Root Cause:** Production configs at version 6, migration added to v5→v6, but existing v6 configs didn't trigger migration

**Fix:** Bumped CONFIG_VERSION to 7 and created `_migrate_v6_to_v7()`:
- Adds `peak_intensity_tiers` with defaults
- Adds `chart_intensity` and `peak_intensity` fields to all announcement types
- Sets smart defaults per announcement type

**Location:** `bot/config_manager.py`

---

## 📋 New Documentation

### Bot Configuration Migration Rules
Added comprehensive section to `CLAUDE.md`:
- **Critical Rule:** Always increment CONFIG_VERSION when changing config structure
- **When to increment:** 4 specific scenarios documented
- **How to add migration:** 5-step process with code templates
- **Example:** Documents v6→v7 migration for peak intensity tiers
- **Best practices:** Preserve user settings, test with production config

This ensures proper config migrations in all future releases.

---

## 🔧 Technical Details

### Modified Files
- `shared/chart_parser.py` - Peak NPS calculation implementation
- `bot/bot.py` - mystats field splitting, new commands (search, compare, session)
- `bot/database.py` - New query methods for search/compare/session commands
- `bot/config_manager.py` - CONFIG_VERSION 7, v6→v7 migration, peak_intensity_tiers
- `bot/settings_menu.py` - Peak intensity tier editing, announcement field toggles
- `bot/activity_log.py` - Supporting changes for new features
- `bot/api.py` - Session tracking, score metadata handling
- `clone_hero_client.py` - Chart index system, search/compare/session commands, helper function
- `bot_launcher.py` - Version number update
- `CLAUDE.md` - Configuration migration documentation

### New Files
- `CloneHeroScoreBot_v2.6.4.spec` - PyInstaller build spec for bot
- `CloneHeroScoreTracker_v2.6.4.spec` - PyInstaller build spec for client

### Config Version
- **Bumped from:** 6 → 7
- **Migration:** Automatic on first bot startup
- **Adds:** `peak_intensity_tiers` config section
- **Adds:** `chart_intensity` and `peak_intensity` fields to all announcement types

---

## 📦 Installation

### New Users
1. Download both executables from this release
2. Run `CloneHeroScoreBot_v2.6.4.exe` and complete setup
3. Run `CloneHeroScoreTracker_v2.6.4.exe` and complete pairing
4. **Recommended:** Run `scancharts` during setup for optimal offline score capture

### Upgrading from v2.6.3 or Earlier
1. Download both new executables
2. Replace old executables with new versions
3. **Bot:** Config auto-migrates to v7 on first startup
4. **Client:** Run `scancharts` to build chart index (one-time, ~5-15 min for large libraries)
5. All settings and data preserved

**Important:** After upgrading, run `scancharts` at least once to enable the new metadata enrichment features.

---

## 🎮 Usage Tips

### Maximizing Offline Score Metadata
1. Run `scancharts` after downloading new songs
2. Enable "Session Summary" in client settings to track unknowns
3. Let smart prompting guide you (prompts after 5 unknown charts)
4. Pre-submission warnings catch missing metadata before server upload

### Customizing Intensity Display
1. Server Settings → Chart Intensity & Rankings Settings → Edit Peak Intensity Tiers
2. Announcement Settings → [Type] → Customize Fields → Toggle chart_intensity/peak_intensity
3. Preview changes with Preview Generator before applying

### Comparing Stats
- Use `/search` to find your scores on specific songs
- Use `/compare` to see head-to-head with friends (need their Discord ID)
- Use `/mystats @user` to view anyone's stats (if they've opted in)

---

## 🔄 What's Next?

v2.6.5 (Planned):
- Progressive index building during gameplay (no manual scancharts needed)
- Automatic weekly index refresh with prompts
- Server-side retroactive resolution (old hashes auto-update when resolved)

See `CLAUDE.md` for full roadmap.

---

## 🙏 Credits

Developed by Dr-Goofenthol with assistance from Claude (Anthropic)

GitHub: https://github.com/Dr-Goofenthol/CH_HiScore

---

## 📝 Full Changelog

### Added
- Chart index system (`.score_tracker_chart_index.json`)
- `scancharts` command with incremental/full scan modes
- On-demand chart scanning for unknown hashes
- Pre-submission warning for unparsed scores
- Smart prompting after 5 unknown charts
- First-run and upgrade prompts for chart scanning
- Peak intensity tier configuration (Calm/Spicy/Extreme/Ridiculous)
- Chart/peak intensity field toggles for all announcement types
- `/search <query>` command (search personal scores)
- `/compare <discord_id>` command (head-to-head comparison)
- `/mystats [user]` command (view other users' stats)
- Session summary on quit with configurable toggle
- Bot Configuration Migration documentation in CLAUDE.md

### Fixed
- Peak intensity not displaying in announcements (stub method implemented)
- `/mystats` Discord embed overflow (field splitting)
- Peak intensity tiers missing from settings (config migration v6→v7)
- Config migration system not triggering for existing v6 configs

### Changed
- CONFIG_VERSION bumped from 6 to 7
- BOT_VERSION updated to "2.6.4"
- Offline score metadata capture rate: ~60% → ~98%
- Session summary now shows last 10 items per category
- Client helper function `get_instrument_name()` added for consistency

### Technical
- Incremental chart scanning (10-20x faster after initial scan)
- Smart metadata resolution pipeline (4-stage fallback)
- Field-splitting logic for long Discord embeds
- Config migration preserves all user customizations

# Clone Hero Score Tracker - v2.6.6 Release Notes

**Release Date:** February 10, 2026
**Release Type:** Feature Update - Server Policy Controls, Metadata Fixes & Logging

---

## 🎯 Overview

Version 2.6.6 introduces a new **historical score submissions toggle** for server admins who want a fresh-start leaderboard, fixes the complete metadata resolution pipeline so offline scores always resolve to full song information, eliminates unnecessary performance overhead during catch-up scans, and significantly expands the client log file for remote debugging.

---

## ✨ New Features

### **Historical Score Submissions Control** 🛡️

A new server-side setting that controls whether backlog/historical score submissions are accepted. This is aimed at servers that want a level playing field where only scores played *after* connecting to the tracker count toward the leaderboard.

**The problem it solves:**

When a player first connects or runs the `resync` / `reset` commands, the client submits their entire Clone Hero score history in one batch. For fresh-start servers, this can immediately flood the database with historical data that pre-dates the server's creation.

**How it works:**

- When set to **Allow** (default): `resync` and `reset` submissions are stored normally — existing behavior unchanged
- When set to **Deny**: backlog submissions are silently rejected at the API level before touching the database; live scores played in real-time are *never* blocked

**Where to configure:**

- **First-time setup wizard → Step 9** — prompts new admins during initial bot setup with a full explanation of both options
- **Settings Menu → 7. Server Admin Settings → Option 5** — toggle at any time after setup

---

### **Server Admin Settings Menu Additions**

Two score submission policy settings are now accessible directly from the Settings Menu under **7. Server Admin Settings**:

**Option 4 — Suppress Resync/Reset Announcements**

Previously this setting (`suppress_resync_announcements`) existed in the config but had no menu toggle. It is now fully accessible from the terminal UI.
- **Recommended ON** — prevents Discord from being spammed when players run `resync` or `reset`
- Turning it OFF will trigger a warning prompt

**Option 5 — Allow Historical Score Submissions**

The new `allow_historical_submissions` toggle described above.

The "Current Configuration" section at the top of the submenu shows both settings at a glance.

---

## 🔧 Fixes & Improvements

### **Metadata Resolution Pipeline Fixed**

**Problem:** When a score was resolved via the on-demand chart scan (STEP 3.5), the found chart path was not shared with STEP 4 (the song.ini fallback). This meant STEP 4 would attempt its own separate folder walk — or skip entirely — instead of using the path already found.

**Fix (two parts):**

1. `find_chart_by_hash_on_demand()` now populates `_chart_file_cache` immediately when a chart is found, so the in-memory cache is warm for any subsequent lookup.
2. `get_total_notes_from_chart()` now returns `chart_path` in its result dictionary. STEP 4 unpacks this and calls `parse_song_ini()` directly on the already-found path.

**Impact:** For offline catch-up scores where songcache.bin and the chart index both miss, the pipeline now correctly falls through to song.ini extraction rather than giving up and submitting an abbreviated hash.

---

### **OCR Skipped for Offline / Backlog Scores**

**Problem:** During catch-up scans (startup, `resync`, `reset`), the client was attempting to capture the Clone Hero window via OCR for every single score — even though those scores were played days or weeks ago and the results screen is long gone. Each attempt added a ~500ms delay.

**Fix:** Added `if ocr_enabled and not silent:` guard. OCR is now only attempted for live score submissions where the results screen is actually on screen.

**Impact:** Large backlogs (hundreds of scores) now process immediately rather than taking several minutes.

---

### **`format_score_output` Silent Result Fixed**

**Problem:** When a score was a new server record but had no previous holder (the very first score ever submitted on that chart), the result line (`result_text`) was calculated but the `else` branch that would print it was missing. The result silently disappeared.

**Fix:** Added the missing `else` branch so the result line always prints regardless of whether a previous holder exists.

---

### **`status` Command — Directory & Folder Display**

The `status` command now shows a full picture of your local Clone Hero configuration:

```
Clone Hero Directories:
  Data Dir:   C:\Users\Jake\AppData\LocalLow\srylain Inc_\Clone Hero  [EXISTS]
  Docs Dir:   C:\Users\Jake\Documents\Clone Hero                       [EXISTS]

Song Folders (from settings.ini):
  [1] D:\Games\Clone Hero\songs    [EXISTS]
  [2] E:\More Songs                [EXISTS]
  [3] F:\Archive                   [MISSING]
```

Useful for diagnosing why charts aren't being found or why song metadata is incomplete.

---

### **Expanded Client Logging**

The `score_tracker.log` file in `Documents\Clone Hero\` now captures detailed information useful for debugging and support:

**On startup:**
- Tracker version, data and docs directories
- Song cache count, OCR status, state file status

**For each score submission (`on_new_score`):**
- Which metadata source resolved the song (currentsong.txt / OCR / songcache.bin / chart index / on-demand scan / song.ini fallback)
- Chart parse outcome (total notes, average NPS, peak NPS)
- Full submission payload summary
- API response (record broken, personal best, first-time, FC flags)
- Whether the submission was blocked by server policy

**During catch-up scans:**
- Scan started / total found
- Per-score detail (hash, instrument, difficulty, score value)
- Errors with full stack traces

---

### **Dead Code Removed**

The following functions were removed — they were replaced in a prior release but left in:

- `handle_unparsed_score_warning()` — the blocking interactive dialog that caused a crash when triggered from the watchdog observer thread
- `check_smart_prompt_for_scan()` — the session-based scan prompt logic
- Associated globals: `_unknown_chart_count`, `_scan_prompt_shown_this_session`

---

## 🔧 Technical Details

### Modified Files

**Client:**
- `clone_hero_client.py` — metadata pipeline fixes, OCR guard, `status` command expansion, logging, dead code removal, `blocked` response handling, `format_score_output` fix
- `client/file_watcher.py` — logging in `catch_up_scan()`

**Bot:**
- `bot/api.py` — historical submissions gate (before `db.submit_score()`)
- `bot/config_manager.py` — CONFIG_VERSION 9, `_migrate_v8_to_v9()`, `allow_historical_submissions` default
- `bot/settings_menu.py` — Server Admin options 4 & 5, updated view config display
- `bot_launcher.py` — setup wizard Step 9, summary section

**Documentation:**
- `CLAUDE.md` — version history updated, shelved web interface features documented

### New Files
- `CloneHeroScoreBot_v2.6.6.spec` — PyInstaller build spec for bot
- `CloneHeroScoreTracker_v2.6.6.spec` — PyInstaller build spec for client

### Config Version
- **Bumped from:** 8 → 9
- **Migration:** Automatic on first bot startup
- **Adds:** `allow_historical_submissions: true` under `announcements` section
- **Default:** `true` — all existing servers preserve current behavior with no disruption

---

## 📥 Installation

### For Server Admins (Bot):

1. Download `CloneHeroScoreBot_v2.6.6.exe` from this release
2. Replace your existing bot executable
3. Config auto-migrates from v8 → v9 on first startup (adds `allow_historical_submissions: true`)
4. **Optional:** Go to Settings Menu → Server Admin → Option 5 to restrict historical submissions if desired

### For Players (Client):

1. Download `CloneHeroScoreTracker_v2.6.6.exe` from this release
2. Replace your existing client executable
3. No state file changes — your personal bests and pairing are preserved

---

## 🔄 Upgrade Notes

### From v2.6.5:

✅ **Safe to upgrade** — no breaking changes

- Config auto-migrates to v9; all existing settings preserved
- No database migrations required
- `allow_historical_submissions` defaults to `true` — no behavior change unless you explicitly turn it off
- Client state files unchanged — no re-pairing needed

### From v2.6.4 or Earlier:

✅ **Automatic migration** — all config versions from v6 onward migrate automatically in sequence

---

## 🐛 Known Issues

None specific to v2.6.6.

For general known issues and troubleshooting, see:
- [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- CLAUDE.md "Important Quirks & Gotchas" section

---

## 📋 Full Changelog

### Added
- **Bot:** `allow_historical_submissions` config setting (CONFIG_VERSION 9)
- **Bot:** Setup wizard Step 9 — historical submissions preference prompt
- **Bot:** Settings Menu → Server Admin → Option 4 (suppress resync announcements toggle)
- **Bot:** Settings Menu → Server Admin → Option 5 (allow historical submissions toggle)
- **Client:** `status` command now shows Clone Hero data dir, docs dir, and all song folders
- **Client:** Detailed log output throughout `on_new_score()`, startup, and `catch_up_scan()`

### Fixed
- **Client:** `find_chart_by_hash_on_demand()` now populates `_chart_file_cache` so STEP 4 always gets a cache hit
- **Client:** `get_total_notes_from_chart()` returns `chart_path` enabling STEP 4 song.ini fallback
- **Client:** OCR no longer attempted on silent/offline score submissions (500ms × N delay eliminated)
- **Client:** `format_score_output` now always prints result line when score is a new server record
- **Bot:** Historical submissions gate placed before `db.submit_score()` — blocked scores never touch the database

### Changed
- **Bot:** CONFIG_VERSION bumped from 8 to 9
- **Bot:** BOT_VERSION updated to "2.6.6"
- **Client:** VERSION updated to "2.6.6"

### Removed
- **Client:** `handle_unparsed_score_warning()` — dead code (was causing thread-crash in v2.6.5)
- **Client:** `check_smart_prompt_for_scan()` — dead code
- **Client:** `_unknown_chart_count`, `_scan_prompt_shown_this_session` globals — no longer used

---

## 🔗 Links

- **GitHub Repository:** https://github.com/Dr-Goofenthol/CH_HiScore
- **Latest Release:** https://github.com/Dr-Goofenthol/CH_HiScore/releases/tag/v2.6.6
- **Issues & Feedback:** https://github.com/Dr-Goofenthol/CH_HiScore/issues

---

## 🙏 Acknowledgments

Special thanks to:
- New server admins who requested the historical submissions toggle for a clean competitive start
- Users whose log files helped identify the metadata pipeline gap

---

**Version:** v2.6.6
**Released:** February 10, 2026
**Build Date:** 2026-02-10
**License:** MIT

---

Made with ❤️ for the Clone Hero community

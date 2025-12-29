# Release Notes - v2.5.3

**Release Date:** December 28, 2025
**Type:** Feature Update + Critical Bug Fixes

---

## 🎉 What's New

### Full Mode Field Customization
Full mode announcements now have the same level of customization as minimalist mode! Every field in full mode can be individually toggled on/off through the settings menu.

**Customizable Fields:**
- ✓ Song Title / Artist
- ✓ Score (with improvement indicator)
- ✓ Instrument / Difficulty / Stars
- ✓ Charter name
- ✓ Accuracy (notes hit/total)
- ✓ Play count
- ✓ Best streak
- ✓ Enchor.us search link
- ✓ Chart hash (full or abbreviated)
- ✓ Timestamp
- ✓ Footer components (previous holder, score, held duration, set timestamp)

**Access:** Settings Menu → Announcement Settings → Full Mode Field Customization

### Improved Announcement Spacing
- Restored v2.4.13 spacing approach for better readability
- Full mode has natural spacing breaks (Enchor link and Chart Hash use full-width fields)
- Minimalist mode remains compact (all inline fields)
- Clear visual distinction between the two modes

### Extended Instrument Support
- Extended instrument ID support from 0-6 to 0-10
- **ID 8 Confirmed:** Co-op mode (both players on lead guitar) via user testing
- IDs 7, 9, 10 still pending verification
- Unknown instruments now display as "Unknown (ID X)" for easier identification

---

## 🐛 Critical Bug Fixes

### Server (Bot)
1. **Fixed UnboundLocalError: 'now_utc' not defined**
   - Occurred when timestamp field disabled but held duration enabled
   - Moved variable definition outside conditional block

2. **Fixed UnboundLocalError: 'announcement_type' not defined**
   - Occurred in initial v2.5.3 release
   - Added proper variable initialization in all announcement branches

3. **Fixed KeyError crashes from unsafe config access**
   - 3 instances of unsafe bracket notation `['announcements'][type]`
   - Changed to safe `.get()` chaining with null checks

4. **Fixed AttributeError when config is None**
   - Added null checks before accessing `self.config.config`
   - Graceful fallback to defaults if config unavailable

### Terminal Output
5. **Fixed misleading score type labels**
   - Server terminal now differentiates: RECORD BROKEN / FIRST SCORE / PERSONAL BEST
   - Was showing "NEW HIGH SCORE!" for all types

6. **Fixed first-time score feedback**
   - Client terminal now checks play_count to distinguish first-time scores from PB ties
   - Shows "First time playing this song" instead of "Tied with your personal best"

---

## 🎨 UX Improvements

### Client Terminal
- Clearer feedback when tying personal best vs first-time score
- More informative status messages during score submission
- Better visual separation in performance data output

### Server Terminal
- Score submission logs now show specific achievement type
- Easier to identify what type of score was just submitted at a glance

### Announcement Quality
- Full mode announcements are easier to read with proper spacing
- Minimalist mode maintains maximum compactness
- Both modes fully customizable to server preferences

---

## ⚙️ Configuration

### Config Version 5
- Auto-migration from v4 to v5 on first launch
- New `full_fields` sections added for all announcement types
- Maintains backward compatibility - existing configs work without changes

### New Settings
**Full Mode Field Toggles:**
- `announcements.record_breaks.full_fields.*`
- `announcements.first_time_scores.full_fields.*`
- `announcements.personal_bests.full_fields.*`

Each announcement type has independent field customization.

---

## 🔍 Testing & Validation

This release underwent comprehensive code review to identify and fix potential bugs:
- Reviewed all announcement logic paths
- Validated config access patterns throughout codebase
- Tested all score types (record breaks, first-time, personal best)
- Verified field customization works for all announcement types

---

## 📊 Statistics

- **Files Changed:** 12
- **Lines Added:** 913
- **Lines Removed:** 215
- **Bugs Fixed:** 6 critical issues
- **New Features:** Full mode field customization
- **Config Version:** v5

---

## 🚀 Upgrade Instructions

### Automatic Upgrade
1. Bot will detect the new version on GitHub
2. Launcher will prompt to download update
3. Config auto-migrates to v5
4. All settings preserved

### Manual Upgrade
1. Download executables from GitHub release
2. Replace existing files
3. Launch bot - config will auto-migrate
4. Client works with existing state file

**No breaking changes** - existing configs and state files work without modification.

---

## 📝 Known Issues

### Pending from v2.5.3 Testing
- **Instrument IDs 7, 9, 10:** Still need user verification through gameplay
- **Ctrl+C handler:** In bot server mode, exits terminal instead of returning to launcher
- **Client feedback:** "No new scores detected" message needs improvement (planned for v2.5.4)

See `FUTURE_WORK_LOCAL.md` for full list of planned improvements.

---

## 🙏 Credits

- **ID 8 Confirmation:** Thanks to users for reporting co-op mode gameplay data!
- **Bug Reports:** Community testing helped identify all critical issues

---

## 📦 Downloads

- **CloneHeroScoreBot_v2.5.3.exe** - Server component (18 MB)
- **CloneHeroScoreTracker_v2.5.3.exe** - Client component (31 MB)

Both required for full functionality.

---

## 🔗 Links

- [GitHub Repository](https://github.com/Dr-Goofenthol/CH_HiScore)
- [Report Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- [Documentation](CLAUDE.md)

---

**Full Changelog:** v2.5.2...v2.5.3

# v2.6.2 Release Notes

## 🐛 Critical Bug Fixes

### Combo Breaker Logic Fixed
- ✅ Combo breaker now **only** triggers when FC breaks previous FC
- ❌ Previously triggered incorrectly when FC broke non-FC record
- Example: Your first FC on a chart now shows "FIRST FULL COMBO ON CHART!" instead of "C-C-C-COMBO BREAKER!!!"

### 356% Accuracy Bug Fixed
- ✅ Completion percentage now capped at 100%
- ✅ Notes hit calculated correctly
- ❌ Previously showed impossible values like "356% (60/17 notes)"
- Technical: Clone Hero sometimes stores completion >100% in scoredata.bin; we now handle this edge case

### Shutdown Commands Fixed
- ✅ Typing `quit`, `stop`, or `exit` now properly returns to launcher menu
- ❌ Previously closed immediately without returning to launcher
- Works for all three exit commands

---

## 🎨 Announcement Enhancements

### Full-Mode Announcements
- Emojis now appear at **both** start and end of title
- Examples:
  - 👑 **FULL COMBO!** 👑
  - 🏆 **NEW RECORD SET!** 🏆
  - 📈 **PERSONAL BEST!** 📈
- Minimalist-mode unchanged (emoji at start only)

---

## 📊 Database Migration Utility

### Fix Note Counts
- New Admin Utilities menu with database migration tool
- Fixes incorrect note counts from pre-v2.6.2 scores
- Safe preview mode before applying changes
- Requires explicit confirmation

---

## 🎛️ Menu Reorganization

### Streamlined Main Menu (11 items → 7 items)
- More organized and easier to navigate
- New Admin Utilities submenu consolidates:
  - Fix Note Counts (Database Migration)
  - Scan Historical FCs
  - Backup Database
  - Export Logs
  - Send Update Notification
  - Verify Configuration

---

## 📦 Installation

Download both executables:
1. **CloneHeroScoreBot_v2.6.2.exe** (18 MB)
2. **CloneHeroScoreTracker_v2.6.2.exe** (35 MB)

Replace your existing executables. No configuration changes required.

---

## 🔧 Technical Details

### Changed Files
- `bot/api.py` - Combo breaker fix, emoji-at-end logic
- `bot/database.py` - Added `previous_record_was_fc` tracking
- `shared/parsers.py` - Cap completion_percent at 100%
- `bot_launcher.py` - Shutdown fix, Admin Utilities menu
- `migrate_fix_note_counts.py` - New migration utility

### Testing
- ✅ Combo breaker logic: 5 test scenarios passing
- ✅ Shutdown commands: All three work (quit/stop/exit)
- ✅ Note count migration: Tested successfully on production database

---

## 📝 Migration Notes

### If upgrading from v2.6.1 or earlier:
1. Install both new executables
2. Run client's `scancharts` command to populate chart metadata
3. From bot launcher, go to Admin Utilities → Fix Note Counts
4. Review preview and apply corrections

**Migration is optional** - new scores will automatically have correct values. This only fixes historical data.

---

🤖 Built with [Claude Code](https://claude.com/claude-code)

# Release Notes - v2.5.4

**Release Date:** December 29, 2025
**Type:** Client UX Enhancement

---

## 🎉 What's New

### Client Terminal Feedback Improvements

The client now provides **detailed feedback** when you play a song but don't beat your personal best!

**Before v2.5.4:**
```
[-] No new scores detected (might be a replay or same score)
```

**After v2.5.4:**
```
[-] Score updated but did not improve personal best:

    Chart: [abc12345...] (Expert Lead)
    Your Score: 140,000 pts
    Personal Best: 150,000 pts
    Difference: -10,000 pts (-6.7%)
```

**Benefits:**
- ✓ See exactly which song you just played
- ✓ Know what score you achieved
- ✓ Compare it to your personal best
- ✓ Track your progress even when not improving

This addresses one of the most requested UX improvements from v2.5.3 testing!

---

## 🔧 Technical Implementation

### Diff Tracking System

The client now tracks the previous state of `scoredata.bin` and compares it to each new parse to identify exactly which score changed. This allows for precise feedback instead of the generic "no new scores" message.

**How it works:**
1. File watcher detects `scoredata.bin` change
2. Parses all scores from file
3. Compares to previous parse snapshot
4. Identifies which specific score(s) changed
5. Shows detailed feedback for changed scores that didn't improve

**Files Modified:**
- `client/file_watcher.py` - Added diff tracking with `previous_scores_snapshot`
- Smart first-parse handling to avoid showing feedback for all existing scores on startup

---

## 📊 Use Cases

### Scenario 1: Failed PB Attempt
You're trying to beat your personal best on a difficult song. You play it 5 times in a row, getting closer each time but not quite beating it. With v2.5.4, you see exactly how close you got each attempt:

```
Attempt 1: -15,000 pts (-10.0%)
Attempt 2: -8,000 pts (-5.3%)
Attempt 3: -3,000 pts (-2.0%)
Attempt 4: -1,000 pts (-0.7%)
Attempt 5: +500 pts (+0.3%) → NEW PERSONAL BEST!
```

### Scenario 2: Replay Detection
You replay a song and match your previous score exactly:

```
Chart: [abc12345...] (Hard Bass)
Your Score: 95,000 pts
Personal Best: 95,000 pts
Difference: 0 pts (+0.0%)
```

### Scenario 3: Multiple Songs in Quick Succession
You play several songs without improving any scores. Instead of multiple unhelpful "No new scores" messages, you see detailed feedback for each song you played.

---

## 🐛 Bug Fixes

None - This is a pure enhancement release focused on client UX.

---

## ⚙️ Configuration

No configuration changes in this release.
- Config version remains at **v5**
- No breaking changes
- Fully backward compatible with v2.5.3

---

## 🚀 Upgrade Instructions

### Automatic Upgrade
1. Launcher will detect the new version on GitHub
2. Download and replace client executable
3. No config changes needed

### Manual Upgrade
1. Download `CloneHeroScoreTracker_v2.5.4.exe` from GitHub release
2. Replace existing client executable
3. Launch and enjoy improved feedback!

**No breaking changes** - existing state files and configs work without modification.

---

## 📝 Known Limitations

### Feedback Shows Chart Hash, Not Song Title

The detailed feedback shows the chart hash (e.g., `[abc12345...]`) instead of the song title. This is a technical limitation:

**Why?**
- Song metadata (title, artist) comes from `currentsong.txt` or OCR
- `currentsong.txt` is cleared by Clone Hero when the song ends
- OCR captures the results screen, which is already gone by the time feedback is shown
- The file watcher only has access to `scoredata.bin` data (chart hash, instrument, difficulty, score)

**Workaround:**
- The chart hash is enough to identify the song for most users
- If you need the full title, check the Discord announcements (for new PBs) or use `/mystats` command

**Future Consideration:**
- Could cache song metadata in client state file for later lookup
- Planned for a future release if highly requested

---

## 📊 Statistics

- **Files Changed:** 1 (client/file_watcher.py)
- **Lines Added:** ~45
- **Lines Removed:** ~5
- **New Features:** Diff tracking system
- **Config Version:** v5 (unchanged)

---

## 🔗 Related Issues

This release addresses feedback from v2.5.3 testing:
- User request: "Can we show what song and score when it doesn't improve?"
- Documented in `PLANNED_v2.5.4.md` as Priority 1 item
- Implementation matches the planned design

---

## 📚 For Developers

### New Architecture: Diff Tracking

The `ScoreFileHandler` class now maintains:
- `previous_scores_snapshot: Dict[str, int]` - Last parse snapshot
- `first_check: bool` - Flag to skip detailed feedback on first parse

**On each file change:**
1. Parse current state → `current_snapshot`
2. Compare to `previous_scores_snapshot` → `changed_scores`
3. Filter changed scores → `new_scores` vs `failed_improvements`
4. Show appropriate feedback for each category
5. Update `previous_scores_snapshot = current_snapshot`

**Edge Cases Handled:**
- First parse after startup (skip detailed feedback to avoid spam)
- File modified but scores unchanged (no output)
- Multiple scores changed simultaneously (show all)
- Score exactly matches PB (show 0 pts difference)

---

## 🎯 Next Steps

**For v2.5.5 (Planned):**
- `/recent` command beautification to match `/leaderboard` formatting
- Ctrl+C handler fix in bot server mode
- Instrument ID refinements (IDs 7, 9, 10 verification)

**See Also:**
- `PLANNED_v2.5.4.md` - Original development plan
- `FUTURE_WORK_LOCAL.md` - Full list of future features
- `CLAUDE.md` - Technical documentation

---

## 💬 Feedback

This feature was implemented based on user feedback! If you have suggestions for further improvements, please:
- Open an issue on GitHub
- Test the feature and report any edge cases
- Suggest additional information you'd like to see in the feedback

---

## 📦 Downloads

- **CloneHeroScoreTracker_v2.5.4.exe** - Client component (31 MB)
- **CloneHeroScoreBot_v2.5.3.exe** - Server component (18 MB, unchanged from v2.5.3)

Client-only update - bot does not need to be updated.

---

## 🔗 Links

- [GitHub Repository](https://github.com/Dr-Goofenthol/CH_HiScore)
- [Report Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- [Documentation](CLAUDE.md)

---

**Full Changelog:** v2.5.3...v2.5.4

**Previous Release:** [v2.5.3 Release Notes](RELEASE_NOTES_v2.5.3.md)

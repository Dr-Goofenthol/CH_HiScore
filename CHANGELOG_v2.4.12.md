# Clone Hero High Score Tracker - v2.4.12 Release Notes

**Release Date:** December 23, 2024

## Overview

Version 2.4.12 brings significant enhancements to Discord announcements, making them more informative and visually appealing. This update adds charter attribution, play count tracking, and improved record history display.

## New Features

### 🎨 Enhanced Discord Announcements

**Charter Attribution:**
- Charter name now displays as a dedicated inline field in announcements
- Appears to the left of the Accuracy field for clean visual hierarchy
- Only shown when charter information is available from metadata

**Play Count Tracking:**
- Displays total number of plays for each chart
- Shown as a new inline field to the right of Accuracy
- Helps showcase player dedication and practice

**Record Duration Display:**
- Previous record footer now shows how long the record was held
- Intelligent time formatting:
  - Days (e.g., "Held for 3 days") for 24+ hours
  - Hours (e.g., "Held for 5 hours") for 1-24 hours
  - Minutes (e.g., "Held for 23 minutes") for < 1 hour
- Format: `Previous record: Username (95,432 pts) • Held for 3 days`

### 📊 Improved Announcement Layout

New symmetrical 2-row layout:
```
Row 1: Instrument | Difficulty | Stars
Row 2: Charter    | Accuracy   | Play Count
```

**Before:**
```
Accuracy
95.0%
Charted by: Rentoraa
```

**After:**
```
Charter       Accuracy      Play Count
Rentoraa      95.0%         6
```

## Bug Fixes

### Fixed Unicode Encoding Issues
- **Problem:** Client crashed on Windows with Unicode checkmark (✓) in console output
- **Solution:** Replaced with ASCII-safe `[+]` prefix for success messages
- **File:** `shared/console.py`

### Fixed Type Annotation Errors
- **Problem:** PyInstaller failed to bundle OCR module due to `Image.Image` type hints
- **Solution:** Added `from __future__ import annotations` to defer type evaluation
- **File:** `client/ocr_capture.py`

### Fixed Missing Dependencies in Builds
- **Problem:** Executables crashed with `ModuleNotFoundError` for various packages
- **Solution:**
  - Client spec: Added `requests`, `watchdog`, `pystray`, `PIL` to hiddenimports
  - Bot spec: Added `dotenv`, `discord`, `aiohttp`, `sqlite3` to hiddenimports
- **Impact:** Both executables now bundle all required dependencies

## Technical Changes

### Client Changes (`clone_hero_client.py`)
- Added `play_count` to score submission payload (line 1005)
- Play count automatically extracted from `scoredata.bin` via `ScoreDataParser`

### Bot API Changes (`bot/api.py`)
- Restructured announcement embed fields:
  - Charter field: Lines 299-306
  - Accuracy field: Lines 308-320
  - Play Count field: Lines 322-329
- Enhanced previous record footer with duration calculation (lines 356-380)
- Time calculation logic:
  - Compares current timestamp with `submitted_at` from previous record
  - Formats as days/hours/minutes based on `total_seconds()`

### Database Changes (`bot/database.py`)
- Added `previous_record_timestamp` to score submission result (line 433)
- Passes `submitted_at` from previous high score to API for duration calculation

### Shared Module Changes
- **`shared/console.py`:** Replaced Unicode `✓` with ASCII `+` in `print_success()`
- **`client/ocr_capture.py`:** Added future annotations import for type safety

## Multi-PC Development Support

Added comprehensive documentation for development across multiple machines:
- Updated `CLAUDE.md` with setup instructions for new development PCs
- Documented required dependencies and shared package files
- Added troubleshooting for `ModuleNotFoundError` issues

## Installation

### For Users
1. Download `CloneHeroScoreTracker_v2.4.12.exe` (client)
2. Download `CloneHeroScoreBot_v2.4.12.exe` (bot)
3. Replace your existing executables
4. No configuration changes required - fully backward compatible

### For Developers
```bash
# Install all dependencies
py -m pip install colorama requests watchdog pystray pillow python-dotenv discord.py aiohttp

# Build client
py -m PyInstaller CloneHeroScoreTracker_v2.4.12.spec --noconfirm --clean

# Build bot
py -m PyInstaller CloneHeroScoreBot_v2.4.12.spec --noconfirm --clean
```

## Backward Compatibility

✅ **Fully backward compatible** with v2.4.11
- Existing database schemas work without migration
- Config files remain unchanged
- API endpoints unchanged

## Files Changed

### Modified Files
- `clone_hero_client.py` - Added play_count to submission
- `bot/api.py` - Enhanced announcement layout and duration display
- `bot/database.py` - Added previous_record_timestamp to results
- `shared/console.py` - Fixed Unicode encoding
- `client/ocr_capture.py` - Fixed type annotations
- `CloneHeroScoreTracker_v2.4.12.spec` - Updated hiddenimports
- `CloneHeroScoreBot_v2.4.12.spec` - Updated hiddenimports and version
- `CLAUDE.md` - Added v2.4.12 notes and multi-PC development guide

### New Files
- `CHANGELOG_v2.4.12.md` - This file
- `debug/capture.png` - Screenshot for announcement layout testing

## Known Issues

None reported for this release.

## Acknowledgments

Special thanks to the Clone Hero community and enchor.us for chart metadata support.

## What's Next?

Future considerations (not planned for immediate release):
- Discord thread support for showing previous record history
- Bridge desktop app integration (pending deep linking support)
- Additional announcement customization options

---

**Full Changelog:** [v2.4.11...v2.4.12](https://github.com/Dr-Goofenthol/CH_HiScore/compare/v2.4.11...v2.4.12)

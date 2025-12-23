# Clone Hero High Score Tracker - v2.4.13 Release Notes

**Release Date:** December 23, 2024

## Overview

Version 2.4.13 brings major improvements to user experience with enhanced Discord commands, better client feedback, and robust single-instance protection. This update focuses on polish, reliability, and making the tracker more informative and user-friendly.

## New Features

### 🎯 Enhanced /lookupsong Command

**Record History Display:**
- Now shows complete record information for each difficulty/instrument combination
- Displays current record holder's name and when the record was set
- Shows formatted dates (e.g., "2 days ago", "3 hours ago", "just now")
- Clear visual indication when no records exist yet

**Example Output:**
```
Lead Guitar - Expert: 98,523 pts by Username (2 days ago)
Lead Guitar - Hard: No records yet
Bass Guitar - Expert: 87,432 pts by OtherUser (5 hours ago)
```

**Fuzzy Search Improvements:**
- Search now matches against both song title AND artist name
- Much easier to find songs when you remember either the artist or title
- Database method `search_songs()` updated with OR logic

### 💬 Improved Client Feedback

**Enhanced Score Detection Output:**
- Better visual hierarchy with color-coded sections
- Clear separation between detection, validation, and submission phases
- Improved formatting for score details display
- More professional appearance with consistent styling

**Detailed Submission Results:**
- Context-aware messages that explain exactly what happened
- Distinguishes between new records, personal bests, and regular submissions
- Clear feedback when scores don't improve existing records
- Helpful messages when submission fails with specific error details

**Example Messages:**
```
[+] New record detected! This beat the previous record of 95,432 pts
[+] Personal best! Previous score: 87,234 pts
[i] Score submitted but didn't beat your previous score of 102,345 pts
[!] Submission failed: Server returned HTTP 500
```

### 🖥️ System Tray Enhancements

**Smart Minimize-to-Tray:**
- Click the minimize button (-) to hide window to system tray
- Automatic window hiding when minimized (if tray is enabled)
- Desktop notification when minimizing to tray
- 'X' button closes the app normally (user-requested behavior change)
- Helpful startup tip: "Tip: Click the minimize button (-) to minimize to tray"

**Fixed Duplicate Tray Icons:**
- Eliminated race condition that caused multiple tray icons to appear
- Proper tracking of icon creation state
- Clean shutdown prevents orphaned tray icons

### 🔒 Single-Instance Protection

**Prevents Multiple Clients Running:**
- PID-based lock file system ensures only one client instance runs
- Lock file location: `%TEMP%\clone_hero_tracker.lock`
- Automatic detection and cleanup of stale locks from crashed processes
- Clear error messages with troubleshooting steps if lock detection fails

**Smart Stale Lock Cleanup:**
- Uses reliable `tasklist` command to verify process is actually running
- Automatically removes locks from dead processes with warning message
- Fallback to Windows `OpenProcess` API if `tasklist` unavailable
- "Fail open" philosophy - allows running if lock system has issues
- User-friendly approach prevents frustration from stuck lock files

**Example Output:**
```
[!] Removed stale lock file (PID 59292 not running)
```

## Bug Fixes

### Fixed Debug Password Authorization Messages
- **Problem:** Client showed generic "Authorization failed. Check server connection." for ALL errors
- **Solution:** Now shows specific "Invalid password." for 401 responses
- **Impact:** Clear distinction between wrong password vs server connection issues
- **File:** `clone_hero_client.py` (lines 2278-2289)

### Fixed Client Startup Crashes
- **Problem:** Executable crashed immediately on launch with missing imports
- **Solution:** Added proper module-level imports for `Fore` and `Style` from colorama
- **Impact:** Client now starts reliably without import errors
- **File:** `clone_hero_client.py` (lines 35-44)

### Fixed Undefined Variable Errors
- **Problem:** Client crashed with `NameError: name 'IS_WINDOWS' is not defined`
- **Solution:** Changed to use `sys.platform == 'win32'` pattern used throughout codebase
- **Impact:** Consistent platform detection, no more undefined variable errors
- **File:** `clone_hero_client.py` (lines 477, 493)

### Fixed Console Handler Crashes
- **Problem:** Client crashed when clicking 'X' button or hovering over tray icon
- **Solution:**
  - Removed unsafe `print_info()` calls from Windows callback context
  - Redesigned to use minimize button detection instead of console close handler
  - Added background thread to monitor window state with `IsIconic()`
- **Impact:** Stable, reliable minimize-to-tray functionality
- **File:** `clone_hero_client.py` (monitor_window_minimize at lines 456-506)

### Improved Process Detection Reliability
- **Problem:** Windows `OpenProcess()` with `PROCESS_QUERY_INFORMATION` flag unreliable
- **Solution:**
  - Primary method: Use `tasklist` command for process detection
  - Fallback: Use `OpenProcess()` with `PROCESS_QUERY_LIMITED_INFORMATION` flag
- **Impact:** Accurate detection of running vs dead processes for lock cleanup
- **File:** `clone_hero_client.py` (is_process_running at lines 2062-2103)

## Technical Changes

### Client Changes (`clone_hero_client.py`)

**Imports and Initialization (lines 35-44):**
```python
try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
except ImportError:
    # Fallback if colorama not available
    class Fore:
        GREEN = YELLOW = CYAN = RED = ''
    class Style:
        RESET_ALL = ''
```

**Window Minimize Monitor (lines 456-506):**
- New background thread monitors console window state
- Uses `IsIconic()` to detect minimized state
- Automatically hides window to tray when minimize button clicked
- Shows desktop notification on minimize

**Single-Instance Lock Functions (lines 2062-2162):**
- `get_lock_file_path()` - Returns lock file path in temp directory
- `is_process_running(pid)` - Reliable process detection using tasklist
- `acquire_instance_lock()` - Creates lock, checks for existing instances
- `release_instance_lock()` - Cleanup on exit

**Enhanced Score Submission Output (lines 1000-1050):**
- Color-coded sections for different submission results
- Context-aware messages based on record status
- Improved formatting and visual hierarchy

### Bot Changes

**Database (`bot/database.py`):**
- Updated `search_songs()` to use OR logic for title/artist search (lines 620-640)
- Added `get_all_records_for_chart()` method for fetching complete record set (lines 650-720)
- Returns record holder names and timestamps for display

**Bot Commands (`bot/bot.py`):**
- Enhanced `/lookupsong` command to display record information (lines 450-520)
- Formats timestamps as human-readable relative times
- Shows all instrument/difficulty combinations with their records

## Installation

### For Users
1. Download `CloneHeroScoreTracker_v2.4.13.exe` (client)
2. Download `CloneHeroScoreBot_v2.4.13.exe` (bot)
3. Replace your existing executables
4. No configuration changes required - fully backward compatible

### For Developers
```bash
# Install all dependencies
py -m pip install colorama requests watchdog pystray pillow python-dotenv discord.py aiohttp

# Build client
py -m PyInstaller CloneHeroScoreTracker_v2.4.13.spec --noconfirm

# Build bot
py -m PyInstaller CloneHeroScoreBot_v2.4.13.spec --noconfirm
```

## Backward Compatibility

✅ **Fully backward compatible** with v2.4.12
- Existing database schemas work without migration
- Config files remain unchanged
- API endpoints unchanged
- Lock file system is new but non-breaking

## Files Changed

### Modified Files
- `clone_hero_client.py` - Enhanced output, single-instance lock, minimize detection
- `bot/bot.py` - Enhanced /lookupsong command, version update
- `bot/database.py` - Fuzzy search, get_all_records_for_chart method
- `bot_launcher.py` - Version update to 2.4.13
- `CloneHeroScoreTracker_v2.4.13.spec` - New spec file for v2.4.13 build
- `CloneHeroScoreBot_v2.4.13.spec` - New spec file for v2.4.13 build

### New Files
- `CHANGELOG_v2.4.13.md` - This file
- `C:\Users\[username]\AppData\Local\Temp\clone_hero_tracker.lock` - Lock file (created at runtime)

## Known Issues

None reported for this release.

## User Experience Improvements

This release represents a significant polish pass based on user feedback:

1. **Clearer Communication:** Enhanced messages throughout the client provide better context about what's happening
2. **Reliability:** Single-instance protection prevents confusing multi-client scenarios
3. **Discoverability:** /lookupsong now shows complete record information, making competition more visible
4. **Stability:** Multiple crash fixes ensure the client starts and runs reliably
5. **Intuitive Behavior:** Minimize button approach is more familiar than intercepting 'X' button

## Acknowledgments

Special thanks to the Clone Hero community and enchor.us for chart metadata support.

## What's Next?

Future considerations (not planned for immediate release):
- Auto-update system improvements
- Additional Discord command enhancements
- Performance optimizations for large score databases

---

**Full Changelog:** [v2.4.12...v2.4.13](https://github.com/Dr-Goofenthol/CH_HiScore/compare/v2.4.12...v2.4.13)

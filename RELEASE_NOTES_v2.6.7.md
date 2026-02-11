# Clone Hero Score Tracker - v2.6.7 Release Notes

**Release Date:** February 10, 2026
**Release Type:** Patch - Bug Reporting Tool, Large Library Support & Path Detection Fixes

---

## Overview

Version 2.6.7 is a focused patch release that improves the debugging and support experience for both users and developers. It introduces a one-command bug report generator, dramatically improves on-demand chart scanning for users with very large song libraries (30,000+ songs), and fixes an underlying path detection bug that caused the client log file to appear in the wrong location for users with non-standard Windows Documents folder configurations.

---

## New Features

### `bugreport` Command

A new command that automatically assembles everything needed to file a GitHub issue — no manual log hunting required.

**Usage:**
```
> bugreport
```

**What it collects:**
- Tracker version and OS details
- Status of all key paths: data directory, docs directory, log file (with size), state file (with score count), song cache, and chart index — all labelled `[EXISTS]` or `[MISSING]`
- Sanitized settings: bot URL, OCR, startup, songs folder (auth tokens are never included)
- Whether the client is paired
- Last 200 lines of `score_tracker.log` pasted inline

**What it produces:**

A single timestamped file — `CH_BugReport_20260210_153012.txt` — saved to your Desktop (with OneDrive Desktop support). After saving, it prints step-by-step instructions and asks:

```
Open GitHub issues page now? [Y/n]:
```

Typing `Y` opens `https://github.com/Dr-Goofenthol/CH_HiScore/issues/new` directly in your browser. Drag the report file into the issue and you're done.

---

## Fixes & Improvements

### On-Demand Scan: Large Library Support

**Problem:** `find_chart_by_hash_on_demand` had a 10-second timeout. For users with 35,000+ songs (not uncommon in the Clone Hero community), this is far too short — a 35k library on an SSD takes ~35 seconds to scan, and significantly longer on an HDD or network drive.

**Fixes:**
- **Timeout raised from 10s → 60s** (both the default parameter and the call site in `on_new_score`)
- **Live progress counter** updates every 100 charts: `Searching: D:\Songs\GH RB (3,400 charts, 28s)...`
- **Full folder path displayed** instead of just the folder name — `D:\Games\Songs\GH RB` instead of `GH RB`
- **Large-library tip on timeout**: if more than 5,000 charts were scanned before timing out, the client now prints: *"Your library is very large. Run 'scancharts' to build a full index for instant lookups."*
- **Detailed logging**: scan start, per-folder progress, timeout with elapsed time and chart count, not-found with chart count

**Impact:** Users with large libraries will see meaningful progress instead of a hanging cursor, and get actionable guidance when the on-demand scan can't finish in time.

---

### Windows Documents Path Detection Fixed

**Problem:** `get_clone_hero_documents_dir()` and `get_client_logger()` both hardcoded `Path.home() / 'Documents' / 'Clone Hero'` as the Windows Documents path. On systems where Documents has been redirected — via OneDrive Known Folder Move, manual folder relocation, or enterprise group policy — this path could point to the wrong location.

**Symptom:** The tracker would create an empty `C:\Users\username\Documents\Clone Hero\` folder and write `score_tracker.log` there, while Clone Hero's actual documents were at `D:\Documents\Clone Hero` (or `C:\Users\username\OneDrive\Documents\Clone Hero`). Users looking in their "real" Documents folder would see no log.

**Fix:**
Both `get_clone_hero_documents_dir()` (in `clone_hero_client.py`) and `get_client_logger()` (in `shared/logger.py`) now read the actual Documents path from the Windows registry:

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Personal
```

This is the same source Windows Explorer uses, and correctly reflects any folder redirection. The standard `Path.home() / 'Documents'` path is kept as a fallback if the registry lookup fails.

**Impact:** The log file and all metadata lookups now consistently target the correct Clone Hero documents folder, regardless of how the user has configured Windows folder locations.

---

### Startup: Log File Path Printed to Console

On every startup, the tracker now prints the exact path where `score_tracker.log` is being written:

```
[i] Debug log: C:\Users\Jake\Documents\Clone Hero\score_tracker.log
```

This eliminates the guesswork of finding the log file when a user needs to share it for support.

---

## Technical Details

### Modified Files

**Client:**
- `clone_hero_client.py` — `bugreport` command, `find_chart_by_hash_on_demand` timeout/progress/logging, `get_clone_hero_documents_dir` registry fix, startup log path print

**Shared:**
- `shared/logger.py` — `_get_windows_documents_dir()` helper using Windows registry; `get_client_logger()` uses it instead of hardcoded path

**Bot:**
- `bot/config_manager.py` — BOT_VERSION bumped to "2.6.7" (no config or behavior changes)

### New Files
- `CloneHeroScoreTracker_v2.6.7.spec` — PyInstaller build spec for client
- `CloneHeroScoreBot_v2.6.7.spec` — PyInstaller build spec for bot

### Config Version
- **Unchanged** — CONFIG_VERSION remains 9; no config structure changes
- **No migration required**

---

## Installation

### For Server Admins (Bot):

1. Download `CloneHeroScoreBot_v2.6.7.exe` from this release
2. Replace your existing bot executable
3. No config changes — starts normally

### For Players (Client):

1. Download `CloneHeroScoreTracker_v2.6.7.exe` from this release
2. Replace your existing client executable
3. No state file changes — your personal bests and pairing are preserved

---

## Upgrade Notes

### From v2.6.6:

✅ **Safe to upgrade** — no breaking changes

- No config migration required
- No database migrations required
- Client state files unchanged — no re-pairing needed

### From v2.6.5 or Earlier:

✅ **Automatic migration** — all config versions from v6 onward migrate automatically in sequence

---

## Known Issues

None specific to v2.6.7.

For general known issues and troubleshooting, see:
- [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- CLAUDE.md "Important Quirks & Gotchas" section

---

## Full Changelog

### Added
- **Client:** `bugreport` command — generates `CH_BugReport_<timestamp>.txt` on Desktop with full diagnostics and offers to open GitHub Issues in browser
- **Client:** Startup console print of `score_tracker.log` path

### Fixed
- **Client:** `find_chart_by_hash_on_demand` timeout raised from 10s to 60s for large libraries
- **Client:** `find_chart_by_hash_on_demand` now shows full folder path and live chart count
- **Client:** `find_chart_by_hash_on_demand` prints large-library tip when timing out with >5,000 charts scanned
- **Client:** `get_clone_hero_documents_dir()` now uses Windows registry to find the real Documents path
- **Shared:** `get_client_logger()` now uses Windows registry to find the real Documents path for `score_tracker.log`

### Changed
- **Client:** VERSION updated to "2.6.7"
- **Bot:** BOT_VERSION updated to "2.6.7"

---

## Links

- **GitHub Repository:** https://github.com/Dr-Goofenthol/CH_HiScore
- **Latest Release:** https://github.com/Dr-Goofenthol/CH_HiScore/releases/tag/v2.6.7
- **Issues & Feedback:** https://github.com/Dr-Goofenthol/CH_HiScore/issues

---

## Acknowledgments

Special thanks to:
- Users who reported the log file not appearing in their expected Documents folder
- The french server players whose debug screenshots revealed the on-demand scan timeout issue

---

**Version:** v2.6.7
**Released:** February 10, 2026
**Build Date:** 2026-02-10
**License:** MIT

---

Made with ❤️ for the Clone Hero community

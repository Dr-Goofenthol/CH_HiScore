# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Discord bot-based high score tracking system for Clone Hero that automatically detects new scores and posts announcements to Discord. The system consists of two executables:

1. **Client** (CloneHeroScoreTracker): Monitors local Clone Hero score files and submits to bot API
2. **Bot** (CloneHeroScoreBot): Discord bot with HTTP API for receiving scores and managing leaderboards

## Multi-PC Development Note

**IMPORTANT:** Development on this project occurs across multiple PCs. When switching machines:

1. **Pull from GitHub** to get the latest code
2. **Download shared package from GitHub** if missing:
   - `shared/parsers.py`
   - `shared/console.py`
   - `shared/logger.py`
   - `shared/__init__.py`
3. **Install all dependencies** (see Prerequisites below)
4. **Test builds** before committing

If you encounter `ModuleNotFoundError` for `shared` or other packages, ensure all files are present and dependencies are installed.

## Building the Project

### Prerequisites

**Required Python packages:**
```bash
py -m pip install colorama requests watchdog pystray pillow python-dotenv discord.py aiohttp
```

These packages are essential for PyInstaller to bundle all dependencies correctly.

### Building Executables

Update version numbers first in both files:
- `clone_hero_client.py` - Set `VERSION = "X.Y.Z"`
- `bot_launcher.py` - Set `VERSION = "X.Y.Z"`

Build client:
```bash
py -m PyInstaller CloneHeroScoreTracker_v{VERSION}.spec --noconfirm
```

Build bot:
```bash
py -m PyInstaller CloneHeroScoreBot_v{VERSION}.spec --noconfirm
```

Outputs are placed in `dist/` directory.

### Running from Source

Client:
```bash
py clone_hero_client.py
```

Bot:
```bash
py bot_launcher.py
```

## Architecture

### Two-Component System

**Client → Bot API → Discord**

1. Client watches `scoredata.bin` for file changes
2. Parses binary format to extract scores
3. Sends HTTP POST to bot API with score data
4. Bot validates, stores in SQLite, and posts Discord announcements

### Key Data Flow

```
Clone Hero (writes) → scoredata.bin
                           ↓
CloneHeroWatcher (monitors) → ScoreDataParser (parses)
                           ↓
                    HTTP POST /api/score
                           ↓
Bot API (validates) → Database (stores) → Discord (announces if record)
```

### Pairing System

Users link their client to Discord identity via 6-digit codes:
1. Client requests code from bot API
2. User runs `/pair <code>` in Discord
3. Bot returns auth token to client
4. Client stores token and includes in all future requests

## Critical Architecture Details

### Clone Hero Binary File Formats

All integers are **little-endian**.

**scoredata.bin structure:**
- Header (4 bytes) + Song Count (4 bytes)
- For each song:
  - Chart Hash (16 bytes) - blake3 hash, NOT MD5 despite variable names
  - Instrument Count (1 byte)
  - Play Count (3 bytes)
  - For each instrument:
    - Instrument ID (2 bytes):
      - **Confirmed:** 0=Lead Guitar, 1=Bass, 2=Rhythm, 3=Keys, 4=Drums, 5=GH Live Guitar, 6=GH Live Bass
      - **Partially Confirmed:** 8=Co-op Mode (observed: both players on lead guitar - Dec 2025)
      - **Needs Verification:** 7=GH Live Rhythm(?), 9=Pro Drums(?), 10=Guitar Co-op(?)
      - Note: ID 8 confirmed via user testing - co-op gameplay with both players on lead guitar
      - Note: Exact naming for ID 8 TBD (could be "Guitar Co-op", "Lead Co-op", or general "Co-op")
      - IDs 7, 9, 10 are educated guesses based on Clone Hero's documented instrument types
      - Unknown IDs will display as "Unknown (ID X)" in announcements
    - Difficulty (1 byte): 0=Easy, 1=Medium, 2=Hard, 3=Expert
    - Completion Numerator/Denominator (2 bytes each)
    - Stars (1 byte): 0-5
    - Padding (4 bytes)
    - Score (4 bytes)

**Important:** The completion numerator/denominator is NOT notes hit/total. It's a different metric.

### Song Metadata Sources

Priority order (from highest to lowest):

1. **currentsong.txt** - Authoritative source written by Clone Hero during play
   - Problem: Clone Hero clears this file when song ends
   - Solution: Background polling thread caches values while playing
   - Location: `Documents\Clone Hero\currentsong.txt`

2. **OCR Results Screen** - Fallback for additional data
   - Uses Windows built-in OCR (winocr)
   - Captures notes hit/total and best streak
   - Only used if currentsong.txt fails

3. **Chart Hash** - Last resort identifier
   - Displayed as `[abc12345]` (first 8 chars)

### Database Schema

**users** - Discord accounts linked to clients
- `discord_id` (unique), `auth_token`, `discord_username`

**scores** - All score submissions
- `user_id`, `chart_hash`, `instrument_id`, `difficulty_id`, `score`
- `completion_percent`, `stars`, `notes_hit`, `notes_total`
- `submitted_at`

**songs** - Song metadata cache
- `chart_hash` (unique), `title`, `artist`, `album`, `charter`, `length_ms`

**record_breaks** - History of records broken
- `user_id`, `chart_hash`, `instrument_id`, `difficulty_id`
- `new_score`, `previous_score`, `previous_holder_id`, `broken_at`
- Used for Discord announcements and `/recent` command

**pairing_codes** - Temporary codes for client/Discord linking
- 6-character codes (34-char alphabet: excludes confusing chars like 0/O, I/1)
- 5-minute expiration
- One-time use (`completed` flag prevents reuse)
- Generated with `secrets.choice()` for cryptographic security

### State Management

**Client State File** (`.score_tracker_state.json` in Clone Hero directory):
- Tracks `known_scores` as `Dict[str, int]` (key → score value)
- Key format: `"{chart_hash}:{instrument_id}:{difficulty_id}"`
- Critical: Must track score VALUES not just keys to detect offline plays

**Why Dict not Set:** Originally used Set, which caused bug where offline plays weren't detected if key already existed. Changed to Dict to compare score values.

**Record Breaking Logic:**
- `is_high_score = True`: New personal best or first time on chart
- `is_record_broken = True`: Beat an existing server record ONLY
- First-time scores don't trigger Discord announcements (not a "broken" record)
- Only scores that beat previous holders get announced

### Configuration Persistence

**Client:** Settings stored in Clone Hero directory (`%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\`)
- `.score_tracker_config.json` - Auth token, client ID
- `.score_tracker_settings.json` - Bot URL, paths, OCR settings
- `.score_tracker_state.json` - Known scores

**Bot:** Settings stored in AppData Roaming for persistence across updates
- Windows: `%APPDATA%\CloneHeroScoreBot\bot_config.json`
- Contains Discord token, channel IDs, API port, debug password
- Database also in same location: `%APPDATA%\CloneHeroScoreBot\scores.db`
- Automatic migration from old location (exe directory) on first run with v2.4+

## Common Development Commands

### Building Specific Version

When incrementing version, use these exact commands:

```bash
# Update VERSION in both files first
# Then rename spec files (or create copies)
ren CloneHeroScoreTracker_v2.4.11.spec CloneHeroScoreTracker_v2.4.12.spec
ren CloneHeroScoreBot_v2.4.11.spec CloneHeroScoreBot_v2.4.12.spec

# Build with new specs
py -m PyInstaller CloneHeroScoreTracker_v2.4.12.spec --noconfirm
py -m PyInstaller CloneHeroScoreBot_v2.4.12.spec --noconfirm
```

### Testing

Test score parser:
```bash
py -c "from shared.parsers import ScoreDataParser; parser = ScoreDataParser('path/to/scoredata.bin'); print(parser.parse())"
```

Test database operations:
```bash
py -c "from bot.database import ScoreDatabase; db = ScoreDatabase('test.db'); db.create_tables()"
```

Run migration manually:
```bash
py run_migration.py
```

Analyze scoredata.bin:
```bash
py analyze_scoredata.py <path_to_scoredata.bin>
```

Check installed dependencies:
```bash
py -m pip show colorama discord.py aiohttp watchdog winocr pystray
```

### Debug Mode

Client debug mode (requires password authorization from bot):
```bash
> debug
Enter debug password: [get from bot config]
debug> send_test_score -song "Test" -score 50000
debug> testocr
debug> status
debug> exit
```

## Code Architecture

### Shared Modules (`shared/`)

**parsers.py** - Binary parsers for Clone Hero files
- `ScoreDataParser` - Parses scoredata.bin (all scores)
- `SongCacheParser` - Parses songcache.bin (metadata)
- `parse_song_ini()` - Extract artist from song.ini files
- `get_artist_for_song()` - Hybrid artist extraction (song.ini + filepath patterns)

**console.py** - Colored console output
- `print_success()`, `print_info()`, `print_warning()`, `print_error()`
- ASCII only (no Unicode) for Windows console compatibility

**logger.py** - Structured logging
- `get_client_logger()` / `get_bot_logger()`
- Logs to `Documents\Clone Hero\score_tracker.log`

### Client Modules (`client/`)

**file_watcher.py** - Core score detection
- `CloneHeroWatcher` - Monitors scoredata.bin with watchdog
- `initialize_state()` - Sets up known_scores on first run
- `catch_up_scan()` - Detects offline scores on restart
- Debounces file writes (Clone Hero writes multiple times per save)

**ocr_capture.py** - Results screen OCR
- `capture_and_extract()` - Captures Clone Hero window, runs OCR
- Uses Windows OCR (winocr) - no Tesseract needed
- Extracts: notes hit/total, best streak, song title, artist
- Window detection excludes tracker's own window

### Bot Modules (`bot/`)

**bot.py** - Discord commands
- Slash commands: `/pair`, `/leaderboard`, `/mystats`, `/recent`, `/lookupsong`, `/updatesong`, `/setartist`, `/missingartists`
- Command sync: Instant if `DISCORD_GUILD_ID` set, 1 hour globally

**api.py** - HTTP API server (aiohttp)
- `POST /api/score` - Submit score (requires auth_token in header)
- `POST /api/pair/request` - Request pairing code (returns 6-digit code)
- `GET /api/pair/status/{client_id}` - Poll for pairing completion (returns auth_token when paired)
- `POST /api/debug/authorize` - Authorize debug mode access (password protected)
- `GET /health` - Health check (returns bot status)

**Security:** All score submissions require `X-Auth-Token` header with valid token from pairing. Tokens are cryptographically secure (`secrets.token_urlsafe(32)`).

**database.py** - SQLite operations
- `ScoreDatabase` - All database operations
- Methods: `add_score()`, `get_leaderboard()`, `get_user_stats()`, etc.
- Thread-safe (uses connection per operation)

**migrations.py** - Database schema migrations
- `run_migrations()` - Applies pending migrations
- Automatic on bot startup
- Important: chart_md5 → chart_hash terminology migration (v2.4.2)

**config.py** - Configuration loader (reads from environment variables set by launcher)

## Important Quirks & Gotchas

### 1. currentsong.txt Timing Issue

Clone Hero clears `currentsong.txt` when song ends, but `scoredata.bin` is written AFTER. Solution: Background thread polls currentsong.txt every second and caches values.

### 2. Chart Hash Terminology

The identifier is called `chart_md5` in some old code and `chart_hash` in new code. It's actually a **blake3 hash**, not MD5. Migration to `chart_hash` happened in v2.4.2.

**Database constraint:** `UNIQUE(chart_hash, instrument_id, difficulty_id, user_id)` ensures one score per user per chart/instrument/difficulty combo. Uses `INSERT ... ON CONFLICT DO UPDATE` for automatic upsert.

### 3. Completion Numerator/Denominator

The values in scoredata.bin are NOT notes hit/total. They're a different metric. Notes data only comes from OCR.

### 4. State File Migration

Old format: `Set[str]` of keys
New format: `Dict[str, int]` of key → score value

Migration is automatic but silent. Check `needs_state_migration()`.

### 5. PyInstaller Hidden Imports

Windows OCR requires many hidden imports (see `.spec` files):
- All WinRT modules (`winsdk.windows.*`)
- `pystray._base`, `pystray._win32`
- `aiohttp`, `discord`, `watchdog` internals
- `colorama.win32`, `colorama.winterm` (console colors)

**Important:** The `.spec` files may be incomplete. If runtime errors occur about missing modules, add them to the `hiddenimports` list in the appropriate `.spec` file.

### 6. Config File Locations

Critical for persistence across exe updates:
- Client: Config in Clone Hero directory (survives exe replacement)
- Bot: Config in AppData Roaming (survives exe replacement)

Never store config next to the exe when using PyInstaller.

### 7. File Monitoring Debouncing

Clone Hero writes `scoredata.bin` multiple times per save operation. The watcher uses a 2-second debounce delay to ensure all writes complete before parsing. Without this, partial reads can cause parse errors or miss data.

### 8. Clone Hero Settings.ini Format

Clone Hero uses standard INI format with sections like `[directories]`, `[game]`, `[streamer]`, etc. Song folder paths are typically stored as:

```ini
[directories]
path0=D:\Games\Clone Hero\songs
path1=E:\More Songs
```

**Always use `configparser.ConfigParser()`** to read this file, never manual line-by-line parsing. The resolvehashes command relies on correctly reading these paths.

### 9. Charter Data Pipeline

Charter information flows through multiple stages:

1. **Collection:** Read from `currentsong.txt` line 3 during gameplay (cached by background thread)
2. **Submission:** Sent to bot API via `POST /api/score` with `song_charter` parameter
3. **Storage:** `submit_score()` → `save_song_info()` saves to database `songs.charter` field
4. **Resolution:** `resolvehashes` command extracts from `song.ini` for missing data
5. **Display:** Included in Discord announcements and Enchor.us search links

**Critical:** All stages must pass charter through. Missing any link breaks the chain.

### 10. Debugging Methodology

When debugging complex issues like resolvehashes:

1. **Add extensive debug output** at each step of the pipeline
2. **Test with known data** (specific song hash you know exists)
3. **Check for silent failures** (exception handlers that swallow errors)
4. **Verify imports** (missing imports cause NameError at runtime)
5. **Remove debug output** before production release

Example from v2.4.15 debugging:
- Hash was correctly calculated ✓
- Hash was in unresolved list ✓
- Match logic worked ✓
- But `parse_song_ini` wasn't imported ✗ (silent failure in exception handler)

## Database Migrations

Migrations run automatically on bot startup. To add a new migration:

1. Edit `bot/migrations.py`
2. Add migration function (e.g., `migrate_v2_to_v3`)
3. Add to `run_migrations()` function
4. Test with standalone script: `py run_migration.py`

Example:
```python
def migrate_v2_to_v3(db_path: Path):
    """Add new column to scores table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE scores ADD COLUMN new_field TEXT")
    conn.commit()
    conn.close()
```

**Migration naming convention:** `migration_00X_descriptive_name()` where X is sequential number. Always check existing migrations before adding new ones.

## Release Process

1. Update `VERSION` in both `clone_hero_client.py` and `bot_launcher.py`
2. Rename `.spec` files to match new version if needed:
   - `CloneHeroScoreTracker_v{VERSION}.spec`
   - `CloneHeroScoreBot_v{VERSION}.spec`
3. Build both executables with updated spec files
4. Test locally (pairing, score submission, Discord announcements)
5. Create GitHub release with tag `vX.Y.Z`
6. Attach both exe files to release with consistent naming:
   - `CloneHeroScoreTracker_v{VERSION}.exe`
   - `CloneHeroScoreBot_v{VERSION}.exe`
7. Auto-update system will notify users on next launch

**Critical:** All three version numbers must match (client VERSION, bot VERSION, and spec filenames). The auto-updater relies on GitHub release asset names containing "Tracker" or "Bot" to identify the correct executable.

## Testing Notes

### Manual Testing Checklist

1. Start bot, verify Discord connection
2. Start client, complete pairing with `/pair`
3. Play a song in Clone Hero
4. Verify score appears in client console
5. Verify Discord announcement (if record)
6. Check `/leaderboard` and `/mystats` commands
7. Test offline: Stop bot, play song, restart bot, run `resync`
8. Test OCR: Enable in settings, verify results screen capture

### Common Test Scenarios

**First-time setup:** Delete config files and state file, restart
**Migration:** Use old database/state file from previous version
**Offline play:** Network disconnect during gameplay
**Multiple machines:** Pair two clients to same Discord account

## Client Commands

### resolvehashes Command

Scans local song folders to populate missing charter information in the database.

**How it works:**
1. Fetches list of chart hashes with missing/incomplete metadata from server
2. Reads Clone Hero's `settings.ini` to find song folder paths
3. Walks all song folders, calculating MD5 hash of each chart file
4. Matches hashes against server's unresolved list
5. Extracts metadata (title, artist, charter) from `song.ini` files
6. Sends updates to server with user confirmation

**Important implementation details:**
- Uses `configparser.ConfigParser()` to read settings.ini (handles INI sections properly)
- Searches ALL sections for `path0`, `path1`, `path2` entries (typically in `[directories]` section)
- Uses `parse_song_ini()` from `shared.parsers` to extract metadata
- User-filtered: only resolves hashes for songs the current user has played
- Hashes chart files (`notes.chart`, `notes.mid`, `notes.midi`) using MD5

**Common issues:**
- Missing `parse_song_ini` import causes silent failure (all matches fail with NameError)
- Manual line-by-line parsing of settings.ini can't handle sectioned INI format
- Overly broad exception handling can hide errors (always check what's inside try/except blocks)

## Version History & Migration Notes

**v2.5.3** - Announcement Customization & Bug Fixes (Dec 2025)
- **NEW:** Full mode field customization - all announcement fields now configurable
  - Added `full_fields` config section for record_breaks, first_time_scores, personal_bests
  - Admins can toggle any field on/off in full mode (song, artist, charter, accuracy, etc.)
  - Footer components fully customizable (previous holder, score, held duration, timestamp)
- **FIXED:** Previous record holder mentions not working in minimalist mode
  - Both full and minimalist modes now respect `ping_previous_holder` config
- **IMPROVED:** Extended instrument ID support (IDs 0-10)
  - Added GH Live instruments (IDs 5-6 confirmed)
  - Added co-op/pro drums support (IDs 7-10 educated guesses)
  - **ID 8 partially confirmed:** Co-op mode (both players on lead guitar) via user testing
- **FIXED:** Client terminal output for tied scores
  - Fixed confusing "-0 pts gap" message when matching your own PB
  - Gap calculation corrected (was showing backwards)
  - Clearer status messages: "Tied with your personal best" vs "Below your personal best"
- **ENHANCED:** Settings menu with full mode field customization options
- **ENHANCED:** Preview generator respects both full and minimalist field configurations
- CONFIG_VERSION: 5 (auto-migration from v4)

**v2.4.15** - Critical Bugfix (resolvehashes command)
- **FIXED:** resolvehashes command now functional (was completely broken)
  - Added missing `parse_song_ini` import
  - Fixed settings.ini parser to use `configparser.ConfigParser()` instead of manual line-by-line
  - Successfully tested resolving 116+ songs with complete metadata
- Charter data pipeline fully operational (currentsong.txt → database → Enchor.us links)
- User-filtered hash resolution (only scans for your songs, not all server users)

**v2.4.12** - Discord Announcement Enhancements
- Added charter name display as separate inline field in announcements
- Added play count tracking and display in announcements
- Added "Held for X days/hours/minutes" to previous record footer
- Improved Discord announcement layout (3-field rows: Instrument|Difficulty|Stars, Charter|Accuracy|Play Count)
- Enhanced enchor.us link generation with charter parameter
- Fixed Unicode encoding issues in console output (changed ✓ to ASCII +)
- Fixed type annotation issues in OCR module (added `from __future__ import annotations`)

**v2.4.11** - Security & UX Enhancements
**v2.4.8** - Bug Fixes (chart hash truncation in embeds)
**v2.4.5** - Migration timing fix
**v2.4.4** - Discord command improvements
**v2.4.2** - chart_md5 → chart_hash migration (BREAKING: requires DB migration)
**v2.4** - Config persistence in AppData
**v2.3** - Auto-update system
**v2.2** - System tray and Windows startup
**v2.1** - Windows OCR integration
**v2.0** - Artist name extraction

## GitHub Repository

URL: https://github.com/Dr-Goofenthol/CH_HiScore

Auto-update checks this repo on startup for both client and bot.

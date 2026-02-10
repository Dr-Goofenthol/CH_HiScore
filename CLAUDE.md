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
py -m pip install colorama requests watchdog pystray pillow python-dotenv discord.py aiohttp tzdata
```

These packages are essential for PyInstaller to bundle all dependencies correctly.

**Note:** `tzdata` is required for timezone support on Windows (activity log scheduling and display).

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

## Discord Bot Setup Requirements

### Required Discord Intents

**CRITICAL:** When creating the Discord bot application, the following intents MUST be enabled in the Discord Developer Portal:

1. **Server Members Intent** - Required for user lookups and username resolution
2. **Message Content Intent** - Required for bot functionality

**Where to enable:**
1. Go to https://discord.com/developers/applications
2. Select your application
3. Go to **"Bot"** section in left sidebar
4. Scroll down to **"Privileged Gateway Intents"**
5. Toggle ON:
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**

**Note:** These intents are set in `bot/bot.py` lines 240-243:
```python
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
```

Without these intents enabled in the Discord Developer Portal, the bot will fail to start or experience limited functionality.

### Bot Permissions (OAuth2 Scopes & Permissions)

**Scopes** (for invite URL):
- `bot` - Allow bot to join servers
- `applications.commands` - Enable slash commands

**Bot Permissions** (minimum required):
- Send Messages
- Embed Links
- Use Slash Commands

**Invite URL Format:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&permissions=2048&scope=bot%20applications.commands
```

### First-Time Setup Wizard

The bot includes a comprehensive setup wizard (`bot_launcher.py` lines 366-632) that prompts for:

1. **Discord Bot Token** - Secret token from Bot settings
2. **Discord Application ID** - Numeric ID from General Information
3. **Discord Guild ID** (optional but recommended) - Server ID for instant command sync
4. **Announcement Channel ID** - Channel where scores will be posted
5. **API Port** - Port for client connections (default: 8080)
6. **Debug Password** - Password for client debug mode access
7. **Display Settings** - Timezone and time format preferences
8. **Announcement Preferences** - Which score types to announce

**Command Sync Behavior:**
- **WITH Guild ID:** Slash commands appear INSTANTLY after bot restart
- **WITHOUT Guild ID:** Slash commands take up to 1 HOUR to appear globally

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

**IMPORTANT:** See comprehensive schema reference in `bot/database.py` header comments. This is the authoritative source.

**users** - Discord accounts linked to clients
- `id`, `discord_id` (unique), `discord_username`, `auth_token`
- `created_at`, `last_seen`

**scores** - All score submissions
- `id`, `user_id`, `chart_hash`, `instrument_id`, `difficulty_id`, `score`
- `completion_percent`, `stars`, `submitted_at`
- `is_full_combo` (v2.6.0), `notes_total` (v2.6.0)
- **NO** `play_count`, **NO** `notes_hit` (calculated: `completion_percent * notes_total`)

**songs** - Song metadata cache
- `id`, `chart_hash` (unique), `title`, `artist`, `album`, `charter`, `length_ms`, `first_seen`
- **NO** `genre` (genre is in `chart_metadata` table!)

**chart_metadata** - Parsed chart data (v2.6.0+)
- `id`, `chart_hash`, `instrument_id`, `difficulty_id`
- `total_notes`, `chord_count`, `tap_count`, `open_note_count`, `star_power_phrases`
- `song_length_ms`, `note_density`, `peak_note_density` (v2.6.3)
- `song_name`, `artist`, `charter`, `genre`
- `parsed_at`, `chart_file_path`
- `UNIQUE(chart_hash, instrument_id, difficulty_id)`

**record_breaks** - History of records broken
- `id`, `user_id`, `chart_hash`, `instrument_id`, `difficulty_id`
- `new_score`, `previous_score`, `previous_holder_id`, `broken_at`
- Used for Discord announcements and `/recent` command

**pairing_codes** - Temporary codes for client/Discord linking
- `id`, `code` (unique), `client_id`, `discord_id`, `auth_token`
- `created_at`, `expires_at`, `completed`
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

## Bot Configuration Migrations

**CRITICAL RULE:** Any time you make changes that affect the bot config structure, you MUST increment `CONFIG_VERSION` in `bot/config_manager.py` and create a corresponding migration.

### When to Increment CONFIG_VERSION

Increment `CONFIG_VERSION` whenever you:
1. **Add new config fields** (e.g., `peak_intensity_tiers`, new announcement settings)
2. **Change field structure** (e.g., converting string to dict, renaming fields)
3. **Add new default values** to existing sections
4. **Remove deprecated fields** (rare, but requires migration to clean up)

### How to Add a Config Migration

1. **Increment CONFIG_VERSION** in `bot/config_manager.py` (lines 18-19):
   ```python
   CONFIG_VERSION = 8  # Increment from 7 to 8
   BOT_VERSION = "2.6.5"  # Update to match release version
   ```

2. **Add migration check** in `_migrate_config()` method:
   ```python
   # Migration v7 -> v8 (v2.6.5)
   if from_version < 8:
       self._migrate_v7_to_v8()
   ```

3. **Create migration method** following this template:
   ```python
   def _migrate_v7_to_v8(self):
       """Migrate from v7 to v8 (add v2.6.5 features)"""
       print_info("[Config] Adding v2.6.5 features (description of changes)")

       default = self._create_default_config()

       # Add new config section if missing
       if 'new_section' not in self.config:
           self.config['new_section'] = default['new_section']
           print_success("[Config] Added new_section settings")

       # Add fields to existing announcements
       if 'announcements' in self.config:
           for announcement_type in ['record_breaks', 'first_time_scores', 'personal_bests', 'full_combos']:
               if announcement_type in self.config['announcements']:
                   if 'new_field' not in self.config['announcements'][announcement_type]:
                       self.config['announcements'][announcement_type]['new_field'] = default_value

       # Update config version
       self.config['config_version'] = 8
       print_success("[Config] v2.6.5 migration complete - all existing settings preserved!")
   ```

4. **Update default config** in `_create_default_config()` to include new fields

5. **Test migration** by:
   - Copying production config from `debug/` folder
   - Running bot to trigger migration
   - Verifying new fields appear correctly
   - Checking settings menu displays new options

### Example: v6 → v7 Migration (v2.6.4)

**Problem:** Production configs at version 6 didn't have `peak_intensity_tiers`, but we added it to v6 migration. Migration didn't run because configs were already at v6.

**Solution:** Bumped to v7 and created `_migrate_v6_to_v7()`:
- Added `peak_intensity_tiers` with defaults (Calm/Spicy/Extreme/Ridiculous)
- Added `chart_intensity` and `peak_intensity` fields to all announcement types
- Set smart defaults (ON for record_breaks/full_combos, OFF for others in minimalist mode)

### Key Points

- **Never skip versions** - if current is v6, next must be v7 (not v8)
- **Always preserve user settings** - only add missing fields, never overwrite existing values
- **Use `if 'field' not in config`** checks to avoid clobbering user customizations
- **Print success messages** for each change so admins know what was migrated
- **Update config_version at end** of migration function
- **Test with real production config** from `debug/` folder before release

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

### Current Version: v2.6.6 (Feb 10, 2026)

**Key Features:**
- Historical score submissions toggle (`allow_historical_submissions`) — fresh-start servers can block resync/reset backfills
- Full metadata resolution pipeline: on-demand chart scan now populates `_chart_file_cache` so STEP 4 song.ini fallback always fires
- Offline score catch-up no longer triggers OCR (eliminates 500ms × N delay for large backlogs)
- Expanded client logging for remote debugging and support
- `status` command shows all configured Clone Hero directories and song folders
- Settings Menu → Server Admin: options to toggle suppress-resync-announcements and historical submissions
- **CONFIG_VERSION: 9** (adds `allow_historical_submissions` flag)

**v2.6.5** (Feb 2026)
- Setup wizard improvements, `parse` command for on-demand chart indexing
- `suppress_resync_announcements` config flag to silence Discord spam during resync/reset
- `save_basic_chart_metadata()` for inline NPS data without a full chart scan
- Migration 002/003 crash fixes for fresh bot installs
- **CONFIG_VERSION: 8**

**v2.6.4** (Jan 19, 2026)
- Chart Index System (`.score_tracker_chart_index.json`) with incremental scanning
- On-demand chart scanning for offline scores (98-99% metadata capture rate)
- Peak Intensity tiers (Calm/Spicy/Extreme/Ridiculous) and configurable announcement fields
- Timezone-aware activity log scheduling and display
- **CONFIG_VERSION: 7**

### Shelved Features (Future Consideration)

**Per-Chart Record History Page (Web Interface)**
- **What:** A dedicated page showing the full record-break history for a specific chart/instrument/difficulty — who held the record, at what score, and when it was broken
- **UX:** Clicking any score value anywhere on the website (leaderboard, activity feed, mystats, song search) would navigate to this chart history page
- **Data source:** Already exists in the `record_breaks` table (`new_score`, `previous_score`, `previous_holder_id`, `broken_at`)
- **Why shelved:** Deferred to avoid scope creep during initial web interface design; design pattern for score-click navigation needs to be consistent across all pages
- **When to revisit:** After core web pages are built and data API is in place; relatively straightforward since the data already exists

**Discord Username → Player Profile Linking (Web Interface)**
- **What:** Hyperlink any displayed Discord username on the site to that player's My Stats page
- **UX:** Username appears as a clickable link throughout the activity feed, leaderboard, song search results, etc.
- **Decision made:** My Stats will be a single per-user public page with a URL parameter (e.g., `/mystats?user=andrew_the_amigo`), no separate "public profile" page needed
- **When to revisit:** When implementing the web backend/routing layer

**Server Stats / Dashboard Page (Web Interface)**
- **What:** A server-wide statistics overview page — total scores submitted, total FCs, total record breaks, most played songs, most competitive songs (most record changes), activity heatmap by day/hour, newest and most recently active players
- **UX:** Accessible from main nav or as a new nav item; gives a bird's-eye view of server health and engagement
- **Data source:** Aggregated queries across `scores`, `record_breaks`, `users` tables
- **Why shelved:** No current equivalent Discord command; lower priority than per-user and per-song pages
- **When to revisit:** After core pages (activity, leaderboard, mystats, compare, song detail) are built

**Leaderboard Page Filters (Web Interface)**
- **What:** Add instrument and difficulty filter controls to the Server Leaderboard page
- **UX:** Filter pills or dropdowns: All Instruments / Lead / Bass / Drums / Keys; All Difficulties / Expert / Hard / Medium / Easy
- **Data source:** `scores.instrument_id`, `scores.difficulty_id`
- **Why shelved:** Mockup shows unfiltered view; filters require frontend JS or backend query params
- **When to revisit:** Minor enhancement once the leaderboard page is wired to real data

**My Stats Enhancements (Web Interface)**
- **My Records tab:** Within a player's stats page, a dedicated tab/section showing all charts where they currently hold the server record (Andrew has 23)
- **Head-to-head summary widget:** On a player's profile, show win/loss records vs each other server member ("You vs Jake: 34W / 22L across 58 shared charts") with a link to the Compare page
- **Score progression per chart:** Timeline of a user's score history on a specific chart — how their personal best improved over time
- **Why shelved:** Incremental improvements to the My Stats page; head-to-head widget requires compare-page logic to be built first
- **When to revisit:** After Compare page is implemented; head-to-head summary can reuse compare query logic

**Unresolved Hashes / Missing Metadata Page (Web Interface)**
- **What:** A page showing all chart hashes with missing or incomplete metadata (no title, artist, or charter)
- **UX:** Table of hashes with a hash-based enchor.us search link, "flag as identified" button, and admin ability to manually enter metadata
- **Data source:** Songs with null/empty title or artist in `songs` table; hashes not in `chart_metadata`
- **Maps to:** `missingartists` Discord command and `resolvehashes` client terminal command
- **Why shelved:** Admin/utility feature; not visible to regular users
- **When to revisit:** After core user-facing pages are complete; useful for server admins

**Achievements / Badges Page (Web Interface)**
- **What:** A formal achievements system showing all possible badges (Most Records, FC Master, Rising Star, Newcomer, etc.) with unlock criteria and progress bars
- **UX:** Gallery of achievement cards; unlocked ones highlighted, locked ones grayed with progress shown (e.g., "12 / 25 records for 'Record Hoarder'")
- **Why shelved:** Requires defining a formal achievement schema that doesn't currently exist in the database
- **When to revisit:** Requires design work to define achievement tiers and unlock conditions first

**Server Records Page (Web Interface)**
- **What:** Dedicated page showing every song that has a server record, who holds it, their score, and when it was set — sorted by most recently broken
- **UX:** Essentially the leaderboard filtered to only top scores per chart; can be sorted by date set, holder, or score value
- **Data source:** `record_breaks` table joined with `songs` and `users`
- **Why shelved:** Partially covered by the Server Leaderboard page; a pure "current records" view is a subset of the leaderboard
- **When to revisit:** Low-effort addition once the leaderboard page is built; just a filtered query

**Per-Player Activity Feed (Web Interface)**
- **What:** When viewing a player's profile page (`/mystats?user=X`), their Recent Activity tab shows only their own submissions rather than the full server activity feed
- **UX:** Same card-based layout as the main Recent Activity page but filtered to one user
- **Data source:** `scores` and `record_breaks` tables filtered by `user_id`
- **Why shelved:** The My Stats page already has a Recent Activity table section; a full card-based feed per player is an enhancement
- **When to revisit:** After the My Stats page is wired to real data with the user parameter

### Recent Releases

**Full release history and detailed changelogs:** See [GitHub Releases](https://github.com/Dr-Goofenthol/CH_HiScore/releases)

**v2.6.3** (Jan 4, 2026) - Username handling fixes, update notification crash fix
- See: `RELEASE_NOTES_v2.6.3.md`, `INVESTIGATION_USERNAME_HANDLING.md`

**v2.6.2** (Jan 1, 2026) - Combo breaker logic, accuracy cap, shutdown handling
- See: `RELEASE_NOTES_v2.6.2.md`, `migrate_fix_note_counts.py`

**v2.5.x** (Dec 2025) - UI/UX polish, field customization, terminal feedback
- See: `RELEASE_NOTES_v2.5.*.md` for detailed changelogs

**v2.4.15** (Dec 2024) - resolvehashes command fix, charter data pipeline
**v2.4.12** - Charter display, play count, enchor.us links
**v2.4.2** - chart_md5 → chart_hash migration (BREAKING)
**v2.4** - Config persistence in AppData (BREAKING)

### Critical Migration Notes

**Upgrading from <v2.4:** Config files moved to AppData Roaming. Bot will auto-migrate on first run.

**Upgrading from <v2.4.2:** Database migration renames `chart_md5` to `chart_hash`. Auto-applied on startup.

**Upgrading to v2.6.4:** First run prompts for chart scan to enable offline metadata capture (recommended).

**CONFIG_VERSION History:**
- v7 (v2.6.4): peak_intensity_tiers, announcement field toggles
- v6 (v2.6.x): Announcement customization system
- v5 (v2.5.x): Full/minimalist field configuration
- See `bot/config_manager.py` for migration details

## GitHub Repository

URL: https://github.com/Dr-Goofenthol/CH_HiScore

Auto-update checks this repo on startup for both client and bot.

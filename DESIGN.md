# Clone Hero High Score System - Design Document

## Project Overview
A Discord bot-based high score tracking system for Clone Hero that automatically detects new scores and updates a centralized leaderboard.

## Architecture

```
Local Client (Python)          Discord Bot (Python)              Database
     |                              |                              |
     |-- File Watcher               |-- HTTP API                   |-- SQLite/Postgres
     |-- Score Parser               |-- Discord Commands           |
     |-- HTTP Client                |-- Score Validation           |
     |                              |-- Leaderboard Logic          |
     +---> POST /api/score -------->+---> UPDATE scores ---------->+
                                    |
                                    +---> Discord Channel
                                          (High Score Announcements)
```

## Components

### 1. Local Client (`client/`)
- **File Watcher**: Monitors Clone Hero's score database for changes
- **Score Parser**: Extracts score data from Clone Hero's storage format
- **HTTP Client**: Sends score data to bot API
- **Pairing System**: One-time code to link local client to Discord identity

**Target**: Package as standalone `.exe` using PyInstaller

### 2. Discord Bot (`bot/`)
- **HTTP API**: REST endpoint to receive scores from clients
- **Discord Integration**: Posts high score announcements
- **Database Manager**: Handles score storage and queries
- **Pairing Manager**: Generates and validates pairing codes

### 3. Database
- **Users**: Discord ID, pairing token, username
- **Scores**: Song hash, player, score, accuracy, difficulty, modifiers, timestamp
- **Songs**: Chart hash, song name, artist, charter

## Clone Hero Data Structure

### Score Storage Location
- **Windows**: `%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\`
- **Mac**: `~/Library/Application Support/com.srylain.CloneHero`
- **Linux**: `~/.config/unity3d/srylain Inc_/Clone Hero`
- **Files**: `scoredata.bin` (scores) and `songcache.bin` (song metadata)

### scoredata.bin Binary Format
All integers use **little-endian** byte order.

```
[Header - 4 bytes]
[Song Count - 4 bytes]

For each song:
    [MD5 Checksum - 16 bytes]  (notes.mid file hash)
    [Instrument Count - 1 byte]
    [Play Count - 3 bytes]

    For each instrument:
        [Instrument ID - 2 bytes]  (0=lead, 1=bass, 2=rhythm, 3=keys, etc)
        [Difficulty - 1 byte]      (0=easy, 1=medium, 2=hard, 3=expert)
        [Completion Numerator - 2 bytes]
        [Completion Denominator - 2 bytes]
        [Stars - 1 byte]           (0-5)
        [Padding - 4 bytes]        (always 1)
        [Score - 4 bytes]
```

### songcache.bin Binary Format
```
[Header - 20 bytes]

For each category (Title, Artist, Album, Genre, Year, Charter, Playlist):
    [Marker - 1 byte]
    [Entry Count - 4 bytes]
    For each entry:
        [String Length - 1-2 bytes]  (variable-length encoding)
        [String Data - variable]

[Song Count - 4 bytes]

For each song:
    [Filepath - variable-length string]
    [Unknown Checksum - 16 bytes]
    [Filename - variable-length string]
    [Delimiter - 1 byte]
    [Metadata Indices - 16 bytes]  (4 bytes each for title, artist, album, genre, etc)
    [Unknown - 8 bytes]
    [Instrument Difficulties - 13 bytes]
    [Start Offset - 4 bytes]
    [Icon - variable-length string]
    [Unknown - 8 bytes]
    [Song Length - 4 bytes]  (milliseconds)
    [Unknown - 8 bytes]
    [Game - variable-length string]
    [Delimiter - 1 byte]
    [File Checksum - 16 bytes]  (PRIMARY KEY - matches scoredata MD5)
```

### Key Data Points Available
- Chart MD5 hash (unique song identifier)
- Score value
- Completion percentage (numerator/denominator)
- Difficulty (Easy/Medium/Hard/Expert)
- Instrument (Lead Guitar/Bass/Rhythm/Keys/Drums)
- Star rating (0-5)
- Play count per song
- Song metadata (title, artist, charter, length)

## Pairing System Flow

1. User runs client executable
2. Client generates unique ID, requests pairing code from bot
3. Bot generates 6-digit code, stores it with temp mapping
4. User runs Discord command: `/pair <code>`
5. Bot links code to Discord user, returns auth token
6. Client stores auth token locally for future use
7. All subsequent score submissions include auth token

## Anti-Cheat Considerations

- Store chart hash to prevent name spoofing
- Optional: Screenshot verification for disputed scores
- Rate limiting on score submissions
- Modifier tracking (disable scores with certain modifiers)

## Technology Stack

- **Python 3.14**
- **discord.py 2.6.4** - Discord bot framework
- **aiohttp 3.13.2** - HTTP API server
- **requests 2.32.5** - HTTP client for score submission
- **watchdog 6.0.0** - File system monitoring
- **python-dotenv 1.2.1** - Environment configuration
- **sqlite3** - Database (built-in, pending implementation)
- **PyInstaller** - Executable packaging (pending)

## Project Status

### Current Version: v2.2
**Status**: Production Ready - Full Documentation

### ✅ Completed (All Phases)
- [x] Research Clone Hero file structure
- [x] Set up project structure and documentation
- [x] Binary parser for scoredata.bin (fully functional)
- [x] Binary parser for songcache.bin (filepath-based title extraction)
- [x] File watcher with state tracking
- [x] Discord bot with slash commands
- [x] HTTP API for score submission
- [x] End-to-end integration (Clone Hero → Watcher → Bot API)
- [x] SQLite database with full schema
- [x] Persistent score storage
- [x] User pairing system (new + existing user flows)
- [x] High score comparison logic
- [x] Discord announcements for record breaks
- [x] Record breaks tracking
- [x] Enhanced `/leaderboard` with song titles
- [x] Enhanced `/mystats` with records and stats
- [x] Package as standalone executable (v1.0 - v1.4)
- [x] Multi-machine support
- [x] Debug mode with test scores

### ⏳ Future Enhancements (Optional)
- [ ] Artist name recovery (parse song.ini files)
- [ ] Offline score queue (when bot unavailable)
- [ ] Screenshot verification (optional)
- [ ] Weekly/monthly leaderboards

## Configuration Files

### Bot Config (`.env`)
**Location**: Project root
**Status**: ✅ Implemented

```env
# Discord Bot Token (from Discord Developer Portal)
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_APP_ID=your_application_id_here

# Discord Server Settings
DISCORD_GUILD_ID=your_server_id_here
DISCORD_CHANNEL_ID=your_channel_id_for_announcements

# API Settings
API_HOST=localhost
API_PORT=8080
API_SECRET_KEY=change_this_to_a_random_string_later

# Database
DATABASE_PATH=bot/scores.db
```

### Client State File (`.score_state.json`)
**Location**: `client/` directory
**Status**: ✅ Auto-generated
**Purpose**: Tracks which scores have been seen to avoid duplicates

```json
{
  "known_scores": [
    "ecd1c69af09ebeec96a4ad24754f3eed:0:1",
    "chart_md5:instrument_id:difficulty"
  ],
  "last_updated": 1234567890.123
}
```

## Notes

- Clone Hero uses MD5 hashes for chart identification
- Scores are stored in **binary format** (scoredata.bin), NOT SQLite
- Song metadata is stored separately in songcache.bin
- Need to handle both online and offline mode (queue scores if bot is unreachable)
- Consider supporting multiple Clone Hero installations/profiles
- Reference implementation: https://github.com/coolcarp/clonehero-score-exporter

## Implementation Strategy

### Phase 1: Score Parser (Current)
1. Create binary parser for scoredata.bin
2. Create binary parser for songcache.bin
3. Combine data from both files to get complete score information

### Phase 2: File Watcher
1. Monitor scoredata.bin for file modifications
2. When changed, parse and extract new/updated scores
3. Compare with cached state to detect only new high scores

### Phase 3: Discord Bot & API
1. Set up Discord bot with HTTP API endpoint
2. Implement pairing code system
3. Design database schema
4. Implement score submission and validation

### Phase 4: Packaging
1. Package as standalone executable with PyInstaller
2. Test on multiple systems
3. Create simple setup/configuration UI

## Current Implementation Details

### Discord Bot Commands (Implemented)
**Status**: ✅ Fully Working

1. **`/ping`** - Health check command
   - Returns latency in milliseconds
   - Ephemeral (only visible to user)

2. **`/pair <code>`** - Pairing command
   - Accepts 6-digit pairing code
   - Links Discord user to Clone Hero client
   - Returns auth token to client

3. **`/leaderboard [difficulty] [instrument]`** - View high scores
   - Optional filters for difficulty and instrument
   - Shows song titles (from filepath extraction)
   - Displays top 10 record holders

4. **`/mystats`** - Personal statistics
   - Total scores, records held, record breaks
   - Total points, average accuracy, average stars
   - Top 5 records held with song titles

### HTTP API Endpoints (Implemented)
**Status**: ✅ Fully Working
**Base URL**: `http://localhost:8080`

1. **`GET /`** - API information
2. **`GET /health`** - Health check (returns bot connection status)
3. **`POST /api/score`** - Submit a score
   - Validates auth token
   - Checks for record breaks
   - Stores in database
   - Posts Discord announcement if record broken
   - Returns result (is_high_score, is_record_broken, etc.)
4. **`POST /api/pair/request`** - Request pairing code
   - Generates 6-character code
   - Stores with 5-minute expiration
5. **`GET /api/pair/status/{client_id}`** - Check pairing status
   - Returns auth token when pairing complete

### File Structure
```
CH_HiScore/
├── .env                    # Bot configuration (gitignored)
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
├── DESIGN.md              # This file
├── README.md              # User documentation
│
├── shared/                # Shared code between client and bot
│   ├── __init__.py
│   └── parsers.py         # Binary parsers for Clone Hero files
│
├── client/                # Local client application
│   ├── __init__.py
│   ├── file_watcher.py    # File monitoring and score detection
│   └── .score_state.json  # State tracking (auto-generated)
│
├── bot/                   # Discord bot
│   ├── __init__.py
│   ├── config.py          # Configuration loader
│   ├── bot.py             # Main bot with Discord commands
│   ├── api.py             # HTTP API server
│   └── scores.db          # SQLite database (pending)
│
└── Test Scripts:
    ├── run_bot.py         # Launch Discord bot
    ├── test_parser.py     # Test score parsing
    ├── test_watcher.py    # Test file watcher + API integration
    ├── test_api.py        # Test API endpoints
    └── get_discord_ids.py # Get server/channel IDs
```

## Session Log

### Session 1 - 2025-11-20
**Duration**: ~4 hours
**Status**: Core integration complete

**Phase 1: Research & Parsing**
- Initial project setup and architecture design
- Researched Clone Hero file structure
- Discovered binary format (scoredata.bin and songcache.bin)
- Documented complete binary format specifications
- Found reference implementation (coolcarp/clonehero-score-exporter)
- Successfully implemented scoredata.bin parser
- Songcache.bin parser partially working (issue with charter category parsing)
- **Decision**: Proceeding with MD5 hashes as primary identifier

**Phase 2: File Watcher**
- Implemented file monitoring using watchdog library
- Created state tracking system to detect only new scores
- Built debouncing logic to handle file write delays
- Tested successfully with live Clone Hero gameplay

**Phase 3: Discord Bot & API**
- Created Discord bot in Developer Portal
- Implemented slash commands (/ping, /pair, /leaderboard, /mystats)
- Built HTTP API using aiohttp
- Integrated API with Discord bot (runs in same process)
- Configured bot for test server (localhost deployment)

**Phase 4: Integration**
- Connected file watcher to HTTP API
- Tested end-to-end flow: Clone Hero → Watcher → Bot API
- Verified score submission works correctly
- **Result**: Complete working prototype ready for database layer

**Testing Results**:
- ✅ Parser tested with real data (11,396 points, Medium Lead Guitar)
- ✅ File watcher detects new scores in real-time
- ✅ Discord bot online and responsive
- ✅ HTTP API receives and processes scores
- ✅ End-to-end flow working

## Known Issues

### Artist Names (Resolved in v2.0)
**Status**: ✅ Fixed

- Original songcache lookup table parsing was unreliable (indices pointed to wrong entries)
- **Solution v1.2**: Extract song titles from filepaths stored after MD5 in songcache.bin
- **Solution v2.0**: Hybrid approach - parse song.ini files + filepath pattern extraction
- **Impact**: Artist names now available for songs with song.ini files
- **Manual Override**: `/setartist` command for songs without song.ini

### Unicode Console Output (Resolved)
**Status**: Fixed

- Initial scripts had Unicode characters that Windows console couldn't display
- **Solution**: Replaced all Unicode box-drawing and emoji characters with ASCII
- **Impact**: None - purely cosmetic issue

## Deployment Plan

### Current: Local Deployment
- **Bot Host**: Localhost (developer machine)
- **API**: http://localhost:8080
- **Database**: SQLite (bot/scores.db)
- **Purpose**: Development and production use

### Future: Home Server Deployment
- **Bot Host**: User's dedicated home machine
- **API**: http://[home-ip]:[port] with port forwarding
- **Access**: Friends can connect from anywhere
- **Database**: SQLite (sufficient for small group)
- **Benefits**: 24/7 availability, no cloud costs

### Alternative: Cloud Deployment (Optional)
- **Options**: Railway, Heroku, DigitalOcean
- **Cost**: ~$5-10/month
- **Benefits**: Professional hosting, easier management
- **Consideration**: For later if home server proves unreliable

---

### Session 2 - 2025-11-21
**Duration**: ~6 hours
**Status**: v1.4 Released - Production Ready

**Phase 4: Database & High Score Logic (Completed)**
- Implemented SQLite database with full schema
- Created users, scores, songs, pairing_codes tables
- Added record_breaks tracking table
- Implemented complete pairing flow (new user + existing user)
- High score comparison and record break detection
- Discord announcements for record breaks

**Phase 5: Packaging & Polish (Completed)**
- v1.0: Initial PyInstaller build with standalone exe
- v1.1: Fixed offline play detection (track score values, not just keys)
- v1.2: Fixed song title parsing (use filepaths instead of lookup tables)
- v1.3: Added debug mode with password protection
- v1.4: Enhanced stats, leaderboard song titles, debug timeout

**Key Fixes:**
1. **Offline Play Bug**: Changed `known_scores` from `Set[str]` to `Dict[str, int]` to track score values
2. **Song Title Mismatch**: Discovered lookup table indices were unreliable; switched to filepath extraction
3. **Debug Mode UX**: Added 3-second timeout so normal users don't have to interact

**Features Implemented:**
- `/leaderboard` shows song titles instead of MD5 hashes
- `/mystats` shows records held, record breaks, total points, top records
- Multi-machine support for existing users
- Debug mode with `send_test_score` command

**Testing Results:**
- ✅ All 4 client versions built successfully
- ✅ Score submission and record detection working
- ✅ Discord announcements posting correctly
- ✅ Stats and leaderboard commands fully functional
- ✅ Debug mode with timeout working

---

### Session 3 - 2025-11-21
**Duration**: ~4 hours
**Status**: v1.9 Released - Full UX Polish Complete

**v1.5 - State & Debug Fixes**
- Fixed debug mode to continue to normal operation (not exit)
- Added catch-up scan on startup for offline scores
- Moved state file to Clone Hero directory for persistence
- Fixed state file migration from old format

**v1.6 - Notes Statistics**
- Added notes_hit/notes_total to ScoreEntry dataclass
- Updated client and bot to track note counts
- Enhanced Discord announcement with Notes field
- Improved bot terminal output with all score fields

**v1.7 - Configuration System (Group A)**
- Created settings persistence system (.score_tracker_settings.json)
- Made bot URL configurable (no longer hardcoded)
- Added manual Clone Hero path override
- Created interactive settings menu
- Settings accessible via 'settings' command or on connection failure

**v1.8 - Always-Available Commands**
- Restructured to run watcher in background thread
- Added always-available command prompt (>)
- Commands: help, status, resync, settings, unpair, debug, quit
- Completed Group C (unpair, resync) and Group D (status) features

**v1.9 - Onboarding & Error Recovery (Groups B, D)**
- Added welcome message for first-time users
- Step-by-step pairing instructions with server info
- Connection retry with visible attempt counter (3 retries)
- Comprehensive error recovery guidance for all failure modes
- Improved Clone Hero not found error with settings option

**Phase 6 Features Completed:**
- 6.1a Welcome message ✓
- 6.1b Discord server info ✓
- 6.2a-d Settings system ✓
- 6.3a Unpair/reset ✓
- 6.3b Manual resync ✓
- 6.4a Connection status ✓
- 6.4b Error guidance ✓
- 6.4c Visible retry ✓

**Deferred to Future:**
- System tray mode
- Start with Windows
- Auto-update check

---

### Session 4 - 2025-11-21
**Duration**: ~2 hours
**Status**: v2.0 Released - Artist Names Complete

**Phase 7: Artist Names (Completed)**
- Implemented song.ini parser in shared/parsers.py
- Added filepath pattern extraction fallback ("Artist - Title" folders)
- Created hybrid `get_artist_for_song()` function
- Updated client to extract and send artist with score submissions
- Artist stored in songs table, displayed throughout system
- Added three new Discord commands:
  - `/lookupsong <query>` - Search songs by title
  - `/setartist <md5> <artist>` - Manually set artist
  - `/missingartists` - List songs without artist info

**Research Findings:**
- Chorus API (chorus.fightthe.pw) - No direct MD5 lookup endpoint
- Chorus Encore (enchor.us) - API not publicly documented
- Community databases use text-based search, not hash lookup
- **Decision**: Implement local song.ini parsing + manual override

**Key Implementation:**
1. Parse song.ini from chart filepath (most reliable)
2. Extract from filepath patterns if no song.ini
3. Store in database for future lookups
4. Allow manual override via Discord commands

**Files Modified:**
- `shared/parsers.py` - Added `parse_song_ini()`, `extract_artist_from_filepath()`, `get_artist_for_song()`
- `clone_hero_client.py` - Updated score handler to extract artist
- `bot/api.py` - Updated terminal output to show artist
- `bot/database.py` - Added song search/update methods
- `bot/bot.py` - Added `/lookupsong`, `/setartist`, `/missingartists` commands

**Testing Results:**
- ✅ All syntax checks pass
- ✅ Parser imports correctly
- ✅ Client imports correctly
- ✅ Database methods added
- ✅ Bot commands added

---

### Session 5 - 2025-11-21
**Duration**: ~3 hours
**Status**: v2.1 Released - OCR & Deployment

**Phase 8: OCR Integration**
- Replaced Tesseract with Windows built-in OCR (winocr)
- No external installation required - works out of the box
- Captures results screen for notes hit/total, best streak
- Fixed window detection to exclude tracker's own window
- Added bring_window_to_front() for proper capture
- OCR results marked as "rich" scores vs "raw" (MD5 only)

**Phase 8: Bot Deployment**
- Created bot_launcher.py with first-time setup wizard
- Created bot_launcher.spec for PyInstaller
- Bot executable prompts for Discord token, App ID, Channel ID
- Config persistence in bot_config.json

**Bug Fixes:**
- Config files now stored in Clone Hero directory (persists across exe runs)
- Fixed auth token not persisting after unpair/restart
- Deleted old bundled config file causing conflicts

**Files Added/Modified:**
- `client/ocr_capture.py` - Complete rewrite for Windows OCR
- `bot_launcher.py` - New bot executable entry point
- `bot_launcher.spec` - PyInstaller config for bot

---

### Session 6 - 2025-11-21
**Duration**: ~2 hours
**Status**: v2.2 Released - System Integration & Documentation

**Phase 9: System Integration**
- Added `reset` command to clear state and re-submit all scores
- Added "Minimize to Tray" setting with pystray
- Added "Start with Windows" setting via Registry
- Updated settings menu with new options (4 and 5)

**Phase 10: Documentation**
- Completely rewrote README.md
- Created SERVER_SETUP.md - Comprehensive bot installation guide
- Created CLIENT_SETUP.md - Player setup guide with troubleshooting
- Created DEVELOPMENT.md - Developer notes for future work
- Updated NEXT_STEPS.md with current status

**Files Added/Modified:**
- `clone_hero_client.py` - Reset command, tray support, Windows startup
- `clone_hero_client.spec` - Added pystray imports, version 2.2
- `requirements.txt` - Added pystray dependency
- `README.md`, `SERVER_SETUP.md`, `CLIENT_SETUP.md`, `DEVELOPMENT.md`

**Build Results:**
- ✅ CloneHeroScoreTracker_v2.2.exe built successfully
- ✅ All new features integrated
- ✅ Documentation complete

# Development Notes

Notes for future development on the Clone Hero High Score System.

## Project Overview

This project consists of two main components:
1. **Client** (`clone_hero_client.py`) - Windows app that monitors Clone Hero scores
2. **Bot** (`bot_launcher.py` + `bot/`) - Discord bot with HTTP API for score submission

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.10+ (developed on 3.14) |
| Discord | discord.py | 2.3.0+ |
| HTTP API | aiohttp | 3.9.0+ |
| File Watching | watchdog | 3.0.0+ |
| OCR | winocr | 0.0.15+ (Windows native OCR) |
| Screen Capture | mss + Pillow | Latest |
| System Tray | pystray | 0.19.0+ |
| Database | SQLite3 | Built-in |
| Packaging | PyInstaller | 6.0.0+ |

---

## Architecture

### Data Flow

```
Clone Hero Game
       │
       ▼ (saves to)
scoredata.bin ──────────────────────────────────────┐
       │                                            │
       ▼ (watchdog monitors)                        │
CloneHeroWatcher                                    │
       │                                            │
       ├── ScoreDataParser (parses binary)          │
       │                                            │
       ├── OCRCapture (optional, captures screen)   │
       │                                            │
       ▼                                            │
HTTP POST to Bot API ─────────────────────┐         │
       │                                  │         │
       ▼                                  ▼         ▼
Bot API Server ◄──────────────────── Database (SQLite)
       │                                  │
       │                                  │ (stores)
       ▼                                  │
Discord Announcements                     │
       │                                  │
       ▼                                  │
Discord Channel ◄─── /leaderboard ────────┘
                 ◄─── /mystats
                 ◄─── /pair
```

### Key Files

| File | Purpose |
|------|---------|
| `clone_hero_client.py` | Main client entry point, command loop |
| `client/file_watcher.py` | Monitors scoredata.bin for changes |
| `client/ocr_capture.py` | Windows OCR for results screen |
| `shared/parsers.py` | Binary parsers for Clone Hero files |
| `bot_launcher.py` | Bot entry point with setup wizard |
| `bot/bot.py` | Discord commands and slash handlers |
| `bot/api.py` | HTTP API endpoints |
| `bot/database.py` | SQLite operations |
| `bot/config.py` | Configuration loader |

---

## Clone Hero File Formats

### scoredata.bin

Binary file containing all player scores. Little-endian byte order.

```
[Header - 4 bytes]
[Song Count - 4 bytes]

For each song:
    [MD5 Checksum - 16 bytes]  # Chart identifier
    [Instrument Count - 1 byte]
    [Play Count - 3 bytes]

    For each instrument:
        [Instrument ID - 2 bytes]   # 0=lead, 1=bass, 2=rhythm, 3=keys, 4=drums
        [Difficulty - 1 byte]       # 0=easy, 1=medium, 2=hard, 3=expert
        [Completion Num - 2 bytes]
        [Completion Den - 2 bytes]
        [Stars - 1 byte]            # 0-5
        [Padding - 4 bytes]         # Always 1
        [Score - 4 bytes]
```

**Location:**
- Windows: `%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\scoredata.bin`

### songcache.bin

Contains song metadata. Used for title lookups.

**Important quirk:** The lookup table indices are unreliable. Song titles are extracted from the filepath stored after the MD5 checksum instead.

---

## Database Schema

```sql
-- Users who have paired their accounts
users (
    id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE,
    discord_username TEXT,
    auth_token TEXT UNIQUE,
    created_at TIMESTAMP,
    last_seen TIMESTAMP
)

-- Score submissions
scores (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    chart_md5 TEXT,
    instrument_id INTEGER,  -- 0-4
    difficulty_id INTEGER,  -- 0-3
    score INTEGER,
    completion_percent REAL,
    stars INTEGER,
    notes_hit INTEGER,
    notes_total INTEGER,
    submitted_at TIMESTAMP
)

-- Song metadata
songs (
    id INTEGER PRIMARY KEY,
    chart_md5 TEXT UNIQUE,
    title TEXT,
    artist TEXT,
    album TEXT,
    charter TEXT,
    length_ms INTEGER,
    first_seen TIMESTAMP
)

-- Temporary pairing codes
pairing_codes (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,
    client_id TEXT,
    discord_id TEXT,
    auth_token TEXT,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    completed INTEGER DEFAULT 0
)

-- Record break history
record_breaks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    chart_md5 TEXT,
    instrument_id INTEGER,
    difficulty_id INTEGER,
    new_score INTEGER,
    previous_score INTEGER,
    previous_holder_id INTEGER,
    broken_at TIMESTAMP
)
```

---

## Building Executables

### Client Build

```bash
# Update version in clone_hero_client.py and clone_hero_client.spec first
py -m PyInstaller clone_hero_client.spec --noconfirm
```

Output: `dist/CloneHeroScoreTracker_v{VERSION}.exe`

### Bot Build

```bash
# Update version in bot_launcher.py and bot_launcher.spec first
py -m PyInstaller bot_launcher.spec --noconfirm
```

Output: `dist/CloneHeroScoreBot_v{VERSION}.exe`

### PyInstaller Tips

- Hidden imports must be listed in `.spec` files
- Data folders (`bot/`, `client/`, `shared/`) are bundled
- WinRT imports for OCR require many hidden imports (see spec file)
- pystray requires `pystray._base` and `pystray._win32`

---

## Known Issues & Workarounds

### 1. songcache.bin Lookup Table Unreliability

**Problem:** The lookup table indices don't consistently point to correct entries.

**Solution:** Extract song titles from filepaths stored in songcache.bin after each MD5 checksum. See `SongCacheParser.parse()` in `shared/parsers.py`.

### 2. OCR Window Capture

**Problem:** OCR captures wrong window or black screen.

**Solutions implemented:**
- Exclude tracker's own window by title pattern matching
- Bring Clone Hero to foreground before capture
- Require windowed/windowed-fullscreen mode

### 3. Config Persistence with PyInstaller

**Problem:** Relative paths in frozen exe point to temp extraction directory.

**Solution:** Store configs in Clone Hero directory (persistent) rather than relative to exe. See `get_config_path()` in `clone_hero_client.py`.

### 4. Unicode Console Output

**Problem:** Windows console doesn't handle Unicode box-drawing characters.

**Solution:** Use ASCII alternatives (`[+]`, `[-]`, `[*]`, `[!]`).

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info and version |
| `/health` | GET | Health check, bot connection status |
| `/api/score` | POST | Submit a score (requires auth_token) |
| `/api/pair/request` | POST | Request pairing code |
| `/api/pair/status/{client_id}` | GET | Check if pairing complete |

### Score Submission Payload

```json
{
    "auth_token": "user_auth_token",
    "chart_md5": "abc123...",
    "instrument_id": 0,
    "difficulty_id": 3,
    "score": 147392,
    "completion_percent": 98.5,
    "stars": 5,
    "song_title": "Through the Fire and Flames",
    "song_artist": "DragonForce",
    "score_type": "rich",
    "notes_hit": 2847,
    "notes_total": 2901,
    "best_streak": 1543,
    "ocr_artist": "DragonForce"
}
```

### Score Types

- **raw**: Basic score from file parsing only (MD5 identifier)
- **rich**: OCR-enhanced with notes/streak data

---

## Feature Backlog

### High Priority

1. **Offline Score Queue**
   - Queue scores locally when bot unreachable
   - Retry on reconnection
   - Files: `clone_hero_client.py`, new queue storage

2. **Auto-Update Check**
   - Check GitHub releases on startup
   - Notify user of new versions
   - Don't auto-download (security)

### Medium Priority

3. **Weekly/Monthly Leaderboards**
   - Time-filtered queries in database.py
   - New Discord commands

4. **Achievement System**
   - First FC, streak milestones
   - Discord announcements for achievements

5. **Multi-Server Support**
   - Allow bot to run on multiple Discord servers
   - Per-server leaderboards

### Low Priority

6. **Web Dashboard**
   - View leaderboards in browser
   - Historical charts/graphs

7. **Screenshot Verification**
   - Optional screenshot submission with scores
   - Admin review queue

---

## Testing

### Manual Testing Workflow

1. Start bot: `py run_bot.py`
2. Start client: `py clone_hero_client.py`
3. Complete pairing via Discord `/pair`
4. Play a song in Clone Hero
5. Verify score appears in tracker output
6. Verify Discord announcement (if record broken)
7. Check `/leaderboard` and `/mystats`

### Debug Mode

Access with `debug` command + password (`admin123`):

```
debug> send_test_score -song "Test Song" -score 50000 -instrument 0 -difficulty 3 -stars 5
debug> testocr
debug> exit
```

### Test Files

- `test_parser.py` - Test score parsing
- `test_api.py` - Test API endpoints
- `get_discord_ids.py` - Get Discord IDs for setup

---

## Code Style Notes

- Use ASCII for console output (no Unicode)
- Prefer explicit error messages with troubleshooting hints
- Log to console with prefixes: `[+]` success, `[-]` neutral, `[*]` info, `[!]` error
- Keep functions focused and well-documented
- Settings stored in Clone Hero directory for persistence

---

## Session History

### Session 1 (Nov 20, 2025)
- Initial architecture and research
- Binary parsers for scoredata.bin and songcache.bin
- File watcher implementation
- Basic Discord bot and API

### Session 2 (Nov 21, 2025)
- SQLite database with full schema
- Pairing system
- High score detection and announcements
- PyInstaller packaging (v1.0-v1.4)

### Session 3 (Nov 21, 2025)
- UX improvements (v1.5-v1.9)
- Settings system
- Command prompt interface
- Error handling and guidance

### Session 4 (Nov 21, 2025)
- Artist name extraction (v2.0)
- song.ini parsing
- Lookup commands

### Session 5 (Nov 21, 2025)
- Windows OCR integration (v2.1)
- Bot standalone executable
- Config persistence fixes

### Session 6 (Nov 21, 2025)
- System tray support (v2.2)
- Start with Windows
- Reset command
- Documentation overhaul

### Session 7 (Nov 23, 2025)
- GitHub repository setup: https://github.com/Dr-Goofenthol/CH_HiScore
- First GitHub release (v2.2) with executables
- Auto-update system implementation:
  - Version check via GitHub Releases API
  - Download with progress indicator
  - Supports both .exe and .zip assets
  - Startup check + manual `update` command
- Comprehensive development roadmap created (tiered system)
- Next: Tier 1 quick wins, then Tier 2 high-value features

---

## GitHub Repository

**URL:** https://github.com/Dr-Goofenthol/CH_HiScore

### Releases

Releases are hosted on GitHub. The client auto-checks for updates on startup.

**To create a new release:**
1. Update VERSION in `clone_hero_client.py`
2. Build: `py -m PyInstaller clone_hero_client.spec --noconfirm`
3. Go to GitHub → Releases → Draft new release
4. Tag as `vX.Y`, attach exe via "Attach binaries" section (bottom of page)
5. Publish

See NEXT_STEPS.md for detailed release instructions.

---

## Contact / Ownership

Originally developed as a personal project. No external dependencies on cloud services - fully self-hosted.

---

## License

MIT License - feel free to modify and distribute.

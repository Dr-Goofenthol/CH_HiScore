# Next Steps - Clone Hero High Score System

## Current Status: v2.3.1 Released

All core features complete. System is production-ready with full documentation.
OCR disabled by default due to data quality issues - currentsong.txt is now the authoritative metadata source.

---

## Development Roadmap (v2.3+)

The following features are organized into tiers by implementation complexity and priority.
Work should proceed tier-by-tier, completing items within each tier before moving to the next.

---

## Tier 1: Quick Wins (< 30 min each) - COMPLETE

These are simple fixes and improvements that can be completed quickly.

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Remove OCR debug PNG file | Done | Trivial | Changed `save_debug=True` to `False` |
| Make /mystats visible to all | Done | Trivial | Removed `ephemeral=True` from command |
| Fix [X] display in /mystats | Done | Trivial | Changed "X" to "Expert" in difficulty mapping |
| Improve server IP setup flow | Done | Easy | Added explicit prompt during first-time setup |
| Verify full MD5 storage | Done | Check | Full MD5 now shown in announcements for enchor.us lookup |

**Completed in v2.3**

---

## Tier 2: Low-Medium Effort (1-3 hours each) - MOSTLY COMPLETE

These items provide significant value with moderate implementation effort.

### 2.1 Clone Hero Settings Integration - DONE

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Check settings.ini on boot | Done | Easy | Reads `Documents\Clone Hero\settings.ini` on startup |
| Warn if song_export = 0 | Done | Easy | Guides user to enable in CH settings |
| Warn if auto_screenshot != 1 | Done | Easy | Same location |

### 2.2 currentsong.txt Integration - DONE

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Read currentsong.txt | Done | Medium | Authoritative source for song/artist/charter |
| Use as primary metadata source | Done | Medium | Overrides OCR/filepath when available |

**File location:** `C:\Users\[User]\Documents\Clone Hero\currentsong.txt`

**Format:**
```
Line 1: Song Title
Line 2: Artist
Line 3: Charter
```

### 2.3 Screenshot-Based OCR - DEFERRED

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Watch screenshot folder | Pending | Medium | More reliable than live capture |
| Parse screenshots for stats | Pending | Medium | CH already saves results screen automatically |

**Screenshot location:** `C:\Users\[User]\Documents\Clone Hero\Screenshots`

**Note:** OCR currently disabled by default due to data quality issues. Plan documented below.

### 2.4 Bug Fixes & Enhancements - MOSTLY DONE

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Fix minimize to tray | Done | Debug | Added delay + minimize-then-hide |
| OCR retry for missing fields | Deferred | Medium | OCR disabled by default for now |
| /mystats for other users | Done | Easy | Added optional `user` parameter |
| /updatesong command | Done | Easy | Update title AND/OR artist by MD5 |
| Add /recent x command | Done | Easy | Shows last x record breaks (1-20) |

### 2.5 Announcement Quality - PARTIAL (v2.4/v2.4.1)

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Use scoredata.bin for notes hit/total | **REVERTED** | - | Data was WRONG (showed 356/100 instead of 78/78) |
| Remove notes from OCR dependency | **REVERTED** | - | Notes still need OCR |
| Update notification in Discord | Done | Medium | Bot announces when new version released |

**CORRECTION (Session 10):** The accuracy numerator/denominator in scoredata.bin are NOT notes hit/total. They appear to be some other metric. Notes data is only available via OCR.

### 2.8 Best Streak & Notes OCR - DEFERRED

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Fix notes hit/total OCR parsing | Deferred | Medium | Notes only available via OCR |
| Fix best streak OCR parsing | Deferred | Medium | Only available via OCR |
| Screenshot-based OCR | Deferred | Medium | More reliable than live window capture |
| Verification/sanity checks | Deferred | Easy | Ensure streak <= notes_total |

**Note:** Both notes and best streak require OCR. The scoredata.bin numerator/denominator fields are NOT notes data. Defer until OCR quality issues are resolved.

### 2.9 Reset Command Split - NEW

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Split reset into 2 functions | Pending | Easy | User requested separation |

### 2.6 Config Persistence - DONE (v2.4)

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Move bot config to %APPDATA% | Done | Easy | Store in `%APPDATA%\CloneHeroScoreBot\bot_config.json` |
| Migration from old location | Done | Easy | Check exe directory first, migrate if found |

### 2.7 Non-Highscore Feedback - DONE (v2.4)

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Show full score data for all scores | Done | Easy | Display song/score/accuracy even if not a PB |
| Explain why score wasn't submitted | Done | Easy | Shows current PB and point difference |

**Example output for non-highscore:**
```
[*] Score detected!
    Song: Through the Fire and Flames
    Artist: DragonForce
    Score: 425,000
    Accuracy: 92.5%
    Difficulty: Expert
    Source: currentsong.txt

[i] Score not submitted - not a personal best
    Your current PB: 450,000
```

**Implementation:**
```python
def get_config_path():
    """Get persistent config path in AppData"""
    if sys.platform == 'win32':
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        config_dir = appdata / 'CloneHeroScoreBot'
    else:
        config_dir = Path.home() / '.config' / 'CloneHeroScoreBot'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'bot_config.json'

def migrate_old_config():
    """Check for config next to exe and migrate to AppData"""
    old_config = Path(__file__).parent / 'bot_config.json'
    new_config = get_config_path()
    if old_config.exists() and not new_config.exists():
        shutil.copy(old_config, new_config)
        print(f"[+] Migrated config to {new_config}")
```

**Completed in v2.3/v2.3.1**

---

## Tier 3: Medium Effort - Database & Scoring Changes (4-8 hours each)

These items require schema changes and careful consideration of data integrity.

### 3.1 Score Separation by Instrument

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Separate leaderboards per instrument | Pending | Medium | Each instrument has its own high score hierarchy |
| Update /leaderboard command | Pending | Medium | Show instrument-specific rankings |
| Update Discord announcements | Pending | Easy | Clarify which instrument record was broken |

**Current behavior:** One record per MD5 + instrument + difficulty + user
**New behavior:** Leaderboards filtered/grouped by instrument

### 3.2 Expert vs Non-Expert Score Separation

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Track expert scores separately | Pending | Medium | Expert = competitive, non-expert = casual |
| Non-expert scores can overwrite each other | Pending | Medium | Only track "best" for non-expert |
| Expert scores tracked individually | Pending | Medium | Full history and competition |

**Schema consideration:**
- Add `is_expert` flag or separate tables
- Expert (difficulty_id = 3) gets full tracking
- Non-expert (difficulty_id 0-2) simplified tracking

### 3.3 Enhanced Lookups & Stats

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| /lookupsong show all highscores | Pending | Medium | Display all scores for MD5 by instrument/difficulty |
| Track user's best note streak | Pending | Medium | Add `best_streak` column to users table |
| Propagate song metadata to all MD5 instances | Pending | Easy | When artist/title learned, update all related rows |

### 3.4 Discord Announcement Improvements

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Include full MD5 in announcements | Done | Easy | Added in v2.3 for enchor.us lookup |
| Format MD5 for easy copying | Done | Easy | Uses backtick code formatting |
| Add enchor.us mention on boot | Pending | Trivial | Encourage users to use Bridge app |

**Estimated Total: 12-20 hours** (reduced - some items complete)

---

## Tier 4: Larger Features (1-2 days each)

These are substantial features requiring significant implementation effort.

### 4.1 Auto-Update System - DONE

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Version check on startup (client) | Done | Medium | Checks GitHub releases API |
| Notify user of new version (client) | Done | Easy | Shows changelog, prompts to download |
| Auto-download new exe (client) | Done | Medium | Downloads with progress bar |
| Version check on startup (bot) | Done | Medium | Same as client |
| Auto-download new exe (bot) | Done | Medium | Same as client |
| Discord update notification | Pending | Medium | Bot announces new version to channel |

**Completed in v2.3**

### 4.2 Offline Score Queue

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Queue scores when offline | Pending | Medium | Store to JSON file in CH directory |
| Retry on reconnection | Pending | Medium | Submit queued scores when server reachable |
| Queue status indicator | Pending | Easy | Show "X scores queued" in status |

### 4.3 Client Tracking in Bot

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Online clients count | Pending | Medium | Heartbeat/ping system |
| Client version reporting | Pending | Easy | Include version in API calls |
| (Optional) Client IP tracking | Pending | Easy | Only if simple to implement |

### 4.4 Bot Admin System

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Admin password in config | Pending | Easy | Set during first-time setup |
| Password-protected commands | Pending | Medium | Check password before execution |
| Default password warning | Pending | Easy | Prompt if "admin" detected |

### 4.5 Announcement Toggles

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Toggle: announce all scores | Pending | Medium | Not just record breaks |
| New announcement types | Pending | Medium | "score posted", "personal best", "first completion" |
| Server-side toggle storage | Pending | Easy | Store in bot_config.json |

### 4.6 Executable Improvements

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Add file icons | Pending | Easy | Requires .ico file, update .spec files |
| (Stretch) Code signing | Pending | $$$ | ~$100-400/year for certificate |

**Estimated Total: 5-8 days**

---

## Tier 5: Major Feature - Star & Bounty System (1-2 weeks)

This is a comprehensive competitive feature set. Implement in phases.

### Phase A: Star Tracking Foundation

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Regular star balance tracking | Pending | Medium | Career stat from unique charts played |
| Max 5 stars per unique chart | Pending | Medium | Based on highest score's star rating |
| /stars command | Pending | Easy | Show top 3 star holders |
| Add stars to /mystats | Pending | Easy | Display current star balance |

### Phase B: Bounty Mode Foundation

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Bounty mode toggle | Pending | Medium | Server-level on/off |
| /bountymode_on command | Pending | Medium | Admin password required |
| /bountymode_off command | Pending | Medium | With top 3 announcement |
| Bounty star balance (separate from regular) | Pending | Medium | Competitive currency |
| Back-calc option on toggle-on | Pending | Medium | Initialize from existing expert records |

### Phase C: Bounty Creation & Management

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| /bountycreate command | Pending | High | Multiple bounty types |
| Bounty types: beat-me, beat-this, beat-score, beat-accuracy, perfect | Pending | High | Different win conditions |
| Bounty escrow system | Pending | High | Lock stars until claimed/cancelled |
| /bounty command | Pending | Medium | Show active bounty board |
| /bountycancel command | Pending | Medium | Creator or admin override |

**Bounty Types Explained:**
- **beat-me**: Beat the creator's score on a track
- **beat-this**: Beat the current record (any holder)
- **beat-score**: Post score higher than specified value
- **beat-accuracy**: Achieve at least X% accuracy
- **perfect**: Achieve 100% accuracy (FC)

### Phase D: Bounty Claiming & Economy

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Automatic bounty claiming | Pending | High | Check all bounties on score submission |
| Star transfers | Pending | Medium | From escrow to claimer |
| /bountyhistory x command | Pending | Easy | Last x bounties claimed |
| /stareconomy command | Pending | Medium | Total stars earned, taken, etc. |
| Record-loss star transfer (optional) | Pending | Medium | Lose stars when record broken |

### Phase E: Admin Bounties

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| Server admin escrow account | Pending | Medium | For server-sponsored bounties |
| Admin bounty commands | Pending | Medium | Hidden from other users |
| Bonus stars for record breaks (toggleable) | Pending | Medium | Configurable value |

**Database Tables Required:**
```sql
-- User star balances
star_balances (
    user_id INTEGER PRIMARY KEY,
    regular_stars INTEGER DEFAULT 0,
    bounty_stars INTEGER DEFAULT 0,
    escrow_stars INTEGER DEFAULT 0
)

-- Active bounties
bounties (
    id INTEGER PRIMARY KEY,
    creator_id INTEGER,
    chart_md5 TEXT,
    instrument_id INTEGER,
    difficulty_id INTEGER,
    bounty_type TEXT,  -- 'beat-me', 'beat-this', 'beat-score', 'beat-accuracy', 'perfect'
    target_value INTEGER,  -- score or accuracy target
    star_value INTEGER,
    created_at TIMESTAMP,
    status TEXT  -- 'active', 'claimed', 'cancelled'
)

-- Bounty claims history
bounty_claims (
    id INTEGER PRIMARY KEY,
    bounty_id INTEGER,
    claimer_id INTEGER,
    claimed_at TIMESTAMP,
    winning_score INTEGER
)
```

**Estimated Total: 2-3 weeks**

---

## Tier 6: Stretch Goals

These are nice-to-have features for future consideration.

| Item | Status | Effort | Notes |
|------|--------|--------|-------|
| GUI client (tkinter) | Pending | Very High | Complete UI rewrite |
| Sound effects for events | Pending | Medium | Toggleable, user-definable |
| Web dashboard | Pending | Very High | Browser-based leaderboards |
| Multi-server support | Pending | High | One bot, multiple Discord servers |
| Bridge/enchor.us integration | Pending | Research | Direct chart download from announcements |

### 6.1 Bridge / Enchor.us Integration (Research Required)

**Goal:** Allow users to easily download charts directly from Discord announcements using MD5 hash.

**Current State:**
- We include full MD5 in announcements (copy-friendly for manual lookup)
- No documented public API or URL scheme for enchor.us
- Bridge app has no documented deep-link or command-line interface

**Research Findings (Session 9):**
- [Chorus Encore (enchor.us)](https://www.enchor.us/) - Web search engine for CH charts
- [Bridge](https://github.com/Geomitron/Bridge) - Desktop app (Electron/Angular)
- [scan-chart](https://github.com/Geomitron/scan-chart) - Chart scanning library
- Original [Chorus API](https://github.com/Paturages/chorus) had `/api/search` endpoint

**Hash Types (Important):**
| Hash | Purpose |
|------|---------|
| MD5 | All files in chart folder |
| Chart Hash (blake3) | Chart file + .ini modifiers (used for score tracking) |

**Note:** Clone Hero may use chart hash, not MD5, for score identification. Need to verify our hash matches enchor.us index.

**Next Steps:**
1. Join [Chorus Encore Discord](https://discord.gg/cqaUXGm) and ask about:
   - Public API endpoints
   - URL schemes for direct hash lookup
   - Bridge deep-link capability
2. Test URL parameters: `enchor.us/?hash=XXX`, `enchor.us/search?q=XXX`
3. Consider requesting Bridge protocol handler feature (e.g., `bridge://hash/XXX`)

**Potential Integration Methods:**
| Method | Feasibility |
|--------|-------------|
| Clickable URL in announcement | Needs URL scheme discovery |
| Discord bot command `/getchart <md5>` | Would open browser to enchor.us |
| Bridge deep link | Requires Bridge feature request |

---

## Completed Features (v1.0 - v2.2)

### Phase 1-3: Core Infrastructure
- [x] Binary parser for scoredata.bin
- [x] Binary parser for songcache.bin
- [x] File watcher with state tracking
- [x] Discord bot with slash commands
- [x] HTTP API for score submission
- [x] End-to-end integration

### Phase 4: Database & High Score Logic
- [x] SQLite database with full schema
- [x] User pairing system (new + existing user flows)
- [x] High score comparison and detection
- [x] Discord announcements for record breaks
- [x] `/leaderboard` and `/mystats` commands

### Phase 5: Packaging & Polish
- [x] PyInstaller client executable (v1.0 - v2.2)
- [x] PyInstaller bot executable (v2.1)
- [x] Debug mode with test score submission
- [x] Multi-machine support
- [x] Persistent state and config files

### Phase 6: User Experience
- [x] Welcome message for first-time users
- [x] Configurable bot URL
- [x] Interactive settings menu
- [x] Always-available command prompt
- [x] Connection retry with guidance
- [x] Error recovery instructions

### Phase 7: Artist Names
- [x] song.ini parser
- [x] Filepath pattern extraction fallback
- [x] `/lookupsong`, `/setartist`, `/missingartists` commands

### Phase 8: OCR & Deployment
- [x] Windows OCR integration (winocr)
- [x] Notes hit/total from results screen
- [x] Best streak capture
- [x] Bot standalone executable with setup wizard

### Phase 9: System Integration
- [x] Reset command (clear state, resubmit all)
- [x] Minimize to system tray
- [x] Start with Windows

### Phase 10: Documentation
- [x] README.md - Project overview
- [x] SERVER_SETUP.md - Bot installation guide
- [x] CLIENT_SETUP.md - Player setup guide
- [x] DEVELOPMENT.md - Developer notes

---

## Version History

| Version | Key Features |
|---------|--------------|
| v2.4.1 | Fixed currentsong.txt caching (song metadata now appears), reverted notes from scoredata.bin (data was wrong) |
| v2.4 | Config persistence (%APPDATA%), non-highscore feedback with PB, Discord update notification |
| v2.3.1 | OCR disabled by default, bug fixes for data truncation |
| v2.3 | currentsong.txt integration, settings.ini check, /recent, /updatesong, auto-update (both apps), full MD5 in announcements |
| v2.2 | Reset command, minimize to tray, start with Windows, documentation |
| v2.1 | Windows OCR, bot executable, config persistence |
| v2.0 | Artist names, song.ini parsing, lookup commands |
| v1.9 | Welcome message, error guidance, retry mechanism |
| v1.8 | Always-available command prompt |
| v1.7 | Configurable server URL, settings menu |
| v1.6 | Notes hit/total tracking |
| v1.5 | Catch-up scan, persistent state |
| v1.4 | Enhanced stats, record breaks tracking |
| v1.3 | Debug mode |
| v1.2 | Song title parsing fix |
| v1.1 | Offline play detection fix |
| v1.0 | Initial release |

---

## Known Limitations

1. **Windows-only executable** - Mac/Linux users must run from Python source
2. **Single Discord server** - Bot designed for one server at a time
3. **OCR requires windowed mode** - Fullscreen exclusive mode not supported
4. **Local hosting** - Requires always-on machine for bot

---

## Quick Development Reference

### Building New Version

1. Update `VERSION` in:
   - `clone_hero_client.py`
   - `clone_hero_client.spec`
   - (or bot files for bot release)

2. Build:
   ```bash
   py -m PyInstaller clone_hero_client.spec --noconfirm
   ```

3. Test the new executable

4. Update documentation

### Debug Commands

```
debug> send_test_score -song "Test" -score 50000 -difficulty 3
debug> testocr
debug> exit
```

### Key Files

| Purpose | File |
|---------|------|
| Client entry | `clone_hero_client.py` |
| Bot entry | `bot_launcher.py` |
| Score parsing | `shared/parsers.py` |
| Discord commands | `bot/bot.py` |
| HTTP API | `bot/api.py` |
| Database | `bot/database.py` |
| OCR | `client/ocr_capture.py` |
| File watching | `client/file_watcher.py` |

### Clone Hero File Locations

| File | Location | Purpose |
|------|----------|---------|
| scoredata.bin | `%LOCALAPPDATA%Low\srylain Inc_\Clone Hero\` | Score data |
| songcache.bin | `%LOCALAPPDATA%Low\srylain Inc_\Clone Hero\` | Song metadata |
| settings.ini | `%USERPROFILE%\Documents\Clone Hero\` | CH settings |
| currentsong.txt | `%USERPROFILE%\Documents\Clone Hero\` | Current song info |
| Screenshots | `%USERPROFILE%\Documents\Clone Hero\Screenshots\` | Auto-screenshots |

---

## Session Log

### Session 7 - 2025-11-23
**Status:** Auto-Update System Implemented

**Completed:**
- [x] Set up GitHub repository: https://github.com/Dr-Goofenthol/CH_HiScore
- [x] Created first release (v2.2) with exe files attached
- [x] Implemented auto-update system in client:
  - `check_for_updates()` - Checks GitHub API for newer version
  - `download_update()` - Downloads exe/zip with progress bar
  - `prompt_for_update()` - Shows changelog, asks user to confirm
  - `check_and_prompt_update()` - Combined check/prompt workflow
  - Startup integration - Checks automatically on launch
  - `update` command - Manual check anytime

**Files Modified:**
- `clone_hero_client.py` - Added auto-update functions, GITHUB_REPO constant

**Notes:**
- GitHub releases can host .exe files directly via "Attach binaries" section (not description)
- Current release has both client and bot executables attached
- Update system handles both .exe and .zip files

### Session 8 - 2025-11-23
**Status:** Tier 1 & Tier 2 Features Implemented

**Completed:**
- [x] Tier 1: Remove OCR debug PNG (save_debug=False)
- [x] Tier 1: Make /mystats visible to all users
- [x] Tier 1: Fix "X" display → now shows "Expert"
- [x] Tier 1: Server URL prompt on first-time setup
- [x] Tier 2.1: Settings.ini check on boot (song_export, auto_screenshot warnings)
- [x] Tier 2.2: currentsong.txt integration (authoritative song/artist/charter)
- [x] Tier 2.4a: Fix minimize to tray (delay + minimize-then-hide)
- [x] Tier 2.4b: /mystats user parameter (view other users)
- [x] Tier 2.4c: /recent x command (show recent record breaks)
- [x] /updatesong command (set title AND/OR artist)
- [x] Full MD5 in Discord announcements (copy-friendly for enchor.us)
- [x] Bot auto-update system (same as client)

**New Functions Added:**
- `get_clone_hero_documents_dir()` - Find CH Documents folder
- `read_current_song()` - Read currentsong.txt
- `check_clone_hero_settings()` - Validate settings.ini
- `get_recent_record_breaks()` - DB query for recent records
- `update_song_metadata()` - Update title and/or artist

**New Commands:**
- `/updatesong <md5> [title] [artist]` - Update song metadata
- `/recent [count]` - Show recent record breaks (1-20)

**Files Modified:**
- `clone_hero_client.py` - Settings check, currentsong.txt, minimize fix
- `bot/bot.py` - /mystats user param, /recent, /updatesong commands
- `bot/database.py` - get_recent_record_breaks(), update_song_metadata()
- `bot/api.py` - Full MD5 in announcements
- `bot_launcher.py` - Auto-update system added

**Deferred:**
- Tier 2.3: Screenshot-Based OCR (plan documented, needs implementation)

---

## How to Release Updates

### Step-by-Step Release Process

1. **Update version number** in:
   - `clone_hero_client.py` (line 7): `VERSION = "2.3"`
   - `clone_hero_client.spec`: Update exe name if needed

2. **Build the executable:**
   ```bash
   py -m PyInstaller clone_hero_client.spec --noconfirm
   ```

3. **Create GitHub Release:**
   - Go to: https://github.com/Dr-Goofenthol/CH_HiScore/releases
   - Click **"Draft a new release"**
   - **Tag:** `v2.3` (type and create new tag)
   - **Title:** `v2.3 - Brief Description`
   - **Description:** Changelog (what's new, bug fixes, etc.)
   - **IMPORTANT:** Scroll to bottom, use **"Attach binaries"** section
   - Drag and drop `dist/CloneHeroScoreTracker_v2.3.exe`
   - Click **"Publish release"**

4. **Users will be notified** on next client launch

### Release Naming Convention

- Client: `CloneHeroScoreTracker_v{VERSION}.exe`
- Bot: `CloneHeroScoreBot_v{VERSION}.exe`
- Tags: `v{VERSION}` (e.g., `v2.3`, `v2.4`)

---

## Next Session: Resume Development

### Where We Left Off (Session 10 - 2025-11-24)

v2.4.1 released! Fixed currentsong.txt caching issue.

### Session 10 Summary (v2.4 & v2.4.1)

**v2.4 Implemented:**
- [x] Config persistence - bot config now in `%APPDATA%\CloneHeroScoreBot\`
- [x] Auto-migration from old config location
- [x] Non-highscore feedback - shows current PB and point difference
- [x] Discord update notification when new version available

**v2.4.1 Bug Fixes:**
- [x] Fixed currentsong.txt not being read - added background polling/caching
- [x] Reverted notes from scoredata.bin - the numerator/denominator are NOT notes hit/total

**Key Discovery (CORRECTED):**
- scoredata.bin numerator/denominator are NOT notes hit/total (values were wrong like 356/100)
- Notes data only available via OCR (when enabled)
- Clone Hero clears currentsong.txt when song ends, but scoredata.bin written AFTER - need to cache song info while playing

**Pending:**
- [ ] Split reset command into 2 functions

### Priority for Next Session (v2.5)

**Tier 2.8 - Best Streak OCR** (DEFERRED)
- [ ] Fix best streak OCR parsing (only field requiring OCR)
- [ ] Screenshot-based OCR for reliability

**Tier 2.3 - Screenshot-Based OCR** (When OCR re-enabled)
- [ ] Watch Screenshots folder for new files
- [ ] OCR screenshots instead of live capture

**Tier 3 Items**
- [ ] Score separation by instrument
- [ ] Expert vs non-expert tracking

### Screenshot-Based OCR Plan (Tier 2.3)

**Current Flow:**
1. Score detected in scoredata.bin
2. Live window capture via Windows OCR (DISABLED by default)
3. Parse OCR text for notes/streak

**Proposed Flow:**
1. Score detected in scoredata.bin
2. Check Screenshots folder for recent file (within last 5 seconds)
3. If found: OCR the screenshot file
4. If not found: Fall back to live window capture (if enabled)

**Implementation Steps:**
1. Add `get_latest_screenshot()` function to find most recent screenshot
2. Modify score handler to check for screenshot first
3. Add timestamp comparison (screenshot must be recent)
4. Reuse existing OCR parsing logic on screenshot image
5. Add verification: only show notes/streak if values pass sanity checks

**Key Files:**
- `clone_hero_client.py` - Score handler integration
- `client/ocr_capture.py` - Add screenshot file OCR function

### Quick Reference: Key File Locations

| File | Purpose |
|------|---------|
| `clone_hero_client.py` | Main client, score handler, currentsong.txt |
| `bot/bot.py` | Discord commands, /mystats, /recent |
| `bot/database.py` | DB queries, get_recent_record_breaks |
| `bot/api.py` | HTTP API, announcement embed building |
| `client/ocr_capture.py` | OCR capture functions |
| `NEXT_STEPS.md` | This file - development roadmap |

**Current Version:** v2.4.1
**Next Target:** v2.5

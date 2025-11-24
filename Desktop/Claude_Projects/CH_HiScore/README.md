# Clone Hero High Score System

A Discord bot-based high score tracking system for Clone Hero that automatically detects new scores and posts announcements to your Discord server.

## Current Version: v2.4.2

## What It Does

- **Automatic Score Tracking**: Detects when you finish a song in Clone Hero
- **Discord Integration**: Posts announcements when records are broken
- **Leaderboards**: Track high scores across your friend group
- **OCR Enhancement**: Optionally captures additional stats (notes hit, streaks) from the results screen
- **Multi-Machine Support**: Link multiple computers to one Discord account

## Quick Links

| Guide | Description |
|-------|-------------|
| [Server Setup Guide](SERVER_SETUP.md) | For server admins: How to set up the Discord bot |
| [Client Setup Guide](CLIENT_SETUP.md) | For players: How to install and connect the tracker |
| [Development Notes](DEVELOPMENT.md) | For developers: Architecture and future work |

## Features

### For Players
- One-click executable - no Python installation required
- Automatic score detection while you play
- Personal stats tracking (`/mystats` command)
- System tray mode (minimize and forget)
- Start with Windows option

### For Server Admins
- Self-hosted Discord bot (runs on your machine)
- SQLite database (no external database needed)
- Easy first-time setup wizard
- Port forwarding support for remote players

## Version History

### v2.4.2 - Terminology Fix (Latest)
- **Chart Hash Terminology**: Renamed all references from "MD5" to "Chart Hash" for accuracy
- **Automatic Database Migration**: Bot now automatically migrates existing databases on first run
- **Technical**: The identifier stored is actually a blake3 chart hash from Clone Hero, not an MD5

### v2.4.1 - Bug Fixes
- **Fixed song metadata not appearing**: Added background caching of currentsong.txt (Clone Hero clears this file when song ends, but we need it after)
- **Fixed notes display**: Reverted notes from scoredata.bin (data was incorrect)

### v2.4 - Quality of Life
- **Config Persistence**: Bot config now stored in `%APPDATA%` - survives updates
- **Better Feedback**: Non-highscore plays now show your current PB and point difference
- **Discord Update Notification**: Bot notifies channel when client updates are available
- **currentsong.txt Integration**: Uses Clone Hero's song metadata file for accurate titles

### v2.3.1 - Bug Fixes
- OCR disabled by default (was overwriting good data)
- Data source priority fixed

### v2.3 - Auto-Updates & Features
- Auto-update system for both client and bot
- `/recent` command to view recent record breaks
- `/updatesong` command to manually fix song metadata
- `/mystats` can now view other users' stats
- Full MD5 hash in Discord announcements for enchor.us lookup

### v2.2 - System Integration
- **Reset Command**: Clear score history and re-submit all scores to a new server
- **Minimize to Tray**: Keep tracker running in background
- **Start with Windows**: Auto-launch on boot
- OCR results screen capture for enhanced stats

### v2.1 - OCR & Deployment
- Windows OCR integration for notes/streak capture
- Standalone bot executable with setup wizard
- Config persistence fixes

### v2.0 - Artist Names
- Song artist extraction from song.ini files
- Discord commands: `/lookupsong`, `/setartist`, `/missingartists`

### v1.9 and Earlier
- Core functionality: score tracking, pairing, leaderboards
- See [DESIGN.md](DESIGN.md) for full history

## System Requirements

### Client (Players)
- Windows 10 or 11
- Clone Hero installed and run at least once

### Bot Server (Admin)
- Windows 10/11, macOS, or Linux
- Python 3.10+ (if running from source)
- Open port for remote connections (default: 8080)

## Project Structure

```
CH_HiScore/
├── dist/                    # Built executables
│   ├── CloneHeroScoreTracker_v2.4.2.exe   # Client for players
│   └── CloneHeroScoreBot_v2.4.2.exe       # Bot for server admins
│
├── client/                  # Client source code
│   ├── file_watcher.py      # Score detection
│   └── ocr_capture.py       # Results screen OCR
│
├── bot/                     # Bot source code
│   ├── bot.py               # Discord commands
│   ├── api.py               # HTTP API
│   └── database.py          # SQLite operations
│
├── shared/                  # Shared utilities
│   └── parsers.py           # Clone Hero file parsers
│
├── clone_hero_client.py     # Client entry point
├── bot_launcher.py          # Bot entry point
└── *.spec                   # PyInstaller configs
```

## Discord Commands

| Command | Description |
|---------|-------------|
| `/ping` | Check if bot is online |
| `/pair <code>` | Link your Clone Hero client to Discord |
| `/leaderboard [difficulty] [instrument]` | View high scores |
| `/mystats [user]` | View your or another user's statistics |
| `/recent [count]` | Show recent record breaks (1-20) |
| `/lookupsong <query>` | Search for a song |
| `/updatesong <md5> [title] [artist]` | Update song metadata |
| `/setartist <md5> <artist>` | Set artist for a song |
| `/missingartists` | List songs without artist info |

## Client Commands

While the tracker is running, type these at the `>` prompt:

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Check connection and tracked scores |
| `resync` | Scan for missed scores |
| `reset` | Clear state and re-submit ALL scores |
| `settings` | Open settings menu |
| `minimize` | Minimize to system tray (if enabled) |
| `unpair` | Disconnect from Discord account |
| `debug` | Enter debug mode (password required) |
| `quit` | Exit the tracker |

## Architecture

```
┌─────────────────┐      HTTP       ┌─────────────────┐      SQLite     ┌──────────┐
│  Clone Hero     │─────────────────│  Discord Bot    │─────────────────│ Database │
│  Score Tracker  │   POST /api/    │  + HTTP API     │                 │          │
│                 │   score         │                 │                 │ - Users  │
│ - File Watcher  │                 │ - Validation    │                 │ - Scores │
│ - OCR Capture   │                 │ - Leaderboards  │                 │ - Songs  │
│ - Score Parser  │                 │ - Announcements │                 │          │
└─────────────────┘                 └────────┬────────┘                 └──────────┘
                                             │
                                             │ Discord API
                                             ▼
                                    ┌─────────────────┐
                                    │  Discord Server │
                                    │                 │
                                    │ #high-scores    │
                                    │ announcements   │
                                    └─────────────────┘
```

## Support

If you encounter issues:
1. Check the [Client Setup Guide](CLIENT_SETUP.md) troubleshooting section
2. Make sure the bot is running and accessible
3. Try the `resync` or `reset` commands

## License

MIT License - See LICENSE file for details.

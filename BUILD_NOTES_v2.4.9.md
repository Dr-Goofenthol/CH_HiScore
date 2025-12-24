# Build Notes - v2.4.9

## Build Date
November 25, 2025

## Version Updates
- Client: 2.4.8 → 2.4.9
- Bot: 2.4.8 → 2.4.9
- Bot Launcher: 2.4.8 → 2.4.9

## Build Commands
```bash
# Client
python -m PyInstaller CloneHeroScoreTracker_v2.4.9.spec --noconfirm

# Bot
python -m PyInstaller CloneHeroScoreBot_v2.4.9.spec --noconfirm
```

## Output Files
- `dist/CloneHeroScoreTracker_v2.4.9.exe` - Client executable (~25-30 MB)
- `dist/CloneHeroScoreBot_v2.4.9.exe` - Bot executable (~25-30 MB)

## Changes from v2.4.8

### Major Features
1. **Colored Terminal Output** - All console messages now use color-coded output
2. **Enhanced Debug Menu** - Added status, paths, and sysinfo commands
3. **/server_status Command** - New Discord command showing server statistics
4. **Server-Side Debug Auth** - Debug password now managed by server

### Files Modified
- 9 total files changed
- 130+ print statements updated
- 2 new infrastructure files created
- 1 new API endpoint
- 1 new Discord command
- 1 new database method

### New Dependencies
- colorama>=0.4.6 (for cross-platform terminal colors)

## Pre-Release Testing Checklist

### Client Testing
- [ ] Fresh install (new user)
- [ ] Fresh install (existing user)
- [ ] Score submission works
- [ ] Record broken announcement
- [ ] Debug menu (all 3 new commands)
- [ ] Settings menu colors
- [ ] Help menu colors
- [ ] Connection status colors
- [ ] Update check
- [ ] Log file created

### Bot Testing
- [ ] Bot starts successfully
- [ ] /server_status command works
- [ ] /leaderboard still works
- [ ] /mystats still works
- [ ] /pair still works
- [ ] Score announcements post
- [ ] Debug password authorization works
- [ ] Log file created

### Integration Testing
- [ ] Client connects to bot
- [ ] Score submission end-to-end
- [ ] Record break announcement end-to-end
- [ ] Debug password auth works
- [ ] All Discord commands respond

## Known Issues
- ⚠️ Pairing bug on client updates (existing config exists but first-time setup triggered) - TO BE INVESTIGATED

## Server Configuration Updates

### New .env Variable
Add to server `.env` file:
```
DEBUG_PASSWORD=your_secure_password_here
```

If not set, defaults to `admin123`

## Release Notes (for GitHub)

### v2.4.9 - Quality of Life Updates

**New Features:**
- 🎨 Colored terminal output for both client and bot
- 🔍 Enhanced debug menu with system information
- 📊 New `/server_status` Discord command
- 🔐 Server-side debug password authorization

**Improvements:**
- Clean, color-coded console messages (green/cyan/yellow/red)
- File-based error logging (no more console tracebacks)
- Better visual hierarchy in menus
- Improved debugging capabilities

**Technical:**
- Added colorama for cross-platform color support
- Auto-rotating log files (10MB limit, 5 backups)
- New API endpoint for debug authorization
- Comprehensive server statistics

**Files:**
- `CloneHeroScoreTracker_v2.4.9.exe` - Windows client (standalone)
- `CloneHeroScoreBot_v2.4.9.exe` - Windows bot server (standalone)

**Breaking Changes:**
- None - fully backward compatible

**Migration:**
- No migration needed
- Optionally set `DEBUG_PASSWORD` in server `.env`

**Full Changelog:** See [CHANGELOG_v2.4.9_DRAFT.md](CHANGELOG_v2.4.9_DRAFT.md)

## Post-Release Tasks
- [ ] Test executables on clean Windows machine
- [ ] Create GitHub release
- [ ] Upload executables to release
- [ ] Tag release as v2.4.9
- [ ] Update README if needed
- [ ] Announce in Discord (if applicable)

## Developer Notes

### If Builds Fail
Check:
1. All dependencies installed (`pip install -r requirements.txt`)
2. PyInstaller version (6.0.0+)
3. Python version (3.10+)
4. Windows 10+ (for client OCR features)

### Rebuild Commands
```bash
# Clean build
rmdir /s /q build dist
python -m PyInstaller CloneHeroScoreTracker_v2.4.9.spec --noconfirm
python -m PyInstaller CloneHeroScoreBot_v2.4.9.spec --noconfirm
```

### Test in Dev Mode
```bash
# Client
python clone_hero_client.py

# Bot
python bot_launcher.py
```

---

*Build completed by: Claude Code Assistant*
*Build environment: Windows 10, Python 3.14.0, PyInstaller 6.16.0*

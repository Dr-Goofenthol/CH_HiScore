# Future Features Todo List

## Priority Items for Next Build

### 1. Server-Side Debug Password Authorization
**Goal**: Move debug password to server configuration, clients send password to server for authorization

**Changes Needed**:
- [ ] Add `DEBUG_PASSWORD` to server .env configuration
- [ ] Create API endpoint `/api/debug/authorize` for password verification
- [ ] Update client to send debug password to server before entering debug mode
- [ ] Remove hardcoded `DEBUG_PASSWORD` from client code
- [ ] Add server-side authorization check
- [ ] Return success/failure to client

**Benefits**:
- Server admins can set their own debug password
- Centralized security control
- Can change password without rebuilding client

---

### 2. Auto-Update with Quit & Relaunch
**Goal**: When in-app update is triggered, automatically quit, launch new version, delete old version

**Changes Needed**:

**Server**:
- [ ] When update detected, download new exe to temp location
- [ ] Quit current process gracefully
- [ ] Launch new exe from temp location
- [ ] Exit old process

**Client**:
- [ ] When update detected, download new exe to temp location
- [ ] Launch new exe from temp location
- [ ] New exe detects old version running and waits for it to exit
- [ ] New exe deletes old version executable
- [ ] New exe moves itself to proper location
- [ ] Continue normal startup

**Technical Notes**:
- Use `subprocess.Popen()` to launch new exe
- Use `sys.executable` to get current exe path
- Client needs self-delete mechanism (Windows: rename old, delete on next boot OR use batch script)
- Server doesn't need self-delete (stays in place)

---

### 3. Clean Up Client Text & Enhanced Debug Menu
**Goal**: Modernize client output, enhance debug menu with useful information

**Changes Needed**:
- [ ] Review all client print statements
- [ ] Remove outdated/confusing messages
- [ ] Standardize message formatting
- [ ] Add to debug menu:
  - [ ] Current settings values (API URL, pairing status, etc.)
  - [ ] File paths (scoredata.bin location, config file, etc.)
  - [ ] Connection status
  - [ ] Last score submitted
  - [ ] Client version info
  - [ ] System info (OS, Python version if dev mode)

**Debug Menu Structure**:
```
=== DEBUG MENU ===
1. View Current Settings
2. View File Paths
3. View Connection Status
4. Send Test Score
5. View Last Score
6. System Information
7. Exit Debug Mode
```

---

### 4. Add /server_status Discord Command
**Goal**: Show comprehensive server statistics in Discord

**Data to Display**:
- [ ] Total registered users
- [ ] Total scores submitted
- [ ] Total records held
- [ ] Total records broken (all time)
- [ ] Server install date
- [ ] Current bot version
- [ ] Database size
- [ ] Uptime
- [ ] Most active user
- [ ] Most competitive song (most record breaks)

**Implementation**:
- [ ] Create `get_server_stats()` method in `Database` class
- [ ] Add `/server_status` command in `bot.py`
- [ ] Format as Discord embed with fields
- [ ] Cache stats (refresh every 5 minutes to avoid DB spam)

---

### 5. Bot Terminal Input Menu
**Goal**: Add interactive terminal menu to bot similar to client debug menu

**Features**:
- [ ] Non-password protected (server admin already has access)
- [ ] Input field for commands
- [ ] Commands to implement:
  - [ ] `status` - Show bot status, uptime, connected users
  - [ ] `users` - List all registered users
  - [ ] `active` - Show active/recently active users
  - [ ] `stats` - Show server statistics
  - [ ] `db` - Database info (size, schema version, table counts)
  - [ ] `config` - Show current configuration
  - [ ] `help` - List available commands
  - [ ] `exit` - Gracefully shut down bot

**Implementation Notes**:
- [ ] Use threading or asyncio for non-blocking input
- [ ] Don't interfere with Discord bot event loop
- [ ] Clean up client-style terminal output
- [ ] Add command history (arrow keys)
- [ ] Consider using `prompt_toolkit` for better terminal UX

**Terminal Menu Structure**:
```
Clone Hero High Score Bot v2.4.8
[*] Bot online and connected
[*] Type 'help' for available commands

bot> status
[*] Bot Status:
    Uptime: 2 hours 34 minutes
    Registered Users: 5
    Scores Today: 23
    Memory Usage: 45 MB

bot> users
[*] Registered Users (5):
  1. Jake the Simpatico (ID: 110899431787724800)
  2. ...

bot>
```

---

## Implementation Order Suggestion

1. **Server-side debug password** (security improvement, relatively simple)
2. **Clean up text/debug menus** (improves UX, no breaking changes)
3. **/server_status command** (quick win, uses existing data)
4. **Bot terminal menu** (medium complexity, big UX improvement)
5. **Auto-update with relaunch** (complex, needs thorough testing)

---

## Notes

- All features should maintain backwards compatibility where possible
- Consider these for v2.5.0 as a "Quality of Life & Polish" release
- Test each feature thoroughly before combining
- Update documentation for each new feature

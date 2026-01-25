# 🎸 Clone Hero Score Tracker

> **Automatic high score tracking and Discord announcements for Clone Hero**

A powerful, free, and open-source system that automatically detects your Clone Hero scores and posts them to Discord. No manual entry required—just play and let the bot handle the rest.

[![GitHub Release](https://img.shields.io/github/v/release/Dr-Goofenthol/CH_HiScore)](https://github.com/Dr-Goofenthol/CH_HiScore/releases)
[![License](https://img.shields.io/github/license/Dr-Goofenthol/CH_HiScore)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Support-7289DA?logo=discord&logoColor=white)](#support)

---

## ✨ Features

### 🎯 **Automatic Detection**
- Monitors your Clone Hero folder in real-time
- Detects scores the moment you finish playing
- No manual entry or screenshots needed

### 📢 **Discord Announcements**
- Beautiful embeds when records are broken
- Customizable announcement styles (full or minimalist mode)
- Shows song info, score, difficulty, instrument, and more
- Includes links to find charts on [Enchor.us](https://enchor.us)

### 🏆 **Leaderboards & Stats**
- Track high scores for every song, difficulty, and instrument
- View personal stats and improvement over time
- See recent record breaks across your server
- Search songs by title or artist

### 👥 **Multi-User Support**
- Multiple players can track scores on the same server
- Easy pairing via 6-digit codes
- Each user's scores tracked separately
- Supports multiple Clone Hero installations (different PCs)

### 🔄 **Auto-Updates**
- Automatic update checks on startup
- Download new versions directly from GitHub
- Never miss new features or bug fixes

---

## 📸 Screenshots

### Discord Announcements

<table>
<tr>
<td width="50%">

**Record Break**

<img alt="Discord record break announcement" src="https://github.com/user-attachments/assets/79511758-e3f7-4220-afc0-677dd80a45d8" />

</td>
<td width="50%">

**First Score**

<img alt="Discord first score announcement" src="https://github.com/user-attachments/assets/f1328578-102d-4bfe-bbd2-4daafc5a4cb9" />

</td>
</tr>
<tr>
<td>

**First Full Combo (FC)**

<img alt="Discord first FC announcement" src="https://github.com/user-attachments/assets/031cc55c-22a7-4605-b6c5-a40ff0621554" />

</td>
<td>

**Song Lookup**

<img alt="Discord /lookupsong command" src="https://github.com/user-attachments/assets/69a515fb-b423-4830-b210-b507b041e576" />

</td>
</tr>
</table>

### Discord Commands

<table>
<tr>
<td width="50%">

**Leaderboard**

<img alt="Discord /leaderboard command" src="https://github.com/user-attachments/assets/a103cd6d-da79-470f-8279-525421b69e8e" />

</td>
<td width="50%">

**Player Stats**

<img alt="Discord /mystats command" src="https://github.com/user-attachments/assets/32bea17f-58c3-4666-828d-f2e87b9b3f94" />

</td>
</tr>
</table>

### Client Interface

<table>
<tr>
<td width="50%">

**Splash Screen**

<img alt="Client splash screen" src="https://github.com/user-attachments/assets/3b0243e9-b71d-4386-b25e-2990494573c4" />

</td>
<td width="50%">

**Score Detection**

<img alt="Client score detection" src="https://github.com/user-attachments/assets/7a9c4d35-e879-441b-93f7-dedd8a892187" />

</td>
</tr>
</table>

---
---

## 🚀 Quick Start

### Requirements
- **Windows 10/11** (for both bot and client)
- **Discord Server** (you need admin permissions to add the bot)
- **Clone Hero** (any 1.0 version, have not yet tested with 1.1 PTB)

### Installation

**Two components needed:**
1. **Clone Hero Score Bot** - Runs on your PC or server, handles Discord
2. **Clone Hero Score Tracker** - Runs on each player's PC, monitors scores

#### Step 1: Download

Get the latest release from [Releases](https://github.com/Dr-Goofenthol/CH_HiScore/releases):
- `CloneHeroScoreBot_vX.X.X.exe` (for server admin)
- `CloneHeroScoreTracker_vX.X.X.exe` (for players)

#### Step 2: Bot Setup (Server Admin)

1. Run `CloneHeroScoreBot_vX.X.X.exe`
2. Follow the setup wizard:
   - Create Discord bot at [discord.com/developers](https://discord.com/developers)
   - Enter your bot token
   - Enter your Discord server ID
   - Choose announcement channel

The bot will start automatically and connect to Discord.

#### Step 3: Client Setup (Players)

1. Run `CloneHeroScoreTracker_vX.X.X.exe`
2. Follow the setup wizard:
   - Enter bot URL (usually `http://localhost:5000` if on same PC) (ask your server admin for their IP / DNS name if not hosting locally)
   - Client generates a 6-digit pairing code
   - In Discord, type `/pair <code>` to link your account
   - Client starts monitoring your Clone Hero folder

#### Step 4: Play!

That's it! Play a Clone Hero song and watch the magic happen. When you set a new record, your Discord server will be notified automatically.

**Setup time:** ~10-15 minutes for both bot and client

---

## 🌐 Hosting Guide

### Local Network Setup (Easiest)

If all players are on the same local network:
- **Bot Host:** Run the bot on any PC (default port: 5000)
- **Client Setup:** Use bot's local IP address (e.g., `http://192.168.1.100:5000`)
- **No port forwarding required**

### Internet-Accessible Setup (Recommended for Remote Players)

To allow players outside your network to connect:

#### Option 1: Port Forwarding (Free)

1. **Configure Router:**
   - Forward external port (e.g., 5000) to your bot PC's local IP
   - Check your router's admin panel for "Port Forwarding" settings
   - Protocol: TCP

2. **Find Your Public IP:**
   - Visit `https://whatismyipaddress.com`
   - Share this IP with your players: `http://YOUR_PUBLIC_IP:5000`

3. **Handle Dynamic IP (Optional):**
   - Most home ISPs use dynamic IPs that change periodically
   - Use a **free Dynamic DNS service** (No-IP, DuckDNS, etc.)
   - Install DDNS client on bot PC to auto-update your hostname
   - Players use hostname instead: `http://yourserver.ddns.net:5000`

**Pros:** Free, full control
**Cons:** Requires router access, exposes your home IP, manual setup

#### Option 2: Cloud Hosting (Most Reliable)

Host the bot on a cloud server for 24/7 uptime:

**VPS Providers:**
- **DigitalOcean** - $6/month (1GB RAM droplet is sufficient)
- **Linode** - $5/month (Nanode 1GB plan)
- **Vultr** - $5/month (Cloud Compute instances)
- **AWS/Azure** - Free tier available (limited duration)

**Setup Steps:**
1. Create Ubuntu 22.04 VPS instance
2. Install Python 3.10+ and dependencies: `apt install python3 python3-pip`
3. Upload bot files via SCP/SFTP
4. Install Python packages: `pip3 install -r requirements.txt`
5. Run bot with screen/tmux for persistence: `screen -S chbot python3 bot_launcher.py`
6. Use VPS's public IP for client connections

**Pros:** 24/7 uptime, static IP, professional setup
**Cons:** Monthly cost ($5-6), requires basic Linux knowledge

#### Option 3: Tunneling Services (Quick Testing)

For temporary testing without port forwarding:

- **ngrok** - `ngrok http 5000` (free tier has session limits)
- **localtunnel** - `lt --port 5000`
- **Cloudflare Tunnel** - More permanent free option

**Pros:** No port forwarding, instant setup
**Cons:** Free tiers have limitations, URLs change on restart, not ideal for production

### Security Recommendations

- ✅ Use strong Discord bot token (never share publicly)
- ✅ Set debug password in bot config
- ✅ Keep bot software updated
- ✅ Use firewall rules to limit access to bot port
- ⚠️ Avoid running bot as admin/root user
- ⚠️ Don't expose bot on public internet without authentication

### Recommended Setup by Use Case

| Use Case | Recommended Hosting |
|----------|---------------------|
| 2-5 friends on same LAN | Local network (no port forwarding) |
| Small community (5-20 players) | Port forwarding + Dynamic DNS |
| Large community (20+ players) | Cloud VPS hosting |
| Testing/development | Tunneling service (ngrok) |

---

## 📖 Documentation

- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed installation instructions *(coming soon)*
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Configuration and settings reference *(coming soon)*
- **[Commands Reference](docs/COMMANDS.md)** - All Discord slash commands *(coming soon)*
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions *(coming soon)*
- **[FAQ](docs/FAQ.md)** - Frequently asked questions *(coming soon)*

---

## 🎮 Discord Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `/pair <code>` | Link your Clone Hero client to your Discord account |
| `/leaderboard [difficulty] [instrument]` | View high scores for all songs or filtered by difficulty/instrument |
| `/mystats [user]` | View your personal statistics or check another user's stats |
| `/recent [count]` | Show recent record breaks (default: 5, max: 20) |
| `/lookupsong <title>` | Search for a song by title and view its metadata |
| `/hardest [difficulty] [instrument]` | View the most difficult songs ranked by NPS (Note Density) |

### Server Management Commands

| Command | Description |
|---------|-------------|
| `/server_status` | Display comprehensive server statistics dashboard (v2.6.3+) |
| `/ping` | Check bot response time and connection status |

### Metadata Management Commands

| Command | Description |
|---------|-------------|
| `/setartist <hash> <artist>` | Update artist metadata for a specific chart |
| `/updatesong <hash> [title] [artist]` | Manually update song title and/or artist for a chart |
| `/missingartists` | List all charts that are missing artist information |

### Client Terminal Commands

These commands are available in the CloneHeroScoreTracker client terminal:

#### Score & Metadata Management

| Command | Description |
|---------|-------------|
| `resync` | Scan for scores made while offline and submit any missed scores |
| `reset` | Clear all tracked score history and re-submit ALL scores (requires confirmation) |
| `scancharts [--full]` | Upload chart metadata to enable offline score metadata capture (v2.6.4+) |
| `resolvehashes` | Scan local song folders and resolve missing metadata for past scores |
| `refreshcache` | Reload song metadata from Clone Hero's songcache.bin |

#### Statistics & Analysis

| Command | Description |
|---------|-------------|
| `mystats [-t TIMEFRAME] [-i INSTRUMENT] [-f]` | View your server stats with optional filters (today/week/month/all) |
| `search [QUERY] [-i ID] [-d ID] [--fc] [-p NUM]` | Search your scores with advanced filters |
| `compare <discord_user_id>` | Head-to-head comparison with another user |
| `session` | View current session summary (duration, records, FCs, top moment) |
| `recordsreport [--text\|--csv\|--json\|--all]` | Generate comprehensive records report in various formats |

#### Configuration & Utilities

| Command | Description |
|---------|-------------|
| `settings` | Open interactive settings menu (bot URL, paths, OCR, auto-start, etc.) |
| `status` | Check server connection and tracking status |
| `stats` | View quick stats (total scores, last submission, OCR stats) |
| `update` | Check for and download tracker updates from GitHub |
| `backup` / `restore` | Backup or restore configuration files |
| `bridgestatus` | Check Bridge integration status (if using Bridge) |
| `exportlogs` | Export debug logs to a zip file |
| `unpair` | Disconnect this machine from Discord account (requires confirmation) |
| `minimize` | Minimize tracker to system tray (if tray feature enabled) |
| `debug` | Enter debug mode (password required - test scores, OCR, paths, sysinfo) |
| `help` / `?` | Display help message with all available commands |
| `quit` / `exit` | Gracefully exit the tracker |

### Bot Server Terminal Commands

These commands are available in the CloneHeroScoreBot launcher terminal:

#### Main Menu Options

| Command | Description |
|---------|-------------|
| `[1] Start Bot` | Launch the Discord bot server |
| `[2] Settings Menu` | Configure all bot settings (token, channels, announcements, etc.) |
| `[3] View Configuration` | Display current bot configuration (read-only) |
| `[4] Check Status` | Verify bot health and configuration status |
| `[5] Show Statistics` | Display database statistics (users, scores, songs, records) |
| `[6] Admin Utilities` | Access advanced maintenance tools (see below) |
| `[Q] Quit` | Exit the launcher |

#### Runtime Commands

| Command | Description |
|---------|-------------|
| `quit` / `stop` / `exit` | Gracefully shut down the running bot (type in terminal) |

#### Admin Utilities (Submenu)

| Command | Description |
|---------|-------------|
| `[1] Fix Note Counts` | Database migration to correct note counts from pre-v2.6.2 scores |
| `[2] Scan Historical FCs` | Scan 100% completion scores and mark as Full Combos (v2.6.0+) |
| `[3] Backup Database` | Create timestamped backup of scores database |
| `[4] Export Logs` | Create timestamped copy of bot log file |
| `[5] Send Update Notification` | Manually post update notification to Discord |
| `[6] Verify Configuration` | Run diagnostic checks on bot configuration |
| `[B] Back to Main Menu` | Return to launcher main menu |

---

## 🛠️ Features in Detail

### Customizable Announcements

Choose between two announcement modes:

**Full Mode** - Shows all available information:
- Song title and artist
- Score and improvement
- Difficulty and instrument
- Stars and accuracy
- Charter name
- Play count
- Chart intensity (NPS)
- Links to Enchor.us

**Minimalist Mode** - Compact, essential info only:
- Song and score
- Difficulty and instrument
- Previous record (if applicable)

### Announcement Types

Different announcements for different achievements:
- 🏆 **New Record** - Beat the server's high score
- 👑 **Full Combo** - FC'd a song
- 🎯 **Combo Breaker** - FC that beats another FC
- 📈 **Personal Best** - Improved your own score
- 🎉 **First FC** - First full combo on a chart

### Advanced Features

- **Chart Metadata** - Automatically extracts song info from Clone Hero
- **Charter Recognition** - Credits chart creators in announcements
- **Historical Tracking** - Records who held records and for how long
- **Database Management** - Built-in backup and migration tools
- **Admin Utilities** - Scan historical FCs, fix data, verify configuration

---

## 🔧 Configuration

The bot offers extensive customization options:

- **Announcement Style** - Full or minimalist mode
- **Field Visibility** - Toggle individual fields on/off
- **Command Privacy** - Set commands as public or private
- **Display Settings** - Timezone, formatting preferences
- **Chart Intensity Filters** - NPS ranges for `/hardest` command

All settings accessible via the bot's interactive menu.

---

## 🏗️ Architecture

**Two-Component System:**

```
Clone Hero (writes scores) → scoredata.bin
                                  ↓
        Score Tracker Client (monitors file)
                                  ↓
                        HTTP POST /api/score
                                  ↓
        Discord Bot (validates + stores)
                                  ↓
            SQLite Database + Discord Announcements
```

**Key Technologies:**
- Python 3.x
- Discord.py (Discord bot framework)
- SQLite (database)
- aiohttp (async HTTP server)
- watchdog (file monitoring)
- PyInstaller (standalone executables)

---

## 📊 System Requirements

**Bot (Server):**
- Windows 10/11
- 50 MB disk space
- Internet connection
- Python not required (standalone executable)

**Client (Player):**
- Windows 10/11
- Clone Hero installed
- 20 MB disk space
- Network access to bot
- Python not required (standalone executable)

---

## 🤝 Contributing

Contributions are welcome! This project is actively maintained.

**Ways to contribute:**
- Report bugs via [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- Suggest features
- Improve documentation
- Submit pull requests

Please ensure:
- Code follows existing style
- Changes are well-documented
- Testing is performed before PR

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Credits

**Developer:** [Dr-Goofenthol](https://github.com/Dr-Goofenthol)

**Built with:**
- [Discord.py](https://github.com/Rapptz/discord.py) - Discord bot framework
- [Clone Hero](https://clonehero.net/) - The game this tracker supports

**Special thanks to:**
- Beta testers who provided invaluable feedback
- The Clone Hero community for inspiration and support
- Everyone who contributes to making this project better

---

## 💬 Support

**Need help?**
- 📖 Check the [Documentation](docs/) *(coming soon)*
- 🐛 Report bugs: [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- 💬 Questions: Open a [Discussion](https://github.com/Dr-Goofenthol/CH_HiScore/discussions)

**Found this useful?** Give it a ⭐ on GitHub!

---

## 🗺️ Roadmap

**Upcoming features:**
- Comprehensive documentation
- Setup tutorial video
- Enhanced chart metadata extraction
- Performance analytics
- Achievement system
- Web dashboard (maybe!)

See [Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues) for planned features and bug tracking.

---

## 📅 Version History

See [Releases](https://github.com/Dr-Goofenthol/CH_HiScore/releases) for changelog and download links.

**Current Version:** v2.6.3 *(in development)*

---

<div align="center">

**Made with ❤️ for the Clone Hero community**

[⬆ Back to Top](#-clone-hero-score-tracker)

</div>

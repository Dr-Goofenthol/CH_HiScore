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

> **Note:** Screenshots coming soon! This section will showcase Discord announcements, leaderboards, and the client interface.

<!-- Placeholder for screenshots -->
<!--
Example structure:
- Discord announcement (full mode)
- Discord announcement (minimalist mode)
- Leaderboard command
- Stats command
- Client monitoring
-->

---

## 🚀 Quick Start

### Requirements
- **Windows 10/11** (for both bot and client)
- **Discord Server** (you need admin permissions to add the bot)
- **Clone Hero** (any version)

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
   - Enter bot URL (usually `http://localhost:5000` if on same PC)
   - Client generates a 6-digit pairing code
   - In Discord, type `/pair <code>` to link your account
   - Client starts monitoring your Clone Hero folder

#### Step 4: Play!

That's it! Play a Clone Hero song and watch the magic happen. When you set a new record, your Discord server will be notified automatically.

**Setup time:** ~10-15 minutes for both bot and client

---

## 📖 Documentation

- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed installation instructions *(coming soon)*
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Configuration and settings reference *(coming soon)*
- **[Commands Reference](docs/COMMANDS.md)** - All Discord slash commands *(coming soon)*
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions *(coming soon)*
- **[FAQ](docs/FAQ.md)** - Frequently asked questions *(coming soon)*

---

## 🎮 Discord Commands

| Command | Description |
|---------|-------------|
| `/pair <code>` | Link your Clone Hero client to Discord |
| `/leaderboard [difficulty] [instrument]` | View high scores |
| `/mystats [user]` | See your (or another user's) statistics |
| `/recent [count]` | Show recent record breaks |
| `/lookupsong <title>` | Search for a song by title |
| `/hardest [difficulty] [instrument]` | View most difficult songs by NPS |

*More commands available - see full documentation*

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

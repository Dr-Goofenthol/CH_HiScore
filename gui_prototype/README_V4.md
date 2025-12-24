# Clone Hero Score Tracker - GUI Prototype V4 (FINAL)

**Complete GUI implementation with four-panel layout and visual polish**

## ✨ V4 Final Features

### 🎨 **Four-Panel Layout with Colored Borders**

**Top Row (Song Information):**
- **Current Song** (Blue border `#3b8ed0`) - Shows actively playing song
- **Previous Song** (Gray border `#808080`) - Shows last completed song

**Bottom Row (Activity & Stats):**
- **Activity Log** (Dark blue border `#1f538d`) - Scrollable event feed
- **User Stats** (Green border `#2d7a2d`) - Personal Discord statistics

### 📊 **User Stats Panel**
Real-time statistics displayed in a 3x2 grid:
- **Total Scores** - All scores submitted
- **Records Held** - Current high scores owned
- **Records Broken** - Records beaten by you
- **Total Points** - Sum of all your scores
- **Avg Accuracy** - Average completion percentage
- **Avg Stars** - Average star rating

**Auto-Refresh Logic:**
- On startup (when paired)
- 2 seconds after score submission
- 1 second after resync
- Manual refresh via ↻ button

### 🔔 **Status Indicators**
Three real-time status dots at the top:
- **● Server** - Green when connected, red when disconnected
- **● Discord** - Green when paired (shows username), orange when not paired
- **● Song Export** - Green when enabled, orange when disabled

### 🎯 **Complete Feature Set**
- ✅ Two-column song display (Current/Previous)
- ✅ Real-time song tracking with currentsong.txt polling
- ✅ Score display with proper timing (15s persistence)
- ✅ Activity log with Clear button
- ✅ User stats with refresh button
- ✅ Functional Settings dialog
- ✅ System tray integration
- ✅ Status indicators
- ✅ Colored borders for visual separation
- ✅ Proper padding and alignment

## 📐 UI Specifications

**Window Size:** 850x600 (minimum)
**Layout:** 2x2 grid of panels

### Section Heights (approx):
- Header with status: ~80px
- Song panels (top row): ~110px
- Activity Log + Stats: Expands to fill (~360px)
- Button bar: ~40px

### Padding & Borders:
- Border width: 2px on all panels
- Internal padding: 12px
- Column gap: 5px (between panels)
- Outer margin: 10px

### Color Scheme:
- **Current Song**: Blue accent (`#3b8ed0`)
- **Previous Song**: Gray accent (`#808080`)
- **Activity Log**: Dark blue (`#1f538d`)
- **User Stats**: Green (`#2d7a2d`)
- **Success messages**: Green
- **Errors**: Red
- **Warnings**: Orange

## 🚀 Installation & Usage

### Prerequisites
```bash
pip install customtkinter pillow pystray
```

### Run V4
```bash
python gui_prototype/clone_hero_gui_v4.py
```

### First-Time Setup
1. Pair using CLI version first (`python clone_hero_client.py`)
2. Enable "Song Export" in Clone Hero Settings > Gameplay > Streamer Settings
3. Run GUI - it will load your existing config

## 🎮 Usage Flow

### Startup
1. GUI opens at 850x600
2. Connects to bot server
3. Loads Discord pairing info
4. Fetches initial user stats
5. Checks Clone Hero settings
6. Starts monitoring scores

### Playing Songs
1. **Start Playing** → Current Song shows title/artist, "In progress..."
2. **Song Updates** → Live updates every second from currentsong.txt
3. **Song Ends** → Final score displays for 15 seconds
4. **Next Song** → Previous song moves to right panel, new song to left
5. **Stats Refresh** → 2 seconds after score submission

### System Tray
- **X button** → Minimizes to tray (configurable)
- **Hide button** → Explicitly hide to tray
- **Tray menu** → Show, Settings, Resync, Quit
- **Double-click tray** → Restore window

## 🔧 Configuration

### Config Files
All stored in Clone Hero directory:
- `.score_tracker_config.json` - Auth token, Discord username/ID
- `.score_tracker_settings.json` - Bot URL, paths, preferences
- `.score_tracker_state.json` - Known scores for change detection

### Settings Dialog
Access via Settings button:
- **Bot Server URL** - Change API endpoint
- **Clone Hero Path** - Override auto-detection
- **Minimize to tray** - Toggle X button behavior
- **Start with Windows** - Auto-start preference

## 🔍 Status Indicator Guide

### Server Indicator
- 🟢 **Green** - Connected to bot API
- 🔴 **Red** - Cannot reach bot (check if running)

### Discord Indicator
- 🟢 **Green** - Paired and authenticated
- 🟠 **Orange** - Not paired (use CLI to pair)
- Shows username when paired

### Song Export Indicator
- 🟢 **Green** - Enabled in Clone Hero
- 🟠 **Orange** - Disabled (song names won't show)

## 📊 User Stats Panel

### Stats Displayed
All stats pulled from Discord bot database:

**Row 1 (Submission Stats):**
- Total Scores - Count of all submitted scores
- Records Held - Current high scores you own
- Records Broken - Times you've beaten a record

**Row 2 (Performance Stats):**
- Total Points - Sum of all your scores
- Avg Accuracy - Average completion %
- Avg Stars - Average star rating

**Footer:**
- Last updated timestamp (e.g., "Just now", "5m ago")

### Refresh Behavior
Stats automatically refresh when:
- App starts (if paired)
- Score is submitted (2s delay)
- Resync completes (1s delay)
- Manual refresh button clicked

### API Endpoint (Future)
Stats are fetched from `/api/user/stats` endpoint (not yet implemented on bot side).

Current implementation will show:
- "Not paired" if not authenticated
- "Stats fetch failed" if endpoint not available
- Stats grid when data loads successfully

## 🐛 Known Limitations

### Stats API Not Implemented
The bot doesn't have `/api/user/stats` endpoint yet. Stats panel will show:
- Grid layout with "--" values
- "Stats fetch failed" warnings in activity log
- Refresh button functional but returns no data

**To Fix:** Add stats endpoint to `bot/api.py`

### Discord ID Not in Config
Config file may not have `discord_id` field (only `auth_token`).

**Workaround:** Stats will fail silently until ID is added

### Song Export Must Be Enabled
Without Song Export enabled in Clone Hero:
- Song title/artist won't show
- Only chart hash displayed ([abc12345])
- Orange indicator warns user

## 📝 Version History

### V4 (Current) - Four-Panel Layout
- Added User Stats panel
- Colored borders on all panels
- Improved padding and alignment
- Auto-refresh stats logic
- 850x600 window size

### V3 - Two-Column Layout
- Split songs into Current/Previous
- Added status indicators
- 700x600 window size

### V2 - Compact with Tray
- Settings dialog
- System tray integration
- 600x520 window size

### V1 - Initial Prototype
- Basic layout
- Score tracking working
- 700x600 window size

## 🎯 Production Readiness

### ✅ Ready for Use
- All UI components functional
- Score tracking works perfectly
- Settings persist correctly
- System tray fully operational
- Thread-safe operations
- Clean shutdown

### ⚠️ Needs Work
- Stats API endpoint on bot side
- Error handling for stats failures
- Discord ID in config file
- Polish on stats display when loading

## 🔮 Future Enhancements

### High Priority
1. Implement `/api/user/stats` endpoint in bot
2. Add `discord_id` to config during pairing
3. Loading spinner for stats fetch
4. Error states for stats panel

### Nice to Have
1. Recent scores list in stats panel
2. Records breakdown by instrument
3. Graphical stats (charts/graphs)
4. Session stats (current play session)
5. Customizable themes/colors

## 🧪 Testing Checklist

- [x] Window opens at 850x600
- [x] All 4 panels visible with borders
- [x] Status indicators update correctly
- [x] Current song updates while playing
- [x] Previous song updates after score
- [x] Activity log scrolls and shows messages
- [x] Stats panel shows grid (with -- values)
- [x] Refresh button triggers fetch attempt
- [x] Settings dialog opens and saves
- [x] Hide to tray works
- [x] Tray menu functional
- [x] X button behavior follows setting
- [x] All buttons visible without resizing
- [x] Borders and padding look clean
- [x] Colors match design spec

## 📚 Files Overview

```
gui_prototype/
├── clone_hero_gui_v4.py          # Main GUI (RECOMMENDED)
├── clone_hero_gui_v3.py          # Previous version (two-column)
├── clone_hero_gui_v2.py          # Earlier version (compact)
├── clone_hero_gui.py             # Original prototype
├── README_V4.md                  # This file
├── README_V2.md                  # V2 documentation
├── requirements_gui.txt          # Dependencies
└── CODE_REVIEW.md                # Original code review
```

## 💡 Tips

1. **Pair First** - Use CLI to pair before running GUI
2. **Enable Song Export** - Required for song names
3. **Bot Must Run** - GUI needs bot API accessible
4. **Check Logs** - Activity log shows all errors
5. **Stats Coming Soon** - Grid layout ready, API pending

## 🚨 Troubleshooting

### "Not paired" warning
→ Run CLI version and use `/pair` command in Discord

### "Song Export DISABLED" warning
→ Clone Hero > Settings > Gameplay > Streamer Settings > Export Current Song (ON)

### "Connection failed - is bot running?"
→ Start bot with `python bot_launcher.py`

### Stats show "--"
→ Expected - API endpoint not implemented yet

### Previous song shows "Playing..."
→ Fixed in V4 - make sure using clone_hero_gui_v4.py

### Buttons not visible
→ Resize window vertically or use V4 (850x600)

## ✨ Acknowledgments

**V4 Final** - Complete four-panel layout with stats integration
- Visual polish with colored borders
- User stats panel ready for API
- Production-ready GUI implementation

---

**Status:** ✅ Production Ready (pending stats API)
**Last Updated:** 2025-12-02
**Version:** 2.4.11-GUI-V4

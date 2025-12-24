# Clone Hero Score Tracker - GUI Prototype

This is a proof-of-concept GUI version of the Clone Hero Score Tracker using **CustomTkinter** for a modern, clean interface.

## Status: PROTOTYPE

This is a work-in-progress GUI implementation. It demonstrates the visual design and basic functionality, but is not feature-complete.

## Features Implemented

✅ **Visual Status Dashboard**
- Connection status indicator (green/red dot)
- Server connection display
- Score tracking counter

✅ **Current Song Card**
- Real-time display of current song being played
- Shows artist, difficulty, instrument
- Score display with formatting

✅ **Activity Log**
- Scrollable event feed
- Timestamped messages
- Color-coded events (success/error/warning/info)

✅ **Basic Functionality**
- Connects to bot server
- Loads authentication token
- Finds Clone Hero directory
- Starts file watcher
- Detects new scores
- Submits scores to API
- Displays results in real-time

## Features Not Yet Implemented

❌ **Settings Dialog**
- GUI for bot URL configuration
- Clone Hero path selection
- OCR settings

❌ **Pairing Flow**
- First-time setup wizard
- Discord pairing code display
- Visual pairing progress

❌ **System Tray**
- Full integration with pystray
- Minimize to tray functionality
- Tray menu options

❌ **Update System**
- Auto-update check on startup
- Download progress display

❌ **Advanced Features**
- Debug mode UI
- Reset/unpair dialogs
- Statistics view

## Installation

### 1. Install CustomTkinter

```bash
pip install customtkinter
```

This will also install required dependencies:
- `tkinter` (usually included with Python)
- `darkdetect` (for system theme detection)
- `Pillow` (for image handling)

### 2. Run the GUI Prototype

From the `gui_prototype` folder:

```bash
cd gui_prototype
python clone_hero_gui.py
```

Or from the project root:

```bash
python gui_prototype/clone_hero_gui.py
```

## Configuration

The GUI uses the same configuration files as the CLI version:
- Config: `%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\.score_tracker_config.json`
- Settings: `%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\.score_tracker_settings.json`
- State: `%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\.score_tracker_state.json`

You can pair and configure using the CLI version, then run the GUI version - they share the same config.

## Requirements

- Python 3.7+
- CustomTkinter 5.0.0+
- All dependencies from main project (requests, watchdog, etc.)

See `requirements_gui.txt` for full list.

## Design Philosophy

This GUI prototype aims to:

1. **Simplicity** - Clean, uncluttered interface
2. **Visibility** - All important info visible at a glance
3. **Modern** - Follows current UI/UX trends
4. **Native-like** - Uses system theme (dark/light mode)
5. **Non-intrusive** - Can minimize to tray, run in background

## Color Scheme

- **Dark Mode** (default)
- **Light Mode** (system-adaptive)
- Status colors:
  - 🟢 Green = Connected/Success
  - 🔴 Red = Disconnected/Error
  - 🟠 Orange = Warning
  - ⚪ Gray = Neutral/Info

## Layout Structure

```
┌─────────────────────────────────────────┐
│ Clone Hero Score Tracker        [─][□][×]│
├─────────────────────────────────────────┤
│ Header                                  │
│   - Title                               │
│   - Status Indicator                    │
│   - Tracking Count                      │
├─────────────────────────────────────────┤
│ Current Song Card                       │
│   - Song Title                          │
│   - Artist                              │
│   - Difficulty/Instrument               │
│   - Score                               │
├─────────────────────────────────────────┤
│ Activity Log (scrollable)               │
│   - Timestamped events                  │
│   - Color-coded messages                │
│   - Auto-scrolls to latest             │
├─────────────────────────────────────────┤
│ Button Bar                              │
│   [Resync] [Settings]  [Minimize to Tray]│
└─────────────────────────────────────────┘
```

## Next Steps for Full Implementation

1. **Settings Dialog**
   - Use `CTkToplevel` for modal dialogs
   - Form inputs for all settings
   - Save/Cancel buttons

2. **Pairing Wizard**
   - Multi-step dialog
   - Display pairing code
   - Poll for completion
   - Show success message

3. **System Tray Integration**
   - Integrate existing `pystray` code
   - Show/hide window from tray
   - Tray menu with quick actions

4. **Polish & Refinement**
   - Better error handling UI
   - Loading indicators
   - Animations/transitions
   - Tooltips for buttons

## Testing Notes

The GUI has been tested with:
- ✅ Starting without pairing (shows warning)
- ✅ Connecting to bot server
- ✅ Loading song cache
- ✅ Detecting new scores
- ✅ Submitting scores to API
- ✅ Displaying record breaks

## Known Issues

1. **Activity Log** - No color-coding yet (CustomTkinter textbox limitation)
2. **Window Icon** - Uses default Python icon (need custom .ico file)
3. **Threading** - Some UI updates might lag slightly

## Screenshots

(TODO: Add screenshots once design is finalized)

## Feedback

This is a prototype - feedback welcome! Things to consider:

- Is the layout intuitive?
- Are the colors/fonts readable?
- Is any information missing from the main screen?
- Should buttons be arranged differently?
- What additional features would be most useful?

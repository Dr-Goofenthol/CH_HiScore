# Client Setup Guide

This guide helps you set up the Clone Hero Score Tracker on your computer to automatically track your scores and submit them to your Discord server's leaderboard.

## Before You Start

Make sure you have:
- Windows 10 or Windows 11
- Clone Hero installed and run at least once (to create score files)
- The bot server URL from your server admin (e.g., `http://192.168.1.100:8080`)
- Access to the Discord server where the bot is running

---

## Installation

### Step 1: Download the Client

1. Get `CloneHeroScoreTracker_v2.2.exe` from your server admin or the `dist/` folder
2. Place it somewhere permanent (e.g., `C:\Games\CloneHeroTracker\`)
   > **Tip**: Don't put it in Downloads - you might accidentally delete it!

### Step 2: Run the Tracker

1. Double-click `CloneHeroScoreTracker_v2.2.exe`
2. If Windows SmartScreen appears, click "More info" then "Run anyway"
   > This happens because the exe isn't code-signed. It's safe!

### Step 3: First-Time Setup

On first run, you'll see a welcome message explaining how the system works.

1. Press **Enter** to continue
2. The tracker will try to connect to the default server (`localhost:8080`)

### Step 4: Configure Server URL (if needed)

If the bot is running on a different machine:

1. When connection fails, you'll see options
2. Press **S** to open Settings
3. Select option **1** (Bot Server URL)
4. Enter the URL your admin gave you (e.g., `http://192.168.1.100:8080`)
5. Press **0** to go back

---

## Pairing Your Account

### Step 1: Start Pairing

1. When the tracker connects successfully, it will show a pairing code:
   ```
   ==================================================
   YOUR PAIRING CODE: ABC123
   ==================================================
   ```

### Step 2: Link in Discord

1. Open Discord
2. Go to the server where the score bot is running
3. In any channel, type:
   ```
   /pair ABC123
   ```
   (Replace ABC123 with your actual code)

### Step 3: Confirm Pairing

1. The bot will confirm in Discord: "Successfully paired!"
2. The tracker will show: "[+] PAIRING SUCCESSFUL!"
3. You're now linked and ready to play!

---

## Using the Tracker

### Basic Usage

1. Keep the tracker running in the background
2. Play Clone Hero normally
3. When you finish a song, the tracker:
   - Detects your new score
   - Submits it to the server
   - If you broke a record, announces it in Discord!

### Available Commands

While the tracker is running, type commands at the `>` prompt:

| Command | What It Does |
|---------|--------------|
| `help` | Shows all available commands |
| `status` | Shows connection status and tracked scores |
| `resync` | Scans for scores made while tracker was offline |
| `reset` | Clears local state and re-submits ALL scores |
| `settings` | Opens the settings menu |
| `minimize` | Minimizes to system tray (if enabled) |
| `unpair` | Disconnects from your Discord account |
| `quit` | Exits the tracker |

---

## Settings

Access settings by typing `settings` at the `>` prompt.

### 1. Bot Server URL

Change where scores are sent. Use this when:
- Connecting to a friend's server
- Switching between different scoreboards

### 2. Clone Hero Path

Usually auto-detected. Override this if:
- Clone Hero is installed in a non-standard location
- You have multiple Clone Hero installations

### 3. OCR Capture

Enables/disables results screen capture:
- **Enabled**: Captures notes hit, best streak from results screen
- **Disabled**: Only basic score data (faster, no window focus needed)

> **Note**: OCR requires Clone Hero to be in **Windowed** or **Windowed Fullscreen** mode.

### 4. Minimize to Tray

When enabled:
- Type `minimize` to hide to system tray
- Right-click tray icon to show or exit
- Tracker keeps running in background

### 5. Start with Windows

When enabled:
- Tracker automatically starts when Windows boots
- Great for "set it and forget it" usage

---

## Troubleshooting

### "Could not connect to server"

**Check the server URL:**
1. Type `settings`
2. Verify the Bot Server URL is correct
3. Ask your admin if the bot is running

**Check your network:**
- Can you reach the server in a browser?
- Try: `http://[server-url]/health`

### "Clone Hero not found"

The tracker couldn't find Clone Hero's data folder.

**Solutions:**
1. Make sure Clone Hero has been run at least once
2. Go to Settings > Clone Hero Path
3. Manually enter the path:
   - Default: `C:\Users\[YourName]\AppData\LocalLow\srylain Inc_\Clone Hero`

### Score not submitting

**Check connection:**
1. Type `status` to verify connection
2. If disconnected, the server may be down

**Force re-scan:**
1. Type `resync` to scan for missed scores

**Full reset:**
1. Type `reset` to clear state and resubmit everything

### OCR not working

**Requirements:**
- Windows 10 or 11
- Clone Hero in **Windowed** or **Windowed Fullscreen** mode

**Check:**
1. Go to Settings > OCR Capture
2. Verify it shows "Windows OCR available"

**Common issues:**
- Clone Hero is in exclusive fullscreen (switch to windowed fullscreen)
- Another window is covering Clone Hero when song ends

### Authentication errors

If you see "you may need to re-pair":

1. Type `unpair` to disconnect
2. Restart the tracker
3. Complete pairing again with a new code

### Scores showing on wrong account

If you share a computer:
1. Each person needs their own tracker instance
2. Or use `unpair` before switching users

---

## New User vs Existing User

### New User

When pairing for the first time:
- Select **"New user"** during setup
- Your Discord account is linked fresh
- All future scores go to your account

### Existing User (New Machine)

If you already have scores and are connecting a second computer:
- Select **"Existing user"** during setup
- Scores are linked to your existing Discord account
- Your history is preserved

---

## Tips for Best Experience

### Keep Tracker Running

- Leave it open while you play
- Use "Minimize to Tray" to hide it
- Enable "Start with Windows" so you never forget

### Windowed Fullscreen Mode

For best OCR capture:
1. In Clone Hero, go to Settings > Video
2. Set Display Mode to **Windowed Fullscreen**
3. This allows OCR to capture notes/streak without focus issues

### Regular Resyncs

If you played while tracker was closed:
1. Start the tracker
2. Type `resync`
3. All missed scores will be submitted

### Connecting to a New Server

If switching to a different scoreboard:
1. Type `settings`, change Bot Server URL
2. Type `reset` to submit all your scores to the new server

---

## Files Created

The tracker creates these files in your Clone Hero folder:

| File | Purpose |
|------|---------|
| `.score_tracker_config.json` | Your auth token and client ID |
| `.score_tracker_settings.json` | Your settings (server URL, etc.) |
| `.score_tracker_state.json` | Tracks which scores have been submitted |

> **Note**: These are hidden files. Enable "Show hidden files" in Windows to see them.

---

## Uninstalling

1. Close the tracker
2. Delete the `.exe` file
3. (Optional) Delete the config files from your Clone Hero folder

To remove "Start with Windows":
1. Press `Win + R`, type `regedit`, press Enter
2. Navigate to: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
3. Delete the "CloneHeroScoreTracker" entry

---

## Getting Help

1. Check the troubleshooting section above
2. Ask your server admin
3. Try the `status` command to see what's happening
4. Type `reset` as a last resort to start fresh

---

## Quick Reference Card

```
PAIRING:
  1. Run tracker
  2. Note the 6-digit code
  3. In Discord: /pair CODE

DAILY USE:
  1. Start tracker (or let it auto-start)
  2. Play Clone Hero
  3. Records announced automatically!

COMMANDS:
  help     - Show commands
  status   - Check connection
  resync   - Find missed scores
  reset    - Resubmit everything
  settings - Change config
  minimize - Hide to tray
  quit     - Exit

TROUBLE?
  1. Check status
  2. Try resync
  3. Try reset
  4. Re-pair if needed
```

# Clone Hero Score Tracker - v2.6.5 Release Notes

**Release Date:** February 9, 2026
**Release Type:** Feature Update - UX Improvements & Documentation

---

## 🎯 Overview

Version 2.6.5 focuses on improving the first-time setup experience for server admins and adding a powerful new chart inspection tool for users. This release includes major enhancements to the bot setup wizard, comprehensive documentation updates, and a new client command for analyzing charts.

---

## ✨ New Features

### **Client: `parse` Command** 🎸

A new terminal command that allows users to manually inspect chart metadata without playing or submitting scores.

**What it does:**
- Searches local chart index by title, artist, charter, or hash
- Displays comprehensive chart information including:
  - Song title, artist, and charter
  - Chart hash (full and abbreviated)
  - Total notes, average NPS, peak NPS
  - File path and existence verification
  - Scan timestamp
- Fuzzy search with intelligent matching
- Interactive selection menu for multiple matches

**Usage:**
```
> parse through the fire        # Search by title
> parse dragonforce            # Search by artist
> parse frosted                # Search by charter
> parse 3dfe89a1                # Search by hash
```

**Requirements:**
- Chart index must exist (run `scancharts` first)
- Chart must be in your Clone Hero library

**Help:**
```
> parse --help
```

For detailed usage and examples, see the command's built-in help documentation.

---

## 🔧 Bot Improvements

### **Enhanced First-Time Setup Wizard**

The bot's setup wizard has been completely overhauled to provide foolproof instructions for new server admins.

**New Instructions Added:**

1. **Discord Intents Setup (CRITICAL)** 🔴
   - Step-by-step instructions for enabling required intents
   - Clear warning that bot won't work without these
   - Covers both Server Members Intent and Message Content Intent
   - Positioned prominently in setup flow

2. **Bot Invite Instructions**
   - OAuth2 URL Generator walkthrough
   - Required scopes and permissions clearly listed
   - Copy-paste friendly URLs

3. **Preparation Recommendation**
   - Suggests opening notepad to collect values
   - Makes wizard process smoother and less error-prone

4. **Application Naming Guidance**
   - Example name provided: "Clone Hero Score Tracker"
   - Helps admins create professional-looking bots

**Improved Timezone Selection** 🌍

- **Numeric menu system** - No more typing long timezone strings!
- **23 world timezones** organized by region (Americas, Europe, Asia, Pacific)
- **Short list** (8 North American timezones) shown first
- **Progressive disclosure** - Option to expand to full world list
- **Custom timezone entry** still available for edge cases
- **Validation** - Checks timezone format before accepting

**Example:**
```
Select your timezone:

  NORTH AMERICAN TIMEZONES:
  [1] UTC (Coordinated Universal Time)
  [2] US/Eastern (EST/EDT - New York, Toronto, Miami)
  [3] US/Central (CST/CDT - Chicago, Dallas, Mexico City)
  ...
  [9] See all world timezones (23 options)
  [0] Enter custom timezone manually

Enter timezone choice [1]: 2
[+] Timezone set to: US/Eastern
```

**Wizard Flow Improvements:**

- Cross-references between instructions and wizard steps
  - "Copy the bot token (you'll enter it in Step 1)"
- Organized into clear sections:
  - CREATING THE DISCORD BOT
  - ENABLE REQUIRED INTENTS (CRITICAL)
  - INVITE BOT TO YOUR SERVER
  - GET DISCORD IDs
- Better visual hierarchy with section headers
- Consistent feedback messages throughout

---

## 📚 Documentation Updates

### **README.md - Expanded Bot Setup**

The README's "Bot Setup" section has been completely rewritten with comprehensive step-by-step instructions.

**New Structure:**
- **A. Create Discord Bot Application** (6 steps)
- **B. Configure Bot Intents (CRITICAL)** (3 steps with warnings)
- **C. Configure Bot Permissions** (4 steps with OAuth2 details)
- **D. Get Required IDs** (4 steps with Developer Mode instructions)
- **E. Run Bot Setup Wizard** (overview of wizard prompts)

**What's Covered:**
- Every click required in Discord Developer Portal
- Screenshots would fit perfectly (consider for future)
- Clear warnings about critical steps (intents)
- Troubleshooting context (Guild ID for instant command sync)

### **CLAUDE.md - Discord Bot Setup Requirements**

New dedicated section added for developers and advanced users:

**Contents:**
- Required Discord Intents with code references
- Bot permissions (minimum required)
- OAuth2 scopes breakdown
- Invite URL format with explanation
- First-time setup wizard overview
- Command sync behavior documentation

**Technical Details:**
- Code locations referenced (`bot/bot.py` lines 240-243)
- Explains why each intent is needed
- Documents the difference between Guild ID sync (instant) vs global sync (1 hour)

---

## 🛠️ Technical Changes

### **Files Modified:**

**Bot:**
- `bot_launcher.py` - Setup wizard improvements (lines 373-522)
- `bot/config_manager.py` - Version bump to v2.6.5

**Client:**
- `clone_hero_client.py` - Added `parse` command and help system
  - New functions: `parse_command()`, `_display_chart_metadata()`, `show_parse_help()`
  - Command loop integration (line ~6478)
  - Help text additions

**Documentation:**
- `README.md` - Expanded bot setup section
- `CLAUDE.md` - New Discord Bot Setup Requirements section

**Spec Files:**
- Created `CloneHeroScoreBot_v2.6.5.spec`
- Created `CloneHeroScoreTracker_v2.6.5.spec`

### **No Database Changes**

This release does NOT include database migrations. Config version remains at 7.

---

## 📥 Installation

### **For Server Admins (Bot):**

1. Download `CloneHeroScoreBot_v2.6.5.exe` from GitHub releases
2. If upgrading: Your existing config will be preserved
3. If new install: Run the executable and follow the improved setup wizard
4. The bot will auto-detect the new version

### **For Players (Client):**

1. Download `CloneHeroScoreTracker_v2.6.5.exe` from GitHub releases
2. Existing users: Auto-update will prompt on next launch OR use `update` command
3. New users: Run executable and follow pairing instructions
4. Try the new `parse` command after running `scancharts`

---

## 🔄 Upgrade Notes

### **From v2.6.4:**

✅ **Safe to upgrade** - No breaking changes
- Config files automatically preserved
- No database migrations required
- Existing setup wizards won't re-run for configured installations

### **From Earlier Versions (v2.6.3 and below):**

✅ **Automatic migration** - Config migrations will run as needed
- v2.6.4 added peak intensity tiers (CONFIG_VERSION 7)
- All migrations are non-destructive and preserve user settings

### **First-Time Installations:**

New admins will benefit from the completely overhauled setup wizard with:
- Discord Intents instructions (critical for bot functionality)
- Bot invite walkthrough (OAuth2)
- Improved timezone selection (numeric menu)
- Better preparation guidance (notepad recommendation)

---

## 🐛 Known Issues

None specific to v2.6.5.

For general known issues and troubleshooting, see:
- [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues)
- CLAUDE.md "Important Quirks & Gotchas" section

---

## 🎓 User Guide Highlights

### **New Server Admins:**

1. **Before Starting Setup:**
   - Open notepad to collect Discord IDs and tokens
   - Have Discord Developer Portal open in browser
   - Have your Discord server open (for copying IDs)

2. **Critical Steps NOT to Skip:**
   - ⚠️ Enable Server Members Intent
   - ⚠️ Enable Message Content Intent
   - ⚠️ Copy Guild ID for instant command sync (highly recommended)

3. **After Setup:**
   - Verify bot appears online in Discord
   - Test with `/pair` command
   - Check announcement channel permissions

### **Existing Users:**

1. **Try the New Parse Command:**
   ```
   > parse <song name>
   ```
   Inspect any chart in your library to see:
   - Total notes and NPS values
   - Chart file location
   - Verify metadata is correct

2. **Admin Tip:**
   If you ever need to reconfigure the bot, the wizard is now much clearer
   and includes all the steps you might have missed initially (like intents).

---

## 🔗 Links

- **GitHub Repository:** https://github.com/Dr-Goofenthol/CH_HiScore
- **Latest Release:** https://github.com/Dr-Goofenthol/CH_HiScore/releases/tag/v2.6.5
- **Issues & Feedback:** https://github.com/Dr-Goofenthol/CH_HiScore/issues
- **Discord Developer Portal:** https://discord.com/developers/applications

---

## 🙏 Acknowledgments

Special thanks to:
- Server admins who provided feedback on setup difficulties
- Users who requested better chart inspection tools
- The Clone Hero community for continued support

---

## 📋 Full Changelog

### Added
- **Client:** New `parse` command for manual chart inspection
- **Client:** Detailed help documentation for `parse` command (`parse --help`)
- **Bot:** Discord Intents setup instructions in first-time wizard
- **Bot:** Bot invite instructions (OAuth2) in first-time wizard
- **Bot:** Numeric timezone selection menu with 23 world timezones
- **Bot:** Notepad recommendation in setup wizard welcome screen
- **Bot:** Application naming guidance in setup instructions
- **Docs:** "Discord Bot Setup Requirements" section in CLAUDE.md
- **Docs:** Expanded bot setup section in README.md (A-E subsections)

### Changed
- **Bot:** Reorganized setup wizard welcome screen with clear section headers
- **Bot:** Improved timezone selection UX (numeric menu vs text input)
- **Bot:** Enhanced setup wizard instructions with cross-references
- **Docs:** README bot setup now includes every Discord Developer Portal step
- **Docs:** CLAUDE.md now documents required Discord Intents with code references

### Fixed
- N/A (no bug fixes in this release)

### Removed
- N/A (no features removed)

---

## 🚀 What's Next?

Planned for future releases:
- Web interface for leaderboards (see WEB_INTERFACE_IMPLEMENTATION_PLAN.md)
- Progressive chart index building (background thread during gameplay)
- Automatic weekly chart index refresh
- Server-side retroactive hash resolution with Discord message updates

See [GitHub Issues](https://github.com/Dr-Goofenthol/CH_HiScore/issues) for the full roadmap.

---

**Version:** v2.6.5
**Released:** February 9, 2026
**Build Date:** 2026-02-09
**License:** MIT

---

Made with ❤️ for the Clone Hero community

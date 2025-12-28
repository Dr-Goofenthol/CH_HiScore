# Clone Hero Score Bot v2.5.2 - Testing Checklist

## Pre-Testing Setup

### Prerequisites
- [ ] Both executables built successfully:
  - `CloneHeroScoreBot_v2.5.2.exe` (18MB)
  - `CloneHeroScoreTracker_v2.5.2.exe` (31MB)
- [ ] Discord bot token configured
- [ ] Discord server set up with announcement channel

---

## SECTION 1: Bot Startup & Settings Menu

### 1.1 Bot Launcher
- [ ] Run `CloneHeroScoreBot_v2.5.2.exe`
- [ ] Verify startup menu appears with options:
  - [1] Start Bot
  - [2] Settings Menu
  - [Q] Quit
- [ ] Select [2] Settings Menu
- [ ] Verify settings menu loads without errors

### 1.2 Settings Menu Navigation
- [ ] Verify main menu shows all 9 options:
  - [1] Discord Settings
  - [2] Timezone & Display Settings
  - [3] API Server Settings
  - [4] Logging Settings
  - [5] Announcement Settings ← NEW!
  - [6] Database Settings
  - [7] Preview Announcements
  - [8] View Current Configuration
  - [9] Reset to Defaults
  - [S] Save and Exit
  - [0] Exit Without Saving

---

## SECTION 2: NEW FEATURE - Announcement Color Settings

### 2.1 Access Announcement Settings
- [ ] Select [5] Announcement Settings
- [ ] Verify current configuration displays:
  - Record Breaks: Enabled + Color
  - First-Time Scores: Enabled + Color + Style
  - Personal Bests: Enabled + Color + Min % + Min Points
- [ ] Verify no misleading color names shown (just hex codes)

### 2.2 Test Color Customization
- [ ] Select [2] Set Record Breaks Color
- [ ] Enter a valid hex color: `#FF0000` (red)
- [ ] Verify success message shown
- [ ] Return to menu, verify color updated to `#FF0000`
- [ ] Test invalid color: `#GGGGGG`
- [ ] Verify error message: "Invalid hex color format"
- [ ] Test invalid color: `FF0000` (missing #)
- [ ] Verify error message shown

### 2.3 Test All Color Options
- [ ] Set First-Time Scores Color: `#00FF00` (green)
- [ ] Set Personal Bests Color: `#0000FF` (blue)
- [ ] Verify all colors update correctly in menu display
- [ ] Select [9] Reset All Colors to Defaults
- [ ] Verify colors reset to:
  - Record Breaks: `#FFD700`
  - First-Time Scores: `#4169E1`
  - Personal Bests: `#32CD32`

### 2.4 Test Other Announcement Settings
- [ ] Toggle Record Breaks Enabled/Disabled
- [ ] Verify status changes
- [ ] Toggle First-Time Scores Style (Full/Minimalist)
- [ ] Verify style changes
- [ ] Set Personal Bests Thresholds:
  - Min %: `10.0`
  - Min Points: `25000`
- [ ] Verify values update correctly

### 2.5 Save and Restart
- [ ] Select [0] Back to Main Menu
- [ ] Select [S] Save and Exit
- [ ] Verify config saved message
- [ ] Return to launcher, select [2] Settings Menu again
- [ ] Go to Announcement Settings
- [ ] **Verify all customized colors/settings persisted**

---

## SECTION 3: NEW FEATURE - Improved Fuzzy Search

### 3.1 Multi-Word Query (The Main Fix)
**Test the problem scenario that was fixed:**

- [ ] Start bot (option [1])
- [ ] In Discord, use `/lookupsong through the fire and flames`
- [ ] **Expected:** Returns 1-3 highly relevant results
  - Should prioritize exact phrase match first
  - Should NOT return hundreds of results with just "the" or "and"
- [ ] **Verify:** Results are specific to "through" AND "fire" AND "flames"

### 3.2 Single Artist Search
- [ ] `/lookupsong DragonForce`
- [ ] **Expected:** Returns ALL DragonForce songs
- [ ] **Verify:** Multiple songs shown (if available in database)

### 3.3 Two-Word Title
- [ ] `/lookupsong haywyre endlessly` (or another two-word title)
- [ ] **Expected:** Exact match appears first
- [ ] **Verify:** Must contain BOTH words ("haywyre" AND "endlessly")

### 3.4 Chart Hash Search
- [ ] Get a chart hash from a song (first 8-16 chars)
- [ ] `/lookupsong abc12345` (use actual hash)
- [ ] **Expected:** Finds the specific chart by hash
- [ ] **Verify:** Hash search still works as before

### 3.5 Multiple Charts of Same Song
- [ ] Search for a song that has multiple chart versions
- [ ] **Expected:** All different charts shown (different hashes)
- [ ] **Verify:** Duplicates not shown (same hash only once)

### 3.6 Edge Cases
- [ ] `/lookupsong the` (single stop word)
- [ ] **Expected:** Returns results (fallback behavior works)
- [ ] `/lookupsong a` (single-letter query)
- [ ] **Expected:** Returns results or handles gracefully
- [ ] `/lookupsong` (empty query)
- [ ] **Expected:** Error message or empty results (no crash)

---

## SECTION 4: Color Integration - Discord Announcements

### 4.1 Record Break with Custom Color
**Prerequisites:** Set Record Breaks color to `#FF0000` (red) in settings

- [ ] Play Clone Hero and break a server record
- [ ] Verify Discord announcement appears
- [ ] **Verify embed color is RED (#FF0000)** - not gold
- [ ] Verify title still shows: 🏆 NEW RECORD SET!

### 4.2 First-Time Score with Custom Color
**Prerequisites:** Set First-Time Scores color to `#00FF00` (green)

- [ ] Score on a chart for the first time
- [ ] Verify Discord announcement appears
- [ ] **Verify embed color is GREEN (#00FF00)** - not blue
- [ ] Verify title shows: 🎸 FIRST SCORE ON CHART!

### 4.3 Personal Best with Custom Color
**Prerequisites:**
- Set Personal Bests color to `#0000FF` (blue)
- Enable Personal Bests announcements
- Set thresholds: 5% and 10,000 points

- [ ] Improve a personal best (meet thresholds)
- [ ] Verify Discord announcement appears
- [ ] **Verify embed color is BLUE (#0000FF)** - not green
- [ ] Verify title shows: 📈 PERSONAL BEST!

### 4.4 Invalid Color Handling
**Prerequisites:** Manually edit config file to have invalid color

- [ ] Stop bot
- [ ] Edit `bot_config.json` in AppData
- [ ] Set record_breaks.embed_color to `#GGGGGG`
- [ ] Save and restart bot
- [ ] Trigger a record break
- [ ] **Verify:** Bot console shows warning about invalid color
- [ ] **Verify:** Announcement still posts with default gold color
- [ ] **Verify:** Bot doesn't crash

---

## SECTION 5: Existing v2.5.2 Features (Regression Testing)

### 5.1 Timezone Conversion
- [ ] Set timezone to non-UTC (e.g., America/New_York)
- [ ] Trigger an announcement
- [ ] Verify "Achieved" field shows correct timezone
- [ ] Verify timezone abbreviation shown (EST, PST, etc.)

### 5.2 Minimalist Mode
- [ ] Enable minimalist mode for first-time scores
- [ ] Score on new chart
- [ ] Verify announcement has fewer fields
- [ ] Verify charter, accuracy, play count hidden
- [ ] Verify essential fields present (title, score, stars, hash)

### 5.3 Personal Best Thresholds
- [ ] Set thresholds: 10% and 25,000 points
- [ ] Improve score by 8% (below threshold)
- [ ] Verify NO announcement posted
- [ ] Improve score by 12% AND 30,000 points
- [ ] Verify announcement DOES post

### 5.4 Database Auto-Backup
- [ ] Restart bot
- [ ] Verify backup message on startup
- [ ] Check AppData folder for backup files
- [ ] Verify backup file exists with timestamp
- [ ] Verify old backups rotated (only 7 kept)

### 5.5 Command Privacy
- [ ] Set `/leaderboard` to private in settings
- [ ] Use `/leaderboard` in Discord
- [ ] Verify response is ephemeral (only you see it)
- [ ] Set back to public
- [ ] Verify response is visible to everyone

### 5.6 Preview System
- [ ] Access Settings Menu → [7] Preview Announcements
- [ ] Select [1] Record Break (full detail)
- [ ] Verify ASCII art preview shows without errors
- [ ] Verify no Unicode/emoji encoding errors
- [ ] Test all 4 preview types

### 5.7 Log Rotation
- [ ] Check log file size in AppData
- [ ] If under 10MB, wait for it to grow (or manually add data)
- [ ] Verify log rotates when exceeding 10MB
- [ ] Verify old logs kept (5 backups)

---

## SECTION 6: Integration Testing

### 6.1 Full Workflow Test
- [ ] Start fresh with default config
- [ ] Open Settings Menu
- [ ] Customize all announcement colors
- [ ] Set custom timezone
- [ ] Enable personal bests with thresholds
- [ ] Enable minimalist mode
- [ ] Save and exit
- [ ] Start bot
- [ ] Verify backup created
- [ ] Play Clone Hero, trigger all 3 announcement types
- [ ] Verify all customizations applied correctly:
  - Colors match your settings
  - Timezone shows correctly
  - Personal best threshold works
  - Minimalist mode applied

### 6.2 Config Persistence
- [ ] Customize settings
- [ ] Save and exit
- [ ] Close bot completely
- [ ] Reopen bot
- [ ] Verify all settings persisted (didn't reset)

### 6.3 Multiple Restarts
- [ ] Restart bot 3 times in a row
- [ ] Verify no errors on any startup
- [ ] Verify config loads correctly each time
- [ ] Verify backups rotate properly

---

## SECTION 7: Error Handling & Edge Cases

### 7.1 Config Error Recovery
- [ ] Stop bot
- [ ] Delete `bot_config.json`
- [ ] Restart bot
- [ ] Verify default config created
- [ ] Verify bot starts successfully

### 7.2 Invalid Config Values
- [ ] Set timezone to invalid value: "Invalid/Zone"
- [ ] Start bot
- [ ] Verify fallback to UTC (warning shown)
- [ ] Verify bot doesn't crash

### 7.3 Settings Menu Errors
- [ ] Try to enter very long hex color: `#FFFFFFFFFFFFFFFFFF`
- [ ] Verify rejected (length check)
- [ ] Try negative threshold values
- [ ] Verify validation error

### 7.4 Search Edge Cases
- [ ] Search with special characters: `%`, `_`, `'`
- [ ] Verify no SQL errors
- [ ] Verify results shown or empty (graceful handling)

---

## SECTION 8: Client Testing (Quick Smoke Test)

### 8.1 Tracker Executable
- [ ] Run `CloneHeroScoreTracker_v2.5.2.exe`
- [ ] Verify version shows 2.5.2
- [ ] Verify startup successful
- [ ] Test pairing with Discord bot
- [ ] Score a song in Clone Hero
- [ ] Verify score submits successfully

---

## SECTION 9: Performance & Stability

### 9.1 Memory Leaks
- [ ] Let bot run for 30+ minutes
- [ ] Check Task Manager for memory usage
- [ ] Verify memory doesn't continuously grow
- [ ] Verify CPU usage is normal (~0-1% idle)

### 9.2 Concurrent Operations
- [ ] Have multiple users score simultaneously
- [ ] Verify all scores processed
- [ ] Verify no race conditions or crashes
- [ ] Verify all announcements post correctly

---

## SECTION 10: Final Verification

### 10.1 Documentation Match
- [ ] Compare implemented features to `v2.5.2_FINAL_SUMMARY.md`
- [ ] Verify all 12 features work as documented
- [ ] Verify no undocumented behavior

### 10.2 Version Numbers
- [ ] Verify bot shows v2.5.2 on startup
- [ ] Verify config version is 4
- [ ] Verify client shows v2.5.2

### 10.3 Clean Installation Test
- [ ] On a test machine (or clean environment):
  - [ ] Delete all AppData configs
  - [ ] Run fresh executable
  - [ ] Complete initial setup
  - [ ] Verify everything works from scratch

---

## Critical Issues Checklist

**If any of these FAIL, do NOT proceed with release:**

- [ ] ❌ Bot crashes on startup
- [ ] ❌ Config file corruption/loss
- [ ] ❌ Discord announcements not posting
- [ ] ❌ Fuzzy search returns nothing for valid queries
- [ ] ❌ Custom colors not applying to announcements
- [ ] ❌ Settings not persisting after restart
- [ ] ❌ Database errors preventing score storage
- [ ] ❌ Infinite error loops or hangs

---

## Sign-Off

### Test Results Summary
- **Total Tests:** 100+
- **Passed:** _____ / _____
- **Failed:** _____ / _____
- **Critical Issues:** _____ (must be 0 to release)

### Tester Notes
```
[Your observations, issues found, or notes here]
```

### Ready for Release?
- [ ] YES - All tests passed, ready for GitHub release
- [ ] NO - Issues found (see notes above)

---

## Post-Testing Actions

If all tests pass:
1. Create GitHub tag: `v2.5.2`
2. Attach both executables to release
3. Copy relevant sections from `v2.5.2_FINAL_SUMMARY.md` to release notes
4. Highlight the two NEW features:
   - Announcement Color Customization
   - Improved Fuzzy Search (/lookupsong)
5. Publish release

---

**Testing Date:** _____________
**Tester:** _____________
**Environment:** Windows _____ / Python _____
**Completion Time:** _____ hours

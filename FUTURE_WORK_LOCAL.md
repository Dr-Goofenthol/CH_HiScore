# Future Features & Improvements - Working List
**Status:** Local planning document (not for GitHub)
**Last Updated:** 2025-12-28
**Current Version:** v2.5.3 (testing)

---

## 🔧 Pending from v2.5.4.1 Testing

### Bridge Integration Issues
- [ ] **First-launch search not executing reliably**
  - **Status:** Known bug (v2.5.4.1)
  - Current behavior: Bridge launches, fields fill correctly, but Search button doesn't click
  - Works reliably when Bridge is already running
  - Polling approach waits for elements but Search button still not clicking on fresh launch
  - Possible causes:
    - Button exists in DOM but isn't actually interactive yet
    - Angular form validation might be preventing click
    - Bridge might be doing additional initialization after DOM renders
  - Temporary workaround: User can manually click Search after fields auto-fill
  - Future solutions to explore:
    - Check button's `disabled` attribute before clicking
    - Wait for Angular form to be valid before searching
    - Use Bridge's IPC methods directly if exposed for search
    - Monitor network requests to detect when Bridge is fully initialized

### Discord Bridge Links
- [ ] **Discord Bridge deeplink buttons - SHELVED**
  - **Status:** Feature shelved (v2.5.4.1)
  - **Issue:** Discord doesn't recognize `chbridge://` protocol as clickable link
  - **Root cause:** Discord has hardcoded whitelist of URL protocols (http, https, discord, etc.)
  - **Attempted solutions:**
    1. Inline markdown links - Didn't work (Discord treats chbridge:// as plain text)
    2. Discord button with ephemeral instructions - User rejected due to poor UX
       - Button showed copy-paste instructions for manual deeplink execution
       - Required too many steps (Win+R, copy, paste, Enter)
       - Cluttered interface with buttons on every announcement/command
       - User quote: "This looks terrible and I hate it"
  - **Current state:**
    - Bridge integration remains functional as **client-side only feature**
    - `chbridge://` protocol works when manually launched (client can trigger it)
    - Discord announcements and commands reverted to show **Enchor.us links only**
    - All `BridgeLinkView` button code removed from bot.py and api.py
  - **Planned solution for future implementation:**
    - **Caddy reverse proxy with bot-hosted redirect service** (RECOMMENDED)
      - Add lightweight `/bridge` redirect endpoint to existing bot aiohttp server
      - Use Caddy reverse proxy for automatic HTTPS with Let's Encrypt
      - User already has DNS (`jake-realm.freemyip.com`) and port forwarding setup
      - Implementation steps:
        1. Add redirect route to `bot/api.py` (returns HTML with meta refresh to `chbridge://`)
        2. Install Caddy on bot server
        3. Configure Caddyfile (3 lines) to proxy HTTPS → bot
        4. Forward ports 80 (Let's Encrypt validation) and 443 (HTTPS) to bot server
        5. Add `PUBLIC_URL` config option for Discord link generation
        6. Update `build_bridge_url()` to use `{PUBLIC_URL}/bridge?name=...`
      - Pros: Zero external services, automatic cert management, ~50 lines of code
      - Cons: Requires public bot server, port forwarding configuration
      - **Status:** Implementation planned, shelved pending user availability
    - Alternative considered: Cloudflare Workers / ngrok (rejected - prefer self-hosted)
  - **Lessons learned:**
    - Always verify platform limitations before implementing protocol-dependent features
    - Test Discord link rendering with non-standard protocols early
    - Simple solutions (Enchor.us web links) often better than complex workarounds
  - **Related code:**
    - Client Bridge integration still functional: `client/bridge_integration.py`
    - Protocol handler registered: `chbridge://search?name=...&artist=...&charter=...`
    - Bot code reverted: Removed all Bridge buttons, kept `generate_bridge_url()` for potential future use

## 🔧 Pending from v2.5.3 Testing

### Instrument ID Refinement
- [ ] **Verify and refine instrument ID mappings (IDs 7-10)**
  - **ID 8 confirmed:** Co-op mode (both players on lead guitar) - Dec 28, 2025
  - Current label: "GH Live Co-op" - may need to change to "Guitar Co-op" or just "Co-op"
  - Need user testing data for IDs 7, 9, 10
  - Consider renaming based on actual Clone Hero usage patterns
  - May need different co-op IDs for different instrument combinations
  - Action: Wait for more user reports of "Unknown (ID X)" to identify remaining IDs

### Discord Command UX Improvements
- [ ] **Beautify `/recent` command output to match `/leaderboard` formatting**
  - Current format shows basic text output with dates
  - Goal: Match field structure and visual layout of `/leaderboard` command
  - Keep date information (currently shows YYYY-MM-DD)
  - Example desired format:
    ```
    Recent Record Breaks
    Last 2 Record Break(s)

    Andrew the Amigo broke the record on:
    Before I Forget - Slipknot (Hard Lead)
    Score: 212,692 (was 129,126 by Andrew the Amigo)
    2025-12-29

    Jake the Simpatico broke the record on:
    The Magic Spider - Nekrogoblikon (Expert Lead)
    Score: 129,322 (was 117,330 by Andrew the Amigo)
    2025-12-29
    ```
  - Consider using Discord embed fields for cleaner presentation
  - Maintain consistency with other command outputs

### Client Terminal Feedback Improvements
- [ ] **Show detailed feedback for scores below personal best**
  - Current issue: "No new scores detected (might be a replay or same score)" is unhelpful
  - User doesn't know: which song, what score, how far below PB
  - Root cause: Client parses ALL scores in scoredata.bin, doesn't track what just changed
  - Proposed solution:
    1. Store previous parse results to compare against current parse
    2. Identify which score(s) changed (new entries or modified scores)
    3. For scores that didn't improve, show feedback:
       ```
       Song: Through the Fire - DragonForce (Expert Lead)
       Your Score: 140,000 pts
       Personal Best: 150,000 pts
       Difference: -10,000 pts (-6.7%)
       ```
    4. For exact matches: "Matched your personal best (150,000 pts)"
  - Implementation: Add `previous_scores` dict to file_watcher, diff on each parse
  - Benefits: Much clearer feedback, shows progress even on failed improvement attempts

### Bot Launcher Issues
- [ ] **Fix Ctrl+C handler in bot server mode**
  - Current issue: Ctrl+C exits the terminal entirely instead of returning to launcher
  - Expected: Should catch KeyboardInterrupt and return to launcher menu
  - Problem: Discord.py's `bot.run()` may be handling Ctrl+C in a way that prevents our handler from working
  - Current code at `bot_launcher.py:772-776` has try/except but doesn't trigger
  - Possible solutions:
    - Use Discord.py's built-in shutdown mechanism
    - Run bot in separate thread with signal handling
    - Use asyncio.run with proper cleanup
  - Test thoroughly to ensure graceful shutdown

---

## 🎯 High Priority Features

### New Commands/Features
- [ ] **Global leaderboards** - `/globalboard <song>` showing top scores across all users
  - Would require filtering by instrument/difficulty
  - Could show top 10 or configurable limit
  - Maybe pagination for large leaderboards

- [ ] **Achievement system** - Track milestones (100 songs played, first FC, etc.)
  - Database table for achievements
  - Discord notifications when earned
  - `/achievements` command to view progress

- [ ] **Song search command** - `/findsong <partial_title>` to search by song name
  - Fuzzy matching on title/artist
  - Return hash + basic info for use with other commands
  - Helpful when hash is unknown

- [ ] **Streak tracking** - Track consecutive days/scores
  - "X days in a row playing"
  - Could show in `/mystats`
  - System tray notification when streak is maintained

### Quality of Life Improvements
- [ ] **Guided first-time setup** - Interactive setup wizard
  - Check for Clone Hero installation
  - Verify settings.ini configuration
  - Test API connection before pairing
  - Validate song_export and auto_screenshot settings

- [ ] **Better progress indication for resolvehashes**
  - Show percentage complete during scan
  - Estimated time remaining
  - Running total of matches found
  - Option to cancel mid-scan

- [ ] **Bulk metadata updates** - Update multiple songs at once
  - CSV import for batch updates
  - Useful for correcting artist names across a setlist
  - Could integrate with Chorus API for authoritative data

- [ ] **Score history graph** - Visual representation of improvement
  - Show score progression over time for specific song
  - Could be Discord embed with chart image
  - `/history <song>` command

---

## 🐛 Known Issues & Bug Fixes

### Minor Bugs
- [ ] **OCR accuracy issues** - Sometimes misreads numbers on results screen
  - Could add validation (score from OCR vs scoredata.bin)
  - Multiple OCR attempts with majority vote
  - User-configurable OCR regions

- [ ] **currentsong.txt caching edge case** - If Clone Hero crashes during song, cache isn't updated
  - Could add timeout for stale cache entries
  - Fallback to "Unknown" if cache is too old

- [ ] **Unicode handling in console** - Some song titles with special characters display incorrectly
  - Already fixed ✓ to ASCII in some places
  - May need more comprehensive Unicode normalization

### Edge Cases
- [ ] **Multiple Clone Hero instances** - What happens if user runs CH twice?
  - Currently might detect scores twice
  - Could add instance detection
  - Or just document as unsupported

- [ ] **Very large song libraries** - resolvehashes slow with 10,000+ songs
  - Could add progress indicators
  - Maybe incremental scanning (save partial results)
  - Parallel processing for hash calculation

- [ ] **Network interruptions during score submission** - Score might be lost
  - Add retry logic with exponential backoff
  - Queue failed submissions for later retry
  - Notify user if submission ultimately fails

---

## 🚀 Performance Optimizations

### Bridge Integration
- [ ] **Background service for Bridge deeplinks** - Eliminate exe startup delay
  - **Status:** Shelved (v2.5.4.1)
  - **Current issue:** Each `chbridge://` link click launches new tracker instance (~3-4 second PyInstaller startup)
  - **Proposed solution:** Persistent background service that handles deeplinks
    - Service runs continuously in system tray
    - Listens for `chbridge://` protocol invocations via IPC or named pipe
    - Eliminates 3-4 second exe startup overhead
    - Would reduce total deeplink time from ~7 seconds to ~2-3 seconds
  - **Implementation approach:**
    1. Create lightweight background process (separate exe or integrated into tracker)
    2. Register as Windows service or autostart app
    3. Listen for protocol events via named pipe or local socket
    4. Forward deeplink requests to Bridge integration module
    5. Keep CDP connection pool for faster Bridge communication
  - **Complexity:** Medium-High
    - Requires IPC mechanism
    - Service lifecycle management (start, stop, restart)
    - Error handling for service crashes
    - Uninstallation cleanup
  - **Benefits:**
    - 60% faster deeplink execution (4-5 second savings)
    - Better user experience (more responsive)
    - Eliminates "flashing window" on each link click
  - **Considerations:**
    - Adds complexity to deployment
    - Another process for users to manage
    - Resource overhead (minimal, but always-running)
    - Testing across different Windows versions
  - **Alternative approaches:**
    - Use existing tracker instance if already running (check for instance lock)
    - HTTP server listening on localhost port (simpler IPC)
    - Windows COM server (native Windows IPC)

### Database
- [ ] **Index optimization** - Add indexes for common queries
  - `scores(chart_hash, user_id)` composite index
  - `scores(submitted_at)` for recent queries
  - Analyze query plans for `/leaderboard` and `/mystats`

- [ ] **Query result caching** - Cache frequently accessed leaderboards
  - In-memory cache for top 10 songs
  - Invalidate on new score submission
  - Could significantly reduce DB load

- [ ] **Database vacuuming** - Periodic VACUUM to reclaim space
  - Could run on startup if DB size exceeds threshold
  - Or scheduled maintenance command

### Client Performance
- [ ] **Lazy loading for large state files** - Don't load all known_scores into memory
  - SQLite could store state instead of JSON
  - Would scale better for users with 1000+ songs played

- [ ] **Optimized file watching** - Reduce CPU usage during monitoring
  - Current implementation is already good
  - Could add configurable debounce delay

---

## 📊 Data & Analytics

### New Data Tracking
- [ ] **Play count per song** - How many times each song has been played
  - Already tracked in database (v2.4.12)
  - Could add `/mostp played` command

- [ ] **Score distribution** - Statistics on score ranges
  - Average score across all songs
  - Median, percentiles
  - Could show in `/mystats`

- [ ] **Difficulty preference** - Which difficulty user plays most
  - Count scores by difficulty
  - Show in `/mystats` as pie chart or bar graph

- [ ] **Instrument usage** - Track which instruments user plays
  - Similar to difficulty preference
  - "You mostly play Lead Guitar"

### Discord Analytics
- [ ] **Server-wide statistics** - `/serverstats` command
  - Total scores tracked
  - Most active users
  - Most played songs
  - Recent record breaks (aggregate)

- [ ] **Monthly/Weekly reports** - Automated summary posts
  - "This week: X records broken, Y new users"
  - Could be scheduled Discord message
  - Or `/weeklysummary` command

---

## 🎨 User Experience Enhancements

### Discord Embed Improvements
- [ ] **Customizable embed colors** - User preference for announcement colors
  - Per-user settings in database
  - Or server-wide theme

- [ ] **Reaction buttons** - Add reactions to announcements
  - 🎉 for celebrating record breaks
  - 🔥 for hot streaks
  - Could track reactions as "likes"

- [ ] **Rich presence integration** - Show "Playing Clone Hero" in Discord status
  - Would need Discord Rich Presence SDK
  - Could show current song name
  - Medium-high complexity

### Client UI Improvements
- [ ] **GUI version** - Graphical interface instead of console
  - Could use tkinter or PyQt
  - Would be major undertaking
  - Lower priority (console works fine)

- [ ] **Better error messages** - More actionable feedback
  - "Cannot connect to bot" → "Check bot URL in settings"
  - Include suggested fixes in error messages
  - Link to troubleshooting docs

- [ ] **Settings validation** - Validate user input in settings command
  - URL format validation
  - Port number range checking
  - Path existence verification

---

## 🔧 Technical Improvements

### Code Quality
- [ ] **Type hints** - Add comprehensive type annotations
  - Already have some with `from __future__ import annotations`
  - Could add mypy for static type checking
  - Would improve IDE support

- [ ] **Unit tests** - Add automated testing
  - Test score parsing logic
  - Test database operations
  - Test API endpoints
  - Currently zero test coverage

- [ ] **Integration tests** - End-to-end testing
  - Mock score submission flow
  - Test pairing process
  - Test Discord commands
  - Would catch regressions

### Architecture
- [ ] **Plugin system** - Allow community extensions
  - Could load custom commands
  - Custom score processors
  - Would need careful security design

- [ ] **Webhook support** - Alternative to Discord bot
  - Some users might want webhooks instead
  - Simpler setup (no bot hosting)
  - Trade-off: no slash commands

- [ ] **REST API documentation** - OpenAPI/Swagger spec
  - Document all endpoints
  - Auto-generate API docs
  - Would help third-party integrations

---

## 📱 Platform Support

### Cross-Platform
- [ ] **Linux support** - Make client work on Linux
  - Replace Windows OCR with Tesseract
  - Test on Wine for Clone Hero
  - Check file path handling

- [ ] **macOS support** - Similar to Linux
  - Clone Hero runs on macOS
  - Would need macOS-specific OCR
  - Lower priority (smaller user base)

### Alternative Deployment
- [ ] **Web dashboard** - Browser-based interface
  - View leaderboards without Discord
  - Could host on GitHub Pages
  - Static site with API calls

- [ ] **Mobile app** - View stats on phone
  - React Native or Flutter
  - Read-only (no score submission)
  - Very low priority

---

## 🔒 Security Enhancements

### API Security
- [ ] **Rate limiting** - Prevent API abuse
  - Limit score submissions per minute
  - Limit pairing attempts
  - Would prevent spam

- [ ] **HTTPS support** - Optional SSL/TLS
  - For users who want it
  - Would need certificate management
  - Currently overkill for localhost

- [ ] **Auth token rotation** - Periodic token refresh
  - Could invalidate old tokens after 90 days
  - Force re-pairing
  - Better security hygiene

### Data Protection
- [ ] **Score backup/export** - Allow users to export their data
  - JSON export of all scores
  - SQLite database download
  - Privacy compliance (GDPR-ish)

- [ ] **Data deletion** - `/deletemydata` command
  - Remove all user scores from database
  - Unpair from Discord
  - Right to be forgotten

---

## 📚 Documentation

### User Documentation
- [ ] **Video tutorial** - Setup walkthrough
  - YouTube video or GIF guide
  - Show pairing process
  - Demonstrate commands

- [ ] **FAQ document** - Common questions
  - "Why isn't my score showing up?"
  - "How do I update the bot?"
  - "Can I use this with multiple PCs?"

- [ ] **Troubleshooting guide** - Fix common issues
  - Connection problems
  - Missing song data
  - OCR not working

### Developer Documentation
- [ ] **API documentation** - Endpoint specifications
  - Request/response examples
  - Authentication details
  - Error codes

- [ ] **Architecture diagram** - Visual system overview
  - Data flow diagram
  - Component relationships
  - Would help onboarding

- [ ] **Contributing guide** - How to contribute
  - Code style guidelines
  - PR process
  - Testing requirements

---

## 🎮 Game Integration

### Clone Hero Features
- [ ] **Setlist integration** - Track setlist progress
  - Detect when user completes a setlist
  - Announce setlist completion
  - Show setlist statistics

- [ ] **Practice mode detection** - Don't track practice mode scores
  - Would need to detect practice mode somehow
  - Maybe from currentsong.txt?
  - Prevents inflated play counts

- [ ] **Multiplayer support** - Track scores for multiple players
  - Clone Hero supports local multiplayer
  - Would need to distinguish players
  - Complex: pairing multiple users per client

### Community Features
- [ ] **Chart pack detection** - Identify which chart pack a song is from
  - Could use folder structure
  - Or maintain chart pack database
  - Show in announcements: "from Carpal Tunnel Hero 2"

- [ ] **Charter leaderboards** - Most played charters
  - `/topcharters` command
  - Show which charters are popular
  - Could include Enchor.us links

---

## 💡 Ideas / Brainstorming

### Gamification
- [ ] **Leaderboard tiers** - Bronze/Silver/Gold/Platinum rankings
  - Based on score percentile
  - Visual badges in Discord embeds
  - Could motivate improvement

- [ ] **Challenges** - Weekly/monthly challenges
  - "Play 10 songs this week"
  - "Beat a record on Expert difficulty"
  - Rewards could be Discord roles

- [ ] **Rivalries** - Track head-to-head comparisons
  - `/compare @user` to see who's better
  - Win/loss record on specific songs
  - Friendly competition

### Social Features
- [ ] **Score sharing** - Share score screenshots
  - Generate image of score + song info
  - Post to Discord or social media
  - Include Enchor.us link

- [ ] **Friend system** - Follow other players
  - Get notified when friends beat your scores
  - See friends' recent scores
  - `/friends` command

- [ ] **Clans/Teams** - Group players into teams
  - Team leaderboards
  - Team challenges
  - Could be fun for large servers

### Data Visualization
- [ ] **Charts and graphs** - Visual statistics
  - Score progression over time
  - Difficulty distribution pie chart
  - Instrument usage bar graph
  - Could use matplotlib or Chart.js

- [ ] **Heatmaps** - When do users play most?
  - Time of day heatmap
  - Day of week patterns
  - Could show in `/mystats`

---

## 🔄 Maintenance & Operations

### Automated Maintenance
- [ ] **Database backup** - Automatic backups
  - Daily backup to separate file
  - Configurable retention period
  - Could backup to cloud storage

- [ ] **Log rotation** - Prevent log files from growing too large
  - Rotate logs daily/weekly
  - Keep last N log files
  - Compress old logs

- [ ] **Health monitoring** - Detect when system is unhealthy
  - Check API responsiveness
  - Monitor database size
  - Alert if issues detected

### Developer Tools
- [ ] **Debug dashboard** - Web UI for debugging
  - View recent scores
  - Check pairing status
  - Monitor API requests
  - Local-only access

- [ ] **Performance profiling** - Identify bottlenecks
  - Add timing instrumentation
  - Profile database queries
  - Optimize hot paths

---

## 📝 Notes & Considerations

### Implementation Priority
1. **High:** Features that fix pain points or add significant value
2. **Medium:** Nice-to-have improvements
3. **Low:** Experimental or niche features

### Breaking Changes
Some features would require database migrations or breaking API changes:
- Adding new fields to scores table
- Changing authentication scheme
- Modifying command names/signatures

Always document breaking changes and provide migration path.

### User Feedback
Before implementing major features, consider:
- Is this actually requested by users?
- Does it solve a real problem?
- Is the complexity justified?

### Scope Creep
Avoid feature creep. Focus on core functionality:
- Score tracking ✓
- Leaderboards ✓
- Discord integration ✓

New features should enhance these core pillars, not distract from them.

---

## ✅ Recently Completed (for reference)

- [x] Charter data pipeline (v2.4.12-v2.4.15)
- [x] resolvehashes command (v2.4.15)
- [x] Play count tracking (v2.4.12)
- [x] Record hold duration (v2.4.12)
- [x] Enchor.us integration (v2.4.12)
- [x] User-filtered hash resolution (v2.4.15)
- [x] Proper settings.ini parsing (v2.4.15)

---

**End of Document**

This is a living document. Add/remove items as priorities change.

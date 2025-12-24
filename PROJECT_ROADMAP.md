# Clone Hero High Score Tracker - Project Roadmap

## Current Status (v2.4.12)

✅ **Stable and Feature-Complete** for core functionality
- Discord announcements with rich metadata
- Play count tracking
- Charter attribution
- Record duration display
- Enchor.us integration
- System tray with auto-update
- Multi-PC development support

---

## Planned Features & Ideas

### 🎯 High Priority (Quality of Life Improvements)

#### 1. Better Error Messages
- **Status:** Planned for v2.4.13
- **Description:** Improve debug mode authorization error messages
- **Impact:** Better UX when troubleshooting
- **Effort:** Low (single function update)

#### 2. Discord Thread Support for Record History
- **Status:** Discussed, shelved
- **Description:** When a record is broken, create a Discord thread showing:
  - Top 3 all-time scores for that chart/instrument/difficulty
  - Previous record holder info
  - Record progression history
- **Benefits:**
  - Reduces visual clutter in main channel
  - Provides context for competitive players
  - Shows record progression over time
- **Challenges:**
  - Thread permissions required
  - Database queries for historical records
  - Edge cases (first record, insufficient history)
- **Effort:** Medium (2-3 hours)
- **User Feedback:** "I want to shelve that aspect for now"

### 🔮 Future Considerations

#### 3. Bridge Desktop App Integration
- **Status:** Investigated, blocked
- **Description:** Add link to open charts in Bridge desktop app
- **Current Blocker:** Bridge doesn't support URL schemes or deep linking
- **Options:**
  - Submit feature request to Bridge developer for `bridge://` protocol
  - Wait for Bridge to add deep linking support
  - Provide non-clickable search instructions
- **Effort:** N/A (external dependency)
- **User Feedback:** "We will not implement any sort of bridge features for now"

#### 4. Enhanced Leaderboards
- **Status:** Hypothetical
- **Ideas:**
  - Per-charter leaderboards
  - Difficulty-specific rankings
  - Weekly/monthly leaderboards
  - Genre-based leaderboards (if metadata available)
- **Effort:** Medium-High (database queries + Discord embeds)

#### 5. Achievement System
- **Status:** Hypothetical
- **Ideas:**
  - Milestones (100 FCs, 1000 plays, etc.)
  - Combo breaker achievements (beat X consecutive records)
  - Difficulty progression tracking
  - Charter appreciation badges (FC all songs by X charter)
- **Effort:** High (new database tables + logic)

#### 6. Score Comparison Features
- **Status:** Hypothetical
- **Ideas:**
  - Compare your score to previous record with detailed breakdown
  - Show accuracy improvement over time
  - Highlight which sections improved (if data available)
- **Effort:** Medium (requires additional data collection)

#### 7. Custom Announcement Themes
- **Status:** Hypothetical
- **Ideas:**
  - Different embed colors for different record types
  - Custom templates per server
  - Configurable field order
  - Trophy emojis for top performers
- **Effort:** Medium (configuration system)

#### 8. Analytics Dashboard
- **Status:** Hypothetical
- **Ideas:**
  - Web dashboard showing server statistics
  - Top players, most played charts, etc.
  - Record progression graphs
  - Activity heatmaps
- **Effort:** Very High (new web interface)

### 🛠️ Technical Improvements

#### 9. Better OCR Reliability
- **Status:** Ongoing
- **Current:** ~85-90% success rate with Windows OCR
- **Ideas:**
  - Improve image preprocessing
  - Add fallback OCR engines
  - Machine learning for text recognition
- **Effort:** High (research + testing)

#### 10. Database Optimization
- **Status:** Hypothetical
- **Ideas:**
  - Add indices for common queries
  - Implement caching for leaderboards
  - Archive old records
- **Effort:** Medium (database migration)

#### 11. Multi-Server Support
- **Status:** Hypothetical
- **Description:** Allow one bot instance to manage multiple Discord servers
- **Challenges:**
  - Per-server configuration
  - Isolated leaderboards
  - Resource management
- **Effort:** High (architectural changes)

#### 12. API Rate Limiting
- **Status:** Hypothetical
- **Description:** Protect bot API from abuse
- **Ideas:**
  - Per-client rate limits
  - Exponential backoff
  - Ban malicious IPs
- **Effort:** Medium

---

## Recently Completed Features (v2.4.12)

### ✅ Discord Announcement Enhancements
- Charter name as separate field
- Play count tracking
- "Held for X" duration display
- Improved layout (3-field rows)

### ✅ Multi-PC Development Support
- Comprehensive CLAUDE.md documentation
- Setup instructions for new machines
- Dependency documentation

### ✅ Bug Fixes
- Unicode encoding issues
- Type annotation errors
- Missing PyInstaller dependencies

---

## Feature Request Process

### How to Propose a Feature

1. **Create an issue** on GitHub with:
   - Clear description of the feature
   - Use case / problem it solves
   - Example screenshots or mockups
   - Estimated impact (who benefits?)

2. **Label appropriately:**
   - `enhancement` - New feature
   - `bug` - Something broken
   - `quality-of-life` - UX improvement
   - `technical-debt` - Code cleanup

3. **Discuss trade-offs:**
   - Complexity vs benefit
   - Performance impact
   - Breaking changes?
   - Alternative solutions?

---

## Version Planning Philosophy

### Semantic Versioning (v2.X.Y)

- **Major (v3.0.0):** Breaking changes, major architecture updates
- **Minor (v2.X.0):** New features, non-breaking
- **Patch (v2.4.X):** Bug fixes, small improvements

### Release Criteria

**Every release should:**
- ✅ Build successfully on fresh machine
- ✅ Pass manual testing checklist
- ✅ Update CLAUDE.md
- ✅ Create CHANGELOG
- ✅ Tag on GitHub
- ✅ Work with existing configs (backward compatible)

---

## Questions to Consider for Next Release

1. **What's causing the most user friction?**
   - Error messages?
   - Configuration complexity?
   - Missing features?

2. **What would provide the most value?**
   - More data in announcements?
   - Better historical tracking?
   - Community features?

3. **What's achievable in 1-2 hours?**
   - Quick wins for immediate impact
   - Technical debt cleanup

4. **What requires research first?**
   - Features with unknowns
   - External dependencies
   - Performance implications

---

## Current Development Environment

### Supported Platforms
- Windows 10/11 (primary)
- Python 3.12.4
- PyInstaller 6.5.0

### Multi-PC Setup
- Development happens across multiple machines
- GitHub as source of truth
- Shared package files critical (`shared/`)
- All dependencies documented

### Key Dependencies
- **Client:** `colorama`, `requests`, `watchdog`, `pystray`, `pillow`
- **Bot:** `python-dotenv`, `discord.py`, `aiohttp`
- **Shared:** No external deps (stdlib only)

---

## Community & Support

### GitHub Repository
https://github.com/Dr-Goofenthol/CH_HiScore

### Discord
- Announcements in configured server channel
- Support via GitHub Issues

### Documentation
- `CLAUDE.md` - Developer guide
- `CLIENT_SETUP.md` - User setup
- `CHANGELOG_*.md` - Release notes

---

## Acknowledgments

- Clone Hero community for testing and feedback
- Enchor.us for chart database and metadata
- Bridge desktop app for chart browsing

---

**Last Updated:** December 23, 2024 (v2.4.12)

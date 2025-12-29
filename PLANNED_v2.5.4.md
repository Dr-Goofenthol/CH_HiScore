# v2.5.4 Development Plan
**Status:** Planning (not started)
**Planned Start:** 2025-12-29
**Priority:** High priority UX improvements

---

## 🎯 Primary Goals

### 1. Client Terminal Feedback Improvements (HIGH PRIORITY)
**Issue:** "No new scores detected (might be a replay or same score)" is unhelpful

**Current Problem:**
- scoredata.bin changes (file watcher detects it)
- Client parses ALL scores in file (could be hundreds)
- Compares each to local state
- If none are improvements → generic "No new scores detected" message
- User doesn't know: which song, what score, how far below PB

**Root Cause:**
- Code doesn't track WHICH specific score just changed
- Only knows "nothing improved"

**Proposed Solution:**
1. Store previous parse results to compare against current parse
2. Identify which score(s) changed (new entries or modified scores)
3. For scores that didn't improve, show detailed feedback:
   ```
   Song: Through the Fire - DragonForce (Expert Lead)
   Your Score: 140,000 pts
   Personal Best: 150,000 pts
   Difference: -10,000 pts (-6.7%)
   ```
4. For exact matches: "Matched your personal best (150,000 pts)"

**Implementation Details:**
- Add `previous_scores` dict to file_watcher
- Diff on each parse to identify what changed
- Show feedback even on failed improvement attempts

**Benefits:**
- Much clearer feedback
- Shows progress even when not beating PB
- Users can see how close they were

**Files to Modify:**
- `client/file_watcher.py` - Add diff tracking
- May need to adjust ScoreState class

---

### 2. Discord Command UX - `/recent` Beautification (MEDIUM PRIORITY)
**Current:** Basic text output with dates
**Goal:** Match field structure and visual layout of `/leaderboard` command

**Example Desired Format:**
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

**Implementation:**
- Keep date information (currently shows YYYY-MM-DD)
- Use Discord embed fields for cleaner presentation
- Maintain consistency with other command outputs

**Files to Modify:**
- `bot/bot.py` - `/recent` command handler

---

### 3. Bot Launcher Issues (LOW PRIORITY)
**Issue:** Ctrl+C in bot server mode exits terminal instead of returning to launcher

**Problem:**
- Current code at `bot_launcher.py:772-776` has try/except but doesn't trigger
- Discord.py's `bot.run()` handles Ctrl+C internally, preventing our handler from working

**Possible Solutions:**
1. Use Discord.py's built-in shutdown mechanism
2. Run bot in separate thread with signal handling
3. Use asyncio.run with proper cleanup

**Files to Modify:**
- `bot_launcher.py` - Ctrl+C handler

---

## 🔍 Instrument ID Verification (ONGOING)
**Goal:** Verify and refine instrument ID mappings (IDs 7-10)

**Current Status:**
- **ID 8 CONFIRMED:** Co-op mode (both players on lead guitar) - Dec 28, 2025
- Current label: "GH Live Co-op" - may need to change to "Guitar Co-op" or just "Co-op"
- IDs 7, 9, 10 still need user testing data

**Action:**
- Wait for more user reports of "Unknown (ID X)" to identify remaining IDs
- Consider renaming ID 8 based on actual Clone Hero usage patterns
- May need different co-op IDs for different instrument combinations

**Files to Monitor:**
- `shared/parsers.py` - INSTRUMENT_NAMES dict

---

## 📊 Known Issues (NOT for v2.5.4)
These are documented but deferred to later versions:

### OCR Accuracy Issues
- Sometimes misreads numbers on results screen
- Could add validation (score from OCR vs scoredata.bin)
- Multiple OCR attempts with majority vote

### currentsong.txt Caching Edge Case
- If Clone Hero crashes during song, cache isn't updated
- Could add timeout for stale cache entries

### Unicode Handling in Console
- Some song titles with special characters display incorrectly
- May need more comprehensive Unicode normalization

---

## ✅ Pre-Development Checklist

Before starting v2.5.4 development:
- [ ] v2.5.3 released on GitHub ✓
- [ ] v2.5.3 executables available for download ✓
- [ ] User testing of v2.5.3 completed
- [ ] Review FUTURE_WORK_LOCAL.md for additional items
- [ ] Prioritize features based on user feedback

---

## 🎯 Success Criteria for v2.5.4

**Must Have:**
- ✓ Client terminal shows detailed feedback for scores below PB
- ✓ Users can see exactly how far below their PB they scored

**Nice to Have:**
- ✓ `/recent` command beautified to match `/leaderboard`
- ✓ Ctrl+C handler fixed in bot launcher

**Testing:**
- Play songs scoring below PB → verify detailed feedback shown
- Play songs matching PB → verify "matched PB" message
- Test `/recent` command → verify formatting matches `/leaderboard`
- Test Ctrl+C in bot server mode → verify returns to launcher

---

## 📝 Notes

### Development Approach
1. Start with client terminal feedback (highest user impact)
2. Test thoroughly with real gameplay scenarios
3. Move to `/recent` beautification if time permits
4. Ctrl+C handler is low priority (workaround: restart launcher)

### Version Numbering
- v2.5.4 is a minor update (UX improvements, no new major features)
- If significant features are added, consider v2.6.0 instead

### Breaking Changes
- None anticipated for v2.5.4
- Config version should remain at 5
- No database migrations needed

---

## 🔗 Related Documents

- `FUTURE_WORK_LOCAL.md` - Full list of future features
- `REQUESTED_FEATURES.md` - User-requested features
- `CLAUDE.md` - Technical documentation
- `RELEASE_NOTES_v2.5.3.md` - Previous release notes

---

**Next Session:** Begin work on client terminal feedback improvements

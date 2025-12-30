# PLANNED FEATURES FOR v2.6+ - CHART FILE PARSING

**Status:** Planning phase - Not yet implemented
**Target Release:** v2.6 or later
**Priority:** High - Major feature unlock

---

## Overview

Parse Clone Hero chart files (notes.chart, notes.mid, notes.midi) to extract detailed gameplay data that isn't available in scoredata.bin. This unlocks accurate statistics, difficulty rankings, and achievement detection.

---

## Core Features to Implement

### 1. Notes Hit / Notes Total Display ⭐ HIGH PRIORITY

**Goal:** Display accurate note statistics alongside existing accuracy percentage

**Current Limitation:**
- scoredata.bin only provides "completion numerator/denominator" which is NOT notes hit/total
- Currently rely on OCR to extract notes from results screen (optional, unreliable)

**Chart File Solution:**
- Parse total note count from chart file (exact count)
- Compare to notes hit from gameplay
- Display: "1,247 / 1,250 notes (99.76%)"

**Implementation:**
- Add note counting to chart parser
- Store total_notes in songs table
- Display in Discord announcements and /mystats command

**Benefits:**
- Accurate note counts (not OCR dependent)
- Works for all historical scores (can retroactively calculate)
- No OCR required

---

### 2. Highest Note Streak Tracking ⭐ HIGH PRIORITY

**Goal:** Capture and display the longest note streak achieved in a song

**Current Limitation:**
- Not available in scoredata.bin
- OCR can extract "best streak" from results screen (but unreliable)

**Chart File Solution:**
- Parse chart to understand note density
- Track streak length during gameplay (if we can capture it)
- Display: "Best Streak: 847 notes"

**Implementation:**
- May require OCR or memory reading to capture actual streak
- Chart parsing can validate streak is possible (max notes in sequence)
- Store in scores table: best_streak column

**Display Locations:**
- Discord announcements
- /mystats command
- Leaderboards (longest streak on chart)

---

### 3. Note Density Analysis ⭐ HIGH PRIORITY

**Goal:** Calculate notes per second (NPS) to measure song difficulty

**Calculation:**
- Total notes in chart / song length in seconds
- Can also calculate peak density (hardest section)
- Average density vs peak density

**Features:**
- "Hardest Songs" leaderboard sorted by NPS
- Difficulty rating display (Easy: <5 NPS, Medium: 5-8, Hard: 8-12, Expert: 12+)
- Filter songs by difficulty tier

**Implementation:**
- Parse note timestamps from chart file
- Calculate total notes / song duration
- Store in songs table: note_density, peak_density

**Display:**
- Song info embeds: "Note Density: 11.2 NPS (Hard)"
- /hardest command to show top 10 hardest songs
- Filter leaderboards by difficulty tier

---

### 4. "Most Difficult Songs" Rankings ⭐ HIGH PRIORITY

**Goal:** Leaderboard of hardest songs based on objective metrics

**Ranking Factors:**
1. **Note density** (notes per second)
2. **Total note count** (longer songs are harder)
3. **Peak density** (hardest sections)
4. **Note type complexity** (HOPO density, chord density)

**Composite Difficulty Score:**
```
difficulty_score = (note_density * 0.4) +
                   (total_notes / 1000 * 0.2) +
                   (peak_density * 0.3) +
                   (complexity_factor * 0.1)
```

**Features:**
- `/hardest` command - Show top 10 hardest songs
- `/hardest [instrument]` - Filter by instrument
- `/hardest [difficulty]` - Filter by difficulty
- Song difficulty badges in announcements

---

### 5. Full Combo (FC) Detection ⭐ CRITICAL

**Goal:** Detect when a player hits every note in a song and create special announcement

**Detection Logic:**
```
is_full_combo = (notes_hit == total_notes_in_chart) AND (misses == 0)
```

**Current Limitation:**
- Can't reliably detect FC without total note count from chart
- OCR might capture "notes hit" but not always accurate

**Chart File Solution:**
- Parse total notes from chart
- Compare to notes_hit from score submission
- If notes_hit == total_notes AND accuracy == 100% → FC!

**New Announcement Type:**
```
🌟 FULL COMBO! 🌟
PlayerName FC'd Song Title!
Expert Lead Guitar: 487,234 pts
1,250 / 1,250 notes (100.00%)
⭐⭐⭐⭐⭐
```

**Implementation:**
- Add fc_detected boolean to scores table
- New announcement type in bot config (color, style, ping settings)
- Separate FC leaderboard: `/fcs` or `/fullcombos`
- Track FC count per user in stats

**Discord Features:**
- Special emoji/color for FC announcements (Gold with star emoji)
- Optional ping role (@FC-Alert or similar)
- FC count in user stats: "14 Full Combos"
- "First FC" on chart gets special recognition

---

## Additional Chart Parsing Features

### 6. Star Power Phrase Analysis

**What it unlocks:**
- Total Star Power phrases in chart
- Optimal Star Power activation points
- Star Power efficiency rating

**Features:**
- "Star Power Master" achievement for optimal usage
- Display: "7/8 Star Power phrases collected"

---

### 7. Note Type Breakdown

**What it unlocks:**
- Strummed notes vs HOPOs vs Taps
- Chord density (multi-note chords)
- Open note usage

**Features:**
- "HOPO King" achievements
- Detailed accuracy by note type
- Chord hit percentage

---

### 8. Practice Mode Section Detection

**What it unlocks:**
- Detect which sections are hardest (most replays)
- Track improvement on specific sections
- Section-based leaderboards

**Features:**
- "Most Practiced Section" stats
- Section mastery tracking

---

## Technical Implementation Plan

### Phase 1: Chart Parser Development

**Create new parser:** `shared/chart_parser.py`

**Support formats:**
1. `.chart` files (text-based format)
2. `.mid` / `.midi` files (MIDI binary format)

**Data to extract:**
- Total note count (per difficulty, per instrument)
- Note timestamps (for density calculation)
- Note types (normal, HOPO, tap, chord, open)
- Star Power phrase locations
- Song length (from last note timestamp)
- Practice mode sections

**Output:** `ChartData` object with all parsed information

---

### Phase 2: Database Schema Updates

**New columns in `songs` table:**
```sql
ALTER TABLE songs ADD COLUMN note_count_expert_lead INTEGER;
ALTER TABLE songs ADD COLUMN note_count_expert_bass INTEGER;
-- (repeat for all instruments/difficulties)
ALTER TABLE songs ADD COLUMN note_density REAL;
ALTER TABLE songs ADD COLUMN peak_density REAL;
ALTER TABLE songs ADD COLUMN difficulty_score REAL;
ALTER TABLE songs ADD COLUMN star_power_phrases INTEGER;
ALTER TABLE songs ADD COLUMN chart_parsed_at TEXT;
```

**New columns in `scores` table:**
```sql
ALTER TABLE scores ADD COLUMN best_streak INTEGER;
ALTER TABLE scores ADD COLUMN fc_detected BOOLEAN DEFAULT 0;
ALTER TABLE scores ADD COLUMN notes_total INTEGER;
```

**New table for chart metadata:**
```sql
CREATE TABLE chart_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_hash TEXT NOT NULL,
    instrument_id INTEGER NOT NULL,
    difficulty_id INTEGER NOT NULL,
    total_notes INTEGER NOT NULL,
    note_density REAL,
    peak_density REAL,
    star_power_phrases INTEGER,
    parsed_at TEXT NOT NULL,
    UNIQUE(chart_hash, instrument_id, difficulty_id)
);
```

---

### Phase 3: Client-Side Integration

**Enhance score submission:**
1. When score detected, also parse chart file
2. Extract total notes for that instrument/difficulty
3. Include in API submission: `total_notes_in_chart`
4. Bot can then validate notes_hit <= total_notes

**Chart caching:**
- Cache parsed chart data to avoid re-parsing
- Update cache when chart file modified
- Store in `.score_tracker_chart_cache.json`

---

### Phase 4: Server-Side Integration

**Bot enhancements:**
1. Store chart metadata on first score submission
2. Calculate FC detection on score receipt
3. Add FC announcement type to config
4. New commands: `/hardest`, `/fcs`, `/notebreakdown`

**Leaderboard filters:**
- Filter by note density tier
- Show FC counts
- Sort by difficulty score

---

### Phase 5: New Discord Commands

**Commands to add:**
- `/hardest [instrument] [difficulty]` - Hardest songs ranking
- `/fcs [user]` - Full combo leaderboard
- `/songstats <song>` - Detailed chart statistics
- `/notebreakdown <song>` - Note type analysis
- `/density <song>` - Note density visualization

---

## File Locations

**Chart files to parse:**
- `{song_folder}/notes.chart` - Text-based chart format
- `{song_folder}/notes.mid` - MIDI chart format
- `{song_folder}/notes.midi` - MIDI chart format (alternative extension)

**Chart format documentation:**
- .chart format: https://github.com/TheNathannator/GuitarGame_ChartFormats/blob/main/doc/FileFormats/.chart/Core%20Infrastructure.md
- .mid format: Standard MIDI with Clone Hero track conventions

---

## Migration Strategy

**For existing scores:**
1. Run batch chart parsing on all songs in database
2. Calculate total_notes for each chart/instrument/difficulty
3. Retroactively detect FCs in historical scores
4. Update note density for all songs

**Migration command:**
- `parsecharts` - Scan all song folders and parse chart files
- Progress indicator showing X/Y songs parsed
- Store results in chart_metadata table

---

## Configuration Options

**New bot config settings:**
```json
{
  "announcements": {
    "full_combos": {
      "enabled": true,
      "embed_color": "#FFD700",
      "style": "full",
      "ping_previous_holder": true,
      "minimalist_fields": {
        "song": true,
        "score": true,
        "notes": true,
        "stars": true
      }
    }
  },
  "features": {
    "chart_parsing": {
      "enabled": true,
      "cache_parsed_charts": true,
      "parse_on_score_submit": true,
      "difficulty_tiers": {
        "easy": [0, 5],
        "medium": [5, 8],
        "hard": [8, 12],
        "expert": [12, 999]
      }
    }
  }
}
```

---

## Testing Plan

**Test cases:**
1. Parse various .chart file formats
2. Parse various .mid file formats
3. Verify note counts are accurate
4. Test FC detection with known FC scores
5. Verify note density calculations
6. Test with corrupted/malformed chart files
7. Performance test with large song libraries (1000+ songs)

**Edge cases:**
- Charts with no notes (cymbal-only drums)
- Charts with open notes
- Charts with chord spam sections
- Very long songs (>10 minutes)
- Very short songs (<30 seconds)

---

## Performance Considerations

**Chart parsing is expensive:**
- Don't parse on every score submission if chart already cached
- Use background thread for bulk parsing
- Cache results in database
- Only re-parse if chart file modified timestamp changed

**Optimization strategies:**
1. Parse only the difficulty/instrument being played
2. Cache parsed data in `.chart_cache` folder
3. Use fast C-based MIDI parser (python-midi library)
4. Lazy loading - only parse when needed

---

## User-Facing Changes

**Discord Announcements:**
- "Notes: 1,247 / 1,250 (99.76%)" - accurate note stats
- "Best Streak: 847 notes" - longest combo
- "Note Density: 11.2 NPS" - difficulty indicator
- "🌟 FULL COMBO! 🌟" - special FC announcements

**New Commands:**
- `/hardest` - See hardest songs
- `/fcs` - Full combo leaderboard
- `/songstats` - Detailed chart analysis

**Enhanced Commands:**
- `/mystats` - Now includes FC count and average note accuracy
- `/leaderboard` - Can filter by difficulty tier
- `/recent` - Shows if score was a Full Combo

---

## Timeline Estimate

**Development Phases:**
1. **Phase 1 (Chart Parser):** 2-3 days
2. **Phase 2 (Database Schema):** 1 day
3. **Phase 3 (Client Integration):** 2 days
4. **Phase 4 (Bot Integration):** 3-4 days
5. **Phase 5 (Commands & Testing):** 2-3 days

**Total:** ~10-15 development days (spread across v2.6, v2.7, v2.8)

**Incremental Release Strategy:**
- v2.6: Chart parser + note counts + FC detection
- v2.7: Note density + difficulty rankings
- v2.8: Advanced features (Star Power analysis, practice sections)

---

## Dependencies

**Python libraries needed:**
- `mido` - MIDI file parsing (for .mid files)
- Existing libraries sufficient for .chart parsing (text-based)

**Installation:**
```bash
py -m pip install mido
```

---

## Open Questions

1. **How to capture best_streak in real-time?**
   - OCR from results screen (current method, unreliable)
   - Memory reading (invasive, fragile)
   - User manual entry? (not automated)
   - **Resolution:** Stick with OCR, improve reliability

2. **Should we parse charts proactively or on-demand?**
   - Proactive: Slower startup, but faster during gameplay
   - On-demand: Faster startup, slight delay on first score
   - **Recommendation:** On-demand with persistent caching

3. **How to handle charts with multiple difficulties in one file?**
   - Parse all difficulties at once
   - Cache all parsed data
   - Return only requested difficulty

4. **What if chart file is missing or corrupted?**
   - Graceful fallback to scoredata.bin data only
   - Log warning but don't fail score submission
   - Mark song as "chart not parsed" in database

---

## Success Metrics

**Feature adoption:**
- % of songs with parsed chart data
- Number of FC detections per week
- Usage of `/hardest` and `/fcs` commands

**Data quality:**
- Accuracy of note counts (compare to known values)
- FC detection false positive rate
- Note density correlation with player perception of difficulty

**User engagement:**
- Increase in Discord activity around FC announcements
- Leaderboard competition for hardest songs
- User feedback on difficulty rankings

---

## References

**Chart Format Documentation:**
- .chart format spec: https://github.com/TheNathannator/GuitarGame_ChartFormats
- Clone Hero wiki: https://wiki.clonehero.net
- MIDI format for Clone Hero: Community documentation

**Related Files in Codebase:**
- `shared/parsers.py` - Existing parsers (scoredata, songcache)
- `client/file_watcher.py` - Score detection logic
- `bot/api.py` - Announcement creation (lines 306-893)
- `bot/database.py` - Database operations

---

## Notes

- This is a MAJOR feature addition - will significantly enhance the tracker
- All features are backward compatible (works with existing scores)
- Can retroactively analyze historical scores for FCs and note stats
- Chart parsing is one-time cost per song (cached afterward)
- Opens door for future features like rhythm game analysis, heat maps, etc.

---

**Document Created:** 2025-12-30
**Last Updated:** 2025-12-30
**Status:** Ready for v2.6+ development planning

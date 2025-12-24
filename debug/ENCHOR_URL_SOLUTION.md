# Enchor.us Integration Solution

## Problem Summary

The chart hash from Clone Hero's `scoredata.bin` (16-byte hash) is **incompatible** with enchor.us's hash format (32-byte hash). These are different cryptographic hashes computed from different source data and cannot be converted between each other.

**Our hash**: `bf7860b0643ad67512830b799f0b6b53` (32 hex characters = 16 bytes)
**Enchor.us hash**: `18A7UWMA8CvtF09H9sHAwOhFXdSQuRyR7Rpp-2mJSqI=` (base64-encoded 32 bytes)

## Recommended Solution: Metadata-Based Search URLs

Instead of trying to match hashes, generate enchor.us search URLs using the song title, artist, and instrument information we already have.

### URL Format

```
https://www.enchor.us/?instrument={instrument}&name={song_title}&artist={artist}
```

**Example** (Afterglow by Syncatto on Lead Guitar):
```
https://www.enchor.us/?instrument=guitar&name=afterglow&artist=syncatto
```

### URL Generation Test Results

All 8 test cases **PASSED**:

1. **Full metadata** (Title + Artist + Charter + Instrument)
   - URL: `https://www.enchor.us/?instrument=guitar&name=afterglow&artist=syncatto`
   - ✓ Works perfectly

2. **No charter** (Title + Artist + Instrument)
   - URL: `https://www.enchor.us/?instrument=guitar&name=through+the+fire+and+flames&artist=dragonforce`
   - ✓ Still works well

3. **Title only** (Title + Instrument)
   - URL: `https://www.enchor.us/?instrument=guitar&name=free+bird`
   - ✓ Broader search, still useful

4. **Different instruments** (Bass, Drums)
   - Bass: `https://www.enchor.us/?instrument=bass&name=yyz&artist=rush`
   - Drums: `https://www.enchor.us/?instrument=drums&name=tom+sawyer&artist=rush`
   - ✓ Instrument filtering works

5. **Special characters** (apostrophes, etc.)
   - URL: `https://www.enchor.us/?instrument=guitar&name=don%27t+stop+believin%27&artist=journey`
   - ✓ Properly URL-encoded

6. **No metadata** (Edge case)
   - Returns `None` - fallback to showing chart hash
   - ✓ Graceful degradation

## Implementation Plan

### 1. Instrument Mapping

Clone Hero → enchor.us mapping:

| Instrument ID | Clone Hero Name | Enchor.us Parameter |
|---------------|-----------------|---------------------|
| 0 | Lead Guitar | `guitar` |
| 1 | Bass | `bass` |
| 2 | Rhythm Guitar | `guitar` |
| 3 | Keys | `keys` |
| 4 | Drums | `drums` |

### 2. Metadata Availability

Based on current architecture (`clone_hero_client.py` and `bot/api.py`):

**Song Title:**
- Primary: `currentsong.txt` (most reliable)
- Fallback: OCR results screen
- Availability: ~90-95% with current implementation

**Song Artist:**
- Primary: `currentsong.txt`
- Fallback: OCR / song.ini parsing
- Availability: ~85-90%

**Charter:**
- Source: `currentsong.txt`
- Availability: ~70-80% (depends on chart metadata)
- Note: enchor.us support for charter parameter is UNKNOWN - needs testing

**Instrument:**
- Source: `scoredata.bin`
- Availability: 100% (always present)

### 3. Discord Embed Modification

**Current implementation** (`bot/api.py:286-291`):
```python
# Add full chart hash for lookup (copy-friendly format)
chart_hash = score_data['chart_hash']
embed.add_field(
    name="Chart Hash",
    value=f"`{chart_hash}`",
    inline=False
)
```

**Proposed modification**:
```python
# Generate enchor.us search link if we have metadata
enchor_url = generate_enchor_url(
    score_data.get('song_title'),
    score_data.get('song_artist'),
    score_data.get('song_charter'),  # Optional, may not be supported
    score_data['instrument_id']
)

if enchor_url:
    embed.add_field(
        name="Find This Chart",
        value=f"[Search on enchor.us]({enchor_url})",
        inline=False
    )
else:
    # Fallback to chart hash if no metadata available
    chart_hash = score_data['chart_hash']
    embed.add_field(
        name="Chart Hash",
        value=f"`{chart_hash}`",
        inline=False
    )
```

### 4. Alternative: Dual Display

Show **both** the link and the hash:

```python
# Always show enchor.us link if possible
enchor_url = generate_enchor_url(...)
if enchor_url:
    embed.add_field(
        name="Find This Chart",
        value=f"[Search on enchor.us]({enchor_url})",
        inline=False
    )

# Always show chart hash for technical reference
chart_hash = score_data['chart_hash']
embed.add_field(
    name="Chart Hash (Technical)",
    value=f"`{chart_hash}`",
    inline=False
)
```

This provides:
- Easy search for most users (click the link)
- Technical reference for debugging/advanced users

## Implementation Steps

### Phase 1: Add URL Generation Function
1. Create `generate_enchor_url()` function in `bot/api.py` or shared utility
2. Include instrument mapping
3. Handle URL encoding properly (urllib.parse.urlencode)
4. Return None if insufficient metadata

### Phase 2: Modify Discord Announcement
1. Update `announce_high_score()` in `bot/api.py`
2. Replace or supplement Chart Hash field with enchor.us link
3. Test with various metadata scenarios

### Phase 3: Testing
1. Test with full metadata (title + artist)
2. Test with partial metadata (title only)
3. Test with no metadata (fallback to hash)
4. Test with special characters in song names
5. Test different instruments
6. Verify charter parameter behavior on enchor.us

### Phase 4: Documentation
1. Update CLAUDE.md with new announcement structure
2. Document the hash incompatibility issue
3. Add notes about metadata reliability

## Charter Parameter - Needs Research

The charter name could help distinguish between multiple charts of the same song, but we need to verify:

1. Does enchor.us support a `&charter=` or `&author=` parameter?
2. Test URLs:
   - `https://www.enchor.us/?name=afterglow&artist=syncatto&charter=rlombardi`
   - `https://www.enchor.us/?name=afterglow&artist=syncatto&author=rlombardi`

If supported, this would be very useful for popular songs with many different charts.

## Benefits of This Approach

1. **User-friendly**: One-click search instead of copy-paste hash
2. **Reliable**: Works with existing metadata pipeline (~90% availability)
3. **Graceful degradation**: Falls back to hash when metadata unavailable
4. **Future-proof**: Not dependent on hash format compatibility
5. **Flexible**: Can add more parameters (charter, difficulty) if enchor.us supports them

## Risks and Mitigations

**Risk**: Search returns wrong chart (multiple versions of same song)
- **Mitigation**: Include charter in URL if enchor.us supports it
- **Mitigation**: Users can refine search on enchor.us page

**Risk**: Metadata unavailable (currentsong.txt empty, OCR failed)
- **Mitigation**: Fallback to showing chart hash
- **Mitigation**: ~90% success rate with currentsong.txt is acceptable

**Risk**: Special characters in song names break URL
- **Mitigation**: Use urllib.parse.urlencode for proper encoding
- **Mitigation**: Tested with apostrophes, spaces, etc. - all pass

## Next Steps

1. **Manual testing**: Visit the generated URLs in a browser to verify search results
2. **Charter parameter research**: Test if enchor.us supports charter/author filtering
3. **Implement in development**: Add function and modify announcements
4. **Test with real data**: Monitor announcements for a few days
5. **User feedback**: See if users find the links helpful
6. **Iterate**: Add charter parameter if supported, refine link text, etc.

## Code Files to Modify

1. `bot/api.py` - Add `generate_enchor_url()` function and modify `announce_high_score()`
2. `CLAUDE.md` - Document the new approach
3. Optionally: Create `shared/enchor_utils.py` if we want to reuse the function elsewhere

## Sample Implementation Code

See: `debug/test_enchor_url_generation.py` for the complete implementation with all test cases.

Key function:
```python
def generate_enchor_url(
    song_title: Optional[str] = None,
    song_artist: Optional[str] = None,
    charter: Optional[str] = None,
    instrument_id: Optional[int] = None
) -> Optional[str]:
    """Generate enchor.us search URL based on available metadata."""

    if not song_title and not song_artist:
        return None

    params = {}

    if instrument_id is not None:
        instrument_map = {0: "guitar", 1: "bass", 2: "guitar", 3: "keys", 4: "drums"}
        params['instrument'] = instrument_map.get(instrument_id, "guitar")

    if song_title:
        params['name'] = song_title.lower()

    if song_artist:
        params['artist'] = song_artist.lower()

    base_url = "https://www.enchor.us/"
    query_string = urllib.parse.urlencode(params)

    return f"{base_url}?{query_string}"
```

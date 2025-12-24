"""
Diagnostic script to test enchor.us URL generation for Discord announcements

This script explores different strategies for generating enchor.us search URLs
based on the metadata we have available from Clone Hero scores.
"""

import urllib.parse
from typing import Optional


# Clone Hero instrument mapping
INSTRUMENTS = {
    0: "Lead Guitar",
    1: "Bass",
    2: "Rhythm Guitar",
    3: "Keys",
    4: "Drums"
}

# Possible enchor.us instrument parameter values
# Based on the URL: ?instrument=guitar&name=...&artist=...
ENCHOR_INSTRUMENT_MAP = {
    0: "guitar",      # Lead Guitar → guitar
    1: "bass",        # Bass → bass
    2: "guitar",      # Rhythm Guitar → guitar (or rhythm?)
    3: "keys",        # Keys → keys
    4: "drums",       # Drums → drums
}


def generate_enchor_url(
    song_title: Optional[str] = None,
    song_artist: Optional[str] = None,
    charter: Optional[str] = None,
    instrument_id: Optional[int] = None
) -> Optional[str]:
    """
    Generate an enchor.us search URL based on available metadata.

    Args:
        song_title: Song title (e.g., "Afterglow")
        song_artist: Artist name (e.g., "Syncatto")
        charter: Charter name (e.g., "RLOMBARDI")
        instrument_id: Clone Hero instrument ID (0-4)

    Returns:
        URL string or None if insufficient metadata
    """
    # Need at least title or artist to make a useful search
    if not song_title and not song_artist:
        return None

    # Build query parameters
    params = {}

    if instrument_id is not None and instrument_id in ENCHOR_INSTRUMENT_MAP:
        params['instrument'] = ENCHOR_INSTRUMENT_MAP[instrument_id]

    if song_title:
        params['name'] = song_title.lower()

    if song_artist:
        params['artist'] = song_artist.lower()

    # Charter parameter - need to verify if enchor.us supports this
    # Might be 'charter' or 'author' or might not be supported
    # if charter:
    #     params['charter'] = charter.lower()

    # Build URL
    base_url = "https://www.enchor.us/"
    query_string = urllib.parse.urlencode(params)

    return f"{base_url}?{query_string}"


def generate_enchor_markdown_link(
    song_title: Optional[str] = None,
    song_artist: Optional[str] = None,
    charter: Optional[str] = None,
    instrument_id: Optional[int] = None
) -> Optional[str]:
    """
    Generate a markdown-formatted link for Discord embeds.

    Returns:
        Markdown link like "[Search on enchor.us](url)" or None
    """
    url = generate_enchor_url(song_title, song_artist, charter, instrument_id)
    if not url:
        return None

    # Create descriptive link text
    if song_title and song_artist:
        link_text = f"Search on enchor.us"
    elif song_title:
        link_text = f"Search \"{song_title}\" on enchor.us"
    elif song_artist:
        link_text = f"Search {song_artist} on enchor.us"
    else:
        link_text = "Search on enchor.us"

    return f"[{link_text}]({url})"


def test_url_generation():
    """Test URL generation with various scenarios"""

    test_cases = [
        # Case 1: Full metadata (ideal scenario)
        {
            "name": "Full metadata",
            "song_title": "Afterglow",
            "song_artist": "Syncatto",
            "charter": "RLOMBARDI",
            "instrument_id": 0,
            "expected": "https://www.enchor.us/?instrument=guitar&name=afterglow&artist=syncatto"
        },
        # Case 2: Title and artist, no charter
        {
            "name": "No charter",
            "song_title": "Through the Fire and Flames",
            "song_artist": "DragonForce",
            "charter": None,
            "instrument_id": 0,
            "expected": "https://www.enchor.us/?instrument=guitar&name=through+the+fire+and+flames&artist=dragonforce"
        },
        # Case 3: Title only (from OCR, artist failed)
        {
            "name": "Title only",
            "song_title": "Free Bird",
            "song_artist": None,
            "charter": None,
            "instrument_id": 0,
            "expected": "https://www.enchor.us/?instrument=guitar&name=free+bird"
        },
        # Case 4: Artist only (weird edge case)
        {
            "name": "Artist only",
            "song_title": None,
            "song_artist": "Metallica",
            "charter": None,
            "instrument_id": 0,
            "expected": "https://www.enchor.us/?instrument=guitar&artist=metallica"
        },
        # Case 5: Different instruments
        {
            "name": "Bass guitar",
            "song_title": "YYZ",
            "song_artist": "Rush",
            "charter": "FretTheater",
            "instrument_id": 1,
            "expected": "https://www.enchor.us/?instrument=bass&name=yyz&artist=rush"
        },
        {
            "name": "Drums",
            "song_title": "Tom Sawyer",
            "song_artist": "Rush",
            "charter": None,
            "instrument_id": 4,
            "expected": "https://www.enchor.us/?instrument=drums&name=tom+sawyer&artist=rush"
        },
        # Case 6: No metadata (should return None)
        {
            "name": "No metadata",
            "song_title": None,
            "song_artist": None,
            "charter": None,
            "instrument_id": 0,
            "expected": None
        },
        # Case 7: Title with special characters
        {
            "name": "Special characters",
            "song_title": "Don't Stop Believin'",
            "song_artist": "Journey",
            "charter": None,
            "instrument_id": 0,
            "expected": "https://www.enchor.us/?instrument=guitar&name=don%27t+stop+believin%27&artist=journey"
        },
    ]

    print("=" * 80)
    print("ENCHOR.US URL GENERATION TESTING")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"  Input:")
        print(f"    Title: {test['song_title']}")
        print(f"    Artist: {test['song_artist']}")
        print(f"    Charter: {test['charter']}")
        print(f"    Instrument: {INSTRUMENTS.get(test['instrument_id'], 'N/A')}")

        url = generate_enchor_url(
            test['song_title'],
            test['song_artist'],
            test['charter'],
            test['instrument_id']
        )

        markdown = generate_enchor_markdown_link(
            test['song_title'],
            test['song_artist'],
            test['charter'],
            test['instrument_id']
        )

        print(f"  Generated URL:")
        print(f"    {url}")
        print(f"  Markdown Link:")
        print(f"    {markdown}")

        # Compare with expected
        if url == test['expected']:
            print(f"  [PASS]")
        else:
            print(f"  [FAIL]")
            print(f"  Expected: {test['expected']}")

        print()

    print("=" * 80)
    print("METADATA AVAILABILITY ANALYSIS")
    print("=" * 80)
    print()
    print("Based on current codebase architecture:")
    print()
    print("1. Song Title:")
    print("   ✓ Available from currentsong.txt (authoritative)")
    print("   ✓ Available from OCR as fallback")
    print("   - Missing if both sources fail → falls back to chart hash")
    print()
    print("2. Song Artist:")
    print("   ✓ Available from currentsong.txt")
    print("   ✓ Available from OCR as fallback")
    print("   ✓ Available from song.ini parsing")
    print("   - Generally reliable")
    print()
    print("3. Charter:")
    print("   ✓ Available from currentsong.txt")
    print("   - Reliability depends on chart metadata")
    print("   - Could help distinguish multiple charts of same song")
    print()
    print("4. Instrument:")
    print("   ✓ Always available (from scoredata.bin)")
    print("   ✓ 100% reliable")
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("Strategy 1: HYBRID APPROACH (RECOMMENDED)")
    print("  - If we have title/artist: Show enchor.us search link")
    print("  - If we have title only: Show enchor.us search link (partial)")
    print("  - If no metadata: Keep showing chart hash as fallback")
    print("  - Always include instrument in URL for better filtering")
    print()
    print("Strategy 2: DUAL DISPLAY")
    print("  - Show both enchor.us link AND chart hash")
    print("  - Link for easy searching")
    print("  - Hash for technical reference")
    print()
    print("Strategy 3: CHARTER PARAMETER (NEEDS TESTING)")
    print("  - Test if enchor.us supports &charter= parameter")
    print("  - If yes, include charter to narrow results")
    print("  - Especially useful for popular songs with many charts")
    print()
    print("Implementation considerations:")
    print("  - URL encode all parameters properly (urllib.parse)")
    print("  - Lowercase all search terms (enchor.us appears case-insensitive)")
    print("  - Use markdown links in Discord embeds for clean presentation")
    print("  - Consider adding a footer note: 'Use Bridge to download charts'")
    print()


def analyze_current_discord_announcement():
    """
    Analyze what metadata is available in current Discord announcements
    by looking at the bot/api.py announce_high_score function
    """
    print("=" * 80)
    print("CURRENT DISCORD ANNOUNCEMENT METADATA")
    print("=" * 80)
    print()
    print("From bot/api.py:announce_high_score(), we have access to:")
    print()
    print("score_data dict contains:")
    print("  - chart_hash         (always available)")
    print("  - instrument_id      (always available)")
    print("  - difficulty_id      (always available)")
    print("  - score              (always available)")
    print("  - stars              (always available)")
    print("  - completion_percent (always available)")
    print("  - song_title         (available if currentsong.txt or OCR succeeded)")
    print("  - song_artist        (available if currentsong.txt or OCR succeeded)")
    print("  - song_charter       (available if currentsong.txt succeeded)")
    print("  - notes_hit          (available if OCR succeeded)")
    print("  - notes_total        (available if OCR succeeded)")
    print("  - best_streak        (available if OCR succeeded)")
    print("  - score_type         ('raw' or 'rich')")
    print()
    print("Current announcement structure (bot/api.py:236-305):")
    print("  1. Title: 'NEW HIGH SCORE!'")
    print("  2. Description: User mention, song, score")
    print("  3. Fields:")
    print("     - Instrument")
    print("     - Difficulty")
    print("     - Stars")
    print("     - Notes/Accuracy")
    print("     - Best Streak (if available)")
    print("     - Chart Hash (full 32-char hex) ← THIS IS THE PROBLEM")
    print("  4. Footer: Previous record info")
    print()
    print("PROPOSED MODIFICATION:")
    print("  Replace 'Chart Hash' field with 'Find This Chart' field")
    print("  Content: enchor.us link if metadata available, else hash")
    print()
    print("Example field code:")
    print("```python")
    print("# Generate enchor.us link")
    print("enchor_url = generate_enchor_url(")
    print("    score_data.get('song_title'),")
    print("    score_data.get('song_artist'),")
    print("    score_data.get('song_charter'),")
    print("    score_data['instrument_id']")
    print(")")
    print()
    print("if enchor_url:")
    print("    embed.add_field(")
    print("        name='Find This Chart',")
    print("        value=f'[Search on enchor.us]({enchor_url})',")
    print("        inline=False")
    print("    )")
    print("else:")
    print("    # Fallback to chart hash")
    print("    embed.add_field(")
    print("        name='Chart Hash',")
    print("        value=f'`{chart_hash}`',")
    print("        inline=False")
    print("    )")
    print("```")
    print()


if __name__ == "__main__":
    test_url_generation()
    print()
    analyze_current_discord_announcement()

"""
Diagnostic script to show all available fields from scoredata.bin

This script analyzes the binary format of Clone Hero's scoredata.bin
and shows exactly what data is available for each score.
"""

import struct
from pathlib import Path
from typing import Optional


def analyze_scoredata_format(filepath: Optional[str] = None):
    """
    Analyze and display the complete scoredata.bin format
    """
    print("=" * 80)
    print("CLONE HERO scoredata.bin FORMAT")
    print("=" * 80)
    print()
    print("Source: analyze_scoredata.py and Clone Hero binary file format")
    print()

    print("FILE STRUCTURE:")
    print("-" * 80)
    print()

    print("Header Section:")
    print("  [Bytes 0-3]   Header (4 bytes)           - File signature")
    print("  [Bytes 4-7]   Song Count (4 bytes)       - Number of songs with scores")
    print()

    print("For each song:")
    print("  [Bytes 0-15]  Chart Hash (16 bytes)      - Blake3 hash of chart")
    print("  [Byte 16]     Instrument Count (1 byte)  - Number of instruments played")
    print("  [Bytes 17-19] Play Count (3 bytes)       - Total times played")
    print()

    print("  For each instrument/difficulty combination:")
    print("    [Bytes 0-1]   Instrument ID (2 bytes)  - See instrument mapping below")
    print("    [Byte 2]      Difficulty (1 byte)      - 0=Easy, 1=Medium, 2=Hard, 3=Expert")
    print("    [Bytes 3-4]   Numerator (2 bytes)      - Completion metric (NOT notes hit)")
    print("    [Bytes 5-6]   Denominator (2 bytes)    - Completion metric (NOT total notes)")
    print("    [Byte 7]      Stars (1 byte)           - Star rating 0-5")
    print("    [Bytes 8-11]  Padding (4 bytes)        - Unknown/unused")
    print("    [Bytes 12-15] Score (4 bytes)          - The actual score value")
    print()

    print("=" * 80)
    print("AVAILABLE FIELDS FROM scoredata.bin")
    print("=" * 80)
    print()

    fields = [
        ("chart_hash", "16 bytes (32 hex chars)", "Blake3 hash - chart identifier", "100%"),
        ("instrument_id", "2 bytes (0-4)", "0=Lead, 1=Bass, 2=Rhythm, 3=Keys, 4=Drums", "100%"),
        ("difficulty", "1 byte (0-3)", "0=Easy, 1=Medium, 2=Hard, 3=Expert", "100%"),
        ("score", "4 bytes", "The score value (e.g., 147392)", "100%"),
        ("stars", "1 byte (0-5)", "Star rating achieved", "100%"),
        ("completion_numerator", "2 bytes", "Completion metric (NOT notes hit!)", "100%"),
        ("completion_denominator", "2 bytes", "Completion metric (NOT total notes!)", "100%"),
        ("play_count", "3 bytes", "Times this song has been played", "100%"),
    ]

    print(f"{'Field Name':<25} {'Type':<20} {'Description':<40} {'Available'}")
    print("-" * 80)
    for field, ftype, desc, avail in fields:
        print(f"{field:<25} {ftype:<20} {desc:<40} {avail}")

    print()
    print("=" * 80)
    print("INSTRUMENT ID MAPPING")
    print("=" * 80)
    print()

    instruments = [
        (0, "Lead Guitar", "guitar"),
        (1, "Bass", "bass"),
        (2, "Rhythm Guitar", "guitar"),
        (3, "Keys", "keys"),
        (4, "Drums", "drums"),
    ]

    print(f"{'ID':<5} {'Clone Hero Name':<20} {'Enchor.us Parameter'}")
    print("-" * 50)
    for inst_id, name, enchor in instruments:
        print(f"{inst_id:<5} {name:<20} {enchor}")

    print()
    print("=" * 80)
    print("DIFFICULTY MAPPING")
    print("=" * 80)
    print()

    difficulties = [
        (0, "Easy"),
        (1, "Medium"),
        (2, "Hard"),
        (3, "Expert"),
    ]

    print(f"{'ID':<5} {'Difficulty Name'}")
    print("-" * 30)
    for diff_id, name in difficulties:
        print(f"{diff_id:<5} {name}")

    print()
    print("=" * 80)
    print("IMPORTANT NOTES")
    print("=" * 80)
    print()

    print("1. COMPLETION NUMERATOR/DENOMINATOR IS NOT NOTES HIT/TOTAL")
    print("   - These values represent a different metric")
    print("   - Actual notes hit/total only available via OCR")
    print("   - See CLAUDE.md line 100 for details")
    print()

    print("2. CHART HASH IS 16 BYTES (NOT COMPATIBLE WITH ENCHOR.US)")
    print("   - scoredata.bin hash: 16 bytes blake3")
    print("   - enchor.us hash: 32 bytes (different algorithm)")
    print("   - These cannot be converted between each other")
    print("   - Solution: Use metadata-based search URLs")
    print()

    print("3. NO METADATA IN scoredata.bin")
    print("   - Song title: NOT available")
    print("   - Artist: NOT available")
    print("   - Charter: NOT available")
    print("   - Album: NOT available")
    print("   - Metadata comes from currentsong.txt or OCR")
    print()

    print("=" * 80)
    print("METADATA SOURCES (OUTSIDE scoredata.bin)")
    print("=" * 80)
    print()

    metadata_sources = [
        ("currentsong.txt", "Song title, artist, charter", "~90-95%", "Primary source"),
        ("OCR (results screen)", "Song title, artist, notes, streak", "~70-80%", "Fallback"),
        ("song.ini parsing", "Artist name", "~60-70%", "Legacy fallback"),
        ("songcache.bin", "Song title (from filepath)", "~95%", "Not currently used"),
    ]

    print(f"{'Source':<25} {'Fields Available':<35} {'Success Rate':<15} {'Notes'}")
    print("-" * 80)
    for source, fields_avail, success, notes in metadata_sources:
        print(f"{source:<25} {fields_avail:<35} {success:<15} {notes}")

    print()
    print("=" * 80)
    print("COMPLETE DATA AVAILABLE FOR DISCORD ANNOUNCEMENTS")
    print("=" * 80)
    print()

    print("From scoredata.bin (100% reliable):")
    print("  - chart_hash")
    print("  - instrument_id")
    print("  - difficulty")
    print("  - score")
    print("  - stars")
    print("  - completion_percent (calculated from numerator/denominator)")
    print()

    print("From currentsong.txt (~90-95% available):")
    print("  - song_title")
    print("  - song_artist")
    print("  - song_charter")
    print()

    print("From OCR (~70-80% available, only if enabled):")
    print("  - notes_hit")
    print("  - notes_total")
    print("  - best_streak")
    print("  - song_title (fallback if currentsong.txt empty)")
    print("  - song_artist (fallback if currentsong.txt empty)")
    print()

    print("Calculated fields:")
    print("  - completion_percent = (numerator / denominator) * 100")
    print("  - accuracy = (notes_hit / notes_total) * 100 [if OCR available]")
    print()

    print("=" * 80)
    print("FIELDS USED FOR ENCHOR.US URL GENERATION")
    print("=" * 80)
    print()

    print("Required for URL generation:")
    print("  1. song_title (from currentsong.txt or OCR)")
    print("  2. song_artist (from currentsong.txt or OCR)")
    print("  3. instrument_id (from scoredata.bin)")
    print("  4. charter (from currentsong.txt) [OPTIONAL but helpful]")
    print()

    print("Example URL with all fields:")
    print("  https://www.enchor.us/?instrument=guitar&name=afterglow&artist=syncatto&charter=RLOMBARDI")
    print()

    print("Fallback if metadata unavailable:")
    print("  Display chart_hash instead of link")
    print()

    # If a file path is provided, actually parse and show sample data
    if filepath and Path(filepath).exists():
        print()
        print("=" * 80)
        print("SAMPLE DATA FROM PROVIDED FILE")
        print("=" * 80)
        print()
        parse_sample_data(filepath)


def parse_sample_data(filepath):
    """Parse and display sample data from a scoredata.bin file"""

    try:
        with open(filepath, 'rb') as f:
            # Read header
            header = f.read(4)
            print(f"Header: {header.hex()}")

            # Read song count
            song_count = struct.unpack('<I', f.read(4))[0]
            print(f"Total songs: {song_count}")
            print()

            # Show first 3 songs as samples
            max_display = min(3, song_count)
            print(f"Showing first {max_display} song(s):")
            print()

            for song_num in range(max_display):
                print(f"--- Song {song_num + 1} ---")

                # Chart hash
                hash_bytes = f.read(16)
                hash_hex = hash_bytes.hex()
                print(f"  Chart Hash: {hash_hex}")
                print(f"  Hash (short): [{hash_hex[:8]}]")

                # Instrument count
                instrument_count = struct.unpack('B', f.read(1))[0]
                print(f"  Instruments played: {instrument_count}")

                # Play count
                play_count_bytes = f.read(3) + b'\x00'
                play_count = struct.unpack('<I', play_count_bytes)[0]
                print(f"  Play count: {play_count}")

                # Instruments
                for inst_num in range(instrument_count):
                    inst_id = struct.unpack('<H', f.read(2))[0]
                    diff = struct.unpack('B', f.read(1))[0]
                    numerator = struct.unpack('<H', f.read(2))[0]
                    denominator = struct.unpack('<H', f.read(2))[0]
                    stars = struct.unpack('B', f.read(1))[0]
                    padding = f.read(4)
                    score = struct.unpack('<I', f.read(4))[0]

                    inst_names = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
                    diff_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

                    completion = (numerator / denominator * 100) if denominator > 0 else 0

                    print(f"    [{diff_names.get(diff, '?')} {inst_names.get(inst_id, '?')}]")
                    print(f"      Score: {score:,}")
                    print(f"      Stars: {stars}")
                    print(f"      Completion: {completion:.1f}% ({numerator}/{denominator})")

                print()

            if song_count > max_display:
                print(f"... and {song_count - max_display} more song(s)")

    except Exception as e:
        print(f"Error parsing file: {e}")


if __name__ == "__main__":
    import sys

    # Check if a file path was provided
    filepath = None
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"Analyzing: {filepath}")
        print()

    analyze_scoredata_format(filepath)

    if not filepath:
        print()
        print("To analyze a specific scoredata.bin file, run:")
        print("  python analyze_scoredata_fields.py <path_to_scoredata.bin>")

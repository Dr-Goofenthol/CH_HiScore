"""
Generate sample enchor.us URLs from actual scoredata.bin file

This script:
1. Parses scoredata.bin to get chart hashes and scores
2. Checks database for metadata (if charts have been submitted before)
3. Generates example enchor.us URLs
"""

import struct
import sqlite3
import urllib.parse
from pathlib import Path
import sys


def find_scoredata_bin():
    """Try to find the scoredata.bin file"""
    # Common Clone Hero locations
    possible_paths = [
        Path.home() / "AppData" / "LocalLow" / "srylain Inc_" / "Clone Hero" / "scoredata.bin",
        Path.home() / "Documents" / "Clone Hero" / "scoredata.bin",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def find_database():
    """Try to find the scores database"""
    possible_paths = [
        Path(r"C:\Users") / Path.home().name / "AppData" / "Roaming" / "CloneHeroScoreBot" / "scores.db",
        Path("scores.db"),
        Path("bot") / "scores.db",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def parse_scoredata(filepath):
    """Parse scoredata.bin and return all scores"""
    scores = []

    with open(filepath, 'rb') as f:
        # Read header
        header = f.read(4)

        # Read song count
        song_count = struct.unpack('<I', f.read(4))[0]

        # Parse each song
        for song_num in range(song_count):
            # Chart hash (16 bytes)
            hash_bytes = f.read(16)
            chart_hash = hash_bytes.hex()

            # Instrument count
            instrument_count = struct.unpack('B', f.read(1))[0]

            # Play count
            play_count_bytes = f.read(3) + b'\x00'
            play_count = struct.unpack('<I', play_count_bytes)[0]

            # Parse each instrument/difficulty combination
            for inst_num in range(instrument_count):
                inst_id = struct.unpack('<H', f.read(2))[0]
                diff = struct.unpack('B', f.read(1))[0]
                numerator = struct.unpack('<H', f.read(2))[0]
                denominator = struct.unpack('<H', f.read(2))[0]
                stars = struct.unpack('B', f.read(1))[0]
                padding = f.read(4)
                score = struct.unpack('<I', f.read(4))[0]

                completion = (numerator / denominator * 100) if denominator > 0 else 0

                scores.append({
                    'chart_hash': chart_hash,
                    'instrument_id': inst_id,
                    'difficulty': diff,
                    'score': score,
                    'stars': stars,
                    'completion': completion,
                    'play_count': play_count
                })

    return scores


def get_metadata_from_db(chart_hash, db_path):
    """Get song metadata from database if available"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, artist, charter
            FROM songs
            WHERE chart_hash = ?
        """, (chart_hash,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'title': row['title'],
                'artist': row['artist'],
                'charter': row['charter']
            }
    except Exception as e:
        pass

    return None


def generate_enchor_url(title=None, artist=None, charter=None):
    """Generate enchor.us URL (WITHOUT instrument parameter)"""
    if not title and not artist:
        return None

    params = {}

    if title:
        params['name'] = title.lower()
    if artist:
        params['artist'] = artist.lower()
    if charter:
        params['charter'] = charter  # Test both with and without lowercasing

    query = urllib.parse.urlencode(params)
    return f"https://www.enchor.us/?{query}"


def main(scoredata_path=None, db_path=None, max_samples=10):
    """Main function"""
    print("=" * 80)
    print("ENCHOR.US URL GENERATOR - SAMPLE SCORES")
    print("=" * 80)
    print()

    # Find scoredata.bin
    if not scoredata_path:
        scoredata_path = find_scoredata_bin()
        if not scoredata_path:
            print("ERROR: Could not find scoredata.bin")
            print("Please provide path as argument:")
            print(f"  python {sys.argv[0]} <path_to_scoredata.bin> [path_to_scores.db]")
            return

    scoredata_path = Path(scoredata_path)
    if not scoredata_path.exists():
        print(f"ERROR: File not found: {scoredata_path}")
        return

    print(f"Reading: {scoredata_path}")

    # Find database
    if not db_path:
        db_path = find_database()

    if db_path and Path(db_path).exists():
        print(f"Database: {db_path}")
        has_db = True
    else:
        print("Database: Not found (will show chart hashes only)")
        has_db = False

    print()

    # Parse scoredata.bin
    print("Parsing scoredata.bin...")
    scores = parse_scoredata(scoredata_path)
    print(f"Found {len(scores)} total scores")
    print()

    # Group by chart hash to get unique songs
    songs_by_hash = {}
    for score in scores:
        chart_hash = score['chart_hash']
        if chart_hash not in songs_by_hash:
            songs_by_hash[chart_hash] = []
        songs_by_hash[chart_hash].append(score)

    print(f"Unique songs: {len(songs_by_hash)}")
    print()

    # Show sample URLs
    print("=" * 80)
    print(f"SAMPLE ENCHOR.US URLs (showing up to {max_samples} songs)")
    print("=" * 80)
    print()

    # Get metadata for each unique song and generate URLs
    samples = []
    for chart_hash, song_scores in songs_by_hash.items():
        metadata = None
        if has_db:
            metadata = get_metadata_from_db(chart_hash, db_path)

        # Take the best score for this chart
        best_score = max(song_scores, key=lambda s: s['score'])

        samples.append({
            'chart_hash': chart_hash,
            'metadata': metadata,
            'score': best_score
        })

    # Sort by whether we have metadata (prioritize songs with metadata)
    samples.sort(key=lambda s: (s['metadata'] is not None, s['score']['score']), reverse=True)

    # Show samples
    instrument_names = {0: "Lead Guitar", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
    difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

    shown = 0
    with_metadata = 0
    without_metadata = 0

    for sample in samples[:max_samples]:
        chart_hash = sample['chart_hash']
        metadata = sample['metadata']
        score_data = sample['score']

        shown += 1

        print(f"Sample {shown}:")
        print(f"  Chart Hash: {chart_hash}")
        print(f"  Best Score: {score_data['score']:,} pts ({difficulty_names[score_data['difficulty']]} {instrument_names[score_data['instrument_id']]})")
        print(f"  Stars: {score_data['stars']}, Completion: {score_data['completion']:.1f}%")

        if metadata:
            with_metadata += 1
            title = metadata['title']
            artist = metadata['artist']
            charter = metadata['charter']

            print(f"  Metadata (from database):")
            print(f"    Title: {title or '[None]'}")
            print(f"    Artist: {artist or '[None]'}")
            print(f"    Charter: {charter or '[None]'}")

            # Generate URL
            url = generate_enchor_url(title, artist, charter)

            if url:
                print(f"  Enchor.us URL:")
                print(f"    {url}")
            else:
                print(f"  Enchor.us URL: [Cannot generate - no title or artist]")
        else:
            without_metadata += 1
            print(f"  Metadata: Not available in database")
            print(f"  Enchor.us URL: [Would need title/artist from currentsong.txt]")
            print(f"  Fallback: Display chart hash [{chart_hash[:8]}]")

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total unique songs: {len(songs_by_hash)}")
    print(f"Samples shown: {shown}")
    print(f"  With metadata: {with_metadata} ({with_metadata/shown*100:.0f}%)")
    print(f"  Without metadata: {without_metadata} ({without_metadata/shown*100:.0f}%)")
    print()

    if with_metadata > 0:
        print("SUCCESS RATE:")
        print(f"  {with_metadata}/{shown} songs have metadata for enchor.us links")
        print()

    if not has_db:
        print("NOTE: No database found. Metadata would come from currentsong.txt")
        print("      during live gameplay. These samples only show chart hashes.")
        print()

    print("To test the generated URLs:")
    print("  1. Copy a URL from above")
    print("  2. Paste into your browser")
    print("  3. Verify the search results match the song")
    print()
    print("Next step: Implement URL generation in bot/api.py")


if __name__ == "__main__":
    import sys

    scoredata = None
    database = None

    if len(sys.argv) > 1:
        scoredata = sys.argv[1]

    if len(sys.argv) > 2:
        database = sys.argv[2]

    main(scoredata, database)

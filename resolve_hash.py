"""
Test script to resolve chart hashes to song names using songcache.bin

This script helps identify songs for scores that only have chart hashes.
It can optionally update the database with the resolved metadata.

Usage:
    python resolve_hash.py

Then follow the prompts to enter a hash and optionally update the database.
"""

import sys
import sqlite3
from pathlib import Path
from shared.parsers import SongCacheParser, parse_song_ini
from shared.console import print_success, print_info, print_error, print_warning


def find_clone_hero_path():
    """Try to find Clone Hero installation path"""
    import os

    # Common locations
    userprofile = os.environ.get('USERPROFILE', '')
    common_paths = [
        Path(userprofile) / "AppData" / "LocalLow" / "srylain Inc_" / "Clone Hero",
        Path("C:/Program Files/Clone Hero"),
        Path("C:/Program Files (x86)/Clone Hero"),
        Path(userprofile) / "Documents" / "Clone Hero"
    ]

    for path in common_paths:
        songcache_path = path / "songcache.bin"
        if songcache_path.exists():
            return path

    return None


def resolve_hash(hash_input: str, songcache_path: Path):
    """
    Resolve a chart hash to song metadata

    Args:
        hash_input: Chart hash (can be partial like "34c41852" or full)
        songcache_path: Path to songcache.bin file

    Returns:
        Tuple of (full_hash, title, artist, filepath) or None if not found
    """
    # Normalize hash input (remove brackets, spaces, etc.)
    hash_input = hash_input.strip().lower().replace('[', '').replace(']', '')

    print_info(f"Searching for hash: {hash_input}")
    print_info(f"Parsing songcache: {songcache_path}")

    # Parse songcache.bin
    try:
        parser = SongCacheParser(str(songcache_path))
        songs = parser.parse()
        print_success(f"Found {len(songs)} songs in songcache")
    except Exception as e:
        print_error(f"Failed to parse songcache: {e}")
        return None

    # Find matching hash (supports partial hash matching)
    matches = []
    for chart_hash, metadata in songs.items():
        if chart_hash.startswith(hash_input) or hash_input in chart_hash:
            matches.append((chart_hash, metadata))

    if not matches:
        print_error(f"No songs found matching hash: {hash_input}")
        return None

    if len(matches) > 1:
        print_warning(f"Found {len(matches)} matches for '{hash_input}':")
        for i, (h, m) in enumerate(matches[:5], 1):
            print(f"  {i}. [{h[:8]}] {m.title}")
        if len(matches) > 5:
            print(f"  ... and {len(matches) - 5} more")
        print_info("Please use a more specific hash")
        return None

    # Found exactly one match
    chart_hash, metadata = matches[0]

    print_success(f"Found match!")
    print_info(f"Hash: {chart_hash}")
    print_info(f"Title: {metadata.title}")
    print_info(f"Path: {metadata.filepath}")

    # Try to get artist from song.ini
    artist = ""
    if metadata.filepath:
        try:
            ini_data = parse_song_ini(metadata.filepath)
            if ini_data:
                artist = ini_data.get('artist', '')
                if artist:
                    print_info(f"Artist: {artist}")
        except Exception as e:
            print_warning(f"Could not read song.ini: {e}")

    return (chart_hash, metadata.title, artist, metadata.filepath)


def update_database(chart_hash: str, title: str, artist: str, db_path: Path):
    """
    Update the bot database with resolved song metadata

    Args:
        chart_hash: Full chart hash
        title: Song title
        artist: Artist name
        db_path: Path to bot database
    """
    if not db_path.exists():
        print_error(f"Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if song already exists
        cursor.execute("SELECT title, artist FROM songs WHERE chart_hash = ?", (chart_hash,))
        existing = cursor.fetchone()

        if existing:
            existing_title, existing_artist = existing
            print_info(f"Current DB entry: {existing_title} - {existing_artist}")

            # Update
            cursor.execute("""
                UPDATE songs
                SET title = ?, artist = ?
                WHERE chart_hash = ?
            """, (title, artist, chart_hash))
            print_success(f"Updated existing song entry")
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO songs (chart_hash, title, artist)
                VALUES (?, ?, ?)
            """, (chart_hash, title, artist))
            print_success(f"Added new song entry")

        conn.commit()
        conn.close()

        print_success(f"Database updated: {title} - {artist}")
        return True

    except Exception as e:
        print_error(f"Database update failed: {e}")
        return False


def main():
    """Main script loop"""
    print("\n" + "=" * 60)
    print("Clone Hero Hash Resolver")
    print("=" * 60)
    print()

    # Find Clone Hero path
    ch_path = find_clone_hero_path()
    if not ch_path:
        print_error("Could not find Clone Hero installation")
        custom_path = input("Enter path to Clone Hero directory (or 'quit'): ").strip()
        if custom_path.lower() == 'quit':
            return
        ch_path = Path(custom_path)

    songcache_path = ch_path / "songcache.bin"
    if not songcache_path.exists():
        print_error(f"songcache.bin not found at: {songcache_path}")
        return

    print_success(f"Found Clone Hero at: {ch_path}")
    print()

    # Find database
    db_path = None
    common_db_paths = [
        Path.cwd() / "scores.db",
        Path.cwd() / "bot" / "scores.db",
        Path.home() / "AppData" / "Roaming" / "CloneHeroScoreBot" / "scores.db"
    ]

    for path in common_db_paths:
        if path.exists():
            db_path = path
            break

    if db_path:
        print_success(f"Found database at: {db_path}")
    else:
        print_warning("Database not found - lookup only mode")

    print()
    print("Enter 'quit' to exit")
    print("-" * 60)
    print()

    # Main loop
    while True:
        hash_input = input("Enter chart hash (e.g., 34c41852): ").strip()

        if hash_input.lower() in ['quit', 'exit', 'q']:
            print_info("Goodbye!")
            break

        if not hash_input:
            continue

        # Resolve hash
        result = resolve_hash(hash_input, songcache_path)

        if result:
            chart_hash, title, artist, filepath = result

            # Ask if user wants to update database
            if db_path:
                print()
                update = input("Update database with this info? (y/n): ").strip().lower()
                if update == 'y':
                    update_database(chart_hash, title, artist, db_path)

        print()
        print("-" * 60)
        print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

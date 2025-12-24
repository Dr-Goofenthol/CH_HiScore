"""
Resolve chart hashes by scanning song folders directly and calculating blake3 hashes

This script:
1. Scans your Clone Hero songs folder
2. Calculates blake3 hash for each chart file (same as Clone Hero)
3. Matches hashes from scoredata.bin to actual songs
4. Extracts metadata from song.ini files
5. Optionally updates the database

This bypasses the incomplete songcache.bin entirely.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple
from shared.parsers import parse_song_ini
from shared.console import print_success, print_info, print_error, print_warning

# Try to import blake3 (same hash Clone Hero uses)
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False
    print_warning("blake3 library not installed. Install with: pip install blake3")


def calculate_chart_hash(chart_path: Path) -> Optional[str]:
    """
    Calculate the blake3 hash for a chart file (same as Clone Hero)

    Args:
        chart_path: Path to chart file (notes.chart, notes.mid, etc.)

    Returns:
        16-byte hex hash string or None if error
    """
    if not HAS_BLAKE3:
        return None

    try:
        with open(chart_path, 'rb') as f:
            hasher = blake3.blake3()
            hasher.update(f.read())
            # Clone Hero uses 16-byte (128-bit) blake3 hash
            return hasher.digest()[:16].hex()
    except Exception as e:
        return None


def scan_songs_folder(songs_path: Path, target_hashes: set = None) -> Dict[str, Tuple[str, str, str]]:
    """
    Scan songs folder and calculate hashes for all charts

    Args:
        songs_path: Path to Clone Hero songs folder
        target_hashes: Optional set of hashes to look for (stops when all found)

    Returns:
        Dictionary mapping chart_hash -> (title, artist, filepath)
    """
    results = {}
    total_scanned = 0
    found_count = 0

    print_info(f"Scanning: {songs_path}")
    print_warning("This may take several minutes for large libraries...")
    print()

    # Walk through all subdirectories
    for root, dirs, files in os.walk(songs_path):
        # Look for chart files
        chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

        if not chart_files:
            continue

        total_scanned += 1

        # Show progress every 100 songs
        if total_scanned % 100 == 0:
            print(f"  Scanned {total_scanned} songs... (found {found_count} matches)", end='\r')

        chart_file = chart_files[0]
        chart_path = Path(root) / chart_file

        # Calculate hash
        chart_hash = calculate_chart_hash(chart_path)

        if not chart_hash:
            continue

        # Check if this is a target hash
        if target_hashes and chart_hash not in target_hashes:
            # Also check if partial match (first 8 chars)
            if not any(chart_hash.startswith(h) for h in target_hashes):
                continue

        # Found a match! Get metadata
        try:
            ini_data = parse_song_ini(str(chart_path))

            if ini_data:
                title = ini_data.get('name', ini_data.get('title', ''))
                artist = ini_data.get('artist', '')

                # If no title in ini, try to extract from folder name
                if not title:
                    title = Path(root).name

                results[chart_hash] = (title, artist, str(chart_path))
                found_count += 1

                print(f"\n[+] Found: {title} - {artist}")
                print(f"    Hash: {chart_hash[:8]}...")

                # If we found all target hashes, we can stop
                if target_hashes and found_count >= len(target_hashes):
                    print()
                    print_success(f"Found all {found_count} target hashes!")
                    break
        except:
            pass

    print(f"\n\nScanned {total_scanned} total songs")
    print_success(f"Found {found_count} matching hashes")

    return results


def resolve_hashes_interactive(songs_path: Path, db_path: Path = None):
    """
    Interactive mode: user enters hashes to resolve
    """
    print("\n" + "=" * 70)
    print("Hash Resolver - Direct Song Scan Mode")
    print("=" * 70)
    print()

    if not HAS_BLAKE3:
        print_error("blake3 library required!")
        print_info("Install with: pip install blake3")
        return

    print("Enter chart hashes (comma-separated) or 'all' to scan everything:")
    print("Example: 34c41852, 30799ff2")
    print()

    hash_input = input("Hashes: ").strip()

    if not hash_input:
        return

    # Parse input
    if hash_input.lower() == 'all':
        target_hashes = None
        print_warning("Scanning ALL songs - this will take a while!")
    else:
        target_hashes = set()
        for h in hash_input.split(','):
            h = h.strip().lower().replace('[', '').replace(']', '')
            if h:
                target_hashes.add(h)

        print_info(f"Looking for {len(target_hashes)} hashes...")

    print()

    # Scan songs folder
    results = scan_songs_folder(songs_path, target_hashes)

    if not results:
        print_error("No matches found!")
        return

    # Display results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    for chart_hash, (title, artist, filepath) in results.items():
        print(f"\n[{chart_hash[:8]}]")
        print(f"  Title:  {title}")
        print(f"  Artist: {artist}")
        print(f"  Path:   {filepath}")

    # Update database if available
    if db_path and db_path.exists():
        print()
        update = input("\nUpdate database with these songs? (y/n): ").strip().lower()

        if update == 'y':
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                for chart_hash, (title, artist, filepath) in results.items():
                    # Check if exists
                    cursor.execute("SELECT title FROM songs WHERE chart_hash = ?", (chart_hash,))
                    existing = cursor.fetchone()

                    if existing:
                        cursor.execute("""
                            UPDATE songs SET title = ?, artist = ?
                            WHERE chart_hash = ?
                        """, (title, artist, chart_hash))
                        print(f"  [+] Updated: {title}")
                    else:
                        cursor.execute("""
                            INSERT INTO songs (chart_hash, title, artist)
                            VALUES (?, ?, ?)
                        """, (chart_hash, title, artist))
                        print(f"  [+] Added: {title}")

                conn.commit()
                conn.close()

                print()
                print_success(f"Database updated with {len(results)} songs!")

            except Exception as e:
                print_error(f"Database update failed: {e}")


def main():
    # Default paths
    default_songs_path = r"D:\Games\Clone Hero\clonehero-win64\songs"
    default_db_path = Path.cwd() / "bot" / "scores.db"

    # Check for database
    if not default_db_path.exists():
        alt_db = Path.cwd() / "scores.db"
        if alt_db.exists():
            default_db_path = alt_db
        else:
            default_db_path = None

    # Get songs path
    print("\n" + "=" * 70)
    print("Clone Hero Hash Resolver - Song Scanner")
    print("=" * 70)
    print()

    songs_input = input(f"Songs folder path (default: {default_songs_path}): ").strip()
    songs_path = Path(songs_input) if songs_input else Path(default_songs_path)

    if not songs_path.exists():
        print_error(f"Path not found: {songs_path}")
        return

    print_success(f"Songs folder: {songs_path}")

    if default_db_path:
        print_success(f"Database: {default_db_path}")
    else:
        print_warning("No database found - lookup only mode")

    # Run interactive mode
    resolve_hashes_interactive(songs_path, default_db_path)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

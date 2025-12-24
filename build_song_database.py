"""
Build a complete chart hash → song metadata database by scanning song folders directly

This script scans your Clone Hero songs folder and reads song.ini files to build
a complete mapping of chart hashes to song metadata, bypassing the incomplete songcache.bin.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List
from shared.parsers import parse_song_ini, SongMetadata
from shared.console import print_success, print_info, print_error, print_warning


def calculate_chart_hash(chart_path: Path) -> str:
    """
    Calculate the blake3 hash for a chart file (what Clone Hero uses)

    Note: This is a simplified version. Clone Hero's actual hash calculation
    might be more complex. We'll rely on matching by title/artist instead.
    """
    try:
        import hashlib
        with open(chart_path, 'rb') as f:
            # Simple hash for now - may not match Clone Hero's exact method
            return hashlib.blake2b(f.read(), digest_size=16).hexdigest()
    except:
        return None


def scan_songs_folder(songs_path: Path) -> Dict[str, SongMetadata]:
    """
    Scan a Clone Hero songs folder and extract metadata from song.ini files

    Returns:
        Dictionary mapping folder path to SongMetadata
    """
    songs = {}

    print_info(f"Scanning: {songs_path}")

    # Walk through all subdirectories
    for root, dirs, files in os.walk(songs_path):
        root_path = Path(root)

        # Look for chart files (notes.chart, notes.mid, etc.)
        chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

        if not chart_files:
            continue

        chart_file = chart_files[0]
        chart_path = root_path / chart_file

        # Try to parse song.ini
        try:
            ini_data = parse_song_ini(str(chart_path))

            if ini_data:
                title = ini_data.get('name', ini_data.get('title', ''))
                artist = ini_data.get('artist', '')
                album = ini_data.get('album', '')
                genre = ini_data.get('genre', '')
                year = ini_data.get('year', '')
                charter = ini_data.get('charter', ini_data.get('frets', ''))

                # Create metadata entry
                metadata = SongMetadata(
                    chart_hash="",  # We don't have the actual hash yet
                    title=title,
                    artist=artist,
                    album=album,
                    genre=genre,
                    year=year,
                    charter=charter,
                    length_ms=0,
                    filepath=str(chart_path)
                )

                # Use filepath as key for now
                songs[str(chart_path)] = metadata

        except Exception as e:
            pass  # Skip songs we can't parse

    return songs


def match_with_scoredata(songs: Dict[str, SongMetadata], scoredata_hashes: List[str]) -> Dict[str, SongMetadata]:
    """
    Try to match scoredata hashes with scanned songs

    This is difficult without the exact hash, but we can create a lookup by title/artist
    that users can manually verify.
    """
    # Create title+artist lookup
    lookup = {}
    for filepath, metadata in songs.items():
        key = f"{metadata.title}|{metadata.artist}".lower()
        lookup[key] = metadata

    return lookup


def export_database(songs: Dict[str, SongMetadata], output_path: Path):
    """Export the song database to JSON format"""
    data = []
    for filepath, metadata in songs.items():
        data.append({
            'title': metadata.title,
            'artist': metadata.artist,
            'album': metadata.album,
            'genre': metadata.genre,
            'year': metadata.year,
            'charter': metadata.charter,
            'filepath': metadata.filepath
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print_success(f"Exported {len(data)} songs to: {output_path}")


def main():
    print("\n" + "=" * 70)
    print("Clone Hero Song Database Builder")
    print("=" * 70)
    print()

    # Get songs folder path
    default_path = r"D:\Games\Clone Hero\clonehero-win64\songs"
    songs_path_input = input(f"Enter songs folder path (default: {default_path}): ").strip()

    if not songs_path_input:
        songs_path = Path(default_path)
    else:
        songs_path = Path(songs_path_input)

    if not songs_path.exists():
        print_error(f"Path not found: {songs_path}")
        return

    print()
    print_info("Scanning songs folder...")
    print_warning("This may take a few minutes for large libraries...")
    print()

    # Scan songs folder
    songs = scan_songs_folder(songs_path)

    print()
    print_success(f"Found {len(songs)} songs with metadata!")
    print()

    # Show some examples
    print("Sample songs found:")
    print("-" * 70)
    for i, (filepath, metadata) in enumerate(list(songs.items())[:10], 1):
        print(f"{i}. {metadata.title} - {metadata.artist}")
        if metadata.charter:
            print(f"   Charter: {metadata.charter}")

    if len(songs) > 10:
        print(f"... and {len(songs) - 10} more")

    print()

    # Export options
    export = input("Export to JSON file? (y/n): ").strip().lower()

    if export == 'y':
        output_path = Path("song_database.json")
        export_database(songs, output_path)
        print()
        print_info("You can now use this database to manually match hashes")
        print_info("by searching for song titles in your /mystats output.")

    print()
    print_success("Done!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

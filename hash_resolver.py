"""
Simple hash resolver - finds songs by their MD5 chart hash

Usage:
    python hash_resolver.py 34c41852
    python hash_resolver.py d8c243cc 30799ff2
"""

import os
import sys
import hashlib
from pathlib import Path
from shared.parsers import parse_song_ini


def calculate_md5(file_path):
    """Calculate MD5 hash of a file"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def scan_songs(songs_path, target_hashes):
    """Scan songs folder for matching hashes"""
    results = {}
    scanned = 0

    print(f"Scanning: {songs_path}")
    print(f"Looking for {len(target_hashes)} hash(es)...")
    print()

    for root, dirs, files in os.walk(songs_path):
        # Look for chart files
        chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

        if not chart_files:
            continue

        scanned += 1

        if scanned % 100 == 0:
            print(f"[Scanned {scanned} songs, found {len(results)} matches...]", end='\r')

        chart_path = Path(root) / chart_files[0]

        # Calculate MD5
        md5_hash = calculate_md5(chart_path)

        if not md5_hash:
            continue

        # Check if this matches any target hash
        for target in target_hashes:
            if md5_hash.startswith(target):
                # Found a match!
                try:
                    ini_data = parse_song_ini(str(chart_path))

                    if ini_data:
                        title = ini_data.get('name', ini_data.get('title', ''))
                        artist = ini_data.get('artist', '')
                        charter = ini_data.get('charter', ini_data.get('frets', ''))

                        if not title:
                            title = Path(root).name

                        results[md5_hash] = {
                            'title': title,
                            'artist': artist,
                            'charter': charter,
                            'path': str(chart_path),
                            'folder': Path(root).name
                        }

                        print(f"\n[+] Found {target}: {title} - {artist}")
                except:
                    pass

                # Stop scanning if we found all hashes
                if len(results) >= len(target_hashes):
                    print()
                    return results

    print(f"\nScanned {scanned} total songs")
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python hash_resolver.py <hash1> [hash2] [hash3] ...")
        print("Example: python hash_resolver.py 34c41852 d8c243cc")
        return

    # Get target hashes from command line
    target_hashes = [h.strip().lower() for h in sys.argv[1:]]

    # Default songs path
    songs_path = Path(r"D:\Games\Clone Hero\clonehero-win64\songs")

    if not songs_path.exists():
        print(f"ERROR: Songs path not found: {songs_path}")
        return

    print("="*70)
    print("Clone Hero Hash Resolver")
    print("="*70)
    print()

    # Scan for hashes
    results = scan_songs(songs_path, target_hashes)

    # Display results
    print()
    print("="*70)
    print(f"RESULTS ({len(results)} found)")
    print("="*70)

    if not results:
        print("No matches found!")
        return

    for hash_val, info in results.items():
        print()
        print(f"Hash:    [{hash_val[:8]}] {hash_val}")
        print(f"Title:   {info['title']}")
        print(f"Artist:  {info['artist']}")
        if info['charter']:
            print(f"Charter: {info['charter']}")
        print(f"Folder:  {info['folder']}")
        print(f"Path:    {info['path']}")

    print()
    print("="*70)


if __name__ == '__main__':
    main()

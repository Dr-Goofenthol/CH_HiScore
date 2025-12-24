"""
Test script to validate blake3 hash calculation against Clone Hero's method

This script attempts different hash calculation methods to find the one that matches
Clone Hero's actual hashes, helping us reverse-engineer the exact format.
"""

import os
import blake3
from pathlib import Path
from typing import Optional, Dict
from shared.parsers import parse_song_ini, ScoreDataParser
from shared.console import print_success, print_info, print_error, print_warning


def read_chart_file(chart_path: Path) -> Optional[bytes]:
    """Read the raw chart file content"""
    try:
        with open(chart_path, 'rb') as f:
            return f.read()
    except Exception as e:
        return None


def get_ini_modifiers(chart_path: Path) -> Dict[str, str]:
    """
    Extract the .ini modifiers that affect chart hash

    Modifiers from scan-chart documentation:
    - song_length
    - hopo_frequency
    - eighthnote_hopo
    - multiplier_note
    - sustain_cutoff_threshold
    - chord_snap_threshold
    - five_lane_drums
    - pro_drums
    """
    try:
        ini_data = parse_song_ini(str(chart_path))
        if not ini_data:
            return {}

        # Extract relevant modifiers with defaults
        modifiers = {
            'song_length': ini_data.get('song_length', ''),
            'hopo_frequency': ini_data.get('hopo_frequency', ''),
            'eighthnote_hopo': ini_data.get('eighthnote_hopo', ''),
            'multiplier_note': ini_data.get('multiplier_note', ''),
            'sustain_cutoff_threshold': ini_data.get('sustain_cutoff_threshold', ''),
            'chord_snap_threshold': ini_data.get('chord_snap_threshold', ''),
            'five_lane_drums': ini_data.get('five_lane_drums', ''),
            'pro_drums': ini_data.get('pro_drums', '')
        }

        return modifiers
    except:
        return {}


def calculate_hash_method1(chart_content: bytes, modifiers: Dict[str, str]) -> str:
    """
    Method 1: MD5 of raw chart file (CONFIRMED CORRECT METHOD!)
    """
    import hashlib
    return hashlib.md5(chart_content).hexdigest()


def calculate_hash_method2(chart_content: bytes, modifiers: Dict[str, str]) -> str:
    """
    Method 2: Hash chart file + concatenated modifier values (as string)
    """
    hasher = blake3.blake3()
    hasher.update(chart_content)

    # Add modifiers as concatenated string
    modifier_str = ''.join(str(v) for v in modifiers.values())
    hasher.update(modifier_str.encode('utf-8'))

    return hasher.digest()[:16].hex()


def calculate_hash_method3(chart_content: bytes, modifiers: Dict[str, str]) -> str:
    """
    Method 3: Hash chart file + modifier key=value pairs (sorted)
    """
    hasher = blake3.blake3()
    hasher.update(chart_content)

    # Add modifiers as key=value pairs, sorted by key
    for key in sorted(modifiers.keys()):
        if modifiers[key]:  # Only include if value exists
            pair = f"{key}={modifiers[key]}\n"
            hasher.update(pair.encode('utf-8'))

    return hasher.digest()[:16].hex()


def calculate_hash_method4(chart_content: bytes, modifiers: Dict[str, str]) -> str:
    """
    Method 4: Hash chart file + only non-empty modifier values (sorted)
    """
    hasher = blake3.blake3()
    hasher.update(chart_content)

    # Add only non-empty modifier values, sorted by key
    for key in sorted(modifiers.keys()):
        if modifiers[key]:
            hasher.update(str(modifiers[key]).encode('utf-8'))

    return hasher.digest()[:16].hex()


def test_chart_against_known_hash(chart_path: Path, target_hash: str) -> bool:
    """
    Test a chart file against a known hash using multiple methods
    """
    # Read chart content
    chart_content = read_chart_file(chart_path)
    if not chart_content:
        return False

    # Get .ini modifiers
    modifiers = get_ini_modifiers(chart_path)

    # Calculate MD5 hash (the correct method!)
    import hashlib
    calculated_hash = hashlib.md5(chart_content).hexdigest()

    print(f"\nTesting: {chart_path.name}")
    print(f"Target hash: {target_hash[:16]}...")
    print(f"Calculated:  {calculated_hash[:16]}...")

    # Check for match
    if calculated_hash.startswith(target_hash[:8]):
        print()
        print("=" * 70)
        print("*** MATCH FOUND! ***")
        print("=" * 70)
        print(f"Song: {chart_path.parent.name}")
        print(f"Full hash: {calculated_hash}")
        print(f"Path: {chart_path}")

        # Try to get metadata
        try:
            ini_data = parse_song_ini(str(chart_path))
            if ini_data:
                print(f"Title: {ini_data.get('name', 'Unknown')}")
                print(f"Artist: {ini_data.get('artist', 'Unknown')}")
                print(f"Charter: {ini_data.get('charter', 'Unknown')}")
        except:
            pass

        print("=" * 70)
        return True

    return False


def scan_and_test(songs_path: Path, target_hash: str):
    """
    Scan songs folder and test charts against target hash
    """
    print_info(f"Scanning: {songs_path}")
    print_info(f"Target hash: {target_hash}")
    print_warning("Scanning all songs - this may take a while...")
    print()

    scanned = 0
    total_folders = 0
    chart_files_found = []

    for root, dirs, files in os.walk(songs_path):
        total_folders += 1

        # Look for chart files
        chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

        if not chart_files:
            continue

        scanned += 1

        # Store first 5 for diagnostics
        if scanned <= 5:
            chart_files_found.append(Path(root) / chart_files[0])

        chart_file = chart_files[0]
        chart_path = Path(root) / chart_file

        # Test this chart
        if test_chart_against_known_hash(chart_path, target_hash):
            return True

        # Show progress every 100 songs
        if scanned % 100 == 0:
            print(f"[Scanned {scanned} songs...]", end='\r')

    print()
    print()
    print_warning(f"Scan complete:")
    print(f"  Total folders checked: {total_folders}")
    print(f"  Chart files found: {scanned}")
    print()

    if chart_files_found:
        print("First 5 charts scanned:")
        for p in chart_files_found:
            print(f"  {p}")
        print()

    print_error(f"No matching hash found for {target_hash[:8]}")
    print_info("The song with this hash may not be in your current songs folder.")
    return False


def main():
    print("\n" + "=" * 70)
    print("Clone Hero Hash Calculation Test")
    print("=" * 70)
    print()

    # Get target hash from scoredata.bin
    print("First, let's get a known hash from your scoredata.bin...")

    scoredata_path = Path(r'C:\Users\jgold\AppData\LocalLow\srylain Inc_\Clone Hero\scoredata.bin')

    if scoredata_path.exists():
        parser = ScoreDataParser(str(scoredata_path))
        scores = parser.parse()

        if scores:
            # Get unique hashes
            unique_hashes = list(set(s.chart_hash for s in scores))

            print_success(f"Found {len(unique_hashes)} unique chart hashes in scoredata.bin")
            print()
            print("Sample hashes:")
            for i, h in enumerate(unique_hashes[:5], 1):
                print(f"  {i}. {h[:16]}...")

    print()
    print("-" * 70)
    print()

    # Get user input
    target_hash = input("Enter hash to test (or first 8 chars): ").strip().lower()
    target_hash = target_hash.replace('[', '').replace(']', '')

    if not target_hash:
        print_error("No hash provided")
        return

    # Get songs path
    default_songs_path = r"D:\Games\Clone Hero\clonehero-win64\songs"
    songs_input = input(f"Songs folder (default: {default_songs_path}): ").strip()
    songs_path = Path(songs_input) if songs_input else Path(default_songs_path)

    if not songs_path.exists():
        print_error(f"Path not found: {songs_path}")
        return

    print()

    # Run test
    scan_and_test(songs_path, target_hash)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

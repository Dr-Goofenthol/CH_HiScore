"""
Simple MD5 test for Mario Circuit to verify hash calculation
"""

import hashlib
from pathlib import Path
import os

def find_mario_circuit(songs_path: Path):
    """Find Mario Circuit song"""
    print(f"Searching in: {songs_path}\n")

    for root, dirs, files in os.walk(songs_path):
        folder_name = Path(root).name.lower()

        if 'mario' in folder_name and 'circuit' in folder_name:
            # Check if it has a chart file
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if chart_files:
                chart_path = Path(root) / chart_files[0]
                print(f"[+] Found Mario Circuit: {root}\n")
                return chart_path

    return None

def test_md5(chart_path: Path):
    """Test MD5 hash calculation"""
    print(f"Chart file: {chart_path}")
    print(f"File exists: {chart_path.exists()}\n")

    if not chart_path.exists():
        print("ERROR: File not found!")
        return

    # Read raw bytes
    with open(chart_path, 'rb') as f:
        content = f.read()

    print(f"File size: {len(content):,} bytes\n")

    # Calculate MD5
    md5_hash = hashlib.md5(content).hexdigest()

    # Known correct hash from scoredata.bin
    known_hash = "d8c243cc0920e1aaed9c66b5f5274060"

    print("=" * 70)
    print(f"Calculated MD5: {md5_hash}")
    print(f"Expected hash:  {known_hash}")
    print("=" * 70)

    if md5_hash == known_hash:
        print("\n*** MATCH! MD5 calculation is correct! ***\n")
    else:
        print("\n*** NO MATCH - Something is wrong ***\n")
        print(f"First 8 chars calculated: {md5_hash[:8]}")
        print(f"First 8 chars expected:   {known_hash[:8]}")

def main():
    songs_path = Path(r"D:\Games\Clone Hero\clonehero-win64\songs")

    if not songs_path.exists():
        print(f"ERROR: Songs path not found: {songs_path}")
        return

    chart_path = find_mario_circuit(songs_path)

    if not chart_path:
        print("ERROR: Mario Circuit not found!")
        print("Make sure the song folder contains 'mario' and 'circuit' in the name.")
        return

    test_md5(chart_path)

if __name__ == '__main__':
    main()

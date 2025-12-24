"""
Test script to reverse-engineer enchor.us hash calculations
"""

import hashlib
import base64
from pathlib import Path
from shared.parsers import parse_song_ini

try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False
    print("WARNING: blake3 not installed")


def test_enchor_hashes(song_folder: Path):
    """
    Test various hash calculations to match enchor.us format

    Known values for Mario Circuit:
    - Folder MD5: 482e7ded1a1ac06c45f97fdba46baf55
    - Chart Hash (blake3 base64): fiz6NVJ7EYy2VRnEFg2v_afJ3-gCgRovyjTwtJv3I3U=
    - Clone Hero MD5: d8c243cc0920e1aaed9c66b5f5274060
    """

    print("="*70)
    print("Testing enchor.us Hash Methods")
    print("="*70)
    print()

    # Known values
    known_folder_md5 = "482e7ded1a1ac06c45f97fdba46baf55"
    known_chart_b64 = "fiz6NVJ7EYy2VRnEFg2v_afJ3-gCgRovyjTwtJv3I3U="
    known_ch_md5 = "d8c243cc0920e1aaed9c66b5f5274060"

    # Decode blake3 base64 to hex
    chart_blake3_bytes = base64.urlsafe_b64decode(known_chart_b64)
    chart_blake3_hex = chart_blake3_bytes.hex()

    print(f"Song folder: {song_folder}")
    print()
    print("Known enchor.us values:")
    print(f"  Folder MD5:      {known_folder_md5}")
    print(f"  Chart (base64):  {known_chart_b64}")
    print(f"  Chart (hex):     {chart_blake3_hex}")
    print(f"  Clone Hero MD5:  {known_ch_md5}")
    print()

    # Find chart file
    chart_files = list(song_folder.glob('notes.chart')) + list(song_folder.glob('notes.mid'))

    if not chart_files:
        print("ERROR: No chart file found!")
        return

    chart_file = chart_files[0]
    print(f"Chart file: {chart_file.name}")
    print()

    # Read chart content
    with open(chart_file, 'rb') as f:
        chart_content = f.read()

    print(f"Chart size: {len(chart_content):,} bytes")
    print()

    # Test 1: MD5 of chart file (we know this matches Clone Hero)
    md5_chart = hashlib.md5(chart_content).hexdigest()
    match1 = " <-- MATCH!" if md5_chart == known_ch_md5 else ""
    print(f"1. MD5 of chart file:        {md5_chart}{match1}")

    # Test 2: Blake3 of chart file (full 32 bytes)
    if HAS_BLAKE3:
        blake3_chart_32 = blake3.blake3(chart_content).hexdigest()
        match2 = " <-- MATCH!" if blake3_chart_32 == chart_blake3_hex else ""
        print(f"2. Blake3 of chart (32b):    {blake3_chart_32}{match2}")

        # Test 3: Blake3 base64 of chart
        blake3_bytes = blake3.blake3(chart_content).digest()
        blake3_b64 = base64.urlsafe_b64encode(blake3_bytes).decode()
        match3 = " <-- MATCH!" if blake3_b64 == known_chart_b64 else ""
        print(f"3. Blake3 chart (base64):    {blake3_b64}{match3}")

    print()
    print("-" * 70)
    print("Testing Folder MD5 calculations:")
    print("-" * 70)
    print()

    # Get song.ini data
    ini_data = parse_song_ini(str(chart_file))

    if ini_data:
        print("song.ini metadata:")
        for key in ['name', 'artist', 'album', 'genre', 'year', 'charter']:
            if key in ini_data:
                print(f"  {key}: {ini_data[key]}")
        print()

    # Test folder MD5 calculations
    folder_name = song_folder.name

    # Test 4: MD5 of folder name
    md5_folder_name = hashlib.md5(folder_name.encode('utf-8')).hexdigest()
    match4 = " <-- MATCH!" if md5_folder_name == known_folder_md5 else ""
    print(f"4. MD5 of folder name:       {md5_folder_name}{match4}")

    # Test 5: MD5 of folder path
    md5_folder_path = hashlib.md5(str(song_folder).encode('utf-8')).hexdigest()
    match5 = " <-- MATCH!" if md5_folder_path == known_folder_md5 else ""
    print(f"5. MD5 of folder path:       {md5_folder_path}{match5}")

    # Test 6: MD5 of song.ini file content
    ini_file = song_folder / 'song.ini'
    if ini_file.exists():
        with open(ini_file, 'rb') as f:
            ini_content = f.read()
        md5_ini = hashlib.md5(ini_content).hexdigest()
        match6 = " <-- MATCH!" if md5_ini == known_folder_md5 else ""
        print(f"6. MD5 of song.ini content:  {md5_ini}{match6}")

    # Test 7: MD5 of concatenated metadata
    if ini_data:
        metadata_str = f"{ini_data.get('name', '')}{ini_data.get('artist', '')}{ini_data.get('album', '')}"
        md5_metadata = hashlib.md5(metadata_str.encode('utf-8')).hexdigest()
        match7 = " <-- MATCH!" if md5_metadata == known_folder_md5 else ""
        print(f"7. MD5 of metadata concat:   {md5_metadata}{match7}")

    # Test 8: MD5 of all files in folder (sorted)
    all_files = sorted([f.name for f in song_folder.iterdir() if f.is_file()])
    files_str = ''.join(all_files)
    md5_files = hashlib.md5(files_str.encode('utf-8')).hexdigest()
    match8 = " <-- MATCH!" if md5_files == known_folder_md5 else ""
    print(f"8. MD5 of all filenames:     {md5_files}{match8}")

    # Test 9: MD5 of chart + ini combined
    if ini_file.exists():
        combined = chart_content + ini_content
        md5_combined = hashlib.md5(combined).hexdigest()
        match9 = " <-- MATCH!" if md5_combined == known_folder_md5 else ""
        print(f"9. MD5 of chart + ini:       {md5_combined}{match9}")

    print()
    print("="*70)


def main():
    mario_circuit_path = Path(r"D:\Games\Clone Hero\clonehero-win64\songs\Guitar Zero\ÿGuitar Zero Bonus Songs\Super Soul Bros - Mario Circuit")

    if not mario_circuit_path.exists():
        print(f"ERROR: Mario Circuit folder not found at {mario_circuit_path}")
        print("\nSearching for Mario Circuit...")

        songs_path = Path(r"D:\Games\Clone Hero\clonehero-win64\songs")
        import os

        for root, dirs, files in os.walk(songs_path):
            folder_name = Path(root).name.lower()
            if 'mario' in folder_name and 'circuit' in folder_name:
                mario_circuit_path = Path(root)
                print(f"Found: {mario_circuit_path}")
                break

    test_enchor_hashes(mario_circuit_path)


if __name__ == '__main__':
    main()

"""
Test hash calculation for Mario Circuit specifically
"""

import hashlib
import base64
import blake3
from pathlib import Path
from shared.parsers import parse_song_ini
from shared.console import print_success, print_info, print_error, print_warning


def find_mario_circuit(songs_path: Path):
    """Find Mario Circuit song in songs folder"""
    print_info(f"Searching for Mario Circuit...")

    import os

    for root, dirs, files in os.walk(songs_path):
        # Look for folder containing "mario" and "circuit"
        folder_name = Path(root).name.lower()

        if 'mario' in folder_name and 'circuit' in folder_name:
            # Check if it has a chart file
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if chart_files:
                chart_path = Path(root) / chart_files[0]
                print_success(f"Found: {root}")
                return Path(root), chart_path

    return None, None


def test_all_hashes(song_folder: Path, chart_file: Path):
    """Test all possible hash calculations"""

    print("\n" + "=" * 70)
    print("Testing all hash methods for Mario Circuit")
    print("=" * 70)
    print()

    # Known values
    known_scoredata = "d8c243cc0920e1aaed9c66b5f5274060"
    known_folder_md5 = "482e7ded1a1ac06c45f97fdba46baf55"
    known_chart_b64 = "fiz6NVJ7EYy2VRnEFg2v_afJ3-gCgRovyjTwtJv3I3U="

    # Try to decode base64 (might be URL-safe base64)
    known_chart_hex = None
    try:
        # Try URL-safe base64 first
        known_chart_bytes = base64.urlsafe_b64decode(known_chart_b64)
        known_chart_hex = known_chart_bytes.hex()
    except:
        try:
            # Try standard base64
            known_chart_bytes = base64.b64decode(known_chart_b64)
            known_chart_hex = known_chart_bytes.hex()
        except:
            known_chart_hex = "(decode failed)"

    print("Known hashes:")
    print(f"  scoredata.bin: {known_scoredata}")
    print(f"  Folder MD5:    {known_folder_md5}")
    print(f"  Chart (b64):   {known_chart_b64}")
    if known_chart_hex != "(decode failed)":
        print(f"  Chart (hex):   {known_chart_hex}")
    print()

    # Read chart file
    with open(chart_file, 'rb') as f:
        chart_content = f.read()

    print(f"Chart file: {chart_file}")
    print(f"Chart size: {len(chart_content)} bytes")
    print()

    # Calculate various hashes
    print("Calculated hashes:")
    print("-" * 70)

    # MD5 of chart file
    md5_chart = hashlib.md5(chart_content).hexdigest()
    match1 = "✓ MATCH!" if md5_chart == known_scoredata else ""
    match2 = "✓ MATCH!" if md5_chart == known_chart_hex else ""
    print(f"MD5 of chart file:     {md5_chart} {match1} {match2}")

    # MD5 of chart file (base64)
    md5_chart_b64 = base64.b64encode(hashlib.md5(chart_content).digest()).decode()
    match3 = "✓ MATCH!" if md5_chart_b64 == known_chart_b64 else ""
    print(f"MD5 chart (base64):    {md5_chart_b64} {match3}")

    # Blake3 of chart file (16 bytes)
    blake3_chart = blake3.blake3(chart_content).digest()[:16].hex()
    match4 = "✓ MATCH!" if blake3_chart == known_scoredata else ""
    print(f"Blake3 chart (16b):    {blake3_chart} {match4}")

    # Blake3 of chart file (32 bytes)
    blake3_chart_32 = blake3.blake3(chart_content).hexdigest()
    match5 = "✓ MATCH!" if blake3_chart_32 == known_scoredata else ""
    print(f"Blake3 chart (32b):    {blake3_chart_32[:32]} {match5}")

    print()

    # Now test with song.ini modifiers
    print("Testing with .ini modifiers:")
    print("-" * 70)

    ini_data = parse_song_ini(str(chart_file))

    if ini_data:
        print(f"Found song.ini data:")
        for key, value in list(ini_data.items())[:10]:
            print(f"  {key}: {value}")
        print()

        # Get the modifiers that affect hash
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

        # Test different combinations
        # Method 1: chart + concatenated values
        combined1 = chart_content + ''.join(str(v) for v in modifiers.values()).encode('utf-8')
        md5_combined1 = hashlib.md5(combined1).hexdigest()
        blake3_combined1 = blake3.blake3(combined1).digest()[:16].hex()

        match6 = "✓ MATCH!" if md5_combined1 == known_scoredata else ""
        match7 = "✓ MATCH!" if blake3_combined1 == known_scoredata else ""

        print(f"MD5 (chart + mods):    {md5_combined1} {match6}")
        print(f"Blake3 (chart + mods): {blake3_combined1} {match7}")

    else:
        print("No song.ini found")

    print()
    print("=" * 70)


def main():
    songs_path = Path(r"D:\Games\Clone Hero\clonehero-win64\songs")

    if not songs_path.exists():
        print_error(f"Songs path not found: {songs_path}")
        return

    song_folder, chart_file = find_mario_circuit(songs_path)

    if not song_folder:
        print_error("Mario Circuit not found!")
        print_info("Make sure the song folder name contains 'mario' and 'circuit'")
        return

    test_all_hashes(song_folder, chart_file)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

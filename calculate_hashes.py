"""
Calculate both Clone Hero and enchor.us hashes for chart files

Usage:
    python calculate_hashes.py <path_to_notes.chart>
"""

import sys
import hashlib
import base64
from pathlib import Path

try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False


def calculate_all_hashes(chart_path: Path):
    """Calculate all known hash types for a chart file"""

    if not chart_path.exists():
        print(f"ERROR: File not found: {chart_path}")
        return

    # Read chart content
    with open(chart_path, 'rb') as f:
        chart_content = f.read()

    print("="*70)
    print(f"Chart: {chart_path.name}")
    print(f"Size: {len(chart_content):,} bytes")
    print("="*70)
    print()

    # 1. Clone Hero hash (MD5)
    ch_hash = hashlib.md5(chart_content).hexdigest()
    print("Clone Hero Hash (scoredata.bin):")
    print(f"  MD5: {ch_hash}")
    print(f"  Short: [{ch_hash[:8]}]")
    print()

    # 2. enchor.us Chart Hash (Blake3)
    if HAS_BLAKE3:
        blake3_hash = blake3.blake3(chart_content).digest()
        blake3_hex = blake3_hash.hex()
        blake3_b64 = base64.urlsafe_b64encode(blake3_hash).decode()

        print("enchor.us Chart Hash:")
        print(f"  Blake3 (hex):    {blake3_hex}")
        print(f"  Blake3 (base64): {blake3_b64}")
    else:
        print("enchor.us Chart Hash:")
        print("  [blake3 not installed - run: pip install blake3]")

    print()
    print("="*70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python calculate_hashes.py <path_to_chart_file>")
        print()
        print("Examples:")
        print("  python calculate_hashes.py notes.chart")
        print("  python calculate_hashes.py \"D:/Songs/MySong/notes.mid\"")
        return

    chart_path = Path(sys.argv[1])
    calculate_all_hashes(chart_path)


if __name__ == '__main__':
    main()

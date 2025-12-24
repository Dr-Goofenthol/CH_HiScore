"""
Analyze scoredata_test1.bin to understand the hash structure
"""
import struct
from pathlib import Path

def analyze_scoredata(filepath):
    """Analyze the scoredata.bin file structure"""
    with open(filepath, 'rb') as f:
        # Read header
        header = f.read(4)
        print(f"Header: {header.hex()}")

        # Read song count
        song_count = struct.unpack('<I', f.read(4))[0]
        print(f"Song count: {song_count}")
        print()

        # Parse songs
        for song_num in range(song_count):
            print(f"=== Song {song_num + 1} ===")

            # Read the hash (16 bytes)
            hash_bytes = f.read(16)
            hash_hex = hash_bytes.hex()
            print(f"Hash (16 bytes): {hash_hex}")

            # Read instrument count
            instrument_count = struct.unpack('B', f.read(1))[0]
            print(f"Instrument count: {instrument_count}")

            # Read play count (3 bytes)
            play_count_bytes = f.read(3) + b'\x00'
            play_count = struct.unpack('<I', play_count_bytes)[0]
            print(f"Play count: {play_count}")

            # Parse instruments
            for inst_num in range(instrument_count):
                print(f"  Instrument {inst_num + 1}:")

                # Instrument ID (2 bytes)
                inst_id = struct.unpack('<H', f.read(2))[0]
                print(f"    ID: {inst_id}")

                # Difficulty (1 byte)
                diff = struct.unpack('B', f.read(1))[0]
                print(f"    Difficulty: {diff}")

                # Numerator/Denominator (2 bytes each)
                numerator = struct.unpack('<H', f.read(2))[0]
                denominator = struct.unpack('<H', f.read(2))[0]
                print(f"    Num/Denom: {numerator}/{denominator} = {numerator/denominator*100:.1f}%")

                # Stars (1 byte)
                stars = struct.unpack('B', f.read(1))[0]
                print(f"    Stars: {stars}")

                # Padding (4 bytes)
                padding = f.read(4)
                print(f"    Padding: {padding.hex()}")

                # Score (4 bytes)
                score = struct.unpack('<I', f.read(4))[0]
                print(f"    Score: {score:,}")
                print()

if __name__ == '__main__':
    analyze_scoredata('scoredata_test1.bin')

"""
Binary parsers for Clone Hero data files (scoredata.bin and songcache.bin)
"""

import struct
import os
import configparser
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ScoreEntry:
    """Represents a single score entry from Clone Hero"""
    chart_hash: str  # blake3 hash from Clone Hero
    instrument_id: int
    instrument_name: str
    difficulty: int
    difficulty_name: str
    completion_percent: float
    stars: int
    score: int
    play_count: int
    notes_hit: int = 0
    notes_total: int = 0


@dataclass
class SongMetadata:
    """Represents song metadata from songcache.bin"""
    chart_hash: str  # blake3 hash from Clone Hero
    title: str
    artist: str
    album: str
    genre: str
    year: str
    charter: str
    length_ms: int
    filepath: str


class ScoreDataParser:
    """Parser for Clone Hero's scoredata.bin file"""

    INSTRUMENT_NAMES = {
        0: "Lead Guitar",
        1: "Bass",
        2: "Rhythm",
        3: "Keys",
        4: "Drums",
        5: "GH Live Guitar",
        6: "GH Live Bass"
    }

    DIFFICULTY_NAMES = {
        0: "Easy",
        1: "Medium",
        2: "Hard",
        3: "Expert"
    }

    def __init__(self, filepath: str):
        self.filepath = filepath

    def parse(self) -> List[ScoreEntry]:
        """
        Parse the scoredata.bin file and return all score entries

        Returns:
            List of ScoreEntry objects
        """
        scores = []

        with open(self.filepath, 'rb') as f:
            # Read header (4 bytes)
            header = f.read(4)

            # Read number of songs (4 bytes, little-endian)
            song_count = struct.unpack('<I', f.read(4))[0]

            # Parse each song
            for _ in range(song_count):
                # Read chart hash (16 bytes, blake3)
                hash_bytes = f.read(16)
                chart_hash = hash_bytes.hex()

                # Read instrument count (1 byte)
                instrument_count = struct.unpack('B', f.read(1))[0]

                # Read play count (3 bytes, little-endian)
                play_count_bytes = f.read(3) + b'\x00'  # Pad to 4 bytes
                play_count = struct.unpack('<I', play_count_bytes)[0]

                # Parse each instrument
                for _ in range(instrument_count):
                    # Instrument ID (2 bytes, little-endian)
                    instrument_id = struct.unpack('<H', f.read(2))[0]

                    # Difficulty (1 byte)
                    difficulty = struct.unpack('B', f.read(1))[0]

                    # Completion percentage (numerator and denominator, 2 bytes each)
                    numerator = struct.unpack('<H', f.read(2))[0]
                    denominator = struct.unpack('<H', f.read(2))[0]
                    completion_percent = (numerator / denominator * 100) if denominator > 0 else 0

                    # Stars (1 byte)
                    stars = struct.unpack('B', f.read(1))[0]

                    # Padding (4 bytes, always 1)
                    padding = f.read(4)

                    # Score (4 bytes, little-endian)
                    score = struct.unpack('<I', f.read(4))[0]

                    # Create score entry
                    entry = ScoreEntry(
                        chart_hash=chart_hash,
                        instrument_id=instrument_id,
                        instrument_name=self.INSTRUMENT_NAMES.get(instrument_id, f"Unknown ({instrument_id})"),
                        difficulty=difficulty,
                        difficulty_name=self.DIFFICULTY_NAMES.get(difficulty, f"Unknown ({difficulty})"),
                        completion_percent=round(completion_percent, 2),
                        stars=stars,
                        score=score,
                        play_count=play_count,
                        notes_hit=numerator,
                        notes_total=denominator
                    )

                    scores.append(entry)

        return scores


class SongCacheParser:
    """Parser for Clone Hero's songcache.bin file"""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def _extract_title_from_path(self, filepath: str) -> str:
        """Extract song title from filepath"""
        if not filepath:
            return ""

        # Get filename without extension
        import os
        filename = os.path.basename(filepath)

        # Remove common extensions
        for ext in ['.sng', '.chart', '.mid', '.ini']:
            if filename.lower().endswith(ext):
                filename = filename[:-len(ext)]
                break

        # Title case the result
        return filename.title() if filename else ""

    def parse(self) -> Dict[str, SongMetadata]:
        """
        Parse the songcache.bin file and return song metadata indexed by chart hash

        Uses filepath extraction for reliable song names since lookup table
        indices can be misaligned.

        Returns:
            Dictionary mapping chart hash to SongMetadata
        """
        songs = {}

        with open(self.filepath, 'rb') as f:
            file_data = f.read()

        # Pattern: 0x0a "Clone Hero" 0x00 followed by 16-byte hash
        clone_hero_marker = b'\x0aClone Hero\x00'

        pos = 0
        while True:
            # Find next "Clone Hero" marker
            marker_pos = file_data.find(clone_hero_marker, pos)
            if marker_pos == -1:
                break

            # Chart hash is right after the marker
            hash_pos = marker_pos + len(clone_hero_marker)
            if hash_pos + 16 > len(file_data):
                break

            hash_bytes = file_data[hash_pos:hash_pos + 16]
            chart_hash = hash_bytes.hex()

            # Extract filepath from AFTER the hash
            # Filepath is stored as a variable-length string after the hash
            filepath = ""
            after_hash = file_data[hash_pos + 16:hash_pos + 16 + 500]

            # Look for filepath patterns (drive letter or path separators)
            for pattern in [b':\\', b'Songs\\', b'songs\\']:
                pattern_idx = after_hash.find(pattern)
                if pattern_idx != -1:
                    # Find start of path (look for drive letter)
                    start = pattern_idx
                    if pattern == b':\\':
                        start = max(0, pattern_idx - 1)  # Include drive letter

                    # Find end of path (look for .sng, .chart, etc or null byte)
                    end = len(after_hash)
                    for end_marker in [b'.sng', b'.chart', b'.mid']:
                        end_idx = after_hash.find(end_marker, start)
                        if end_idx != -1:
                            end = end_idx + len(end_marker)
                            break

                    # Also check for null terminator
                    null_idx = after_hash.find(b'\x00', start)
                    if null_idx != -1 and null_idx < end:
                        end = null_idx

                    try:
                        filepath = after_hash[start:end].decode('utf-8', errors='ignore')
                        break
                    except:
                        pass

            # Extract title from filepath
            title = self._extract_title_from_path(filepath)

            # Create metadata entry
            metadata = SongMetadata(
                chart_hash=chart_hash,
                title=title,
                artist="",  # Artist not reliably extractable from filepath
                album="",
                genre="",
                year="",
                charter="",
                length_ms=0,
                filepath=filepath
            )

            songs[chart_hash] = metadata

            pos = hash_pos + 16

        return songs


def parse_song_ini(chart_filepath: str) -> Optional[Dict[str, str]]:
    """
    Parse song.ini file from a Clone Hero song folder.

    Args:
        chart_filepath: Path to the chart file (notes.chart, notes.mid, etc.)

    Returns:
        Dictionary with song metadata (artist, name, album, etc.) or None if not found
    """
    if not chart_filepath:
        return None

    try:
        # Navigate to the song folder (parent of chart file)
        song_folder = os.path.dirname(chart_filepath)

        # Handle .sng files (single-file format) - no song.ini available
        if chart_filepath.lower().endswith('.sng'):
            return None

        # Look for song.ini in the song folder
        song_ini_path = os.path.join(song_folder, 'song.ini')

        if not os.path.exists(song_ini_path):
            # Try parent folder (some charts are nested)
            parent_folder = os.path.dirname(song_folder)
            song_ini_path = os.path.join(parent_folder, 'song.ini')

        if not os.path.exists(song_ini_path):
            return None

        # Parse the INI file
        config = configparser.ConfigParser(interpolation=None)
        # Handle case-insensitive section names
        config.read(song_ini_path, encoding='utf-8-sig')

        # Find the [Song] or [song] section
        song_section = None
        for section in config.sections():
            if section.lower() == 'song':
                song_section = section
                break

        if not song_section:
            return None

        # Extract metadata
        metadata = {}
        field_mappings = {
            'artist': ['artist', 'frets'],  # 'frets' is sometimes used for artist
            'name': ['name', 'title', 'song'],
            'album': ['album'],
            'genre': ['genre'],
            'year': ['year'],
            'charter': ['charter', 'frets', 'modchart'],
            'song_length': ['song_length'],
        }

        for key, possible_names in field_mappings.items():
            for name in possible_names:
                try:
                    value = config.get(song_section, name)
                    if value and value.strip():
                        metadata[key] = value.strip()
                        break
                except (configparser.NoOptionError, configparser.NoSectionError):
                    continue

        return metadata if metadata else None

    except Exception as e:
        # Silently fail - song.ini parsing is optional
        return None


def extract_artist_from_filepath(filepath: str) -> Optional[str]:
    """
    Try to extract artist name from filepath patterns.

    Common patterns:
    - "Artist - Song Title/notes.chart"
    - "Artist - Song Title (Charter)/notes.chart"

    Args:
        filepath: Path to the chart file

    Returns:
        Artist name if pattern matched, None otherwise
    """
    if not filepath:
        return None

    try:
        # Get the song folder name
        folder = os.path.dirname(filepath)
        folder_name = os.path.basename(folder)

        # Try "Artist - Title" pattern
        if ' - ' in folder_name:
            parts = folder_name.split(' - ', 1)
            artist = parts[0].strip()

            # Validate: artist shouldn't be too short or look like a number
            if len(artist) >= 2 and not artist.isdigit():
                return artist

        return None

    except Exception:
        return None


def get_artist_for_song(chart_filepath: str) -> Optional[str]:
    """
    Get artist for a song using the hybrid approach:
    1. First try parsing song.ini
    2. Fall back to filepath pattern extraction

    Args:
        chart_filepath: Path to the chart file

    Returns:
        Artist name if found, None otherwise
    """
    # Method 1: Parse song.ini (most reliable)
    ini_data = parse_song_ini(chart_filepath)
    if ini_data and ini_data.get('artist'):
        return ini_data['artist']

    # Method 2: Extract from filepath pattern
    filepath_artist = extract_artist_from_filepath(chart_filepath)
    if filepath_artist:
        return filepath_artist

    return None


def get_scores_with_metadata(scoredata_path: str, songcache_path: str = None) -> List[Dict]:
    """
    Parse both scoredata.bin and songcache.bin and combine them

    Args:
        scoredata_path: Path to scoredata.bin
        songcache_path: Path to songcache.bin (optional)

    Returns:
        List of dictionaries containing complete score information with metadata
    """
    # Parse score file
    score_parser = ScoreDataParser(scoredata_path)
    scores = score_parser.parse()

    # Try to parse song cache (if provided and parsing succeeds)
    songs = {}
    if songcache_path:
        try:
            cache_parser = SongCacheParser(songcache_path)
            songs = cache_parser.parse()
        except Exception as e:
            # Songcache parsing failed, continue with just chart hashes
            print(f"Warning: Could not parse songcache.bin: {e}")
            songs = {}

    # Combine data
    combined = []
    for score in scores:
        metadata = songs.get(score.chart_hash)

        # Use short hash as fallback display name
        short_hash = score.chart_hash[:8]

        entry = {
            'chart_hash': score.chart_hash,
            'instrument': score.instrument_name,
            'instrument_id': score.instrument_id,
            'difficulty': score.difficulty_name,
            'difficulty_id': score.difficulty,
            'score': score.score,
            'completion_percent': score.completion_percent,
            'stars': score.stars,
            'play_count': score.play_count,
            'title': metadata.title if metadata else f'[{short_hash}]',
            'artist': metadata.artist if metadata else '',
            'album': metadata.album if metadata else '',
            'charter': metadata.charter if metadata else '',
            'length_ms': metadata.length_ms if metadata else 0,
        }

        combined.append(entry)

    return combined

"""
Chart File Parser for Clone Hero

Parses .chart and .mid/.midi files to extract detailed chart information
including note counts, difficulty metrics, and gameplay data.

Supported formats:
- .chart (text-based format)
- .mid/.midi (MIDI format)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import IntEnum


class Instrument(IntEnum):
    """Instrument identifiers matching Clone Hero/scoredata.bin"""
    LEAD = 0
    BASS = 1
    RHYTHM = 2
    KEYS = 3
    DRUMS = 4
    GHL_LEAD = 5
    GHL_BASS = 6


class Difficulty(IntEnum):
    """Difficulty identifiers matching Clone Hero/scoredata.bin"""
    EASY = 0
    MEDIUM = 1
    HARD = 2
    EXPERT = 3


class NoteType(IntEnum):
    """Note type classifications"""
    NORMAL = 0  # Regular strum note
    HOPO = 1    # Hammer-on/pull-off
    TAP = 2     # Tap note
    OPEN = 3    # Open note (no frets)


@dataclass
class Note:
    """Individual note data"""
    timestamp: int      # Tick/millisecond position
    fret: int          # Fret number (0-4 for 5-fret, 0-2 for GHL)
    duration: int      # Note sustain length
    note_type: NoteType = NoteType.NORMAL
    is_chord: bool = False  # Part of a multi-note chord


@dataclass
class StarPowerPhrase:
    """Star power phrase data"""
    start_tick: int
    end_tick: int
    duration: int


@dataclass
class PracticeSection:
    """Practice mode section marker"""
    start_tick: int
    name: str


@dataclass
class InstrumentDifficultyData:
    """Data for a specific instrument/difficulty combination"""
    instrument: Instrument
    difficulty: Difficulty
    notes: List[Note] = field(default_factory=list)
    total_notes: int = 0
    chord_count: int = 0
    hopo_count: int = 0
    tap_count: int = 0
    open_note_count: int = 0
    star_power_phrases: List[StarPowerPhrase] = field(default_factory=list)

    def calculate_stats(self):
        """Calculate derived statistics"""
        self.total_notes = len(self.notes)
        self.chord_count = sum(1 for n in self.notes if n.is_chord)
        self.hopo_count = sum(1 for n in self.notes if n.note_type == NoteType.HOPO)
        self.tap_count = sum(1 for n in self.notes if n.note_type == NoteType.TAP)
        self.open_note_count = sum(1 for n in self.notes if n.note_type == NoteType.OPEN)


@dataclass
class ChartData:
    """Complete parsed chart data"""
    chart_path: Path
    song_name: str = ""
    artist: str = ""
    charter: str = ""
    album: str = ""
    year: str = ""
    genre: str = ""

    # Timing information
    resolution: int = 192  # Ticks per beat (default for .chart)
    tempo_map: List[Tuple[int, int]] = field(default_factory=list)  # (tick, BPM * 1000)
    time_signatures: List[Tuple[int, int, int]] = field(default_factory=list)  # (tick, numerator, denominator)

    # Song metadata
    song_length_ms: int = 0  # Calculated from last note
    preview_start_ms: int = 0
    preview_end_ms: int = 0

    # Chart data by instrument/difficulty
    instruments: Dict[Tuple[Instrument, Difficulty], InstrumentDifficultyData] = field(default_factory=dict)

    # Global events
    practice_sections: List[PracticeSection] = field(default_factory=list)

    # Calculated metrics
    average_note_density: float = 0.0  # Notes per second across all difficulties
    peak_note_density: float = 0.0     # Highest NPS in any 5-second window

    def get_instrument_data(self, instrument: Instrument, difficulty: Difficulty) -> Optional[InstrumentDifficultyData]:
        """Get data for specific instrument/difficulty"""
        return self.instruments.get((instrument, difficulty))

    def calculate_note_density(self, instrument: Instrument, difficulty: Difficulty) -> float:
        """Calculate notes per second for a specific chart"""
        data = self.get_instrument_data(instrument, difficulty)
        if not data or not data.notes or self.song_length_ms == 0:
            return 0.0

        return (data.total_notes / self.song_length_ms) * 1000


class ChartParser:
    """Parser for .chart files (text-based format)"""

    # .chart section name mappings to instrument/difficulty
    SECTION_MAPPING = {
        # 5-fret guitar/bass
        'EasySingle': (Instrument.LEAD, Difficulty.EASY),
        'MediumSingle': (Instrument.LEAD, Difficulty.MEDIUM),
        'HardSingle': (Instrument.LEAD, Difficulty.HARD),
        'ExpertSingle': (Instrument.LEAD, Difficulty.EXPERT),

        'EasyDoubleBass': (Instrument.BASS, Difficulty.EASY),
        'MediumDoubleBass': (Instrument.BASS, Difficulty.MEDIUM),
        'HardDoubleBass': (Instrument.BASS, Difficulty.HARD),
        'ExpertDoubleBass': (Instrument.BASS, Difficulty.EXPERT),

        'EasyDoubleRhythm': (Instrument.RHYTHM, Difficulty.EASY),
        'MediumDoubleRhythm': (Instrument.RHYTHM, Difficulty.MEDIUM),
        'HardDoubleRhythm': (Instrument.RHYTHM, Difficulty.HARD),
        'ExpertDoubleRhythm': (Instrument.RHYTHM, Difficulty.EXPERT),

        'EasyKeyboard': (Instrument.KEYS, Difficulty.EASY),
        'MediumKeyboard': (Instrument.KEYS, Difficulty.MEDIUM),
        'HardKeyboard': (Instrument.KEYS, Difficulty.HARD),
        'ExpertKeyboard': (Instrument.KEYS, Difficulty.EXPERT),

        'EasyDrums': (Instrument.DRUMS, Difficulty.EASY),
        'MediumDrums': (Instrument.DRUMS, Difficulty.MEDIUM),
        'HardDrums': (Instrument.DRUMS, Difficulty.HARD),
        'ExpertDrums': (Instrument.DRUMS, Difficulty.EXPERT),

        # GHL
        'EasyGHLGuitar': (Instrument.GHL_LEAD, Difficulty.EASY),
        'MediumGHLGuitar': (Instrument.GHL_LEAD, Difficulty.MEDIUM),
        'HardGHLGuitar': (Instrument.GHL_LEAD, Difficulty.HARD),
        'ExpertGHLGuitar': (Instrument.GHL_LEAD, Difficulty.EXPERT),

        'EasyGHLBass': (Instrument.GHL_BASS, Difficulty.EASY),
        'MediumGHLBass': (Instrument.GHL_BASS, Difficulty.MEDIUM),
        'HardGHLBass': (Instrument.GHL_BASS, Difficulty.HARD),
        'ExpertGHLBass': (Instrument.GHL_BASS, Difficulty.EXPERT),
    }

    def __init__(self, chart_path: Path):
        self.chart_path = chart_path
        self.data = ChartData(chart_path=chart_path)

    def parse(self) -> ChartData:
        """Parse the .chart file and return complete data"""
        if not self.chart_path.exists():
            raise FileNotFoundError(f"Chart file not found: {self.chart_path}")

        with open(self.chart_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Parse into sections
        sections = self._split_into_sections(content)

        # Parse each section
        for section_name, section_content in sections.items():
            if section_name == 'Song':
                self._parse_song_section(section_content)
            elif section_name == 'SyncTrack':
                self._parse_sync_track(section_content)
            elif section_name == 'Events':
                self._parse_events(section_content)
            elif section_name in self.SECTION_MAPPING:
                instrument, difficulty = self.SECTION_MAPPING[section_name]
                self._parse_instrument_section(section_content, instrument, difficulty)

        # Calculate song length and other metrics
        self._calculate_metrics()

        return self.data

    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """Split .chart file into named sections"""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            line = line.strip()

            # Section header: [SectionName]
            if line.startswith('[') and line.endswith(']'):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)

                # Start new section
                current_section = line[1:-1]
                current_content = []
            elif current_section and line:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def _parse_song_section(self, content: str):
        """Parse [Song] section for metadata"""
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('{') or line.startswith('}'):
                continue

            # Format: key = "value" or key = value
            match = re.match(r'(\w+)\s*=\s*"?([^"]+)"?', line)
            if match:
                key, value = match.groups()
                value = value.strip('"').strip()

                if key == 'Name':
                    self.data.song_name = value
                elif key == 'Artist':
                    self.data.artist = value
                elif key == 'Charter':
                    self.data.charter = value
                elif key == 'Album':
                    self.data.album = value
                elif key == 'Year':
                    self.data.year = value
                elif key == 'Genre':
                    self.data.genre = value
                elif key == 'Resolution':
                    self.data.resolution = int(value)
                elif key == 'PreviewStart':
                    self.data.preview_start_ms = int(float(value) * 1000)
                elif key == 'PreviewEnd':
                    self.data.preview_end_ms = int(float(value) * 1000)

    def _parse_sync_track(self, content: str):
        """Parse [SyncTrack] section for tempo and time signature"""
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('{') or line.startswith('}'):
                continue

            # Format: tick = EVENT value
            match = re.match(r'(\d+)\s*=\s*(\w+)\s+(\d+)', line)
            if match:
                tick, event, value = match.groups()
                tick = int(tick)
                value = int(value)

                if event == 'B':  # BPM change
                    self.data.tempo_map.append((tick, value))  # Value is BPM * 1000
                elif event == 'TS':  # Time signature
                    # Value encodes time signature (upper byte = numerator)
                    numerator = value
                    self.data.time_signatures.append((tick, numerator, 4))  # Assume /4

    def _parse_events(self, content: str):
        """Parse [Events] section for practice sections and other markers"""
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('{') or line.startswith('}'):
                continue

            # Format: tick = E "event_text"
            match = re.match(r'(\d+)\s*=\s*E\s+"([^"]+)"', line)
            if match:
                tick, event_text = match.groups()
                tick = int(tick)

                # Practice sections start with "section"
                if event_text.startswith('section '):
                    section_name = event_text[8:]  # Remove "section " prefix
                    self.data.practice_sections.append(
                        PracticeSection(start_tick=tick, name=section_name)
                    )

    def _parse_instrument_section(self, content: str, instrument: Instrument, difficulty: Difficulty):
        """Parse instrument/difficulty section for notes and star power"""
        key = (instrument, difficulty)
        if key not in self.data.instruments:
            self.data.instruments[key] = InstrumentDifficultyData(
                instrument=instrument,
                difficulty=difficulty
            )

        inst_data = self.data.instruments[key]
        notes_by_tick = {}  # Group notes by timestamp to detect chords

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('{') or line.startswith('}'):
                continue

            # Format: tick = TYPE note_number duration
            match = re.match(r'(\d+)\s*=\s*(\w+)\s+(\d+)(?:\s+(\d+))?', line)
            if match:
                tick, event_type, note_num, duration = match.groups()
                tick = int(tick)
                note_num = int(note_num)
                duration = int(duration) if duration else 0

                if event_type == 'N':  # Note
                    # Note numbers 0-4 = frets, 5 = forced, 6 = tap, 7 = open
                    fret = note_num % 8
                    note_type = NoteType.NORMAL

                    if fret == 7:  # Open note
                        note_type = NoteType.OPEN
                        fret = 0
                    elif fret == 6:  # Tap note
                        note_type = NoteType.TAP
                        fret = note_num - 6
                    elif fret == 5:  # Forced strum
                        fret = note_num - 5

                    note = Note(
                        timestamp=tick,
                        fret=fret,
                        duration=duration,
                        note_type=note_type
                    )

                    # Track notes by tick to detect chords
                    if tick not in notes_by_tick:
                        notes_by_tick[tick] = []
                    notes_by_tick[tick].append(note)

                    inst_data.notes.append(note)

                elif event_type == 'S':  # Special event (star power)
                    if note_num == 2:  # Star power phrase
                        inst_data.star_power_phrases.append(
                            StarPowerPhrase(
                                start_tick=tick,
                                end_tick=tick + duration,
                                duration=duration
                            )
                        )

        # Mark chords
        for tick, notes_at_tick in notes_by_tick.items():
            if len(notes_at_tick) > 1:
                for note in notes_at_tick:
                    note.is_chord = True

        # Calculate statistics
        inst_data.calculate_stats()


class MidiParser:
    """Parser for .mid/.midi files (MIDI format)"""

    def __init__(self, midi_path: Path):
        self.midi_path = midi_path
        self.data = ChartData(chart_path=midi_path)

    # MIDI note mappings for Clone Hero (Rock Band / Guitar Hero format)
    # Format: {instrument_track_name: {note_number: (instrument, difficulty, fret)}}
    NOTE_MAPPINGS = {
        'PART GUITAR': Instrument.LEAD,
        'PART BASS': Instrument.BASS,
        'PART RHYTHM': Instrument.RHYTHM,
        'PART KEYS': Instrument.KEYS,
        'PART DRUMS': Instrument.DRUMS,
    }

    # Difficulty ranges for guitar/bass/rhythm/keys
    # Format: note_number -> (difficulty, fret_number)
    GUITAR_NOTE_MAP = {
        # Expert (96-100)
        96: (Difficulty.EXPERT, 0),  # Green
        97: (Difficulty.EXPERT, 1),  # Red
        98: (Difficulty.EXPERT, 2),  # Yellow
        99: (Difficulty.EXPERT, 3),  # Blue
        100: (Difficulty.EXPERT, 4), # Orange
        # Hard (84-88)
        84: (Difficulty.HARD, 0),
        85: (Difficulty.HARD, 1),
        86: (Difficulty.HARD, 2),
        87: (Difficulty.HARD, 3),
        88: (Difficulty.HARD, 4),
        # Medium (72-76)
        72: (Difficulty.MEDIUM, 0),
        73: (Difficulty.MEDIUM, 1),
        74: (Difficulty.MEDIUM, 2),
        75: (Difficulty.MEDIUM, 3),
        76: (Difficulty.MEDIUM, 4),
        # Easy (60-64)
        60: (Difficulty.EASY, 0),
        61: (Difficulty.EASY, 1),
        62: (Difficulty.EASY, 2),
        63: (Difficulty.EASY, 3),
        64: (Difficulty.EASY, 4),
    }

    # Drums have different mappings (shared across difficulties, difficulty encoded separately)
    DRUM_NOTE_MAP = {
        # Expert drums (96-100, 110)
        96: (Difficulty.EXPERT, 0),  # Kick
        97: (Difficulty.EXPERT, 1),  # Red
        98: (Difficulty.EXPERT, 2),  # Yellow
        99: (Difficulty.EXPERT, 3),  # Blue
        100: (Difficulty.EXPERT, 4), # Green (tom)
        110: (Difficulty.EXPERT, 5), # Orange (cymbal)
        # Hard (84-88, 98)
        84: (Difficulty.HARD, 0),
        85: (Difficulty.HARD, 1),
        86: (Difficulty.HARD, 2),
        87: (Difficulty.HARD, 3),
        88: (Difficulty.HARD, 4),
        # Medium (72-76)
        72: (Difficulty.MEDIUM, 0),
        73: (Difficulty.MEDIUM, 1),
        74: (Difficulty.MEDIUM, 2),
        75: (Difficulty.MEDIUM, 3),
        76: (Difficulty.MEDIUM, 4),
        # Easy (60-64)
        60: (Difficulty.EASY, 0),
        61: (Difficulty.EASY, 1),
        62: (Difficulty.EASY, 2),
        63: (Difficulty.EASY, 3),
        64: (Difficulty.EASY, 4),
    }

    def parse(self) -> ChartData:
        """Parse the MIDI file and return complete data"""
        try:
            import mido
        except ImportError:
            raise ImportError(
                "mido library required for MIDI parsing. Install with: pip install mido"
            )

        if not self.midi_path.exists():
            raise FileNotFoundError(f"MIDI file not found: {self.midi_path}")

        # Load MIDI file with clip=True to handle out-of-range data bytes
        midi_file = mido.MidiFile(self.midi_path, clip=True)

        # Store resolution (ticks per beat)
        self.data.resolution = midi_file.ticks_per_beat

        # Parse each track
        for track in midi_file.tracks:
            track_name = None
            current_time = 0
            note_starts = {}  # Track note start times: {note_number: (tick, velocity)}

            # First pass: get track name
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                    break

            # Handle special tracks
            if track_name == 'EVENTS':
                self._parse_events_track(track)
                continue

            # Parse tempo events from all tracks (usually in track 0)
            current_time = 0
            for msg in track:
                current_time += msg.time
                if msg.type == 'set_tempo':
                    # Tempo change (convert from microseconds per beat to BPM * 1000)
                    # MIDI tempo is in microseconds per quarter note
                    # BPM = 60,000,000 / microseconds_per_beat
                    bpm = 60_000_000 / msg.tempo if msg.tempo > 0 else 120
                    bpm_times_1000 = int(bpm * 1000)
                    self.data.tempo_map.append((current_time, bpm_times_1000))

            # Skip non-instrument tracks
            if track_name not in self.NOTE_MAPPINGS:
                continue

            instrument = self.NOTE_MAPPINGS[track_name]

            # Second pass: parse notes
            current_time = 0
            for msg in track:
                current_time += msg.time

                if msg.type == 'note_on' and msg.velocity > 0:
                    # Note start
                    note_starts[msg.note] = current_time
                elif msg.type in ['note_off', 'note_on']:  # note_on with velocity=0 is also note_off
                    # Note end
                    if msg.note in note_starts:
                        start_time = note_starts[msg.note]
                        duration = current_time - start_time
                        del note_starts[msg.note]

                        # Map note number to difficulty and fret
                        if instrument == Instrument.DRUMS:
                            note_map = self.DRUM_NOTE_MAP
                        else:
                            note_map = self.GUITAR_NOTE_MAP

                        if msg.note in note_map:
                            difficulty, fret = note_map[msg.note]

                            # Get or create instrument data
                            key = (instrument, difficulty)
                            if key not in self.data.instruments:
                                self.data.instruments[key] = InstrumentDifficultyData(
                                    instrument=instrument,
                                    difficulty=difficulty
                                )

                            inst_data = self.data.instruments[key]

                            # Create note
                            note = Note(
                                timestamp=start_time,
                                fret=fret,
                                duration=duration,
                                note_type=NoteType.NORMAL,  # Will detect HOPO/tap later
                                is_chord=False  # Will detect chords after all notes loaded
                            )
                            inst_data.notes.append(note)

        # Post-processing: detect chords, calculate totals
        self._post_process()

        # Calculate song length and metrics
        _calculate_metrics_for_chart(self.data)

        return self.data

    def _parse_events_track(self, track):
        """Parse EVENTS track for practice sections"""
        import re
        current_time = 0

        for msg in track:
            current_time += msg.time

            if msg.type == 'text':
                # Practice sections format: [section Section Name]
                match = re.match(r'\[section\s+(.+)\]', msg.text, re.IGNORECASE)
                if match:
                    section_name = match.group(1)
                    self.data.practice_sections.append(
                        PracticeSection(name=section_name, start_tick=current_time)
                    )

    def _post_process(self):
        """Post-process parsed data: detect chords, calculate metrics"""
        for inst_data in self.data.instruments.values():
            # Sort notes by timestamp
            inst_data.notes.sort(key=lambda n: (n.timestamp, n.fret))

            # Detect chords (notes at same timestamp)
            i = 0
            while i < len(inst_data.notes):
                current_time = inst_data.notes[i].timestamp
                chord_notes = [inst_data.notes[i]]

                # Look ahead for notes at same time
                j = i + 1
                while j < len(inst_data.notes) and inst_data.notes[j].timestamp == current_time:
                    chord_notes.append(inst_data.notes[j])
                    j += 1

                # Mark as chord if 2+ notes at same time
                if len(chord_notes) > 1:
                    for note in chord_notes:
                        note.is_chord = True
                    inst_data.chord_count += 1

                i = j if j > i else i + 1

            # Calculate totals
            inst_data.total_notes = len(inst_data.notes)


def parse_chart_file(chart_path: Path) -> Optional[ChartData]:
    """
    Parse a chart file (auto-detects .chart or .mid format)

    Args:
        chart_path: Path to chart file

    Returns:
        ChartData object with parsed information, or None if parsing fails
    """
    try:
        if chart_path.suffix.lower() == '.chart':
            parser = ChartParser(chart_path)
            return parser.parse()
        elif chart_path.suffix.lower() in ['.mid', '.midi']:
            parser = MidiParser(chart_path)
            return parser.parse()
        else:
            print(f"Unsupported chart format: {chart_path.suffix}")
            return None

    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}"
        print(f"Error parsing chart file {chart_path}: {error_msg}")
        # Uncomment for debugging:
        # import traceback
        # traceback.print_exc()
        return None


# Helper function to calculate metrics after parsing
def _calculate_metrics_for_chart(chart_data: ChartData):
    """Calculate derived metrics like song length, note density, etc."""
    # Find the last note timestamp across all instruments/difficulties
    max_timestamp = 0

    for inst_data in chart_data.instruments.values():
        if inst_data.notes:
            last_note = max(inst_data.notes, key=lambda n: n.timestamp)
            max_timestamp = max(max_timestamp, last_note.timestamp + last_note.duration)

    # Convert ticks to milliseconds using tempo map (handle variable tempo)
    if chart_data.tempo_map and max_timestamp > 0:
        ticks_per_beat = chart_data.resolution if chart_data.resolution > 0 else 192

        if ticks_per_beat > 0:
            # Calculate duration by iterating through tempo changes
            total_ms = 0.0
            current_tick = 0

            # Sort tempo map by tick position
            sorted_tempo = sorted(chart_data.tempo_map, key=lambda x: x[0])

            for i, (tempo_tick, bpm_times_1000) in enumerate(sorted_tempo):
                # Find the next tempo change (or end of song)
                if i + 1 < len(sorted_tempo):
                    next_tick = sorted_tempo[i + 1][0]
                else:
                    next_tick = max_timestamp

                # Calculate time in this tempo section
                if tempo_tick < next_tick:
                    ticks_in_section = min(next_tick, max_timestamp) - max(tempo_tick, current_tick)
                    if ticks_in_section > 0:
                        bpm = bpm_times_1000 / 1000.0
                        if bpm > 0:
                            beats_in_section = ticks_in_section / ticks_per_beat
                            minutes_in_section = beats_in_section / bpm
                            total_ms += minutes_in_section * 60 * 1000

                    current_tick = max(current_tick, next_tick)
                    if current_tick >= max_timestamp:
                        break

            chart_data.song_length_ms = int(total_ms)

    # Calculate average note density (across all charts)
    total_notes = sum(inst_data.total_notes for inst_data in chart_data.instruments.values())
    num_charts = len(chart_data.instruments)

    if num_charts > 0 and chart_data.song_length_ms > 0:
        avg_notes_per_chart = total_notes / num_charts
        chart_data.average_note_density = (avg_notes_per_chart / chart_data.song_length_ms) * 1000


# Monkey-patch the _calculate_metrics method
ChartParser._calculate_metrics = lambda self: _calculate_metrics_for_chart(self.data)


if __name__ == '__main__':
    """Test the parser on a sample chart file"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chart_parser.py <path_to_chart_file>")
        sys.exit(1)

    chart_path = Path(sys.argv[1])
    chart_data = parse_chart_file(chart_path)

    if chart_data:
        print(f"\n{'='*60}")
        print(f"Chart: {chart_data.song_name}")
        print(f"Artist: {chart_data.artist}")
        print(f"Charter: {chart_data.charter}")
        print(f"{'='*60}\n")

        print(f"Song Length: {chart_data.song_length_ms / 1000:.2f} seconds")
        print(f"Resolution: {chart_data.resolution} ticks per beat")
        print(f"Practice Sections: {len(chart_data.practice_sections)}")
        print()

        for (instrument, difficulty), inst_data in sorted(chart_data.instruments.items()):
            inst_name = instrument.name
            diff_name = difficulty.name
            density = chart_data.calculate_note_density(instrument, difficulty)

            print(f"{inst_name} {diff_name}:")
            print(f"  Total Notes: {inst_data.total_notes}")
            print(f"  Chords: {inst_data.chord_count}")
            print(f"  HOPOs: {inst_data.hopo_count}")
            print(f"  Taps: {inst_data.tap_count}")
            print(f"  Open Notes: {inst_data.open_note_count}")
            print(f"  Star Power: {len(inst_data.star_power_phrases)} phrases")
            print(f"  Note Density: {density:.2f} NPS")
            print()

"""
File watcher for Clone Hero scoredata.bin

Monitors the scoredata.bin file for changes and detects new scores.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

import sys
sys.path.append(str(Path(__file__).parent.parent))
from shared.parsers import ScoreDataParser


class ScoreState:
    """Tracks the state of scores to detect new or improved ones"""

    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.known_scores: Dict[str, int] = {}  # key -> score value
        self.load_state()

    def _score_key(self, chart_hash: str, instrument_id: int, difficulty: int) -> str:
        """Generate unique key for a score"""
        return f"{chart_hash}:{instrument_id}:{difficulty}"

    def load_state(self):
        """Load known scores from state file"""
        self.needs_migration = False
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Handle both old format (list) and new format (dict with scores)
                    if 'score_values' in data:
                        self.known_scores = data['score_values']
                    elif 'known_scores' in data:
                        # Old format detected - mark for migration
                        # We'll re-initialize from scoredata.bin to get actual values
                        self.known_scores = {}
                        self.needs_migration = True
                        print("[*] Old state format detected, will re-sync with current scores")
                    else:
                        self.known_scores = {}
                if not self.needs_migration:
                    print(f"[+] Loaded {len(self.known_scores)} known scores from state file")
            except Exception as e:
                print(f"[!] Could not load state file: {e}")
                self.known_scores = {}
        else:
            print("[+] No existing state file, starting fresh")

    def save_state(self):
        """Save known scores to state file"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({
                    'score_values': self.known_scores,
                    'last_updated': time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"[!] Could not save state file: {e}")

    def is_new_or_improved_score(self, chart_hash: str, instrument_id: int, difficulty: int, score: int) -> bool:
        """
        Check if this score should be submitted

        Returns True if:
        - We've never seen this chart/instrument/difficulty combo, OR
        - The score is higher than what we've seen before
        """
        key = self._score_key(chart_hash, instrument_id, difficulty)
        if key not in self.known_scores:
            return True
        # Submit if score has improved
        return score > self.known_scores[key]

    def mark_score_seen(self, chart_hash: str, instrument_id: int, difficulty: int, score: int):
        """Mark a score as seen with its value"""
        key = self._score_key(chart_hash, instrument_id, difficulty)
        self.known_scores[key] = score
        self.save_state()

    def initialize_from_scores(self, scores: List):
        """Initialize state from existing scores (on first run)"""
        for score in scores:
            key = self._score_key(score.chart_hash, score.instrument_id, score.difficulty)
            self.known_scores[key] = score.score
        self.save_state()
        print(f"[+] Initialized state with {len(self.known_scores)} scores")


class ScoreFileHandler(FileSystemEventHandler):
    """Handles file system events for scoredata.bin"""

    def __init__(self, scoredata_path: Path, state: ScoreState, on_new_score: Callable):
        self.scoredata_path = scoredata_path
        self.state = state
        self.on_new_score = on_new_score
        self.last_check = 0
        self.debounce_seconds = 2  # Wait 2 seconds after last change before processing
        self.previous_scores_snapshot: Dict[str, int] = {}  # Track previous parse to detect changes
        self.first_check = True  # Flag to skip detailed feedback on first parse

    def on_modified(self, event):
        """Called when scoredata.bin is modified"""
        if not isinstance(event, FileModifiedEvent):
            return

        # Check if it's our target file
        if Path(event.src_path).resolve() != self.scoredata_path.resolve():
            return

        # Debounce: wait a bit to ensure file writing is complete
        current_time = time.time()
        if current_time - self.last_check < self.debounce_seconds:
            return

        self.last_check = current_time
        print(f"\n[*] Detected change in scoredata.bin at {time.strftime('%H:%M:%S')}")

        # Wait a moment for file to finish writing
        time.sleep(0.5)

        # Parse the updated scores
        self.check_for_new_scores()

    def check_for_new_scores(self):
        """Parse scoredata.bin and check for new or improved scores"""
        try:
            parser = ScoreDataParser(str(self.scoredata_path))
            scores = parser.parse()

            # Build current snapshot: key -> score value
            current_snapshot = {}
            for score in scores:
                key = self.state._score_key(score.chart_hash, score.instrument_id, score.difficulty)
                current_snapshot[key] = score.score

            # Find what changed by comparing to previous snapshot
            changed_scores = []
            for score in scores:
                key = self.state._score_key(score.chart_hash, score.instrument_id, score.difficulty)
                # Score changed if: not in previous snapshot OR value different from previous
                if key not in self.previous_scores_snapshot or self.previous_scores_snapshot[key] != score.score:
                    changed_scores.append(score)

            # Separate changed scores into improved vs non-improved
            new_scores = []
            failed_improvements = []

            for score in changed_scores:
                if self.state.is_new_or_improved_score(score.chart_hash, score.instrument_id,
                                                       score.difficulty, score.score):
                    new_scores.append(score)
                    self.state.mark_score_seen(score.chart_hash, score.instrument_id,
                                              score.difficulty, score.score)
                else:
                    # Score changed but didn't improve - track for feedback
                    failed_improvements.append(score)

            # Show feedback for improved scores (existing behavior)
            if new_scores:
                print(f"[+] Found {len(new_scores)} new/improved score(s)!")
                for score in new_scores:
                    self.on_new_score(score)

            # Show detailed feedback for scores that didn't improve
            elif failed_improvements:
                # Skip detailed feedback on first check (would show all existing scores)
                if self.first_check:
                    print("[-] No new scores detected")
                else:
                    print(f"[-] Score updated but did not improve personal best:")
                    print()
                    for score in failed_improvements:
                        # Get personal best from state
                        key = self.state._score_key(score.chart_hash, score.instrument_id, score.difficulty)
                        pb_score = self.state.known_scores.get(key, 0)

                        if pb_score > 0:
                            diff = score.score - pb_score
                            diff_pct = (diff / pb_score * 100) if pb_score > 0 else 0

                            print(f"    Chart: [{score.chart_hash[:8]}...] ({score.difficulty_name} {score.instrument_name})")
                            print(f"    Your Score: {score.score:,} pts")
                            print(f"    Personal Best: {pb_score:,} pts")
                            print(f"    Difference: {diff:,} pts ({diff_pct:+.1f}%)")
                            print()
                        else:
                            # Edge case: changed but PB is 0 (shouldn't happen)
                            print(f"    Chart: [{score.chart_hash[:8]}...] ({score.difficulty_name} {score.instrument_name})")
                            print(f"    Score: {score.score:,} pts (replay or same score)")
                            print()

            # No changes at all (file modified but scores identical)
            elif not changed_scores:
                if not self.first_check:
                    print("[-] No score changes detected (file modified but scores unchanged)")

            # Update snapshot for next comparison
            self.previous_scores_snapshot = current_snapshot

            # Mark first check as complete
            if self.first_check:
                self.first_check = False

        except Exception as e:
            print(f"[!] Error checking for new scores: {e}")


class CloneHeroWatcher:
    """Main watcher class for monitoring Clone Hero scores"""

    def __init__(self, clone_hero_dir: str, state_file: str, on_new_score: Callable):
        """
        Initialize the Clone Hero score watcher

        Args:
            clone_hero_dir: Path to Clone Hero data directory
            state_file: Path to state file for tracking seen scores
            on_new_score: Callback function called with new ScoreEntry objects
        """
        self.clone_hero_dir = Path(clone_hero_dir)
        self.scoredata_path = self.clone_hero_dir / 'scoredata.bin'
        self.state = ScoreState(state_file)
        self.on_new_score = on_new_score
        self.observer = None

        if not self.scoredata_path.exists():
            raise FileNotFoundError(f"scoredata.bin not found at {self.scoredata_path}")

    def needs_state_migration(self):
        """Check if state file needs migration from old format"""
        return getattr(self.state, 'needs_migration', False)

    def initialize_state(self, silent=False):
        """Initialize state with existing scores (call this on first run or migration)"""
        if not silent:
            print("[*] Initializing state with existing scores...")
        try:
            parser = ScoreDataParser(str(self.scoredata_path))
            scores = parser.parse()
            self.state.initialize_from_scores(scores)
            if silent:
                print(f"[+] State migrated: now tracking {len(self.state.known_scores)} scores")
        except Exception as e:
            print(f"[!] Could not initialize state: {e}")

    def catch_up_scan(self):
        """
        Scan for scores that were made while the tracker was not running.
        Compares current scoredata.bin against saved state and submits any
        new or improved scores.
        """
        print("[*] Scanning for scores made while tracker was offline...")
        try:
            parser = ScoreDataParser(str(self.scoredata_path))
            scores = parser.parse()

            new_scores = []
            for score in scores:
                if self.state.is_new_or_improved_score(score.chart_hash, score.instrument_id,
                                                       score.difficulty, score.score):
                    new_scores.append(score)
                    self.state.mark_score_seen(score.chart_hash, score.instrument_id,
                                              score.difficulty, score.score)

            if new_scores:
                print(f"[+] Found {len(new_scores)} score(s) from offline play!")
                for score in new_scores:
                    self.on_new_score(score)
            else:
                print("[+] No new offline scores detected")

        except Exception as e:
            print(f"[!] Error during catch-up scan: {e}")

    def start(self):
        """Start watching for score changes"""
        print(f"[*] Starting Clone Hero score watcher...")
        print(f"[*] Monitoring: {self.scoredata_path}")
        print(f"[*] Tracking {len(self.state.known_scores)} known scores")

        event_handler = ScoreFileHandler(
            self.scoredata_path,
            self.state,
            self.on_new_score
        )

        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.clone_hero_dir), recursive=False)
        self.observer.start()

        print("[+] Watcher started! Play some Clone Hero to test it.")
        print("[*] Press Ctrl+C to stop\n")

    def stop(self):
        """Stop watching"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("\n[*] Watcher stopped")

    def run_forever(self):
        """Start watching and run until interrupted"""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

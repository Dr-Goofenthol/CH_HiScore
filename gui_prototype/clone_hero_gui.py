"""
Clone Hero High Score Client - GUI Version (Prototype)

Modern GUI interface using CustomTkinter for the score tracker.
"""

VERSION = "2.4.11-GUI-PROTOTYPE"

import os
import sys
import json
import time
import threading
import configparser
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: CustomTkinter not installed!")
    print("Install with: pip install customtkinter")
    sys.exit(1)

import requests
from client.file_watcher import CloneHeroWatcher
from shared.parsers import SongCacheParser

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

# Default configuration
DEFAULT_BOT_URL = "http://localhost:8080"


class ScoreTrackerGUI(ctk.CTk):
    """Main GUI window for Clone Hero Score Tracker"""

    def __init__(self):
        super().__init__()

        # Configure window
        self.title(f"Clone Hero Score Tracker v{VERSION}")
        self.geometry("700x600")
        self.minsize(600, 500)

        # Initialize state
        self.watcher = None
        self.is_connected = False
        self.is_initialized = False
        self.auth_token = None
        self.ch_dir = None
        self.song_cache = {}
        self.tracked_scores = 0

        # Activity log
        self.activity_log = []
        self.max_log_entries = 100

        # Song info cache (for currentsong.txt polling)
        self.cached_song_info = {
            'title': None,
            'artist': None,
            'charter': None,
            'last_updated': None
        }
        self.song_cache_running = False
        self.song_cache_thread = None

        # Current song display update
        self.current_song_data = None
        self.show_final_score = False  # Flag to prevent polling from overwriting score display

        # Create UI
        self.create_widgets()

        # Start initialization in background
        self.after(100, self.initialize_tracker)

    def create_widgets(self):
        """Create all GUI widgets"""

        # Main container with padding
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ==================== HEADER ====================
        self.header_frame = ctk.CTkFrame(self.main_container)
        self.header_frame.pack(fill="x", pady=(0, 10))

        # Title
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Clone Hero Score Tracker",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=10)

        # Status indicator
        self.status_frame = ctk.CTkFrame(self.header_frame)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.status_indicator.pack(side="left", padx=(10, 5))

        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Starting up...",
            font=ctk.CTkFont(size=12)
        )
        self.status_text.pack(side="left")

        self.tracking_label = ctk.CTkLabel(
            self.status_frame,
            text="Tracking: 0 scores",
            font=ctk.CTkFont(size=12)
        )
        self.tracking_label.pack(side="right", padx=10)

        # ==================== CURRENT SONG CARD ====================
        self.song_card = ctk.CTkFrame(self.main_container)
        self.song_card.pack(fill="x", pady=(0, 10))

        self.song_card_title = ctk.CTkLabel(
            self.song_card,
            text="Current Song",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.song_card_title.pack(pady=(10, 5))

        self.song_info_frame = ctk.CTkFrame(self.song_card)
        self.song_info_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.song_title_label = ctk.CTkLabel(
            self.song_info_frame,
            text="🎸 No song playing",
            font=ctk.CTkFont(size=13)
        )
        self.song_title_label.pack(anchor="w", padx=10, pady=2)

        self.song_artist_label = ctk.CTkLabel(
            self.song_info_frame,
            text="🎤 --",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.song_artist_label.pack(anchor="w", padx=10, pady=2)

        self.song_details_label = ctk.CTkLabel(
            self.song_info_frame,
            text="⭐ --",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.song_details_label.pack(anchor="w", padx=10, pady=2)

        self.song_score_label = ctk.CTkLabel(
            self.song_info_frame,
            text="💯 Score: --",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.song_score_label.pack(anchor="w", padx=10, pady=2)

        # ==================== ACTIVITY LOG ====================
        self.log_frame = ctk.CTkFrame(self.main_container)
        self.log_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.log_title.pack(pady=(10, 5))

        # Scrollable text box for activity log
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont(size=11),
            wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

        # ==================== BUTTON BAR ====================
        self.button_frame = ctk.CTkFrame(self.main_container)
        self.button_frame.pack(fill="x")

        self.resync_button = ctk.CTkButton(
            self.button_frame,
            text="Resync",
            command=self.on_resync,
            width=100
        )
        self.resync_button.pack(side="left", padx=5, pady=5)

        self.settings_button = ctk.CTkButton(
            self.button_frame,
            text="Settings",
            command=self.on_settings,
            width=100
        )
        self.settings_button.pack(side="left", padx=5, pady=5)

        self.minimize_button = ctk.CTkButton(
            self.button_frame,
            text="Minimize to Tray",
            command=self.on_minimize,
            width=120
        )
        self.minimize_button.pack(side="right", padx=5, pady=5)

    def log_activity(self, message: str, level: str = "info"):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Add to internal log
        self.activity_log.append({
            "time": timestamp,
            "message": message,
            "level": level
        })

        # Trim log if too long
        if len(self.activity_log) > self.max_log_entries:
            self.activity_log.pop(0)

        # Update textbox
        self.log_textbox.configure(state="normal")

        # Color coding based on level
        if level == "success":
            prefix = "✓"
            color = "green"
        elif level == "error":
            prefix = "✗"
            color = "red"
        elif level == "warning":
            prefix = "⚠"
            color = "orange"
        else:
            prefix = "•"
            color = None

        log_line = f"[{timestamp}] {prefix} {message}\n"

        self.log_textbox.insert("end", log_line)
        if color:
            # CustomTkinter doesn't support text tags like tkinter, so we keep it simple
            pass

        self.log_textbox.see("end")  # Auto-scroll to bottom
        self.log_textbox.configure(state="disabled")

    def update_status(self, connected: bool, message: str):
        """Update connection status indicator"""
        self.is_connected = connected

        if connected:
            self.status_indicator.configure(text_color="green")
            self.status_text.configure(text=message)
        else:
            self.status_indicator.configure(text_color="red")
            self.status_text.configure(text=message)

    def update_tracking_count(self, count: int):
        """Update tracked scores count"""
        self.tracked_scores = count
        self.tracking_label.configure(text=f"Tracking: {count} scores")

    def update_current_song(self, score_data, in_progress=False):
        """Update current song display

        Args:
            score_data: Dict with song info
            in_progress: If True, song is being played (not a completed score)
        """
        song_title = score_data.get('song_title', 'Unknown Song')
        song_artist = score_data.get('song_artist', '--')
        instrument = score_data.get('instrument_name', 'Unknown')
        difficulty = score_data.get('difficulty_name', 'Unknown')
        score = score_data.get('score', 0)

        self.song_title_label.configure(text=f"🎸 {song_title}")
        self.song_artist_label.configure(text=f"🎤 {song_artist}")

        if in_progress:
            # Song is being played
            self.song_details_label.configure(text=f"⭐ {instrument}")
            self.song_score_label.configure(text=f"💯 In progress...")
        else:
            # Score completed
            self.song_details_label.configure(text=f"⭐ {difficulty} {instrument}")
            self.song_score_label.configure(text=f"💯 Score: {score:,}")

    def initialize_tracker(self):
        """Initialize the score tracker (runs in background thread)"""
        self.log_activity("Initializing tracker...", "info")

        # Load configuration
        config = self.load_config()
        settings = self.load_settings()

        # Check bot connection
        bot_url = settings.get('bot_url', DEFAULT_BOT_URL)
        self.log_activity(f"Connecting to server: {bot_url}", "info")

        try:
            response = requests.get(f"{bot_url}/health", timeout=5)
            if response.status_code == 200:
                self.update_status(True, f"Connected to {bot_url}")
                self.log_activity("Connected to bot server!", "success")
            else:
                self.update_status(False, "Server connection failed")
                self.log_activity(f"Server error: HTTP {response.status_code}", "error")
                return
        except requests.exceptions.ConnectionError:
            self.update_status(False, "Could not connect to server")
            self.log_activity("Connection failed - is the bot running?", "error")
            return
        except Exception as e:
            self.update_status(False, "Connection error")
            self.log_activity(f"Connection error: {e}", "error")
            return

        # Check authentication
        self.auth_token = config.get('auth_token')
        if not self.auth_token:
            self.log_activity("Not paired with Discord account", "warning")
            self.log_activity("Use Settings to pair with Discord", "info")
            return
        else:
            self.log_activity("Authentication token found", "success")

        # Find Clone Hero directory
        self.ch_dir = self.find_clone_hero_directory()
        if not self.ch_dir:
            self.log_activity("Clone Hero directory not found", "error")
            self.log_activity("Install Clone Hero or set path in Settings", "warning")
            return

        self.log_activity(f"Found Clone Hero: {self.ch_dir}", "success")

        # Load song cache
        songcache_path = self.ch_dir / 'songcache.bin'
        if songcache_path.exists():
            try:
                parser = SongCacheParser(str(songcache_path))
                self.song_cache = parser.parse()
                self.log_activity(f"Loaded {len(self.song_cache)} songs from cache", "success")
            except Exception as e:
                self.log_activity(f"Could not load song cache: {e}", "warning")

        # Check Clone Hero settings for song export
        self.check_clone_hero_settings()

        # Start file watcher
        self.start_watcher()

    def check_clone_hero_settings(self):
        """Check Clone Hero settings.ini for required flags"""
        ch_docs = self.get_clone_hero_documents_dir()
        if not ch_docs:
            self.log_activity("⚠ Clone Hero Documents folder not found", "warning")
            return

        settings_path = ch_docs / 'settings.ini'
        if not settings_path.exists():
            self.log_activity("⚠ Clone Hero settings.ini not found", "warning")
            self.log_activity("  Run Clone Hero at least once", "info")
            return

        try:
            config = configparser.ConfigParser()
            config.read(str(settings_path))

            # Check song_export in [streamer] section
            if config.has_option('streamer', 'song_export'):
                song_export = config.get('streamer', 'song_export')
                if song_export != '1':
                    self.log_activity("⚠ IMPORTANT: Song Export is DISABLED in Clone Hero!", "warning")
                    self.log_activity("  Enable it: Settings > Gameplay > Streamer Settings", "warning")
                    self.log_activity("  > Export Current Song (turn ON)", "warning")
                    self.log_activity("  Without this, song names won't display!", "warning")
                else:
                    self.log_activity("✓ Song Export enabled", "success")
            else:
                self.log_activity("⚠ Song Export setting not found in settings.ini", "warning")

        except Exception as e:
            self.log_activity(f"Could not read settings.ini: {e}", "warning")

    def get_clone_hero_documents_dir(self):
        """Get the Clone Hero Documents directory (for settings.ini, currentsong.txt, etc.)"""
        if sys.platform == 'win32':
            docs_path = Path.home() / 'Documents' / 'Clone Hero'
            if docs_path.exists():
                return docs_path
        elif sys.platform == 'darwin':
            # Mac - same as data directory
            mac_path = Path.home() / 'Library' / 'Application Support' / 'com.srylain.CloneHero'
            if mac_path.exists():
                return mac_path
        else:
            # Linux
            linux_path = Path.home() / '.clonehero'
            if linux_path.exists():
                return linux_path
        return None

    def read_current_song(self):
        """
        Read the currentsong.txt file for authoritative song metadata.
        Returns cached values if file is empty (Clone Hero clears it after song ends).
        """
        result = {
            'title': None,
            'artist': None,
            'charter': None
        }

        ch_docs = self.get_clone_hero_documents_dir()
        if not ch_docs:
            if self.cached_song_info['title']:
                return dict(self.cached_song_info)
            return result

        currentsong_path = ch_docs / 'currentsong.txt'
        if not currentsong_path.exists():
            if self.cached_song_info['title']:
                return dict(self.cached_song_info)
            return result

        try:
            with open(currentsong_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Format: Line 1 = Title, Line 2 = Artist, Line 3 = Charter
            if len(lines) >= 1 and lines[0].strip():
                result['title'] = lines[0].strip()
            if len(lines) >= 2 and lines[1].strip():
                result['artist'] = lines[1].strip()
            if len(lines) >= 3 and lines[2].strip():
                result['charter'] = lines[2].strip()

            # Cache the values if we got valid data
            if result['title']:
                self.cached_song_info['title'] = result['title']
                self.cached_song_info['artist'] = result['artist']
                self.cached_song_info['charter'] = result['charter']
                self.cached_song_info['last_updated'] = time.time()
            elif self.cached_song_info['title']:
                # File is empty but we have cached data - use it
                return {
                    'title': self.cached_song_info['title'],
                    'artist': self.cached_song_info['artist'],
                    'charter': self.cached_song_info['charter']
                }

        except Exception:
            # Return cached info if available
            if self.cached_song_info['title']:
                return dict(self.cached_song_info)

        return result

    def start_song_cache_polling(self):
        """
        Start a background thread that periodically polls currentsong.txt
        to keep the cache updated while a song is playing, and updates the GUI.
        """
        def poll_currentsong():
            while self.song_cache_running:
                try:
                    ch_docs = self.get_clone_hero_documents_dir()
                    if ch_docs:
                        currentsong_path = ch_docs / 'currentsong.txt'
                        if currentsong_path.exists():
                            with open(currentsong_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()

                            # Only cache if we have valid data
                            if len(lines) >= 1 and lines[0].strip():
                                title = lines[0].strip()
                                artist = lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None
                                charter = lines[2].strip() if len(lines) >= 3 and lines[2].strip() else None

                                # Update cache
                                self.cached_song_info['title'] = title
                                self.cached_song_info['artist'] = artist
                                self.cached_song_info['charter'] = charter
                                self.cached_song_info['last_updated'] = time.time()

                                # Update GUI display only if not showing final score
                                if not self.show_final_score:
                                    song_data = {
                                        'song_title': title,
                                        'song_artist': artist or '--',
                                        'instrument_name': 'Playing...',
                                        'difficulty_name': '',
                                        'score': 0
                                    }
                                    self.after(0, lambda sd=song_data: self.update_current_song(sd, in_progress=True))
                            else:
                                # File is empty - song ended or not playing
                                # Don't clear the display, keep showing last song
                                pass
                except Exception:
                    pass

                time.sleep(1)  # Poll every second

        self.song_cache_running = True
        self.song_cache_thread = threading.Thread(target=poll_currentsong, daemon=True)
        self.song_cache_thread.start()

    def stop_song_cache_polling(self):
        """Stop the background song cache polling thread"""
        self.song_cache_running = False

    def clear_song_cache(self):
        """Clear the cached song info after a score is processed"""
        self.cached_song_info = {
            'title': None,
            'artist': None,
            'charter': None,
            'last_updated': None
        }

    def start_watcher(self):
        """Start the file watcher in background thread"""
        if not self.ch_dir or not self.auth_token:
            return

        state_file = self.ch_dir / '.score_tracker_state.json'

        def on_new_score(score):
            """Callback when new score detected"""
            # Debug logging
            self.after(0, lambda: self.log_activity(
                f"Score detected: {score.score:,} on {score.difficulty_name} {score.instrument_name}",
                "info"
            ))

            # Read currentsong.txt for metadata (authoritative source)
            current_song = self.read_current_song()

            # Update UI from score data
            song_data = {
                'song_title': f"[{score.chart_hash[:8]}]",  # Fallback to hash
                'song_artist': '',
                'instrument_name': score.instrument_name,
                'difficulty_name': score.difficulty_name,
                'score': score.score
            }

            # Use currentsong.txt data if available
            if current_song['title']:
                song_data['song_title'] = current_song['title']
                song_data['song_artist'] = current_song['artist'] or ''
            # Otherwise try songcache.bin
            elif score.chart_hash in self.song_cache:
                song_info = self.song_cache[score.chart_hash]
                song_data['song_title'] = song_info.get('title', song_data['song_title'])
                song_data['song_artist'] = song_info.get('artist', '')

            # Store final song data for display updates
            final_song_data = song_data.copy()

            # Set flag to prevent polling thread from overwriting score display
            self.show_final_score = True

            # Update UI (must be done in main thread)
            def update_ui_with_score():
                self.update_current_song(final_song_data, in_progress=False)
                self.log_activity(
                    f"New score: {final_song_data['song_title']} - {final_song_data['score']:,}",
                    "info"
                )
                # Clear flag after 10 seconds to allow new song to update
                self.after(10000, lambda: setattr(self, 'show_final_score', False))

            self.after(0, update_ui_with_score)

            # Submit to bot API
            self.submit_score_to_api(score, song_data)

            # Clear song cache after processing
            self.clear_song_cache()

        try:
            self.watcher = CloneHeroWatcher(
                clone_hero_dir=str(self.ch_dir),
                state_file=str(state_file),
                on_new_score=on_new_score
            )

            # Initialize or load state
            if not state_file.exists():
                self.log_activity("First run - initializing state", "info")
                self.watcher.initialize_state()
            else:
                self.watcher.catch_up_scan()

            # Update tracking count
            self.update_tracking_count(len(self.watcher.state.known_scores))

            # Start watching
            self.watcher.start()
            self.log_activity("Score monitoring started!", "success")

            # Start background polling of currentsong.txt for live updates
            self.start_song_cache_polling()
            self.log_activity("Song tracking started!", "success")

            # Mark as fully initialized
            self.is_initialized = True

        except Exception as e:
            self.log_activity(f"Failed to start watcher: {e}", "error")
            import traceback
            self.log_activity(f"Traceback: {traceback.format_exc()}", "error")

    def submit_score_to_api(self, score, song_data):
        """Submit score to bot API"""
        settings = self.load_settings()
        bot_url = settings.get('bot_url', DEFAULT_BOT_URL)

        payload = {
            "auth_token": self.auth_token,
            "chart_hash": score.chart_hash,
            "instrument_id": score.instrument_id,
            "difficulty_id": score.difficulty,
            "score": score.score,
            "completion_percent": score.completion_percent,
            "stars": score.stars,
            "song_title": song_data['song_title'],
            "song_artist": song_data['song_artist'],
            "score_type": "raw"
        }

        try:
            response = requests.post(
                f"{bot_url}/api/score",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('is_record_broken'):
                    self.after(0, lambda: self.log_activity(
                        "🎉 RECORD BROKEN! Check Discord!",
                        "success"
                    ))
                    if result.get('previous_score'):
                        diff = score.score - result['previous_score']
                        self.after(0, lambda d=diff: self.log_activity(
                            f"   Beat previous by {d:,} points!",
                            "success"
                        ))
                elif result.get('is_high_score'):
                    self.after(0, lambda: self.log_activity(
                        "New personal best!",
                        "success"
                    ))
                else:
                    self.after(0, lambda: self.log_activity(
                        "Score submitted (not a new high score)",
                        "info"
                    ))
            else:
                status_code = response.status_code
                self.after(0, lambda sc=status_code: self.log_activity(
                    f"Failed to submit score: HTTP {sc}",
                    "error"
                ))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self.log_activity(
                f"Error submitting score: {msg}",
                "error"
            ))

    # ==================== CONFIG MANAGEMENT ====================

    def find_clone_hero_directory(self):
        """Find Clone Hero data directory"""
        if sys.platform == 'win32':
            localow = Path(os.environ['USERPROFILE']) / 'AppData' / 'LocalLow' / 'srylain Inc_' / 'Clone Hero'
            if localow.exists():
                return localow
        elif sys.platform == 'darwin':
            mac_path = Path.home() / 'Library' / 'Application Support' / 'com.srylain.CloneHero'
            if mac_path.exists():
                return mac_path
        else:
            linux_path = Path.home() / '.config' / 'unity3d' / 'srylain Inc_' / 'Clone Hero'
            if linux_path.exists():
                return linux_path
        return None

    def get_config_path(self):
        """Get config file path"""
        ch_dir = self.find_clone_hero_directory()
        if ch_dir:
            return ch_dir / '.score_tracker_config.json'
        return Path.home() / '.clone_hero_tracker_config.json'

    def get_settings_path(self):
        """Get settings file path"""
        ch_dir = self.find_clone_hero_directory()
        if ch_dir:
            return ch_dir / '.score_tracker_settings.json'
        return Path.home() / '.clone_hero_tracker_settings.json'

    def load_config(self):
        """Load client configuration"""
        config_path = self.get_config_path()
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def load_settings(self):
        """Load user settings"""
        settings_path = self.get_settings_path()
        default_settings = {
            'bot_url': DEFAULT_BOT_URL,
            'clone_hero_path': None,
            'minimize_to_tray': False,
            'start_with_windows': False
        }

        if settings_path and settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    saved = json.load(f)
                    default_settings.update(saved)
            except:
                pass

        return default_settings

    # ==================== BUTTON HANDLERS ====================

    def on_resync(self):
        """Handle Resync button click"""
        if not self.is_initialized:
            self.log_activity("Tracker not fully initialized yet", "warning")
            return

        self.log_activity("Starting resync scan...", "info")
        if self.watcher:
            def do_resync():
                self.watcher.catch_up_scan()
                # Update count on main thread after scan completes
                count = len(self.watcher.state.known_scores)
                self.after(0, lambda c=count: self.update_tracking_count(c))
                self.after(0, lambda: self.log_activity("Resync complete!", "success"))

            threading.Thread(target=do_resync, daemon=True).start()
        else:
            self.log_activity("Watcher not initialized", "warning")

    def on_settings(self):
        """Handle Settings button click"""
        # TODO: Open settings dialog
        self.log_activity("Settings dialog not yet implemented", "info")

    def on_minimize(self):
        """Handle Minimize to Tray button click"""
        # TODO: Implement system tray
        self.log_activity("Minimize to tray not yet implemented", "info")
        self.iconify()  # For now, just minimize to taskbar

    def on_closing(self):
        """Handle window close event"""
        # Stop all background threads
        self.stop_song_cache_polling()
        if self.watcher:
            self.watcher.stop()
        self.destroy()


def main():
    """Main entry point"""
    app = ScoreTrackerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == '__main__':
    main()

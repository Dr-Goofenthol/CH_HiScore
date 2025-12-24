"""
Clone Hero High Score Client - GUI Version (Prototype v2)

Modern, compact GUI interface with settings and system tray support.
"""

VERSION = "2.4.11-GUI-PROTOTYPE-V2"

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
    import pystray
    from pystray import MenuItem as item
except ImportError as e:
    print(f"ERROR: Required package not installed: {e}")
    print("Install with: pip install customtkinter pillow pystray")
    sys.exit(1)

import requests
from client.file_watcher import CloneHeroWatcher
from shared.parsers import SongCacheParser

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Default configuration
DEFAULT_BOT_URL = "http://localhost:8080"


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog window"""

    def __init__(self, parent, current_settings):
        super().__init__(parent)

        self.parent = parent
        self.settings = current_settings.copy()
        self.result = None

        # Configure window
        self.title("Settings")
        self.geometry("500x400")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def create_widgets(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Bot URL
        ctk.CTkLabel(main_frame, text="Bot Server URL:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        self.bot_url_entry = ctk.CTkEntry(main_frame, width=400)
        self.bot_url_entry.pack(fill="x", pady=(0, 15))
        self.bot_url_entry.insert(0, self.settings.get('bot_url', DEFAULT_BOT_URL))

        # Clone Hero Path (optional)
        ctk.CTkLabel(main_frame, text="Clone Hero Path (optional):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        path_frame = ctk.CTkFrame(main_frame)
        path_frame.pack(fill="x", pady=(0, 15))

        self.ch_path_entry = ctk.CTkEntry(path_frame, width=320)
        self.ch_path_entry.pack(side="left", padx=(0, 10))
        self.ch_path_entry.insert(0, self.settings.get('clone_hero_path', '') or '')

        browse_btn = ctk.CTkButton(path_frame, text="Browse", width=70, command=self.browse_ch_path)
        browse_btn.pack(side="left")

        # Options
        ctk.CTkLabel(main_frame, text="Options:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))

        self.minimize_to_tray_var = ctk.BooleanVar(value=self.settings.get('minimize_to_tray', True))
        minimize_check = ctk.CTkCheckBox(main_frame, text="Minimize to system tray on close", variable=self.minimize_to_tray_var)
        minimize_check.pack(anchor="w", pady=5)

        self.start_with_windows_var = ctk.BooleanVar(value=self.settings.get('start_with_windows', False))
        startup_check = ctk.CTkCheckBox(main_frame, text="Start with Windows", variable=self.start_with_windows_var)
        startup_check.pack(anchor="w", pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))

        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", width=100, command=self.cancel)
        cancel_btn.pack(side="right", padx=(10, 0))

        save_btn = ctk.CTkButton(button_frame, text="Save", width=100, command=self.save)
        save_btn.pack(side="right")

    def browse_ch_path(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Clone Hero Directory")
        if path:
            self.ch_path_entry.delete(0, "end")
            self.ch_path_entry.insert(0, path)

    def save(self):
        self.result = {
            'bot_url': self.bot_url_entry.get().strip(),
            'clone_hero_path': self.ch_path_entry.get().strip() or None,
            'minimize_to_tray': self.minimize_to_tray_var.get(),
            'start_with_windows': self.start_with_windows_var.get()
        }
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class ScoreTrackerGUI(ctk.CTk):
    """Main GUI window for Clone Hero Score Tracker"""

    def __init__(self):
        super().__init__()

        # Configure window - more compact but tall enough for all content
        self.title(f"Clone Hero Score Tracker v{VERSION}")
        self.geometry("600x520")
        self.minsize(550, 500)

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

        # Song info cache
        self.cached_song_info = {
            'title': None,
            'artist': None,
            'charter': None,
            'last_updated': None
        }
        self.song_cache_running = False
        self.song_cache_thread = None

        # Current song display
        self.current_song_data = None
        self.show_final_score = False
        self.score_display_time = None  # Track when score was displayed

        # System tray
        self.tray_icon = None
        self.is_hidden = False

        # Create UI
        self.create_widgets()

        # Setup system tray
        self.setup_tray()

        # Start initialization in background
        self.after(100, self.initialize_tracker)

    def create_widgets(self):
        """Create all GUI widgets - more compact layout"""

        # Main container with less padding
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # ==================== HEADER ====================
        header_frame = ctk.CTkFrame(self.main_container)
        header_frame.pack(fill="x", pady=(0, 8))

        # Title - smaller
        title_label = ctk.CTkLabel(
            header_frame,
            text="Clone Hero Score Tracker",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=5)

        # Status indicator - more compact
        status_frame = ctk.CTkFrame(header_frame)
        status_frame.pack(fill="x", padx=8, pady=(0, 5))

        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.status_indicator.pack(side="left", padx=(5, 3))

        self.status_text = ctk.CTkLabel(
            status_frame,
            text="Starting up...",
            font=ctk.CTkFont(size=11)
        )
        self.status_text.pack(side="left")

        self.tracking_label = ctk.CTkLabel(
            status_frame,
            text="Tracking: 0 scores",
            font=ctk.CTkFont(size=11)
        )
        self.tracking_label.pack(side="right", padx=5)

        # ==================== CURRENT SONG CARD ====================
        song_card = ctk.CTkFrame(self.main_container)
        song_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            song_card,
            text="Current Song",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 3))

        song_info_frame = ctk.CTkFrame(song_card)
        song_info_frame.pack(fill="x", padx=8, pady=(0, 5))

        self.song_title_label = ctk.CTkLabel(
            song_info_frame,
            text="🎸 No song playing",
            font=ctk.CTkFont(size=11)
        )
        self.song_title_label.pack(anchor="w", padx=8, pady=1)

        self.song_artist_label = ctk.CTkLabel(
            song_info_frame,
            text="🎤 --",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.song_artist_label.pack(anchor="w", padx=8, pady=1)

        self.song_details_label = ctk.CTkLabel(
            song_info_frame,
            text="⭐ --",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.song_details_label.pack(anchor="w", padx=8, pady=1)

        self.song_score_label = ctk.CTkLabel(
            song_info_frame,
            text="💯 Score: --",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.song_score_label.pack(anchor="w", padx=8, pady=1)

        # ==================== ACTIVITY LOG ====================
        log_frame = ctk.CTkFrame(self.main_container)
        log_frame.pack(fill="both", expand=True, pady=(0, 8))

        ctk.CTkLabel(
            log_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 3))

        # Scrollable text box - more compact
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(size=10),
            wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 5))
        self.log_textbox.configure(state="disabled")

        # ==================== BUTTON BAR ====================
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x")

        self.resync_button = ctk.CTkButton(
            button_frame,
            text="Resync",
            command=self.on_resync,
            width=80,
            height=28
        )
        self.resync_button.pack(side="left", padx=3, pady=3)

        self.settings_button = ctk.CTkButton(
            button_frame,
            text="Settings",
            command=self.on_settings,
            width=80,
            height=28
        )
        self.settings_button.pack(side="left", padx=3, pady=3)

        self.hide_button = ctk.CTkButton(
            button_frame,
            text="Hide",
            command=self.hide_to_tray,
            width=80,
            height=28
        )
        self.hide_button.pack(side="right", padx=3, pady=3)

    def setup_tray(self):
        """Setup system tray icon"""
        # Create icon image
        image = Image.new('RGB', (64, 64), color='#1f538d')
        dc = ImageDraw.Draw(image)
        dc.rectangle([16, 16, 48, 48], fill='white')

        # Create menu
        menu = pystray.Menu(
            item('Show', self.show_from_tray, default=True),
            item('Settings', self.on_settings),
            item('Resync', self.on_resync),
            pystray.Menu.SEPARATOR,
            item('Quit', self.quit_app)
        )

        # Create tray icon
        self.tray_icon = pystray.Icon(
            "clone_hero_tracker",
            image,
            "Clone Hero Score Tracker",
            menu
        )

    def hide_to_tray(self):
        """Hide window to system tray"""
        self.withdraw()
        self.is_hidden = True
        if self.tray_icon and not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self):
        """Show window from system tray"""
        self.deiconify()
        self.lift()
        self.focus_force()
        self.is_hidden = False

    def quit_app(self):
        """Quit application from tray"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.on_closing()

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

        # Prefix based on level
        if level == "success":
            prefix = "✓"
        elif level == "error":
            prefix = "✗"
        elif level == "warning":
            prefix = "⚠"
        else:
            prefix = "•"

        log_line = f"[{timestamp}] {prefix} {message}\n"

        self.log_textbox.insert("end", log_line)
        self.log_textbox.see("end")
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

    def update_current_song(self, song_data, in_progress=False):
        """Update current song display"""
        song_title = song_data.get('song_title', 'Unknown Song')
        song_artist = song_data.get('song_artist', '--')
        instrument = song_data.get('instrument_name', 'Unknown')
        difficulty = song_data.get('difficulty_name', 'Unknown')
        score = song_data.get('score', 0)

        self.song_title_label.configure(text=f"🎸 {song_title}")
        self.song_artist_label.configure(text=f"🎤 {song_artist}")

        if in_progress:
            self.song_details_label.configure(text=f"⭐ {instrument}")
            self.song_score_label.configure(text=f"💯 In progress...")
        else:
            self.song_details_label.configure(text=f"⭐ {difficulty} {instrument}")
            self.song_score_label.configure(text=f"💯 Score: {score:,}")
            # Record when score was displayed
            self.score_display_time = time.time()

    def initialize_tracker(self):
        """Initialize the score tracker"""
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
                self.update_status(True, f"Connected")
                self.log_activity("Connected to bot server!", "success")
            else:
                self.update_status(False, "Server error")
                self.log_activity(f"Server error: HTTP {response.status_code}", "error")
                return
        except requests.exceptions.ConnectionError:
            self.update_status(False, "Disconnected")
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
            self.log_activity("Use CLI version to pair first", "info")
            return
        else:
            self.log_activity("Authentication token found", "success")

        # Find Clone Hero directory
        self.ch_dir = self.find_clone_hero_directory(settings.get('clone_hero_path'))
        if not self.ch_dir:
            self.log_activity("Clone Hero directory not found", "error")
            self.log_activity("Install Clone Hero or set path in Settings", "warning")
            return

        self.log_activity(f"Found Clone Hero", "success")

        # Load song cache
        songcache_path = self.ch_dir / 'songcache.bin'
        if songcache_path.exists():
            try:
                parser = SongCacheParser(str(songcache_path))
                self.song_cache = parser.parse()
                self.log_activity(f"Loaded {len(self.song_cache)} songs", "success")
            except Exception as e:
                self.log_activity(f"Could not load song cache: {e}", "warning")

        # Check Clone Hero settings
        self.check_clone_hero_settings()

        # Start file watcher
        self.start_watcher()

    def check_clone_hero_settings(self):
        """Check Clone Hero settings.ini for required flags"""
        ch_docs = self.get_clone_hero_documents_dir()
        if not ch_docs:
            return

        settings_path = ch_docs / 'settings.ini'
        if not settings_path.exists():
            return

        try:
            config = configparser.ConfigParser()
            config.read(str(settings_path))

            if config.has_option('streamer', 'song_export'):
                song_export = config.get('streamer', 'song_export')
                if song_export != '1':
                    self.log_activity("⚠ Song Export is DISABLED!", "warning")
                    self.log_activity("Enable: Settings > Streamer Settings", "warning")
                else:
                    self.log_activity("✓ Song Export enabled", "success")
        except Exception:
            pass

    def get_clone_hero_documents_dir(self):
        """Get the Clone Hero Documents directory"""
        if sys.platform == 'win32':
            docs_path = Path.home() / 'Documents' / 'Clone Hero'
            if docs_path.exists():
                return docs_path
        return None

    def read_current_song(self):
        """Read currentsong.txt for song metadata"""
        result = {'title': None, 'artist': None, 'charter': None}

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

            if len(lines) >= 1 and lines[0].strip():
                result['title'] = lines[0].strip()
            if len(lines) >= 2 and lines[1].strip():
                result['artist'] = lines[1].strip()
            if len(lines) >= 3 and lines[2].strip():
                result['charter'] = lines[2].strip()

            if result['title']:
                self.cached_song_info.update(result)
                self.cached_song_info['last_updated'] = time.time()
            elif self.cached_song_info['title']:
                return dict(self.cached_song_info)

        except Exception:
            if self.cached_song_info['title']:
                return dict(self.cached_song_info)

        return result

    def start_song_cache_polling(self):
        """Start background thread to poll currentsong.txt"""
        def poll_currentsong():
            while self.song_cache_running:
                try:
                    ch_docs = self.get_clone_hero_documents_dir()
                    if ch_docs:
                        currentsong_path = ch_docs / 'currentsong.txt'
                        if currentsong_path.exists():
                            with open(currentsong_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()

                            if len(lines) >= 1 and lines[0].strip():
                                title = lines[0].strip()
                                artist = lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None
                                charter = lines[2].strip() if len(lines) >= 3 and lines[2].strip() else None

                                self.cached_song_info['title'] = title
                                self.cached_song_info['artist'] = artist
                                self.cached_song_info['charter'] = charter
                                self.cached_song_info['last_updated'] = time.time()

                                # Only update GUI if not showing final score OR score was displayed >5 seconds ago
                                if not self.show_final_score or (self.score_display_time and time.time() - self.score_display_time > 5):
                                    song_data = {
                                        'song_title': title,
                                        'song_artist': artist or '--',
                                        'instrument_name': 'Playing...',
                                        'difficulty_name': '',
                                        'score': 0
                                    }
                                    self.after(0, lambda sd=song_data: self.update_current_song(sd, in_progress=True))
                except Exception:
                    pass

                time.sleep(1)

        self.song_cache_running = True
        self.song_cache_thread = threading.Thread(target=poll_currentsong, daemon=True)
        self.song_cache_thread.start()

    def stop_song_cache_polling(self):
        """Stop the song cache polling thread"""
        self.song_cache_running = False

    def clear_song_cache(self):
        """Clear cached song info"""
        self.cached_song_info = {
            'title': None,
            'artist': None,
            'charter': None,
            'last_updated': None
        }

    def start_watcher(self):
        """Start the file watcher"""
        if not self.ch_dir or not self.auth_token:
            return

        state_file = self.ch_dir / '.score_tracker_state.json'

        def on_new_score(score):
            """Callback when new score detected"""
            # Read metadata
            current_song = self.read_current_song()

            # Prepare song data
            song_data = {
                'song_title': f"[{score.chart_hash[:8]}]",
                'song_artist': '',
                'instrument_name': score.instrument_name,
                'difficulty_name': score.difficulty_name,
                'score': score.score
            }

            # Use currentsong.txt data if available
            if current_song['title']:
                song_data['song_title'] = current_song['title']
                song_data['song_artist'] = current_song['artist'] or ''
            elif score.chart_hash in self.song_cache:
                song_info = self.song_cache[score.chart_hash]
                song_data['song_title'] = song_info.get('title', song_data['song_title'])
                song_data['song_artist'] = song_info.get('artist', '')

            # Store final song data
            final_song_data = song_data.copy()

            # Set flag to prevent polling from overwriting
            self.show_final_score = True

            # Update UI
            def update_ui_with_score():
                self.update_current_song(final_song_data, in_progress=False)
                self.log_activity(
                    f"Score: {final_song_data['song_title'][:40]} - {final_song_data['score']:,}",
                    "info"
                )
                # Clear flag after 15 seconds
                self.after(15000, lambda: setattr(self, 'show_final_score', False))

            self.after(0, update_ui_with_score)

            # Submit to API
            self.submit_score_to_api(score, song_data)

            # Clear cache
            self.clear_song_cache()

        try:
            self.watcher = CloneHeroWatcher(
                clone_hero_dir=str(self.ch_dir),
                state_file=str(state_file),
                on_new_score=on_new_score
            )

            if not state_file.exists():
                self.log_activity("First run - initializing state", "info")
                self.watcher.initialize_state()
            else:
                self.watcher.catch_up_scan()

            self.update_tracking_count(len(self.watcher.state.known_scores))

            self.watcher.start()
            self.log_activity("Score monitoring started!", "success")

            self.start_song_cache_polling()
            self.log_activity("Song tracking started!", "success")

            self.is_initialized = True

        except Exception as e:
            self.log_activity(f"Failed to start watcher: {e}", "error")

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
                        "Score submitted",
                        "info"
                    ))
            else:
                status_code = response.status_code
                self.after(0, lambda sc=status_code: self.log_activity(
                    f"Failed: HTTP {sc}",
                    "error"
                ))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self.log_activity(
                f"Error: {msg}",
                "error"
            ))

    # ==================== CONFIG MANAGEMENT ====================

    def find_clone_hero_directory(self, custom_path=None):
        """Find Clone Hero data directory"""
        if custom_path:
            custom_path = Path(custom_path)
            if custom_path.exists():
                return custom_path

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
            'minimize_to_tray': True,
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

    def save_settings(self, settings):
        """Save user settings"""
        settings_path = self.get_settings_path()
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            self.log_activity(f"Failed to save settings: {e}", "error")
            return False

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
                count = len(self.watcher.state.known_scores)
                self.after(0, lambda c=count: self.update_tracking_count(c))
                self.after(0, lambda: self.log_activity("Resync complete!", "success"))

            threading.Thread(target=do_resync, daemon=True).start()
        else:
            self.log_activity("Watcher not initialized", "warning")

    def on_settings(self):
        """Handle Settings button click"""
        current_settings = self.load_settings()
        dialog = SettingsDialog(self, current_settings)
        self.wait_window(dialog)

        if dialog.result:
            if self.save_settings(dialog.result):
                self.log_activity("Settings saved", "success")
                self.log_activity("Restart to apply changes", "info")

    def on_closing(self):
        """Handle window close event"""
        settings = self.load_settings()
        if settings.get('minimize_to_tray', True) and not self.is_hidden:
            self.hide_to_tray()
        else:
            # Stop all background threads
            self.stop_song_cache_polling()
            if self.watcher:
                self.watcher.stop()
            if self.tray_icon:
                self.tray_icon.stop()
            self.destroy()


def main():
    """Main entry point"""
    app = ScoreTrackerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == '__main__':
    main()

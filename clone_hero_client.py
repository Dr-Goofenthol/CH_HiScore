"""
Clone Hero High Score Client

Monitors your Clone Hero scores and submits them to the Discord scoreboard.
"""

VERSION = "2.6.7"

# GitHub repository for auto-updates
GITHUB_REPO = "Dr-Goofenthol/CH_HiScore"

import os
import zipfile
import tempfile
import hashlib
import shlex
import sys
import json
import time
import uuid
import configparser
import getpass
from pathlib import Path
import requests
from colorama import Fore, Style
from client.file_watcher import CloneHeroWatcher
from shared.parsers import SongCacheParser, get_artist_for_song, parse_song_ini
from shared.chart_parser import parse_chart_file, Instrument, Difficulty
from client.ocr_capture import capture_and_extract, check_ocr_available, OCRResult
from shared.console import (
    print_success, print_info, print_warning, print_error,
    print_header, print_plain, print_section, format_key_value
)
from shared.logger import get_client_logger, log_exception

# Initialize colorama for Windows
try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
except ImportError:
    # Fallback if colorama not available
    class Fore:
        GREEN = YELLOW = CYAN = RED = ''
    class Style:
        RESET_ALL = ''

# Initialize logger
logger = get_client_logger()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_instrument_name(instrument_id: int) -> str:
    """
    Get instrument name from instrument ID

    Args:
        instrument_id: Instrument ID (0-10)

    Returns:
        Instrument name string
    """
    instrument_names = {
        0: "Lead Guitar",
        1: "Bass Guitar",
        2: "Rhythm Guitar",
        3: "Keys",
        4: "Drums",
        5: "GHL Guitar",
        6: "GHL Bass",
        7: "Unknown (ID 7)",
        8: "Co-op",
        9: "Unknown (ID 9)",
        10: "Unknown (ID 10)"
    }
    return instrument_names.get(instrument_id, f"Unknown (ID {instrument_id})")


# ============================================================================
# SESSION TRACKING (v2.6.4)
# ============================================================================

class SessionTracker:
    """
    Tracks scoring activity for the current session

    Maintains statistics about scores submitted since tracker started,
    including records broken, FCs achieved, personal bests, etc.
    """

    def __init__(self):
        self.session_start = time.time()
        self.scores = []  # All scores this session
        self.records_broken = []  # Scores that broke records
        self.new_fcs = []  # New full combos
        self.personal_bests = []  # Personal bests (not records)
        self.total_notes_hit = 0

    def add_score(self, score_data: dict):
        """
        Track a score submission

        Args:
            score_data: Dict with keys:
                - chart_hash, instrument_id, difficulty_id, score
                - song_title, song_artist (optional)
                - is_record, is_fc, is_personal_best
                - notes_hit, notes_total (optional)
                - completion_percent
                - timestamp
        """
        # Add timestamp if not present
        if 'timestamp' not in score_data:
            score_data['timestamp'] = time.time()

        self.scores.append(score_data)

        # Categorize the score
        if score_data.get('is_record'):
            self.records_broken.append(score_data)
        if score_data.get('is_fc') and score_data.get('is_new_fc'):
            self.new_fcs.append(score_data)
        if score_data.get('is_personal_best') and not score_data.get('is_record'):
            self.personal_bests.append(score_data)

        # Track notes
        if score_data.get('notes_hit'):
            self.total_notes_hit += score_data['notes_hit']

    def get_session_duration(self) -> tuple:
        """Get session duration in (hours, minutes, seconds)"""
        duration_seconds = int(time.time() - self.session_start)
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        return (hours, minutes, seconds)

    def get_average_accuracy(self) -> float:
        """Calculate average accuracy for the session"""
        if not self.scores:
            return 0.0
        accuracies = [s.get('completion_percent', 0) for s in self.scores]
        return sum(accuracies) / len(accuracies)

    def get_instruments_played(self) -> dict:
        """Get count of scores per instrument"""
        from collections import Counter
        instrument_names = {
            0: "Lead Guitar", 1: "Bass Guitar", 2: "Rhythm Guitar",
            3: "Keys", 4: "Drums", 5: "GHL Guitar", 6: "GHL Bass"
        }
        instruments = [s.get('instrument_id') for s in self.scores]
        counts = Counter(instruments)
        return {instrument_names.get(i, f"Unknown({i})"): count
                for i, count in counts.items()}

    def get_best_score(self) -> dict:
        """Get highest scoring play this session"""
        if not self.scores:
            return None
        return max(self.scores, key=lambda s: s.get('score', 0))

    def get_recent_scores(self, limit=5) -> list:
        """Get most recent scores (newest first)"""
        return list(reversed(self.scores[-limit:]))

    def has_activity(self) -> bool:
        """Check if any scores were submitted this session"""
        return len(self.scores) > 0

    def reset(self):
        """Reset session tracking (start new session)"""
        self.__init__()


# Global session tracker instance
session_tracker = SessionTracker()


def show_ascii_banner():
    """Display ASCII art banner with dynamic version"""
    try:
        print()
        print("        ██████╗██╗  ██╗    ██╗  ██╗██╗███████╗ ██████╗ ██████╗ ██████╗ ███████╗")
        print("       ██╔════╝██║  ██║    ██║  ██║██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝")
        print("       ██║     ███████║    ███████║██║███████╗██║     ██║   ██║██████╔╝█████╗  ")
        print("       ██║     ██╔══██║    ██╔══██║██║╚════██║██║     ██║   ██║██╔══██╗██╔══╝  ")
        print("       ╚██████╗██║  ██║    ██║  ██║██║███████║╚██████╗╚██████╔╝██║  ██║███████╗")
        print("        ╚═════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝")
        print()
        print(f"                         SCORE TRACKER CLIENT v{VERSION}")
        print("                          Track • Compete • Dominate")
        print()
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback to simple ASCII if Unicode fails
        print()
        print("=" * 80)
        print(f"         CLONE HERO HIGH SCORE TRACKER v{VERSION}")
        print("                 Track • Compete • Dominate")
        print("=" * 80)
        print()



def is_admin():
    """Check if running with administrator privileges"""
    if sys.platform == 'win32':
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # For non-Windows, check if running as root
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else False


# Windows startup management
if sys.platform == 'win32':
    import winreg

# System tray support (optional)
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY_SUPPORT = True
except ImportError:
    HAS_TRAY_SUPPORT = False

# Default configuration
DEFAULT_BOT_URL = "http://localhost:8080"

# Cached song info - Clone Hero clears currentsong.txt when song ends,
# but scoredata.bin is written AFTER the song ends, so we need to cache
# the song info while playing so it's available when we detect the score.
_cached_song_info = {
    'title': None,
    'artist': None,
    'charter': None,
    'last_updated': None
}
_song_cache_thread = None
_song_cache_running = False

# OCR Statistics tracking
_ocr_stats = {
    'attempts': 0,
    'successes': 0,
    'last_attempt': None
}


# Chart file cache for v2.6.0 chart parsing (chart_hash -> Path to chart file)
_chart_file_cache = {}

# Config files will be stored in Clone Hero directory for persistence
CONFIG_FILE = None  # Set after finding CH directory
SETTINGS_FILE = None  # Set after finding CH directory


def get_config_path():
    """Get the config file path (in Clone Hero directory for persistence)"""
    global CONFIG_FILE
    if CONFIG_FILE:
        return CONFIG_FILE

    # Try to find Clone Hero directory for persistent config
    ch_dir = find_clone_hero_directory_internal()
    if ch_dir:
        CONFIG_FILE = ch_dir / '.score_tracker_config.json'
    else:
        # Fallback to user's home directory
        CONFIG_FILE = Path.home() / '.clone_hero_tracker_config.json'
    return CONFIG_FILE


def get_settings_path():
    """Get the settings file path (in Clone Hero directory for persistence)"""
    global SETTINGS_FILE
    if SETTINGS_FILE:
        return SETTINGS_FILE

    # Try to find Clone Hero directory for persistent settings
    ch_dir = find_clone_hero_directory_internal()
    if ch_dir:
        SETTINGS_FILE = ch_dir / '.score_tracker_settings.json'
    else:
        # Fallback to user's home directory
        SETTINGS_FILE = Path.home() / '.clone_hero_tracker_settings.json'
    return SETTINGS_FILE


def load_settings():
    """Load user settings"""
    settings_path = get_settings_path()
    default_settings = {
        'bot_url': DEFAULT_BOT_URL,
        'clone_hero_path': None,  # None means auto-detect
        'minimize_to_tray': False,  # Minimize to system tray instead of taskbar
        'start_with_windows': False  # Auto-start when Windows boots
    }

    if settings_path and settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                saved = json.load(f)
                # Merge with defaults
                default_settings.update(saved)
        except Exception as e:
            print_warning(f"Could not load settings (using defaults): {e}")
            log_exception(logger, "Failed to load settings", e)

    return default_settings


def save_settings(settings):
    """Save user settings"""
    settings_path = get_settings_path()
    if settings_path:
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print_error(f"Could not save settings: {e}")
    return False


def get_executable_path():
    """Get the path to the current executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return sys.executable
    else:
        # Running as script
        return str(Path(__file__).resolve())


def set_windows_startup(enable: bool) -> bool:
    """Add or remove the program from Windows startup"""
    if sys.platform != 'win32':
        print_warning("Windows startup is only available on Windows")
        return False

    app_name = "CloneHeroScoreTracker"
    exe_path = get_executable_path()

    try:
        # Open the registry key for current user startup programs
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )

        if enable:
            # Add to startup
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            print_success(f"Added to Windows startup: {exe_path}")
        else:
            # Remove from startup
            try:
                winreg.DeleteValue(key, app_name)
                print_success("Removed from Windows startup")
            except FileNotFoundError:
                # Already not in startup
                pass

        winreg.CloseKey(key)
        return True

    except PermissionError:
        print_error("Permission denied - try running as administrator")
        return False
    except Exception as e:
        print_error(f"Failed to modify Windows startup: {e}")
        return False


def ensure_startup_entry_current():
    """
    Update Windows startup registry entry to current executable path.
    Called on startup when start_with_windows is enabled.
    Prevents startup failures after updating to new exe versions.
    """
    if sys.platform != 'win32':
        return

    settings = load_settings()
    if not settings.get('start_with_windows', False):
        return  # Feature not enabled

    # Silently update registry to point to current exe
    app_name = "CloneHeroScoreTracker"
    current_exe_path = get_executable_path()

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )

        # Check if entry exists and if it's outdated
        try:
            existing_path, _ = winreg.QueryValueEx(key, app_name)
            existing_path_clean = existing_path.strip('"')
            current_path_clean = current_exe_path

            # Update if paths don't match
            if existing_path_clean != current_path_clean:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{current_exe_path}"')
                logger.info(f"Updated startup registry entry to: {current_exe_path}")
        except FileNotFoundError:
            # Entry doesn't exist, create it
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{current_exe_path}"')
            logger.info(f"Created startup registry entry: {current_exe_path}")

        winreg.CloseKey(key)
    except Exception as e:
        # Silent fail - don't block startup
        logger.debug(f"Failed to update startup entry: {e}")


# System tray globals
_tray_icon = None
_tray_should_exit = False
_update_available = False
_update_version = None
_update_downloaded = False
_update_file_path = None


def create_tray_icon_image():
    """Create a simple icon image for the system tray"""
    # Create a simple colored circle icon
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Draw a green circle with a white "CH" text
    draw.ellipse([4, 4, size-4, size-4], fill=(46, 204, 113))  # Green
    return image


def on_tray_show(icon, item):
    """Show the console window from tray"""
    if sys.platform == 'win32':
        import ctypes
        # Get the console window handle and show it
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)


def on_tray_exit(icon, item):
    """Exit from tray"""
    import os

    # Stop the tray icon
    try:
        icon.stop()
    except:
        pass

    # Clean up lock file
    release_instance_lock()

    # Force immediate exit (needed because main loop is blocked on input())
    os._exit(0)


def on_tray_check_updates(icon, item):
    """Check for updates from tray menu"""
    global _update_available, _update_version

    try:
        icon.notify(
            title="Checking for Updates",
            message="Please wait..."
        )

        latest_version, download_url = check_for_updates_silent()

        if latest_version and latest_version != VERSION:
            _update_available = True
            _update_version = latest_version
            icon.notify(
                title="Update Available",
                message=f"Version {latest_version} is available!\nUse 'Update Now' from the tray menu."
            )
            # Update the menu to show "Update Now" option
            update_tray_menu(icon)
        else:
            icon.notify(
                title="No Updates",
                message=f"You're running the latest version ({VERSION})"
            )
    except Exception as e:
        icon.notify(
            title="Update Check Failed",
            message=f"Error: {str(e)}"
        )


def on_tray_update_now(icon, item):
    """Download and apply update from tray menu"""
    global _update_downloaded, _update_file_path

    if not _update_available:
        icon.notify(
            title="No Update Available",
            message="Check for updates first"
        )
        return

    try:
        icon.notify(
            title="Downloading Update",
            message=f"Downloading version {_update_version}..."
        )

        # Download the update
        latest_version, download_url = check_for_updates_silent()
        if download_url:
            new_exe_path = download_update_from_url(download_url, latest_version)
            if new_exe_path:
                _update_downloaded = True
                _update_file_path = new_exe_path
                icon.notify(
                    title="Update Downloaded",
                    message=f"Version {_update_version} ready!\nUse 'Restart to Update' from the tray menu."
                )
                # Update the menu to show "Restart" option
                update_tray_menu(icon)
            else:
                icon.notify(
                    title="Download Failed",
                    message="Could not download update"
                )
    except Exception as e:
        icon.notify(
            title="Update Failed",
            message=f"Error: {str(e)}"
        )


def on_tray_restart(icon, item):
    """Restart to apply update"""
    global _tray_should_exit

    if not _update_downloaded or not _update_file_path:
        icon.notify(
            title="No Update to Apply",
            message="Download an update first"
        )
        return

    try:
        icon.notify(
            title="Restarting",
            message="Applying update..."
        )

        # Apply the update and restart
        apply_update(_update_file_path)

        # Exit the tray
        _tray_should_exit = True
        icon.stop()
    except Exception as e:
        icon.notify(
            title="Restart Failed",
            message=f"Error: {str(e)}"
        )


def update_tray_menu(icon):
    """Update the tray menu dynamically based on update state"""
    global _update_available, _update_downloaded

    def create_menu():
        menu_items = [
            pystray.MenuItem("Show", on_tray_show, default=True),
            pystray.MenuItem("Check for Updates", on_tray_check_updates),
        ]

        # Show "Update Now" if update is available
        if _update_available and not _update_downloaded:
            menu_items.append(
                pystray.MenuItem("Update Now", on_tray_update_now)
            )

        # Show "Restart to Update" if update is downloaded
        if _update_downloaded:
            menu_items.append(
                pystray.MenuItem("Restart to Update", on_tray_restart)
            )

        menu_items.append(
            pystray.MenuItem("Exit", on_tray_exit)
        )

        return pystray.Menu(*menu_items)

    icon.menu = create_menu()


def hide_console_window():
    """Hide the console window"""
    if sys.platform == 'win32':
        import ctypes
        # Give the tray icon time to fully initialize
        time.sleep(0.5)

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # SW_HIDE = 0, but some systems need SW_MINIMIZE (6) first
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            time.sleep(0.1)
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE


def start_tray_icon(show_startup_notification=False):
    """Start the system tray icon in a background thread"""
    global _tray_icon

    if not HAS_TRAY_SUPPORT:
        print_warning("System tray not available (install pystray and Pillow)")
        return False

    # If tray icon already exists, don't create duplicate
    if _tray_icon is not None:
        print_info("System tray icon already running")
        return True

    try:
        # Create initial menu
        menu = pystray.Menu(
            pystray.MenuItem("Show", on_tray_show, default=True),
            pystray.MenuItem("Check for Updates", on_tray_check_updates),
            pystray.MenuItem("Exit", on_tray_exit)
        )

        _tray_icon = pystray.Icon(
            "CloneHeroTracker",
            create_tray_icon_image(),
            "Clone Hero Score Tracker",
            menu
        )

        # Setup function to show notification after icon is ready
        def on_ready(icon):
            icon.visible = True
            if show_startup_notification:
                time.sleep(0.5)  # Give tray time to fully initialize
                icon.notify(
                    title="Clone Hero Score Tracker",
                    message="Running in background - monitoring scores"
                )

        # Run the tray icon in a separate thread
        import threading
        tray_thread = threading.Thread(
            target=lambda: _tray_icon.run(setup=on_ready),
            daemon=True
        )
        tray_thread.start()

        print_success("System tray icon started")
        return True

    except Exception as e:
        print_error(f"Failed to start tray icon: {e}")
        return False


def stop_tray_icon():
    """Stop the system tray icon"""
    global _tray_icon
    if _tray_icon:
        try:
            _tray_icon.stop()
        except:
            pass
        _tray_icon = None


def monitor_window_minimize():
    """
    Background thread to monitor console window state and hide to tray when minimized
    """
    if sys.platform != 'win32':
        return

    import ctypes
    import threading
    import time

    def check_window_state():
        SW_MINIMIZE = 6
        SW_HIDE = 0
        last_was_minimized = False  # Track state to only notify once

        while True:
            try:
                # Check if tray is enabled and icon exists
                settings = load_settings()
                if not settings.get('minimize_to_tray', False) or _tray_icon is None:
                    time.sleep(1)
                    continue

                # Get console window handle
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if not hwnd:
                    time.sleep(1)
                    continue

                # Check if window is minimized
                is_minimized = ctypes.windll.user32.IsIconic(hwnd)

                if is_minimized and not last_was_minimized:
                    # Just became minimized - handle this transition once
                    ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)

                    # Show notification only once when minimizing
                    try:
                        if _tray_icon:
                            _tray_icon.notify(
                                title="Clone Hero Score Tracker",
                                message="Minimized to system tray"
                            )
                    except Exception:
                        pass  # Notification failures are non-critical

                last_was_minimized = is_minimized
                time.sleep(0.5)  # Check twice per second
            except Exception:
                time.sleep(1)  # On any error, wait and retry

    # Start monitor thread
    monitor_thread = threading.Thread(target=check_window_state, daemon=True)
    monitor_thread.start()


def get_bot_url():
    """Get the configured bot URL"""
    settings = load_settings()
    return settings.get('bot_url', DEFAULT_BOT_URL)


def load_config():
    """Load client configuration (auth tokens, client ID)"""
    config_path = get_config_path()
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print_warning(f"Could not load config (using defaults): {e}")
            log_exception(logger, "Failed to load config", e)
    return {}


def save_config(config):
    """Save client configuration"""
    config_path = get_config_path()
    if config_path:
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print_error(f"Could not save config: {e}")


def get_or_create_client_id():
    """Get existing client ID or create a new one"""
    config = load_config()
    if 'client_id' not in config:
        config['client_id'] = str(uuid.uuid4())
        save_config(config)
    return config['client_id']


def get_auth_token():
    """Get stored auth token if available"""
    config = load_config()
    return config.get('auth_token')


def save_auth_token(token):
    """Save auth token to config"""
    config = load_config()
    config['auth_token'] = token
    save_config(config)


def request_pairing():
    """Request a pairing code from the bot API"""
    client_id = get_or_create_client_id()

    try:
        response = requests.post(
            f"{get_bot_url()}/api/pair/request",
            json={"client_id": client_id},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('pairing_code')
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to bot API")
        print_warning("Make sure the bot is running first!", indent=1)
    except Exception as e:
        print_error(f"Error requesting pairing")
        log_exception(logger, "Failed to request pairing code", e)

    return None


def poll_for_pairing(timeout=300):
    """Poll the API to check if pairing is complete"""
    client_id = get_or_create_client_id()
    start_time = time.time()
    last_status_message = 0

    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{get_bot_url()}/api/pair/status/{client_id}",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('paired') and data.get('auth_token'):
                    return data['auth_token']
        except requests.exceptions.ConnectionError:
            # Show periodic status if connection keeps failing
            elapsed = time.time() - start_time
            if elapsed - last_status_message >= 30:  # Every 30 seconds
                mins = int(elapsed / 60)
                secs = int(elapsed % 60)
                print_warning(f"Still waiting... ({mins}m {secs}s elapsed - bot may be offline)")
                last_status_message = elapsed
        except Exception as e:
            # Log other exceptions but continue polling
            log_exception(logger, "Error during pairing poll", e)

        time.sleep(2)  # Check every 2 seconds

    return None


def first_time_setup():
    """Show first-time setup prompt and return user type"""
    print_header("FIRST TIME SETUP", width=50)
    print("\nWelcome to Clone Hero High Score Tracker!")
    print("\nIs this a new installation?")
    print()
    print("  1. New user - I'm joining the scoreboard for the first time")
    print("  2. Existing user - I already have scores and I'm connecting")
    print("                     from a new machine")
    print()

    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == '1':
            return 'new'
        elif choice == '2':
            return 'existing'
        else:
            print("Please enter 1 or 2")


def do_pairing(is_existing_user=False):
    """Complete the pairing flow"""
    if is_existing_user:
        print_header("CONNECT EXISTING ACCOUNT", width=50)
        print("\nLet's link this machine to your existing Discord account.")
        print("Your scores will be merged with your existing record.")
    else:
        print_header("NEW USER SETUP", width=50)
        print("\nLet's link your Clone Hero client to Discord.")
        print("This allows your scores to be tracked and announced!")

    print("\nRequesting pairing code from bot...\n")

    pairing_code = request_pairing()

    if not pairing_code:
        print_error("Failed to get pairing code.")
        print_warning("Make sure the bot is running and try again.", indent=1)
        return None

    # Get server info for display
    bot_url = get_bot_url()

    print("\n" + "=" * 50)
    print_success(f"   YOUR PAIRING CODE: {pairing_code}")
    print("=" * 50)
    print_info("\nSTEP 1: Open Discord")
    print_info(f"STEP 2: Go to the server running the score bot")
    print(f"        (Bot server: {bot_url})")
    print_info(f"STEP 3: Type this command in any channel:")
    print_success(f"\n        /pair {pairing_code}")
    print()
    print_plain("Waiting for you to complete pairing...")
    print_warning("(Code expires in 5 minutes)")
    print("=" * 50 + "\n")

    # Poll for completion
    auth_token = poll_for_pairing(timeout=300)

    if auth_token:
        save_auth_token(auth_token)
        print()
        print_header("PAIRING SUCCESSFUL!", width=50)
        if is_existing_user:
            print("This machine is now connected to your account.")
            print("All scores will sync to your existing record!")
        else:
            print("Your Discord account is now linked.")
            print("Scores will be automatically submitted!")
        print("=" * 50 + "\n")

        # ==================== FEATURE CONFIGURATION ====================
        print("\n" + "=" * 50)
        print_header("FEATURE CONFIGURATION", width=50)
        print("Let's configure some helpful features for your tracker.")
        print("=" * 50 + "\n")

        settings = load_settings()

        # System Tray
        print_plain("[1] Minimize to System Tray")
        print("    When enabled, the tracker minimizes to your system tray")
        print("    instead of the taskbar. Keeps your taskbar clean!")
        print()
        tray_choice = input("    Enable minimize to tray? (Y/n): ").strip().lower()
        if tray_choice not in ('n', 'no'):
            settings['minimize_to_tray'] = True
            print_success("    System tray enabled!")
        else:
            settings['minimize_to_tray'] = False
            print_info("    System tray disabled")

        # Start with Windows
        print()
        print_plain("[2] Start with Windows")
        print("    Automatically start the tracker when Windows boots.")
        print("    Ensures your scores are always tracked!")
        print()
        startup_choice = input("    Enable start with Windows? (Y/n): ").strip().lower()
        if startup_choice not in ('n', 'no'):
            try:
                success = set_windows_startup(True)
                if success:
                    settings['start_with_windows'] = True
                else:
                    settings['start_with_windows'] = False
                    print_info("    You can enable this later in Settings")
            except Exception as e:
                settings['start_with_windows'] = False
                print_error(f"    Failed to enable: {e}")
                print_info("    You can enable this later in Settings")
        else:
            settings['start_with_windows'] = False
            print_info("    Auto-start disabled")

        # Clone Hero Path Verification
        print()
        print_plain("[3] Clone Hero Path")
        auto_detected = find_clone_hero_directory_internal()
        if auto_detected:
            print_success(f"    Auto-detected: {auto_detected}")
            print()
            verify = input("    Is this correct? (Y/n): ").strip().lower()
            if verify in ('n', 'no'):
                print("    Enter custom Clone Hero data path:")
                custom_path = input("    > ").strip()
                if custom_path and Path(custom_path).exists():
                    settings['clone_hero_path'] = custom_path
                    print_success(f"    Custom path saved: {custom_path}")
                else:
                    print_warning("    Invalid path, using auto-detect")
                    settings['clone_hero_path'] = None
            else:
                settings['clone_hero_path'] = None  # Use auto-detect
                print_info("    Using auto-detected path")
        else:
            print_warning("    Could not auto-detect Clone Hero")
            print("    Enter Clone Hero data path (or press Enter to configure later):")
            custom_path = input("    > ").strip()
            if custom_path and Path(custom_path).exists():
                settings['clone_hero_path'] = custom_path
                print_success(f"    Custom path saved: {custom_path}")
            else:
                settings['clone_hero_path'] = None
                print_info("    You can set this later in Settings")

        # Save all settings
        save_settings(settings)

        # ==================== SETUP COMPLETE SUMMARY ====================
        print("\n" + "=" * 50)
        print_header("SETUP COMPLETE!", width=50)
        print("=" * 50)
        print()
        print_success("Your Clone Hero Score Tracker is ready!")
        print()
        print("Configured Features:")
        if settings.get('minimize_to_tray'):
            print_success("  + Minimize to system tray")
        else:
            print_plain("  - System tray (disabled)")
        if settings.get('start_with_windows'):
            print_success("  + Start with Windows")
        else:
            print_plain("  - Auto-start (disabled)")
        if settings.get('clone_hero_path'):
            print_success(f"  + Clone Hero path: {settings.get('clone_hero_path')}")
        else:
            print_info("  + Clone Hero path: Auto-detect")

        print()
        print("-" * 50)
        print("NEXT STEPS:")
        print("-" * 50)
        print("  1. The tracker will now monitor your Clone Hero scores")
        print("  2. Play Clone Hero - scores will auto-submit!")
        print("  3. High scores are announced in Discord")
        print("  4. Check Settings menu to customize further")
        print("-" * 50)
        print()
        input("Press Enter to start tracking...")

        print("=" * 50 + "\n")

        return auth_token
    else:
        print("\n" + "-" * 50)
        print("PAIRING FAILED")
        print("-" * 50)
        print("\nPossible reasons:")
        print("  - The pairing code expired (5 minute limit)")
        print("  - The /pair command wasn't entered in Discord")
        print("  - The bot went offline during pairing")
        print("\nTo try again:")
        print("  1. Make sure the Discord bot is online")
        print("  2. Restart this tracker")
        print("  3. Enter the new pairing code quickly")
        print("-" * 50)
        return None


def find_clone_hero_directory_internal():
    """Find Clone Hero data directory (internal - no settings check)"""
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


def find_clone_hero_directory():
    """Find Clone Hero data directory (checks settings first)"""
    settings = load_settings()

    # Check if user has set a custom path
    custom_path = settings.get('clone_hero_path')
    if custom_path:
        custom = Path(custom_path)
        if custom.exists():
            return custom
        else:
            print_error(f"Custom Clone Hero path not found: {custom_path}")
            print_info("Falling back to auto-detection...")

    # Auto-detect
    return find_clone_hero_directory_internal()


def get_clone_hero_documents_dir():
    """Get the Clone Hero Documents directory (for settings.ini, currentsong.txt, etc.)

    Checks multiple candidate paths to find where Clone Hero actually wrote its files,
    rather than blindly trusting any single path. This handles:
    - Standard local Documents (most users)
    - OneDrive with Known Folder Move (junction at C:\\Users\\...\\Documents)
    - OneDrive sync without KFM (registry points to OneDrive, local Documents separate)
    - Manually relocated Documents folders
    """
    if sys.platform == 'win32':
        candidates = []

        # Standard path first — Clone Hero (Unity) typically uses USERPROFILE\Documents
        candidates.append(Path.home() / 'Documents' / 'Clone Hero')

        # Registry-based path as secondary candidate (handles some OneDrive configurations)
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            ) as key:
                docs_str, _ = winreg.QueryValueEx(key, 'Personal')
                reg_path = Path(docs_str) / 'Clone Hero'
                if reg_path not in candidates:
                    candidates.append(reg_path)
        except Exception:
            pass

        # Pass 1: find a path where Clone Hero has actually run (settings.ini present)
        for path in candidates:
            if path.exists() and (path / 'settings.ini').exists():
                return path

        # Pass 2: any existing Clone Hero directory (Clone Hero ran but no settings.ini yet)
        for path in candidates:
            if path.exists():
                return path
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


def read_current_song():
    """
    Read the currentsong.txt file for authoritative song metadata.

    Clone Hero clears currentsong.txt when a song ends, but scoredata.bin is written
    AFTER the song ends. So we cache the song info while playing and return the
    cached values if the file is empty when we need it.

    Returns:
        dict with 'title', 'artist', 'charter' keys (values may be None if not available)
    """
    global _cached_song_info

    result = {
        'title': None,
        'artist': None,
        'charter': None
    }

    ch_docs = get_clone_hero_documents_dir()
    if not ch_docs:
        # Return cached info if available
        if _cached_song_info['title']:
            return {
                'title': _cached_song_info['title'],
                'artist': _cached_song_info['artist'],
                'charter': _cached_song_info['charter']
            }
        return result

    currentsong_path = ch_docs / 'currentsong.txt'
    if not currentsong_path.exists():
        # Return cached info if available
        if _cached_song_info['title']:
            return {
                'title': _cached_song_info['title'],
                'artist': _cached_song_info['artist'],
                'charter': _cached_song_info['charter']
            }
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
            _cached_song_info['title'] = result['title']
            _cached_song_info['artist'] = result['artist']
            _cached_song_info['charter'] = result['charter']
            _cached_song_info['last_updated'] = time.time()
        elif _cached_song_info['title']:
            # File is empty but we have cached data - use it
            # (This happens when Clone Hero clears the file after song ends)
            return {
                'title': _cached_song_info['title'],
                'artist': _cached_song_info['artist'],
                'charter': _cached_song_info['charter']
            }

    except Exception:
        # Return cached info if available
        if _cached_song_info['title']:
            return {
                'title': _cached_song_info['title'],
                'artist': _cached_song_info['artist'],
                'charter': _cached_song_info['charter']
            }
        pass  # Silent fail - file may be in use

    return result


def clear_song_cache():
    """Clear the cached song info after a score is processed"""
    global _cached_song_info
    _cached_song_info = {
        'title': None,
        'artist': None,
        'charter': None,
        'last_updated': None
    }


def find_chart_file_by_hash(chart_hash: str):
    """
    Find a chart file (.chart or .mid) by its hash.

    Scans Clone Hero's song folders from settings.ini to find the chart file
    that matches the given hash. Results are cached for performance.

    Args:
        chart_hash: The MD5 hash of the chart file to find

    Returns:
        Path to chart file, or None if not found
    """
    global _chart_file_cache

    # Check cache first
    if chart_hash in _chart_file_cache:
        return _chart_file_cache[chart_hash]

    # Get Clone Hero song folders from settings.ini
    song_folders = []
    ch_docs = get_clone_hero_documents_dir()
    settings_path = (ch_docs / "settings.ini") if ch_docs else None

    if settings_path and settings_path.exists():
        try:
            # Parse settings.ini using configparser to handle sections properly
            config = configparser.ConfigParser()
            config.read(str(settings_path))

            # Look for path entries in all sections
            for section in config.sections():
                for key in config.options(section):
                    if key.startswith('path') and key[4:].isdigit():
                        folder = config.get(section, key)
                        if folder and Path(folder).exists():
                            song_folders.append(Path(folder))
        except Exception as e:
            logger.debug(f"Could not parse Clone Hero settings: {e}")

    # Fallback to tracker's configured folder (consistent with scancharts / on-demand scan)
    if not song_folders:
        try:
            fallback_folder = load_settings().get('songs_folder')
            if fallback_folder and Path(fallback_folder).exists():
                song_folders.append(Path(fallback_folder))
                logger.debug(f"find_chart_file_by_hash: using tracker fallback folder: {fallback_folder}")
        except Exception:
            pass

    if not song_folders:
        logger.debug(f"find_chart_file_by_hash: no song folders found for [{chart_hash[:8]}]")
        # Cache negative result
        _chart_file_cache[chart_hash] = None
        return None

    # Scan folders for matching chart
    for songs_path in song_folders:
        for root, dirs, files in os.walk(songs_path):
            # Look for chart files
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if not chart_files:
                continue

            chart_path = Path(root) / chart_files[0]

            try:
                # Calculate MD5 hash of chart file
                with open(chart_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

                # Check if this matches the target hash
                if file_hash == chart_hash or file_hash.startswith(chart_hash):
                    # Cache and return
                    _chart_file_cache[chart_hash] = chart_path
                    return chart_path
            except Exception:
                continue

    # Not found - cache negative result
    _chart_file_cache[chart_hash] = None
    return None


def get_total_notes_from_chart(chart_hash: str, instrument_id: int, difficulty_id: int):
    """
    Get chart data (total_notes, NPS) for a specific chart/instrument/difficulty.

    This function finds the chart file by hash, parses it, and extracts the total note
    count and notes-per-second for the specified instrument and difficulty combination.

    Args:
        chart_hash: The MD5 hash of the chart file
        instrument_id: Instrument ID (0=Lead, 1=Bass, 2=Rhythm, 3=Keys, 4=Drums)
        difficulty_id: Difficulty ID (0=Easy, 1=Medium, 2=Hard, 3=Expert)

    Returns:
        Dict with 'total_notes' and 'nps', or just int (backwards compat), or None if failed
    """
    # Find the chart file
    chart_path = find_chart_file_by_hash(chart_hash)

    if not chart_path:
        logger.debug(f"Chart file not found for hash {chart_hash[:8]}")
        return None

    try:
        # Parse chart file
        chart_data = parse_chart_file(chart_path)

        if not chart_data:
            logger.debug(f"Failed to parse chart file: {chart_path}")
            return None

        # Convert IDs to enums
        try:
            instrument = Instrument(instrument_id)
            difficulty = Difficulty(difficulty_id)
        except ValueError as e:
            logger.debug(f"Invalid instrument/difficulty ID: {e}")
            return None

        # Get data for this instrument/difficulty combination
        key = (instrument, difficulty)
        if key not in chart_data.instruments:
            logger.debug(f"No data for {instrument.name}/{difficulty.name} in chart")
            return None

        inst_diff_data = chart_data.instruments[key]

        # v2.6.2: Return dict with total_notes and NPS
        # v2.6.6: Also return chart_path so caller can extract song.ini metadata
        nps = chart_data.calculate_note_density(instrument, difficulty)
        peak_nps = chart_data.calculate_peak_note_density(instrument, difficulty, window_seconds=1.0)
        return {
            'total_notes': inst_diff_data.total_notes,
            'nps': nps,
            'peak_nps': peak_nps,
            'chart_path': chart_path
        }

    except Exception as e:
        logger.warning(f"Failed to parse chart file {chart_path}: {e}")
        return None


def start_song_cache_polling():
    """
    Start a background thread that periodically polls currentsong.txt
    to keep the cache updated while a song is playing.
    """
    global _song_cache_thread, _song_cache_running
    import threading

    def poll_currentsong():
        global _song_cache_running
        while _song_cache_running:
            # Read currentsong.txt to update cache (the read function handles caching)
            try:
                ch_docs = get_clone_hero_documents_dir()
                if ch_docs:
                    currentsong_path = ch_docs / 'currentsong.txt'
                    if currentsong_path.exists():
                        with open(currentsong_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        # Only cache if we have valid data
                        if len(lines) >= 1 and lines[0].strip():
                            _cached_song_info['title'] = lines[0].strip()
                            _cached_song_info['artist'] = lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None
                            _cached_song_info['charter'] = lines[2].strip() if len(lines) >= 3 and lines[2].strip() else None
                            _cached_song_info['last_updated'] = time.time()
            except Exception:
                pass  # Silent fail
            time.sleep(1)  # Poll every second

    _song_cache_running = True
    _song_cache_thread = threading.Thread(target=poll_currentsong, daemon=True)
    _song_cache_thread.start()


def stop_song_cache_polling():
    """Stop the background song cache polling thread"""
    global _song_cache_running
    _song_cache_running = False


def check_clone_hero_settings():
    """
    Check Clone Hero settings.ini for required flags.

    Returns:
        dict with 'warnings' list and 'settings' dict
    """
    result = {
        'warnings': [],
        'settings': {
            'song_export': None,
            'auto_screenshot': None
        }
    }

    ch_docs = get_clone_hero_documents_dir()
    if not ch_docs:
        result['warnings'].append("Could not find Clone Hero Documents folder")
        return result

    settings_path = ch_docs / 'settings.ini'
    if not settings_path.exists():
        result['warnings'].append("Clone Hero settings.ini not found - run Clone Hero at least once")
        return result

    try:
        config = configparser.ConfigParser()
        config.read(str(settings_path))

        # Check song_export in [streamer] section
        if config.has_option('streamer', 'song_export'):
            song_export = config.get('streamer', 'song_export')
            result['settings']['song_export'] = song_export
            if song_export != '1':
                result['warnings'].append(
                    "song_export is disabled! Enable it in Clone Hero:\n"
                    "      Settings > Gameplay > Streamer Settings > Export Current Song"
                )

        # Check auto_screenshot in [game] section
        if config.has_option('game', 'auto_screenshot'):
            auto_screenshot = config.get('game', 'auto_screenshot')
            result['settings']['auto_screenshot'] = auto_screenshot
            if auto_screenshot != '1':
                result['warnings'].append(
                    "auto_screenshot is disabled! Enable it in Clone Hero:\n"
                    "      Settings > Gameplay > Streamer Settings > Auto Screenshot Results"
                )

    except Exception as e:
        result['warnings'].append(f"Could not read settings.ini: {e}")

    return result


def format_score_output(score, song_title, song_artist, song_charter, notes_hit, notes_total,
                       total_notes_in_chart, nps, is_fc, api_response=None):
    """
    Format and print score information in clean ASCII format (v2.6.2)

    Args:
        score: ScoreEntry object
        song_title: Song title string
        song_artist: Artist name string
        song_charter: Charter name string
        notes_hit: Notes hit (from OCR/chart)
        notes_total: Total notes (from chart)
        total_notes_in_chart: Total notes from chart parse
        nps: Notes per second
        is_fc: Full combo boolean
        api_response: Response dict from API (optional)
    """
    # Build stars display
    stars_display = "*" * score.stars

    # Build FC indicator
    fc_indicator = " [FC]" if is_fc else ""

    # Build accuracy display
    if notes_hit is not None and notes_total is not None:
        accuracy_display = f"{score.completion_percent:.1f}% ({notes_hit}/{notes_total} notes"
        if nps:
            accuracy_display += f", {nps:.1f} NPS"
        accuracy_display += ")"
    else:
        accuracy_display = f"{score.completion_percent:.1f}%"
        if nps:
            accuracy_display += f" ({nps:.1f} NPS)"

    # Print header
    print()
    print("=" * 80)
    print(f"  {Fore.CYAN}NEW SCORE{Style.RESET_ALL}")
    print("=" * 80)
    print()

    # Song info
    print(f"  {Fore.CYAN}Song{Style.RESET_ALL}       {song_title}")
    if song_artist:
        print(f"  {Fore.CYAN}Artist{Style.RESET_ALL}     {song_artist}")
    if song_charter:
        print(f"  {Fore.CYAN}Charter{Style.RESET_ALL}    {song_charter}")
    print(f"  {Fore.CYAN}Hash{Style.RESET_ALL}       {score.chart_hash[:8]}...")
    print()

    # Performance data
    fc_colored = f" {Fore.GREEN}[FC]{Style.RESET_ALL}" if fc_indicator else ""
    print(f"  {Fore.CYAN}Chart{Style.RESET_ALL}      {score.instrument_name} ({score.difficulty_name}) {stars_display}{fc_colored}")
    print(f"  {Fore.CYAN}Score{Style.RESET_ALL}      {Fore.WHITE}{score.score:,}{Style.RESET_ALL} pts")
    print(f"  {Fore.CYAN}Accuracy{Style.RESET_ALL}   {accuracy_display}")
    print(f"  {Fore.CYAN}Plays{Style.RESET_ALL}      #{score.play_count}")
    print()

    # Result status (from API response)
    if api_response:
        is_new_pb = api_response.get('is_high_score', False)
        is_record = api_response.get('is_record_broken', False)
        server_record = api_response.get('server_record')
        previous_pb = api_response.get('previous_pb')
        improvement = api_response.get('improvement', 0)

        # Determine result text
        if is_record:
            result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} New Personal Best!  |  {Fore.RED}[RECORD]{Style.RESET_ALL} NEW SERVER RECORD!"
            if api_response.get('previous_score') and api_response.get('previous_holder'):
                prev_score = api_response['previous_score']
                prev_holder = api_response['previous_holder']
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
                print(f"             Previous record: {prev_score:,} pts ({prev_holder})")
            else:
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
        elif is_new_pb:
            if improvement > 0:
                if previous_pb:
                    # Show PB improvement with date
                    from datetime import datetime
                    try:
                        pb_date = datetime.fromisoformat(previous_pb['submitted_at'])
                        days_ago = (datetime.now() - pb_date).days
                        if days_ago == 0:
                            date_str = "today"
                        elif days_ago == 1:
                            date_str = "yesterday"
                        else:
                            date_str = f"{days_ago} days ago"
                        result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} New Personal Best! ({Fore.GREEN}+{improvement:,}{Style.RESET_ALL} from PB set {date_str})"
                    except:
                        result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} New Personal Best! ({Fore.GREEN}+{improvement:,}{Style.RESET_ALL} from previous PB)"
                else:
                    result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} New Personal Best! ({Fore.GREEN}+{improvement:,}{Style.RESET_ALL} improvement)"
            else:
                result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} New Personal Best! (first time!)"

            # Add server record info
            if server_record:
                result_text += f"  |  {Fore.YELLOW}[-]{Style.RESET_ALL} Not a server record"
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
                print(f"             Server record: {server_record['score']:,} pts ({server_record['holder']})")
            else:
                result_text += f"  |  {Fore.RED}[RECORD]{Style.RESET_ALL} NEW SERVER RECORD! (First on chart)"
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
        else:
            # Matched or below PB
            your_best = api_response.get('your_best_score', score.score)
            if score.score == your_best:
                result_text = f"{Fore.GREEN}[+]{Style.RESET_ALL} Personal Best Maintained"
            else:
                result_text = f"{Fore.YELLOW}[-]{Style.RESET_ALL} Below Personal Best"

            if server_record:
                result_text += f"  |  {Fore.YELLOW}[-]{Style.RESET_ALL} Not a server record"
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
                print(f"             Server record: {server_record['score']:,} pts ({server_record['holder']})")
            else:
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")

    print()
    print("=" * 80)


def create_score_handler(auth_token, song_cache=None, ocr_enabled=True):
    """Create a score handler with the given auth token and optional song cache"""

    def on_new_score(score, silent=False):
        """
        Callback function that gets called when a new score is detected

        Sends the score to the Discord bot API.
        Score types: "raw" (chart hash only) or "rich" (has metadata from currentsong.txt or OCR)
        silent=True suppresses Discord announcements (used for resync/reset backlog submissions)
        """
        mode = "offline" if silent else "live"
        logger.info(f"Score detected [{mode}]: [{score.chart_hash[:8]}...] "
                    f"{score.instrument_name} {score.difficulty_name} | "
                    f"{score.score:,}pts | {score.completion_percent:.1f}% | play #{score.play_count}")

        # Track score type - "raw" (chart hash only) or "rich" (has metadata)
        score_type = "raw"

        # Default to chart hash as fallback
        song_title = f"[{score.chart_hash[:8]}]"
        song_artist = ""
        song_charter = None

        # Notes data - only available via OCR (scoredata.bin numerator/denominator is NOT notes)
        # The values in scoredata.bin appear to be a different metric, not notes hit/total
        notes_hit = None
        notes_total = None

        # Best streak only available via OCR (deferred feature)
        best_streak = None

        # =====================================================
        # STEP 1: Read currentsong.txt (authoritative source)
        # =====================================================
        current_song = read_current_song()
        currentsong_used = False

        if current_song['title']:
            print_success("currentsong.txt data found:")
            print(f"    - Title: {current_song['title']}")
            if current_song['artist']:
                print(f"    - Artist: {current_song['artist']}")
            if current_song['charter']:
                print(f"    - Charter: {current_song['charter']}")

            # Use currentsong.txt as authoritative source
            song_title = current_song['title']
            song_artist = current_song['artist'] or ""
            song_charter = current_song['charter']
            score_type = "rich"
            currentsong_used = True
            logger.info(f"  Metadata [currentsong.txt]: '{song_title}' | artist='{song_artist}' | charter='{song_charter}'")
        else:
            logger.debug("  STEP1: currentsong.txt empty or cleared")

        # =====================================================
        # STEP 2: Attempt OCR for additional data (notes, streak)
        # =====================================================
        ocr_result = None

        if ocr_enabled and not silent:
            print_info("Attempting OCR capture of results screen...")
            _ocr_stats['attempts'] += 1
            _ocr_stats['last_attempt'] = time.time()
            ocr_result = capture_and_extract(delay_ms=500, save_debug=False)

            if ocr_result.success:
                _ocr_stats['successes'] += 1
                print_success("OCR extraction successful")
                logger.debug(f"  STEP2 OCR success: title='{ocr_result.song_title}' "
                             f"notes={ocr_result.notes_hit}/{ocr_result.notes_total} "
                             f"streak={ocr_result.streak}")

                # Show what OCR found
                print(f"    OCR parsed fields:")
                if ocr_result.song_title:
                    print(f"      - Song title: {ocr_result.song_title}")
                if ocr_result.artist:
                    print(f"      - Artist: {ocr_result.artist}")
                if ocr_result.notes_hit is not None:
                    print(f"      - Notes: {ocr_result.notes_hit}/{ocr_result.notes_total}")
                if ocr_result.streak is not None:
                    print(f"      - Best Streak: {ocr_result.streak}")
                if ocr_result.score is not None:
                    print(f"      - Score: {ocr_result.score:,}")

                score_type = "rich"

                # Only use OCR for title/artist if currentsong.txt was empty
                if not currentsong_used:
                    if ocr_result.song_title:
                        song_title = ocr_result.song_title
                    if ocr_result.artist:
                        song_artist = ocr_result.artist

                # Notes come from scoredata.bin now (authoritative)
                # Only use OCR for best streak (not available in scoredata.bin)
                if ocr_result.streak is not None:
                    best_streak = ocr_result.streak
            else:
                print_warning(f"OCR extraction failed: {ocr_result.error}")
                logger.debug(f"  STEP2 OCR failed: {ocr_result.error}")
                if not currentsong_used:
                    print("    (Score will be 'raw' with chart hash identifier only)")

        # =====================================================
        # STEP 3: Try songcache.bin for offline scores
        # =====================================================
        # If we still don't have metadata (offline score), try songcache.bin
        if score_type == "raw" and song_cache:
            try:
                print_info("Checking songcache.bin for song metadata...")
                # Look up song by chart hash in the cache dictionary
                cached_song = song_cache.get(score.chart_hash)

                if cached_song:
                    print_success("Song found in cache!")
                    print(f"    - Title: {cached_song.title}")
                    if cached_song.artist:
                        print(f"    - Artist: {cached_song.artist}")
                    if hasattr(cached_song, 'charter') and cached_song.charter:
                        print(f"    - Charter: {cached_song.charter}")

                    # Use songcache.bin metadata
                    song_title = cached_song.title if cached_song.title else song_title
                    song_artist = cached_song.artist if cached_song.artist else ""
                    if hasattr(cached_song, 'charter'):
                        song_charter = cached_song.charter
                    score_type = "rich"
                    logger.info(f"  Metadata [songcache.bin]: '{song_title}' | artist='{song_artist}'")
                else:
                    print_warning("Song not found in cache (may need to refresh songcache in Clone Hero)")
                    logger.debug("  STEP3: not found in songcache.bin")
            except Exception as e:
                print_warning(f"Failed to check songcache.bin: {e}")
                logger.warning(f"  STEP3 songcache.bin error: {e}")

        # =====================================================
        # STEP 3.5: Try chart index for offline scores (v2.6.4)
        # =====================================================
        # If still no metadata, check local chart index
        if score_type == "raw":
            print_info("Checking local chart index...")
            chart_info = lookup_chart_in_index(score.chart_hash)

            if chart_info:
                print_success("Chart found in local index!")
                print(f"    - Title: {chart_info['title']}")
                if chart_info.get('artist'):
                    print(f"    - Artist: {chart_info['artist']}")
                if chart_info.get('charter'):
                    print(f"    - Charter: {chart_info['charter']}")

                # Use chart index metadata
                song_title = chart_info['title']
                song_artist = chart_info.get('artist', '')
                song_charter = chart_info.get('charter')
                score_type = "rich"
                logger.info(f"  Metadata [chart index]: '{song_title}' | artist='{song_artist}' | charter='{song_charter}'")
            else:
                # Not in index - try on-demand scan
                logger.debug("  STEP3.5: not in chart index, starting on-demand scan")
                print_info("Chart not in index, attempting on-demand scan...")
                found_path = find_chart_by_hash_on_demand(score.chart_hash, max_duration=60)

                if found_path:
                    # Parse found chart
                    try:
                        ini_data = parse_song_ini(str(found_path))
                        if ini_data:
                            song_title = ini_data.get('name', ini_data.get('title', song_title))
                            song_artist = ini_data.get('artist', song_artist)
                            song_charter = ini_data.get('charter', ini_data.get('frets'))
                            score_type = "rich"
                            print_success("Metadata extracted from found chart!")
                            logger.info(f"  Metadata [on-demand scan]: '{song_title}' | "
                                        f"artist='{song_artist}' | charter='{song_charter}' | "
                                        f"path=.../{found_path.parent.name}")
                    except Exception as e:
                        logger.debug(f"Failed to parse found chart: {e}")
                else:
                    print_warning("Chart not found via on-demand scan")
                    print("    (Will submit with abbreviated hash)")
                    logger.warning(f"  STEP3.5: on-demand scan found no match for [{score.chart_hash[:8]}]")

        # =====================================================
        # STEP 4: Parse chart file for accurate note count (v2.6.0)
        # =====================================================
        total_notes_in_chart = None
        nps = None
        peak_nps = None

        try:
            print_info("Parsing chart file for note data...")
            chart_result = get_total_notes_from_chart(
                score.chart_hash,
                score.instrument_id,
                score.difficulty
            )

            if chart_result is not None:
                # Handle dict return value (v2.6.2+)
                if isinstance(chart_result, dict):
                    total_notes_in_chart = chart_result.get('total_notes')
                    nps = chart_result.get('nps')
                    peak_nps = chart_result.get('peak_nps')
                    chart_path_found = chart_result.get('chart_path')
                    nps_display = f"{nps:.1f}" if nps is not None else "N/A"
                    print_success(f"Chart parsed! Total notes: {total_notes_in_chart:,}, NPS: {nps_display}")
                    logger.info(f"  Chart parsed: {total_notes_in_chart} notes | "
                                f"NPS {nps_display} | peak {f'{peak_nps:.1f}' if peak_nps is not None else 'N/A'}")

                    # v2.6.6: If still "raw" (all earlier metadata steps failed), extract
                    # song.ini from the chart directory. chart_path_found is reliable here
                    # because find_chart_file_by_hash has no timeout (unlike the on-demand scan).
                    if score_type == "raw" and chart_path_found:
                        try:
                            ini_data = parse_song_ini(str(chart_path_found))
                            if ini_data:
                                new_title = ini_data.get('name', ini_data.get('title', ''))
                                if new_title:
                                    song_title = new_title
                                    song_artist = ini_data.get('artist', '')
                                    song_charter = ini_data.get('charter', ini_data.get('frets'))
                                    score_type = "rich"
                                    print_success("Song metadata resolved from chart directory!")
                                    logger.info(f"  Metadata [STEP4 song.ini]: '{song_title}' | "
                                                f"artist='{song_artist}' | charter='{song_charter}'")
                        except Exception as e:
                            logger.debug(f"Could not extract metadata from chart path: {e}")
                else:
                    # Backwards compatibility - old int return
                    total_notes_in_chart = chart_result
                    print_success(f"Chart parsed! Total notes: {total_notes_in_chart:,}")

                # Update notes_total from chart data (more reliable than OCR)
                notes_total = total_notes_in_chart

                # Detect Full Combo
                is_fc = (score.completion_percent >= 100.0)
            else:
                print_warning("Chart file not found or could not be parsed")
                print("    (Note counts will not be available for this score)")
                logger.warning(f"  STEP4: chart file not found for [{score.chart_hash[:8]}] "
                               f"- note data unavailable")
                is_fc = False

        except Exception as e:
            logger.warning(f"  STEP4: chart parsing exception: {e}", exc_info=True)
            print_warning(f"Chart parsing failed: {e}")
            is_fc = False

        # Calculate notes_hit from completion_percent if we have total notes
        if notes_hit is None and notes_total is not None and score.completion_percent > 0:
            notes_hit = int(notes_total * (score.completion_percent / 100.0))

        # =====================================================
        # STEP 4.5: Warning for unparsed scores (v2.6.4)
        # =====================================================
        # NOTE: No interactive input() here. This callback runs on the watchdog
        # observer thread while the main thread blocks on input("> ") in the
        # command loop. Concurrent input() calls crash the process on Windows.
        # Auto-submit with abbreviated hash; user can run 'scancharts' to resolve.
        if score_type == "raw":
            print_warning(f"Chart [{score.chart_hash[:8]}...] not found in metadata index")
            print_info("Submitting with hash identifier. Run 'scancharts' to add song metadata.")
            logger.warning(f"  No metadata resolved for [{score.chart_hash}] - submitting as raw hash")

        # Send score to bot API
        try:
            print()  # Newline for spacing
            print_info("Submitting to bot API...")
            logger.info(f"  Submitting to API: '{song_title}' | {score_type} | "
                        f"fc={is_fc} | notes={total_notes_in_chart} | silent={silent}")

            payload = {
                "auth_token": auth_token,
                "chart_hash": score.chart_hash,
                "instrument_id": score.instrument_id,
                "difficulty_id": score.difficulty,
                "score": score.score,
                "completion_percent": score.completion_percent,
                "stars": score.stars,
                "song_title": song_title,
                "song_artist": song_artist,
                "score_type": score_type,  # "raw" or "rich"
                "play_count": score.play_count  # Total plays for this chart
            }

            # Add enriched fields only if we have them (rich scores)
            if notes_hit is not None and notes_total is not None:
                payload["notes_hit"] = notes_hit
                payload["notes_total"] = notes_total
            if best_streak is not None:
                payload["best_streak"] = best_streak
            if song_charter:
                payload["song_charter"] = song_charter

            # v2.6.0: Add chart-parsed total notes for FC detection
            if total_notes_in_chart is not None:
                payload["total_notes_in_chart"] = total_notes_in_chart

            # v2.6.2: Add NPS data
            if nps is not None:
                payload["nps"] = nps
            if peak_nps is not None:
                payload["peak_nps"] = peak_nps

            # v2.6.5: Flag backlog submissions so the bot can silence announcements
            if silent:
                payload["silent"] = True

            response = requests.post(
                f"{get_bot_url()}/api/score",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()

                # v2.6.6: Server may block historical/backlog submissions
                if result.get('blocked'):
                    logger.info(f"  API: historical submission blocked by server policy "
                                f"[{score.chart_hash[:8]}] {score.instrument_name} {score.difficulty_name}")
                    if not silent:
                        print_warning("Server does not accept historical score submissions.")
                    return

                logger.info(f"  API OK: record={result.get('is_record_broken')} "
                            f"pb={result.get('is_high_score')} "
                            f"first_time={result.get('is_first_time_score')} "
                            f"fc={result.get('is_full_combo')}")

                # Track in session (v2.6.4)
                session_tracker.add_score({
                    'chart_hash': score.chart_hash,
                    'instrument_id': score.instrument_id,
                    'difficulty_id': score.difficulty,
                    'score': score.score,
                    'song_title': song_title,
                    'song_artist': song_artist,
                    'song_charter': song_charter,
                    'is_record': result.get('is_record_broken', False),
                    'is_fc': is_fc,
                    'is_new_fc': is_fc and result.get('is_high_score', False) and result.get('improvement', 0) == 0,  # New FC if first time FC
                    'is_personal_best': result.get('is_high_score', False),
                    'notes_hit': notes_hit,
                    'notes_total': notes_total,
                    'completion_percent': score.completion_percent,
                    'stars': score.stars,
                    'nps': nps
                })

                # Display score with API response (v2.6.2 format)
                print()  # Spacing before result display
                format_score_output(
                    score=score,
                    song_title=song_title,
                    song_artist=song_artist,
                    song_charter=song_charter,
                    notes_hit=notes_hit,
                    notes_total=notes_total,
                    total_notes_in_chart=total_notes_in_chart,
                    nps=nps,
                    is_fc=is_fc,
                    api_response=result
                )
            elif response.status_code == 401:
                print_error("Authentication failed - you may need to re-pair")
                logger.error(f"  API 401: authentication failed for [{score.chart_hash[:8]}]")
            else:
                print_error(f"Error submitting score: {response.status_code}")
                print(f"    {response.text}")
                logger.error(f"  API {response.status_code}: {response.text[:300]}")

        except requests.exceptions.ConnectionError:
            print_error("Could not connect to bot API")
            print("    Make sure the bot is running!")
            logger.error(f"  API connection failed: {get_bot_url()}")
        except Exception as e:
            print_error(f"Error sending score to API: {e}")
            logger.error(f"  API exception: {e}", exc_info=True)

        # Clear the song cache after processing - next song will re-populate it
        clear_song_cache()

    return on_new_score


def send_test_score(auth_token, song="Test Song", artist="", charter="", score=10000,
                    instrument=0, difficulty=3, stars=5, accuracy=95.0,
                    notes_hit=None, notes_total=None, best_streak=None, chart_hash=None):
    """Send a test score to the bot API with full metadata support"""
    # Use provided chart hash or generate one based on song name
    if chart_hash:
        hash_value = chart_hash
    else:
        hash_value = hashlib.md5(f"test_{song}".encode()).hexdigest()

    instrument_names = {0: "Lead Guitar", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
    difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

    print("\n" + "=" * 50)
    print("SENDING TEST SCORE")
    print("=" * 50)
    print(f"Song: {song}" + (f" - {artist}" if artist else ""))
    if charter:
        print(f"Charter: {charter}")
    print(f"Chart Hash: {hash_value}")
    print(f"Instrument: {instrument_names.get(instrument, f'Unknown ({instrument})')}")
    print(f"Difficulty: {difficulty_names.get(difficulty, f'Unknown ({difficulty})')}")
    print(f"Score: {score:,}")
    print(f"Accuracy: {accuracy:.2f}%")
    if notes_hit is not None and notes_total is not None:
        print(f"Notes: {notes_hit}/{notes_total}")
    if best_streak is not None:
        print(f"Best Streak: {best_streak}")
    print(f"Stars: {stars}")
    print("=" * 50)

    try:
        print("\n[*] Sending test score to bot API...")

        payload = {
            "auth_token": auth_token,
            "chart_hash": hash_value,
            "instrument_id": instrument,
            "difficulty_id": difficulty,
            "score": score,
            "completion_percent": accuracy,
            "stars": stars,
            "song_title": song,
            "song_artist": artist,
            "score_type": "rich" if (artist or notes_hit is not None) else "raw"
        }

        # Add optional fields
        if charter:
            payload["song_charter"] = charter
        if notes_hit is not None and notes_total is not None:
            payload["notes_hit"] = notes_hit
            payload["notes_total"] = notes_total
        if best_streak is not None:
            payload["best_streak"] = best_streak

        response = requests.post(
            f"{get_bot_url()}/api/score",
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            print_success("Test score submitted successfully!")
            if result.get('is_record_broken'):
                print_success("RECORD BROKEN! Check Discord for the announcement!")
                if result.get('previous_score'):
                    diff = score - result['previous_score']
                    print(f"    Beat previous record by {diff:,} points!")
            elif result.get('is_high_score'):
                print_success("New personal best! (First score on this chart)")
            else:
                print_info("Not a new high score")
        elif response.status_code == 401:
            print_error("Authentication failed - you may need to re-pair")
        else:
            print_error(f"Error submitting score: {response.status_code}")
            print(f"    {response.text}")

    except requests.exceptions.ConnectionError:
        print_error("Could not connect to bot API")
        print("    Make sure the bot is running!")
    except Exception as e:
        print_error(f"Error sending test score: {e}")


def debug_mode(auth_token):
    """Interactive debug mode for testing"""
    print_header("DEBUG MODE ACTIVE", width=60)

    print_plain("Available commands:")
    print_plain("")
    print_info("send_test_score [options]")
    print_plain("  -song \"Song Name\"     Song title (default: Test Song)", indent=1)
    print_plain("  -artist \"Artist\"      Artist name", indent=1)
    print_plain("  -charter \"Charter\"    Charter name", indent=1)
    print_plain("  -score 12345          Score value (default: 10000)", indent=1)
    print_plain("  -instrument 0         0=Lead, 1=Bass, 2=Rhythm, 3=Keys, 4=Drums", indent=1)
    print_plain("  -difficulty 3         0=Easy, 1=Medium, 2=Hard, 3=Expert", indent=1)
    print_plain("  -stars 5              Star rating (default: 5)", indent=1)
    print_plain("  -accuracy 95.0        Accuracy % (default: 95.0)", indent=1)
    print_plain("  -notes_hit 500        Notes hit", indent=1)
    print_plain("  -notes_total 520      Total notes", indent=1)
    print_plain("  -best_streak 200      Best streak", indent=1)
    print_plain("  -chart_hash \"abc...\"  Use specific chart hash", indent=1)
    print_plain("")
    print_info("testocr")
    print_plain("  Test OCR capture on Clone Hero window", indent=1)
    print_plain("")
    print_info("help")
    print_plain("  Show this help", indent=1)
    print_plain("")
    print_info("status")
    print_plain("  Show current settings and connection status", indent=1)
    print_plain("")
    print_info("paths")
    print_plain("  Show file paths and locations", indent=1)
    print_plain("")
    print_info("sysinfo")
    print_plain("  Show system information", indent=1)
    print_plain("")
    print_info("exit")
    print_plain("  Exit debug mode", indent=1)
    print("\n" + "=" * 60 + "\n")

    while True:
        try:
            cmd_input = input("debug> ").strip()
            if not cmd_input:
                continue

            # Parse the command
            try:
                parts = shlex.split(cmd_input)
            except ValueError as e:
                print_error(f"Parse error: {e}")
                continue

            if not parts:
                continue

            cmd = parts[0].lower()

            if cmd == "exit" or cmd == "quit":
                print_info("Exiting debug mode...")
                break

            elif cmd == "help":
                print("\nAvailable commands:")
                print("  send_test_score [options]")
                print("    -song \"Song Name\" -artist \"Artist\" -charter \"Charter\"")
                print("    -score 12345 -instrument 0 -difficulty 3 -stars 5 -accuracy 95.0")
                print("    -notes_hit 500 -notes_total 520 -best_streak 200 -chart_hash \"abc...\"")
                print("  testocr                 - Test OCR capture on Clone Hero window")
                print("  status                  - Show current settings and connection")
                print("  paths                   - Show file paths and locations")
                print("  sysinfo                 - Show system information")
                print("  help                    - Show this help")
                print("  exit                    - Exit debug mode")
                print("\nInstruments: 0=Lead, 1=Bass, 2=Rhythm, 3=Keys, 4=Drums")
                print("Difficulties: 0=Easy, 1=Medium, 2=Hard, 3=Expert\n")

            elif cmd == "status":
                print()
                print_header("CURRENT STATUS", width=60)

                # Connection status
                bot_url = get_bot_url()
                print_plain("Connection:")
                print_plain(f"  Server URL: {bot_url}", indent=1)
                try:
                    import requests as req_module
                    response = req_module.get(f"{bot_url}/health", timeout=5)
                    if response.status_code == 200:
                        print_success("Connected", indent=1)
                    else:
                        print_warning(f"Error (HTTP {response.status_code})", indent=1)
                except Exception as e:
                    print_error(f"Disconnected", indent=1)

                # Auth status
                print_plain("\nAuthentication:")
                if auth_token:
                    print_success("Paired", indent=1)
                else:
                    print_warning("Not paired", indent=1)

                # Settings
                settings = load_settings()
                print_plain("\nSettings:")
                ch_path = settings.get('clone_hero_path')
                if ch_path:
                    print_plain(f"  Clone Hero Path: {ch_path}", indent=1)
                else:
                    print_plain(f"  Clone Hero Path: Auto-detect", indent=1)
                ocr_enabled = settings.get('ocr_enabled', False)  # Default False
                print_plain(f"  OCR Enabled: {ocr_enabled}", indent=1)
                minimize = settings.get('minimize_to_tray', False)
                print_plain(f"  Minimize to Tray: {minimize}", indent=1)

                # Clone Hero directory paths
                print_plain("\nClone Hero Directories:")
                ch_data_dir = find_clone_hero_directory()
                if ch_data_dir:
                    print_success(f"  Data Dir:  {ch_data_dir}", indent=1)
                else:
                    print_error("  Data Dir:  Not found", indent=1)

                ch_docs_dir = get_clone_hero_documents_dir()
                if ch_docs_dir:
                    print_success(f"  Docs Dir:  {ch_docs_dir}", indent=1)
                else:
                    print_error("  Docs Dir:  Not found", indent=1)

                # Song folders (read from settings.ini + tracker fallback)
                print_plain("\nSong Folders:")
                _status_song_folders = []

                if ch_docs_dir:
                    _settings_ini = ch_docs_dir / 'settings.ini'
                    if _settings_ini.exists():
                        try:
                            _ini = configparser.ConfigParser()
                            _ini.read(str(_settings_ini))
                            for _sec in _ini.sections():
                                for _key in _ini.options(_sec):
                                    if _key.startswith('path') and _key[4:].isdigit():
                                        _folder = _ini.get(_sec, _key)
                                        if _folder:
                                            _status_song_folders.append(('settings.ini', _folder))
                        except Exception:
                            pass
                    else:
                        print_warning("  settings.ini not found", indent=1)

                _fallback_songs = settings.get('songs_folder')
                if _fallback_songs:
                    _status_song_folders.append(('tracker config', _fallback_songs))

                if _status_song_folders:
                    for _src, _folder in _status_song_folders:
                        _exists = Path(_folder).exists()
                        _label = f"  [{_src}] {_folder}"
                        if _exists:
                            print_success(_label, indent=1)
                        else:
                            print_error(f"{_label}  (NOT FOUND)", indent=1)
                else:
                    print_warning("  No song folders configured", indent=1)
                    print_plain("  (Run 'scancharts' to configure or check Clone Hero settings)", indent=1)

                # Version
                print_plain("\nVersion:")
                print_plain(f"  Client: v{VERSION}", indent=1)

                print("=" * 60 + "\n")

            elif cmd == "paths":
                print()
                print_header("FILE PATHS", width=60)

                # Settings file
                try:
                    settings_path = get_settings_path()
                    print_plain("Configuration:")
                    print_plain(f"  Settings: {settings_path}", indent=1)
                except Exception as e:
                    print_plain("Configuration:")
                    print_error(f"Error: {e}", indent=1)

                # Clone Hero paths
                try:
                    ch_dir = find_clone_hero_directory_internal()
                    print_plain("\nClone Hero:")
                    if ch_dir:
                        print_plain(f"  Data Directory: {ch_dir}", indent=1)
                        print_plain(f"  scoredata.bin: {ch_dir / 'scoredata.bin'}", indent=1)
                        print_plain(f"  currentsong.txt: {ch_dir / 'currentsong.txt'}", indent=1)
                        print_plain(f"  settings.ini: {ch_dir / 'settings.ini'}", indent=1)
                        print_plain(f"  songcache.bin: {ch_dir / 'songcache.bin'}", indent=1)
                    else:
                        print_warning("Not found", indent=1)
                except Exception as e:
                    print_plain("\nClone Hero:")
                    print_error(f"Error: {e}", indent=1)

                # Log file
                print_plain("\nLogs:")
                if sys.platform == 'win32':
                    log_path = Path.home() / 'Documents' / 'Clone Hero' / 'score_tracker.log'
                else:
                    log_path = Path.home() / '.clone_hero' / 'score_tracker.log'
                print_plain(f"  Log File: {log_path}", indent=1)

                print("=" * 60 + "\n")

            elif cmd == "sysinfo":
                print()
                print_header("SYSTEM INFORMATION", width=60)

                # Python version
                print_plain("Python:")
                print_plain(f"  Version: {sys.version.split()[0]}", indent=1)
                print_plain(f"  Executable: {sys.executable}", indent=1)

                # Platform
                print_plain("\nPlatform:")
                print_plain(f"  OS: {sys.platform}", indent=1)
                import platform
                print_plain(f"  System: {platform.system()} {platform.release()}", indent=1)
                print_plain(f"  Machine: {platform.machine()}", indent=1)

                # Client info
                print_plain("\nClient:")
                print_plain(f"  Version: v{VERSION}", indent=1)
                if getattr(sys, 'frozen', False):
                    print_plain(f"  Mode: Standalone executable", indent=1)
                    print_plain(f"  Exe Path: {sys.executable}", indent=1)
                else:
                    print_plain(f"  Mode: Python script", indent=1)
                    print_plain(f"  Script: {__file__}", indent=1)

                # Dependencies status
                print_plain("\nDependencies:")
                try:
                    import watchdog
                    print_success(f"watchdog: {watchdog.__version__}", indent=1)
                except:
                    print_warning("watchdog: Not installed", indent=1)

                try:
                    import requests
                    print_success(f"requests: {requests.__version__}", indent=1)
                except:
                    print_warning("requests: Not installed", indent=1)

                try:
                    import winocr
                    print_success("winocr: Installed", indent=1)
                except:
                    print_warning("winocr: Not installed (OCR unavailable)", indent=1)

                print("=" * 60 + "\n")

            elif cmd == "testocr":
                print("\n[*] Testing OCR capture...")
                print_info("Make sure Clone Hero is visible on screen")
                result = capture_and_extract(delay_ms=0, save_debug=True)

                print(f"\n  OCR Result:")
                print(f"  " + "-" * 40)
                print(f"  Success: {result.success}")
                if result.error:
                    print(f"  Error: {result.error}")

                if result.success:
                    print(f"\n  Parsed fields:")
                    if result.song_title:
                        print(f"    Song: {result.song_title}")
                    if result.artist:
                        print(f"    Artist: {result.artist}")
                    if result.notes_hit is not None:
                        print(f"    Notes: {result.notes_hit}/{result.notes_total}")
                    if result.score is not None:
                        print(f"    Score: {result.score:,}")
                    if result.accuracy is not None:
                        print(f"    Accuracy: {result.accuracy}%")
                    if result.streak is not None:
                        print(f"    Streak: {result.streak}")
                    if result.stars is not None:
                        print(f"    Stars: {result.stars}")

                print(f"\n  Raw OCR text:")
                print(f"  " + "-" * 40)
                if result.raw_text:
                    for line in result.raw_text.split('\n')[:20]:
                        if line.strip():
                            print(f"  {line}")
                else:
                    print("  (no text extracted)")
                print(f"  " + "-" * 40)
                print(f"\n  [*] Screenshot saved to: ocr_debug_capture.png")
                print()

            elif cmd == "send_test_score":
                # Parse arguments
                kwargs = {
                    "auth_token": auth_token,
                    "song": "Test Song",
                    "artist": "",
                    "charter": "",
                    "score": 10000,
                    "instrument": 0,
                    "difficulty": 3,
                    "stars": 5,
                    "accuracy": 95.0,
                    "notes_hit": None,
                    "notes_total": None,
                    "best_streak": None,
                    "chart_hash": None
                }

                i = 1
                while i < len(parts):
                    arg = parts[i]
                    if arg.startswith("-") and i + 1 < len(parts):
                        key = arg[1:].lower()
                        value = parts[i + 1]

                        if key == "song":
                            kwargs["song"] = value
                        elif key == "artist":
                            kwargs["artist"] = value
                        elif key == "charter":
                            kwargs["charter"] = value
                        elif key == "score":
                            kwargs["score"] = int(value)
                        elif key == "instrument":
                            kwargs["instrument"] = int(value)
                        elif key == "difficulty":
                            kwargs["difficulty"] = int(value)
                        elif key == "stars":
                            kwargs["stars"] = int(value)
                        elif key == "accuracy":
                            kwargs["accuracy"] = float(value)
                        elif key == "notes_hit":
                            kwargs["notes_hit"] = int(value)
                        elif key == "notes_total":
                            kwargs["notes_total"] = int(value)
                        elif key == "best_streak":
                            kwargs["best_streak"] = int(value)
                        elif key == "chart_hash":
                            kwargs["chart_hash"] = value
                        else:
                            print_error(f"Unknown argument: {arg}")

                        i += 2
                    else:
                        i += 1

                send_test_score(**kwargs)

            else:
                print_error(f"Unknown command: {cmd}")
                print("    Type 'help' for available commands")

        except KeyboardInterrupt:
            print("\n[*] Exiting debug mode...")
            break
        except Exception as e:
            print_error(f"Error: {e}")


def settings_menu():
    """Interactive settings menu"""
    while True:
        settings = load_settings()
        current_bot_url = settings.get('bot_url', DEFAULT_BOT_URL)
        current_ch_path = settings.get('clone_hero_path', 'Auto-detect')
        current_ocr = settings.get('ocr_enabled', False)
        current_tray = settings.get('minimize_to_tray', False)
        current_startup = settings.get('start_with_windows', False)

        # Check OCR availability
        ocr_ok, ocr_msg = check_ocr_available()
        ocr_status = "Enabled" if current_ocr else "Disabled"
        if current_ocr and not ocr_ok:
            ocr_status = f"Enabled ({ocr_msg})"

        print_header("SETTINGS", width=50)

        print_plain(f"[1] Bot Server URL")
        print_plain(f"    {current_bot_url}", indent=1)

        print_plain(f"\n[2] Clone Hero Path")
        print_plain(f"    {current_ch_path or 'Auto-detect'}", indent=1)

        print_plain(f"\n[3] OCR Capture")
        if current_ocr:
            print_success(f"{ocr_status}", indent=1)
        else:
            print_plain(f"    {ocr_status} (Recommended)", indent=1)

        print_plain(f"\n[4] Minimize to Tray")
        if current_tray:
            print_success("Enabled", indent=1)
        else:
            print_plain("    Disabled", indent=1)

        print_plain(f"\n[5] Start with Windows")
        if current_startup:
            print_success("Enabled", indent=1)
        else:
            print_plain("    Disabled", indent=1)

        # Bridge Integration option
        bridge_config = settings.get('bridge_integration', {})
        bridge_enabled = bridge_config.get('enabled', False)
        bridge_path = bridge_config.get('bridge_path', '')

        print_plain(f"\n[6] Bridge Integration")
        if bridge_enabled:
            print_success("Enabled", indent=1)
            if bridge_path:
                print_plain(f"    Path: {bridge_path}", indent=1)
        else:
            print_plain("    Disabled", indent=1)

        # v2.6.4: Session summary setting
        current_session_summary = settings.get('show_session_summary_on_exit', True)
        print_plain(f"\n[7] Show Session Summary on Exit")
        if current_session_summary:
            print_success("Enabled", indent=1)
        else:
            print_plain("    Disabled", indent=1)

        print_plain(f"\n[0] Back to main menu")
        print("\n" + "=" * 50)

        choice = input("Select option (0-7): ").strip()

        if choice == '0':
            break

        elif choice == '1':
            print(f"\nCurrent Bot URL: {current_bot_url}")
            print("Enter new URL (or press Enter to keep current):")
            new_url = input("> ").strip()

            if new_url:
                # Basic validation
                if not new_url.startswith('http'):
                    new_url = 'http://' + new_url

                # Test connection
                print_info(f"Testing connection to {new_url}...")
                try:
                    response = requests.get(f"{new_url}/health", timeout=5)
                    if response.status_code == 200:
                        print_success("Connection successful!")
                        settings['bot_url'] = new_url
                        save_settings(settings)
                        print_success("Settings saved!")
                    else:
                        print_warning(f"Server responded with status {response.status_code}")
                        confirm = input("Save anyway? (y/n): ").strip().lower()
                        if confirm == 'y':
                            settings['bot_url'] = new_url
                            save_settings(settings)
                            print_success("Settings saved!")
                except requests.exceptions.ConnectionError:
                    print_error("Could not connect to server")
                    confirm = input("Save anyway? (y/n): ").strip().lower()
                    if confirm == 'y':
                        settings['bot_url'] = new_url
                        save_settings(settings)
                        print_success("Settings saved!")

        elif choice == '2':
            print(f"\nCurrent Clone Hero Path: {current_ch_path or 'Auto-detect'}")
            auto_path = find_clone_hero_directory_internal()
            if auto_path:
                print(f"Auto-detected path: {auto_path}")

            print("\nEnter custom path (or press Enter for auto-detect):")
            new_path = input("> ").strip()

            if new_path:
                # Validate path exists
                path = Path(new_path)
                if path.exists():
                    # Check if it looks like Clone Hero directory
                    if (path / 'scoredata.bin').exists() or (path / 'songcache.bin').exists():
                        settings['clone_hero_path'] = str(path)
                        save_settings(settings)
                        print_success("Settings saved!")
                    else:
                        print_warning("This doesn't look like a Clone Hero data directory")
                        print("    (No scoredata.bin or songcache.bin found)")
                        confirm = input("Save anyway? (y/n): ").strip().lower()
                        if confirm == 'y':
                            settings['clone_hero_path'] = str(path)
                            save_settings(settings)
                            print_success("Settings saved!")
                else:
                    print_error(f"Path does not exist: {new_path}")
            else:
                # Reset to auto-detect
                settings['clone_hero_path'] = None
                save_settings(settings)
                print_success("Reset to auto-detect")

        elif choice == '3':
            current_ocr = settings.get('ocr_enabled', False)
            print(f"\nOCR Capture is currently: {'Enabled' if current_ocr else 'Disabled'}")
            print("\nOCR captures the Clone Hero results screen after each song")
            print("to extract artist names and note counts.")
            print("\nUses Windows built-in OCR (Windows 10/11).")

            # Check OCR status
            ocr_ok, ocr_msg = check_ocr_available()
            print(f"\nOCR status: {ocr_msg}")

            print(f"\n  1. Enable OCR")
            print(f"  2. Disable OCR")
            print(f"  0. Cancel")

            ocr_choice = input("\nSelect option: ").strip()
            if ocr_choice == '1':
                settings['ocr_enabled'] = True
                save_settings(settings)
                print_success("OCR enabled")
            elif ocr_choice == '2':
                settings['ocr_enabled'] = False
                save_settings(settings)
                print_success("OCR disabled")

        elif choice == '4':
            current_tray = settings.get('minimize_to_tray', False)
            print(f"\nMinimize to Tray is currently: {'Enabled' if current_tray else 'Disabled'}")
            print("\nWhen enabled, closing the window will minimize to the system tray")
            print("instead of exiting. Right-click the tray icon to restore or exit.")
            print("\nNote: Requires restart to take effect.")

            print(f"\n  1. Enable Minimize to Tray")
            print(f"  2. Disable Minimize to Tray")
            print(f"  0. Cancel")

            tray_choice = input("\nSelect option: ").strip()
            if tray_choice == '1':
                settings['minimize_to_tray'] = True
                save_settings(settings)
                print_success("Minimize to Tray enabled (restart required)")
            elif tray_choice == '2':
                settings['minimize_to_tray'] = False
                save_settings(settings)
                print_success("Minimize to Tray disabled")

        elif choice == '5':
            current_startup = settings.get('start_with_windows', False)
            print(f"\nStart with Windows is currently: {'Enabled' if current_startup else 'Disabled'}")
            print("\nWhen enabled, the tracker will automatically start when Windows boots.")

            print(f"\n  1. Enable Start with Windows")
            print(f"  2. Disable Start with Windows")
            print(f"  0. Cancel")

            startup_choice = input("\nSelect option: ").strip()
            if startup_choice == '1':
                success = set_windows_startup(True)
                if success:
                    settings['start_with_windows'] = True
                    save_settings(settings)
                    print_success("Start with Windows enabled")
                else:
                    print_error("Failed to enable startup - see error above")
            elif startup_choice == '2':
                success = set_windows_startup(False)
                if success:
                    settings['start_with_windows'] = False
                    save_settings(settings)
                    print_success("Start with Windows disabled")
                else:
                    print_error("Failed to disable startup - see error above")

        elif choice == '6':
            from client.bridge_integration import run_bridge_setup, is_protocol_registered, unregister_protocol, is_bridge_installed

            bridge_config = settings.get('bridge_integration', {})
            bridge_enabled = bridge_config.get('enabled', False)

            print(f"\nBridge Integration is currently: {'Enabled' if bridge_enabled else 'Disabled'}")
            print("\nBridge Integration allows you to search for charts directly in the")
            print("Bridge desktop app by clicking links in Discord announcements.")
            print("\nRequires:")
            print("  - Bridge desktop app installed")
            print("  - Protocol registration (chbridge://)")
            print("  - Shortcut modifications for remote debugging")

            print(f"\n  1. Enable Bridge Integration")
            print(f"  2. Disable Bridge Integration")
            print(f"  0. Cancel")

            bridge_choice = input("\nSelect option: ").strip()

            if bridge_choice == '1':
                # Enable Bridge Integration - run setup
                print_info("\nRunning Bridge integration setup...")

                # Get tracker exe path
                import sys
                if getattr(sys, 'frozen', False):
                    # Running as compiled exe
                    tracker_exe = sys.executable
                else:
                    # Running from source (for testing)
                    tracker_exe = str(Path(__file__).resolve())

                # Check if Bridge is installed first
                is_installed, bridge_path = is_bridge_installed()

                if not is_installed:
                    print_warning("\nBridge not found in common installation locations.")
                    print("Please enter the full path to Bridge.exe:")
                    print("(or press Enter to cancel)")

                    custom_path = input("> ").strip()

                    if custom_path:
                        bridge_path = Path(custom_path)
                        if not bridge_path.exists():
                            print_error(f"Path does not exist: {custom_path}")
                            continue
                        elif not bridge_path.name.lower() == 'bridge.exe':
                            print_error("File must be Bridge.exe")
                            continue
                    else:
                        print_info("Setup cancelled")
                        continue

                # Run setup
                success, message = run_bridge_setup(tracker_exe)

                if success:
                    # Save settings
                    if 'bridge_integration' not in settings:
                        settings['bridge_integration'] = {}

                    settings['bridge_integration']['enabled'] = True
                    settings['bridge_integration']['bridge_path'] = str(bridge_path)
                    settings['bridge_integration']['protocol_registered'] = True
                    settings['bridge_integration']['setup_completed'] = True

                    save_settings(settings)
                    print_success(f"\n{message}")
                    print_success("Bridge Integration enabled")
                else:
                    print_error(f"\nSetup failed: {message}")

            elif bridge_choice == '2':
                # Disable Bridge Integration
                print_info("\nDisabling Bridge Integration...")

                # Optionally unregister protocol
                if is_protocol_registered():
                    print("\nDo you want to unregister the chbridge:// protocol?")
                    print("(Shortcuts will keep remote debugging flag)")
                    unregister = input("Unregister protocol? (y/n): ").strip().lower()

                    if unregister == 'y':
                        if unregister_protocol():
                            print_success("Protocol unregistered")
                        else:
                            print_warning("Failed to unregister protocol")

                # Update settings
                if 'bridge_integration' not in settings:
                    settings['bridge_integration'] = {}

                settings['bridge_integration']['enabled'] = False
                save_settings(settings)
                print_success("Bridge Integration disabled")

        elif choice == '7':
            current_session_summary = settings.get('show_session_summary_on_exit', True)
            print(f"\nShow Session Summary on Exit is currently: {'Enabled' if current_session_summary else 'Disabled'}")
            print("\nWhen enabled, typing 'quit' will show a summary of your session")
            print("before exiting (if you submitted any scores).")

            print(f"\n  1. Enable Session Summary on Exit")
            print(f"  2. Disable Session Summary on Exit")
            print(f"  0. Cancel")

            summary_choice = input("\nSelect option: ").strip()
            if summary_choice == '1':
                settings['show_session_summary_on_exit'] = True
                save_settings(settings)
                print_success("Session Summary on Exit enabled")
            elif summary_choice == '2':
                settings['show_session_summary_on_exit'] = False
                save_settings(settings)
                print_success("Session Summary on Exit disabled")

        else:
            print_warning("Invalid option")


# ============================================================================
# AUTO-UPDATE FUNCTIONS
# ============================================================================

def check_for_updates_silent():
    """
    Check for updates silently (for tray menu).
    Returns tuple of (version, download_url) or (None, None)
    """
    update_info = check_for_updates()
    if update_info:
        return (update_info["version"], update_info["download_url"])
    return (None, None)


def download_update_from_url(download_url, version):
    """
    Download update from URL (for tray menu).
    Returns path to downloaded exe or None.
    """
    update_info = {
        "version": version,
        "download_url": download_url,
        "filename": f"CloneHeroScoreTracker_v{version}.exe"
    }
    return download_update(update_info)


def apply_update(new_exe_path):
    """
    Apply the update by restarting with the new exe.
    """
    import subprocess
    try:
        # Start the new exe
        subprocess.Popen([str(new_exe_path)])
        # Exit current process
        sys.exit(0)
    except Exception as e:
        raise Exception(f"Failed to start new version: {e}")


def check_for_updates() -> dict:
    """
    Check GitHub releases for a newer version.

    Returns:
        dict with update info if available, None if up to date or check failed
    """
    try:
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"}
        )

        if response.status_code != 200:
            return None

        release = response.json()
        latest_version = release["tag_name"].lstrip("v")

        # Compare versions
        if latest_version > VERSION:
            # Find the client asset (look for "Tracker" in name, prefer .exe over .zip)
            download_url = None
            filename = None
            for asset in release.get("assets", []):
                if "Tracker" in asset["name"]:
                    # Prefer .exe, but accept .zip
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        filename = asset["name"]
                        break  # Found exe, stop looking
                    elif asset["name"].endswith(".zip") and not download_url:
                        download_url = asset["browser_download_url"]
                        filename = asset["name"]
                        # Keep looking in case there's an exe

            if download_url:
                return {
                    "version": latest_version,
                    "download_url": download_url,
                    "filename": filename,
                    "release_notes": release.get("body", ""),
                    "release_url": release["html_url"]
                }

        return None

    except Exception as e:
        # Silent fail - don't block startup for update check
        return None


def download_update(update_info: dict):
    """
    Download the new version exe (or zip and extract).

    Returns:
        Path to downloaded/extracted exe, or None if failed
    """
    try:
        # Determine download location (same folder as current exe)
        if getattr(sys, 'frozen', False):
            current_dir = Path(sys.executable).parent
        else:
            current_dir = Path(__file__).parent

        filename = update_info["filename"]
        is_zip = filename.endswith(".zip")

        # Determine final exe name
        if is_zip:
            exe_name = filename.replace(".zip", "")
        else:
            exe_name = filename

        new_exe_path = current_dir / exe_name

        # Don't re-download if already exists
        if new_exe_path.exists():
            print_success(f"Update already downloaded: {new_exe_path.name}")
            return new_exe_path

        print_info(f"Downloading v{update_info['version']}...")

        # Download file
        response = requests.get(
            update_info["download_url"],
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        if is_zip:
            # Download zip to temp location, then extract
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_path = tmp_file.name
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        print(f"\r[*] Downloading... {percent}%", end="", flush=True)

            print(f"\r[*] Downloading... Done!      ")
            print_info("Extracting...")

            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                exe_files = [f for f in zip_ref.namelist() if f.endswith('.exe')]
                if exe_files:
                    zip_ref.extract(exe_files[0], current_dir)
                    extracted_path = current_dir / exe_files[0]
                    if extracted_path != new_exe_path and extracted_path.exists():
                        if new_exe_path.exists():
                            new_exe_path.unlink()
                        extracted_path.rename(new_exe_path)

            # Clean up temp zip
            try:
                os.unlink(tmp_path)
            except:
                pass
        else:
            # Download exe directly
            with open(new_exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        print(f"\r[*] Downloading... {percent}%", end="", flush=True)

            print(f"\r[*] Downloading... Done!      ")

        print_success(f"Download complete: {new_exe_path.name}")
        return new_exe_path

    except Exception as e:
        print_error(f"Download failed: {e}")
        return None


def prompt_for_update(update_info: dict) -> bool:
    """
    Show update prompt and ask user if they want to update.

    Returns:
        True if user wants to update, False otherwise
    """
    print_header("UPDATE AVAILABLE", width=50)
    print(f"\n  Current version: v{VERSION}")
    print(f"  New version:     v{update_info['version']}")

    # Show release notes if available (truncated)
    if update_info.get("release_notes"):
        print("\n  What's new:")
        notes = update_info["release_notes"].strip().split("\n")
        for line in notes[:8]:  # First 8 lines
            if line.strip():
                print(f"    {line}")
        if len(notes) > 8:
            print(f"    ...")

    print("\n" + "=" * 50)

    choice = input("\nDownload update now? (y/n): ").strip().lower()
    return choice in ('y', 'yes')


def show_update_complete_message(new_exe_path: Path):
    """Show instructions after update download"""
    print("\n" + "=" * 50)
    print("UPDATE DOWNLOADED")
    print("=" * 50)
    print(f"\n  New version saved to:")
    print(f"  {new_exe_path}")
    print(f"\n  To complete the update:")
    print(f"    1. Close this program (type 'quit')")
    print(f"    2. Run: {new_exe_path.name}")
    print(f"    3. (Optional) Delete the old version")
    print("\n" + "=" * 50)


def check_and_prompt_update(silent_if_current: bool = False) -> bool:
    """
    Check for updates and prompt user if available.

    Args:
        silent_if_current: If True, don't print anything if already up to date

    Returns:
        True if update was downloaded, False otherwise
    """
    if not silent_if_current:
        print_info("Checking for updates...")

    update_info = check_for_updates()

    if update_info:
        if prompt_for_update(update_info):
            new_exe = download_update(update_info)
            if new_exe:
                show_update_complete_message(new_exe)
                return True
            else:
                print_warning("Update download failed. Continuing with current version.")
    elif not silent_if_current:
        print_success("You're running the latest version!")

    return False


def show_ascii_logo():
    """Display ASCII art logo with dynamic version"""
    try:
        # Try to display full Unicode logo
        print()
        print("        ██████╗██╗  ██╗    ██╗  ██╗██╗███████╗ ██████╗ ██████╗ ██████╗ ███████╗")
        print("       ██╔════╝██║  ██║    ██║  ██║██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝")
        print("       ██║     ███████║    ███████║██║███████╗██║     ██║   ██║██████╔╝█████╗  ")
        print("       ██║     ██╔══██║    ██╔══██║██║╚════██║██║     ██║   ██║██╔══██╗██╔══╝  ")
        print("       ╚██████╗██║  ██║    ██║  ██║██║███████║╚██████╗╚██████╔╝██║  ██║███████╗")
        print("        ╚═════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝")
        print()
        print(f"                            SCORE TRACKER v{VERSION}")
        print("                         Track • Compete • Dominate")
        print()
        print("=" * 80)
        print()
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback to simple ASCII if Unicode fails
        print()
        print("=" * 80)
        print(f"        CLONE HERO HIGH SCORE TRACKER v{VERSION}")
        print("                  Track • Compete • Dominate")
        print("=" * 80)
        print()


def show_welcome_message():
    """Show welcome message for first-time users"""
    print("\n" + "=" * 50)
    print("   WELCOME TO CLONE HERO HIGH SCORE TRACKER!")
    print("=" * 50)
    print("""
This program monitors your Clone Hero scores and
automatically submits them to a Discord scoreboard.

HOW IT WORKS:
1. Connect to a Discord bot server
2. Link your Discord account with a pairing code
3. Play Clone Hero - scores are tracked automatically!
4. High scores are announced in Discord

Your scores compete with others on the same server.
Break a record and everyone gets notified!
""")
    print("=" * 50)
    input("\nPress Enter to continue...")


def check_connection_with_retry(bot_url, max_retries=3):
    """Check bot connection with visible retry mechanism"""
    for attempt in range(1, max_retries + 1):
        try:
            print_info(f"Connecting to server... (attempt {attempt}/{max_retries})")
            response = requests.get(f"{bot_url}/health", timeout=5)
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Server responded with status {response.status_code}"
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                print(f"    Connection failed, retrying in 2 seconds...")
                time.sleep(2)
            else:
                return False, "Could not connect to server"
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"    Connection timed out, retrying...")
                time.sleep(1)
            else:
                return False, "Connection timed out"
    return False, "Max retries exceeded"


def get_lock_file_path():
    """Get path to the lock file"""
    import tempfile
    return Path(tempfile.gettempdir()) / 'clone_hero_tracker.lock'


def is_process_running(pid):
    """
    Check if a process with given PID is running

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise
    """
    if sys.platform == 'win32':
        # Use tasklist command - more reliable than OpenProcess
        try:
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # If process exists, tasklist output will contain the PID
            return str(pid) in result.stdout
        except:
            # Fallback to OpenProcess if tasklist fails
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            except:
                return False
    else:
        # Unix-like systems
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def acquire_instance_lock():
    """
    Acquire single-instance lock to prevent multiple clients running

    Returns:
        tuple: (success: bool, message: str, stale_pid: int or None)
    """
    lock_file = get_lock_file_path()

    try:
        # Check if lock file exists
        if lock_file.exists():
            # Read PID from lock file
            try:
                pid = int(lock_file.read_text().strip())

                # Check if process is still running
                if is_process_running(pid):
                    # Process is actually running
                    return (False, f"Another instance is running (PID {pid})", pid)

                # Process not running - stale lock
                print_warning(f"Removed stale lock file (PID {pid} not running)")
                lock_file.unlink()

            except (ValueError, IOError) as e:
                # Invalid lock file - remove it
                print_warning(f"Removed invalid lock file: {e}")
                try:
                    lock_file.unlink()
                except:
                    pass

        # Create new lock file with our PID
        lock_file.write_text(str(os.getpid()))
        return (True, "Lock acquired", None)

    except Exception as e:
        # If we can't create lock, allow running (better than blocking user)
        print_warning(f"Could not create instance lock: {e}")
        return (True, "Lock creation failed, allowing start", None)


def release_instance_lock():
    """Release the single-instance lock"""
    lock_file = get_lock_file_path()
    try:
        if lock_file.exists():
            # Only remove if it's our PID
            try:
                pid = int(lock_file.read_text().strip())
                if pid == os.getpid():
                    lock_file.unlink()
            except:
                pass
    except:
        pass


# Records Report Generation (v2.6.4)
INSTRUMENTS = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums", 7: "GHLGuitar", 8: "GHLBass", 9: "Vocals", 10: "CoDrums"}
DIFFICULTIES = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}


def format_records_text(data: dict) -> str:
    """Format records report as human-readable text"""
    from datetime import datetime

    lines = []
    lines.append("=" * 60)
    lines.append("YOUR RECORD HOLDINGS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Player: {data['user']['discord_username']}")
    lines.append(f"Total Records Held: {data['total_records']}")
    lines.append("=" * 60)
    lines.append("")

    if data['total_records'] == 0:
        lines.append("You don't hold any #1 records yet.")
        lines.append("Keep playing to earn your first record!")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    for i, record in enumerate(data['records'], 1):
        lines.append(f"RECORD #{i}")
        lines.append("-" * 8)

        # Song info
        lines.append(f"Song: {record['song_title']}")
        if record.get('song_artist'):
            lines.append(f"Artist: {record['song_artist']}")
        if record.get('song_charter'):
            lines.append(f"Charter: {record['song_charter']}")
        if record.get('song_album'):
            lines.append(f"Album: {record['song_album']}")
        if record.get('song_genre'):
            lines.append(f"Genre: {record['song_genre']}")
        lines.append("")

        # Chart details
        lines.append("Chart Details:")
        inst_name = INSTRUMENTS.get(record['instrument_id'], f"Unknown({record['instrument_id']})")
        diff_name = DIFFICULTIES.get(record['difficulty_id'], f"Unknown({record['difficulty_id']})")
        lines.append(f"  Instrument: {inst_name}")
        lines.append(f"  Difficulty: {diff_name}")

        if record.get('chart_nps'):
            if record.get('chart_peak_nps'):
                lines.append(f"  NPS: {record['chart_nps']:.1f} (Peak: {record['chart_peak_nps']:.1f})")
            else:
                lines.append(f"  NPS: {record['chart_nps']:.1f}")

        if record.get('chart_total_notes'):
            lines.append(f"  Total Notes: {record['chart_total_notes']:,}")

        if record.get('song_length_ms'):
            length_sec = record['song_length_ms'] / 1000
            minutes = int(length_sec // 60)
            seconds = int(length_sec % 60)
            lines.append(f"  Song Length: {minutes}m {seconds}s")

        lines.append("")

        # Your score
        lines.append("Your Score:")
        lines.append(f"  Score: {record['score']:,} pts")

        if record.get('notes_hit') and record.get('notes_total'):
            accuracy = (record['notes_hit'] / record['notes_total']) * 100
            lines.append(f"  Accuracy: {accuracy:.1f}% ({record['notes_hit']}/{record['notes_total']} notes)")

        fc_status = "Yes" if record.get('is_full_combo') else "No"
        stars = "⭐" * record.get('stars', 0) if record.get('stars') else ""
        lines.append(f"  Full Combo: {fc_status} {stars}")

        if record.get('submitted_at'):
            # Parse timestamp and calculate days ago
            try:
                sub_time = datetime.fromisoformat(record['submitted_at'].replace(' ', 'T'))
                now = datetime.now()
                delta = now - sub_time
                days = delta.days
                hours = delta.seconds // 3600

                if days > 0:
                    time_ago = f"{days} day{'s' if days != 1 else ''} ago"
                elif hours > 0:
                    time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
                else:
                    time_ago = "today"

                lines.append(f"  Achieved: {sub_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago})")

                # Calculate held duration
                lines.append(f"  Held For: {days} days, {hours} hours")
            except:
                lines.append(f"  Achieved: {record['submitted_at']}")

        if record.get('play_count'):
            lines.append(f"  Play Count: {record['play_count']}")

        lines.append("")

        # Previous record
        if record.get('previous_score'):
            lines.append("Previous Record:")
            lines.append(f"  Score: {record['previous_score']:,} pts")
            if record.get('previous_holder'):
                lines.append(f"  Holder: {record['previous_holder']}")
            if record.get('previous_set_at'):
                lines.append(f"  Set: {record['previous_set_at']}")

            # Calculate improvement
            improvement = record['score'] - record['previous_score']
            improvement_pct = (improvement / record['previous_score']) * 100
            lines.append(f"  Improvement: +{improvement_pct:.1f}% (+{improvement:,} pts)")
        else:
            lines.append("Previous Record: None (You set the first score!)")

        lines.append("")

        # Chart hash and link
        if record.get('chart_hash'):
            lines.append(f"Chart Hash: [{record['chart_hash'][:16]}...]")
            # Generate Enchor.us link
            enchor_url = f"https://enchor.us/?s={record['chart_hash']}&i={record['instrument_id']}&d={record['difficulty_id']}"
            lines.append(f"Enchor.us: {enchor_url}")

        lines.append("")
        lines.append("")

    lines.append("=" * 60)
    lines.append("End of Report")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_records_csv(data: dict) -> str:
    """Format records report as CSV"""
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Rank', 'Song', 'Artist', 'Charter', 'Album', 'Genre',
        'Instrument', 'Difficulty', 'Score', 'Accuracy', 'FC', 'Stars',
        'Notes Hit', 'Notes Total', 'NPS', 'Peak NPS', 'Song Length (ms)',
        'Achieved Date', 'Held Duration (days)', 'Play Count',
        'Previous Score', 'Previous Holder', 'Improvement %',
        'Chart Hash', 'Enchor Link'
    ])

    # Data rows
    for i, record in enumerate(data['records'], 1):
        inst_name = INSTRUMENTS.get(record['instrument_id'], f"Unknown({record['instrument_id']})")
        diff_name = DIFFICULTIES.get(record['difficulty_id'], f"Unknown({record['difficulty_id']})")

        # Calculate accuracy
        accuracy = ""
        if record.get('notes_hit') and record.get('notes_total'):
            accuracy = f"{(record['notes_hit'] / record['notes_total']) * 100:.1f}"

        # Calculate held duration in days
        held_days = ""
        if record.get('submitted_at'):
            try:
                from datetime import datetime
                sub_time = datetime.fromisoformat(record['submitted_at'].replace(' ', 'T'))
                now = datetime.now()
                delta = now - sub_time
                held_days = f"{delta.days + (delta.seconds / 86400):.2f}"
            except:
                pass

        # Calculate improvement
        improvement_pct = ""
        if record.get('previous_score'):
            improvement = record['score'] - record['previous_score']
            improvement_pct = f"{(improvement / record['previous_score']) * 100:.1f}"

        # Enchor.us link
        enchor_url = ""
        if record.get('chart_hash'):
            enchor_url = f"https://enchor.us/?s={record['chart_hash']}&i={record['instrument_id']}&d={record['difficulty_id']}"

        writer.writerow([
            i,
            record.get('song_title', ''),
            record.get('song_artist', ''),
            record.get('song_charter', ''),
            record.get('song_album', ''),
            record.get('song_genre', ''),
            inst_name,
            diff_name,
            record.get('score', ''),
            accuracy,
            'Yes' if record.get('is_full_combo') else 'No',
            record.get('stars', ''),
            record.get('notes_hit', ''),
            record.get('notes_total', ''),
            f"{record.get('chart_nps', ''):.1f}" if record.get('chart_nps') else '',
            f"{record.get('chart_peak_nps', ''):.1f}" if record.get('chart_peak_nps') else '',
            record.get('song_length_ms', ''),
            record.get('submitted_at', ''),
            held_days,
            record.get('play_count', ''),
            record.get('previous_score', ''),
            record.get('previous_holder', ''),
            improvement_pct,
            record.get('chart_hash', ''),
            enchor_url
        ])

    return output.getvalue()


def format_records_json(data: dict) -> str:
    """Format records report as JSON (pretty-printed)"""
    return json.dumps(data, indent=2, ensure_ascii=False)


def recordsreport_command(format_option=None):
    """
    Generate comprehensive records report showing all #1 records held by user

    Args:
        format_option: Optional format override ('text', 'csv', 'json', 'all')
    """
    import os
    from datetime import datetime

    print_header("GENERATE RECORDS REPORT")
    print()
    print("This will generate a comprehensive report of all records")
    print("you currently hold (#1 position) with full metadata.")
    print()

    # Check auth token
    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    # Fetch records from server
    print("[*] Fetching your records from server...")
    try:
        response = requests.get(
            f"{bot_url}/api/user_records",
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Server error: HTTP {response.status_code}")
            return

        data = response.json()
        if not data.get('success'):
            print_error(f"Server error: {data.get('error', 'Unknown')}")
            return

        total_records = data.get('total_records', 0)
        print_success(f"Found {total_records} records!")

        if total_records == 0:
            print_info("You don't hold any #1 records yet.")
            print_info("Keep playing to earn your first record!")
            print()
            return

    except Exception as e:
        print_error(f"Failed to fetch records: {e}")
        return

    # Determine format choice
    if format_option:
        # Command-line option provided
        format_map = {
            'text': '1',
            'csv': '2',
            'json': '3',
            'all': '4'
        }
        choice = format_map.get(format_option.lower(), '1')
    else:
        # Interactive mode
        print()
        print("Select output format:")
        print("  1. Text (human-readable, default)")
        print("  2. CSV (spreadsheet)")
        print("  3. JSON (programmatic)")
        print("  4. All formats")
        print()
        choice = input("Choice [1]: ").strip() or "1"

    # Generate output directory
    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    output_dir = ch_dir / 'records'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    username = data['user']['discord_username'].replace(' ', '_')

    generated_files = []

    print()
    print("[*] Generating report...")

    # Generate requested formats
    if choice in ('1', '4'):
        # Text format
        text_content = format_records_text(data)
        text_file = output_dir / f"{username}_records_{timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        generated_files.append(str(text_file))
        print_success(f"Text report: {text_file}")

    if choice in ('2', '4'):
        # CSV format
        csv_content = format_records_csv(data)
        csv_file = output_dir / f"{username}_records_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)
        generated_files.append(str(csv_file))
        print_success(f"CSV report: {csv_file}")

    if choice in ('3', '4'):
        # JSON format
        json_content = format_records_json(data)
        json_file = output_dir / f"{username}_records_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        generated_files.append(str(json_file))
        print_success(f"JSON report: {json_file}")

    print()
    print_success(f"Report generation complete! ({len(generated_files)} file(s) created)")
    print()
    print("Location: " + str(output_dir))
    print()


def session_command():
    """Display current session statistics (v2.6.4)"""
    from datetime import datetime, timedelta

    print_header("CURRENT SESSION SUMMARY")
    print()

    # Check if there's any activity
    if not session_tracker.has_activity():
        print_info("No scores submitted this session yet.")
        print()
        print("Play some Clone Hero and submit scores to see session stats!")
        print()
        return

    # Session duration
    hours, minutes, seconds = session_tracker.get_session_duration()
    if hours > 0:
        duration_str = f"{hours}h {minutes}m"
    elif minutes > 0:
        duration_str = f"{minutes}m {seconds}s"
    else:
        duration_str = f"{seconds}s"

    start_time = datetime.fromtimestamp(session_tracker.session_start)
    time_ago = datetime.now() - start_time
    if time_ago.total_seconds() < 120:
        time_ago_str = "just now"
    elif time_ago.total_seconds() < 3600:
        time_ago_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
    else:
        time_ago_str = f"{int(time_ago.total_seconds() / 3600)} hours ago"

    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_ago_str})")
    print(f"Duration: {duration_str}")
    print()

    # Overall stats
    print(f"{Fore.CYAN}SCORES THIS SESSION{Style.RESET_ALL}")
    print(f"  Total Scores: {len(session_tracker.scores)}")
    if session_tracker.records_broken:
        print(f"  {Fore.RED}New Records: {len(session_tracker.records_broken)} 🏆{Style.RESET_ALL}")
    if session_tracker.new_fcs:
        print(f"  {Fore.GREEN}New FCs: {len(session_tracker.new_fcs)} ⭐{Style.RESET_ALL}")
    if session_tracker.personal_bests:
        print(f"  Personal Bests: {len(session_tracker.personal_bests)}")
    print()

    # Recent scores (last 5)
    print(f"{Fore.CYAN}RECENT SCORES (Last 5){Style.RESET_ALL}")
    recent = session_tracker.get_recent_scores(limit=5)
    for score in recent:
        timestamp = datetime.fromtimestamp(score['timestamp'])
        time_str = timestamp.strftime('%H:%M')

        # Build score line
        song = score.get('song_title', f"[{score['chart_hash'][:8]}]")
        if score.get('song_artist'):
            song += f" - {score['song_artist']}"

        instrument_names = {
            0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums",
            5: "GHLGuitar", 6: "GHLBass"
        }
        difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

        inst = instrument_names.get(score['instrument_id'], f"Inst{score['instrument_id']}")
        diff = difficulty_names.get(score['difficulty_id'], f"Diff{score['difficulty_id']}")

        # Status indicators
        status = []
        if score.get('is_record'):
            status.append(f"{Fore.RED}NEW RECORD!{Style.RESET_ALL}")
        if score.get('is_new_fc'):
            status.append(f"{Fore.GREEN}NEW FC!{Style.RESET_ALL}")
        elif score.get('is_fc'):
            status.append("FC")
        if score.get('is_personal_best') and not score.get('is_record'):
            status.append("PB")

        status_str = " | ".join(status) if status else ""

        print(f"  [{time_str}] {song}")
        print(f"         {diff} {inst} | {score['score']:,} pts | {score['completion_percent']:.1f}%")
        if status_str:
            print(f"         {status_str}")
        print()

    # Session performance
    print(f"{Fore.CYAN}SESSION PERFORMANCE{Style.RESET_ALL}")
    avg_acc = session_tracker.get_average_accuracy()
    print(f"  Average Accuracy: {avg_acc:.1f}%")

    best_score = session_tracker.get_best_score()
    if best_score:
        best_song = best_score.get('song_title', f"[{best_score['chart_hash'][:8]}]")
        print(f"  Best Score: {best_score['score']:,} pts ({best_song})")

    instruments = session_tracker.get_instruments_played()
    if instruments:
        inst_list = ", ".join([f"{name} ({count})" for name, count in instruments.items()])
        print(f"  Instruments Played: {inst_list}")

    if session_tracker.total_notes_hit > 0:
        print(f"  Total Notes Hit: {session_tracker.total_notes_hit:,}")

    print()
    print("=" * 60)
    print()


def mystats_command(timeframe='all', instrument_id=None, full=False):
    """
    Display comprehensive statistics from server (v2.6.4)

    Args:
        timeframe: '7d', '30d', '90d', or 'all' (default)
        instrument_id: Optional instrument filter (0-10)
        full: If True, show extended breakdown details
    """
    print_header("YOUR STATISTICS")
    print()

    # Check auth token
    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    # Build query parameters
    params = {'timeframe': timeframe}
    if instrument_id is not None:
        params['instrument'] = instrument_id

    # Fetch stats from server
    print("[*] Fetching your statistics from server...")
    try:
        response = requests.get(
            f"{bot_url}/api/user_stats_detailed",
            headers={'Authorization': f'Bearer {auth_token}'},
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Server error: HTTP {response.status_code}")
            if response.status_code == 400:
                print(f"    {response.json().get('error', 'Bad request')}")
            return

        data = response.json()
        if not data.get('success'):
            print_error(f"Server error: {data.get('error', 'Unknown')}")
            return

        stats = data.get('stats', {})
        print_success("Statistics retrieved!")
        print()

    except Exception as e:
        print_error(f"Failed to fetch statistics: {e}")
        return

    # Display timeframe filter
    timeframe_labels = {'7d': 'Last 7 Days', '30d': 'Last 30 Days', '90d': 'Last 90 Days', 'all': 'All Time'}
    print(f"Timeframe: {timeframe_labels.get(timeframe, timeframe)}")
    if instrument_id is not None:
        instrument_names = {
            0: "Lead Guitar", 1: "Bass Guitar", 2: "Rhythm Guitar",
            3: "Keys", 4: "Drums", 5: "GHL Guitar", 6: "GHL Bass"
        }
        print(f"Instrument Filter: {instrument_names.get(instrument_id, f'Instrument {instrument_id}')}")
    print()

    # === OVERALL PERFORMANCE ===
    overall = stats.get('overall', {})
    print(f"{Fore.CYAN}OVERALL PERFORMANCE{Style.RESET_ALL}")
    print(f"  Total Scores Submitted: {overall.get('total_scores', 0):,}")
    print(f"  Records Held (#1): {overall.get('records_held', 0)}")
    print(f"  Full Combos: {overall.get('full_combos', 0)}")

    avg_acc = overall.get('avg_accuracy')
    if avg_acc is not None:
        print(f"  Average Accuracy: {avg_acc:.1f}%")
    print()

    # === BREAKDOWN BY INSTRUMENT ===
    by_instrument = stats.get('by_instrument', [])
    if by_instrument and (full or not instrument_id):
        print(f"{Fore.CYAN}BREAKDOWN BY INSTRUMENT{Style.RESET_ALL}")
        instrument_names = {
            0: "Lead Guitar", 1: "Bass Guitar", 2: "Rhythm Guitar",
            3: "Keys", 4: "Drums", 5: "GHL Guitar", 6: "GHL Bass",
            7: "Unknown-7", 8: "Co-op", 9: "Unknown-9", 10: "Unknown-10"
        }

        for inst in by_instrument:
            inst_name = instrument_names.get(inst['instrument_id'], f"Inst-{inst['instrument_id']}")
            total = inst.get('total_scores', 0)
            records = inst.get('records', 0)
            fcs = inst.get('full_combos', 0)
            acc = inst.get('avg_accuracy', 0)

            print(f"  {inst_name:15} {total:4} scores | {records:3} records | {fcs:3} FCs | {acc:5.1f}% avg")
        print()

    # === BREAKDOWN BY DIFFICULTY ===
    by_difficulty = stats.get('by_difficulty', [])
    if by_difficulty and full:
        print(f"{Fore.CYAN}BREAKDOWN BY DIFFICULTY{Style.RESET_ALL}")
        difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

        for diff in by_difficulty:
            diff_name = difficulty_names.get(diff['difficulty_id'], f"Diff-{diff['difficulty_id']}")
            total = diff.get('total_scores', 0)
            records = diff.get('records', 0)
            fcs = diff.get('full_combos', 0)
            acc = diff.get('avg_accuracy', 0)

            print(f"  {diff_name:8} {total:4} scores | {records:3} records | {fcs:3} FCs | {acc:5.1f}% avg")
        print()

    # === TOP ACHIEVEMENTS ===
    top = stats.get('top_achievements', {})
    if top:
        print(f"{Fore.CYAN}TOP ACHIEVEMENTS{Style.RESET_ALL}")

        hardest_fc = top.get('hardest_fc')
        if hardest_fc:
            song_title = hardest_fc.get('song_title', '[Unknown]')
            nps = hardest_fc.get('nps', 0)
            inst_id = hardest_fc.get('instrument_id', 0)
            diff_id = hardest_fc.get('difficulty_id', 3)
            instrument_names = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}
            inst = instrument_names.get(inst_id, f"Inst{inst_id}")
            diff = difficulty_names.get(diff_id, f"Diff{diff_id}")
            print(f"  Hardest FC: {song_title} ({diff} {inst}, {nps:.1f} NPS)")

        highest_score = top.get('highest_score')
        if highest_score:
            song_title = highest_score.get('song_title', '[Unknown]')
            score = highest_score.get('score', 0)
            inst_id = highest_score.get('instrument_id', 0)
            diff_id = highest_score.get('difficulty_id', 3)
            instrument_names = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulty_names = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}
            inst = instrument_names.get(inst_id, f"Inst{inst_id}")
            diff = difficulty_names.get(diff_id, f"Diff{diff_id}")
            print(f"  Highest Score: {song_title} ({diff} {inst}, {score:,} pts)")

        most_played = top.get('most_played')
        if most_played:
            song_title = most_played.get('song_title', '[Unknown]')
            play_count = most_played.get('play_count', 0)
            print(f"  Most Played: {song_title} ({play_count} plays)")

        print()

    # === RECENT ACTIVITY (Last 7 Days) ===
    recent = stats.get('recent_activity', {})
    if recent and timeframe == 'all':  # Only show if viewing all-time stats
        print(f"{Fore.CYAN}RECENT ACTIVITY (Last 7 Days){Style.RESET_ALL}")
        scores_submitted = recent.get('scores_submitted', 0)
        records_broken = recent.get('records_broken', 0)
        new_fcs = recent.get('new_fcs', 0)
        recent_acc = recent.get('avg_accuracy')

        print(f"  Scores Submitted: {scores_submitted}")
        if records_broken > 0:
            print(f"  Records Broken: {records_broken}")
        if new_fcs > 0:
            print(f"  New FCs: {new_fcs}")
        if recent_acc is not None:
            print(f"  Avg Accuracy: {recent_acc:.1f}%")

        print()

    print("=" * 60)
    print()


def search_command(query=None, instrument_id=None, difficulty_id=None, fc_only=False, page=1):
    """
    Search user's scores with various filters (v2.6.4)

    Args:
        query: Text search for song title/artist
        instrument_id: Filter by instrument (0-10)
        difficulty_id: Filter by difficulty (0-3)
        fc_only: Only show full combos
        page: Page number for pagination (default: 1)
    """
    from datetime import datetime

    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    print_header("SEARCH YOUR SCORES")
    print()

    # Build query parameters
    params = {}
    if query:
        params['query'] = query
    if instrument_id is not None:
        params['instrument'] = instrument_id
    if difficulty_id is not None:
        params['difficulty'] = difficulty_id
    if fc_only:
        params['fc'] = 'true'

    # Pagination (10 per page)
    limit = 10
    offset = (page - 1) * limit
    params['offset'] = offset
    params['limit'] = limit

    try:
        # Fetch results from API
        response = requests.get(
            f"{bot_url}/api/search_scores",
            headers={'Authorization': f'Bearer {auth_token}'},
            params=params,
            timeout=30
        )

        if response.status_code == 401:
            print_error("Authentication failed. Try re-pairing with /pair in Discord.")
            return
        elif response.status_code != 200:
            print_error(f"API request failed: {response.status_code}")
            if response.text:
                print(f"Error: {response.text}")
            return

        data = response.json()
        if not data.get('success'):
            print_error(f"Error: {data.get('error', 'Unknown error')}")
            return

        result = data.get('data', {})
        results = result.get('results', [])
        total_count = result.get('total_count', 0)

        # Display filters
        if query or instrument_id is not None or difficulty_id is not None or fc_only:
            print(f"{Fore.CYAN}Filters:{Style.RESET_ALL}")
            if query:
                print(f"  Query: \"{query}\"")
            if instrument_id is not None:
                inst_name = get_instrument_name(instrument_id)
                print(f"  Instrument: {inst_name}")
            if difficulty_id is not None:
                diff_name = ['Easy', 'Medium', 'Hard', 'Expert'][difficulty_id]
                print(f"  Difficulty: {diff_name}")
            if fc_only:
                print(f"  Full Combos Only: Yes")
            print()

        # Display results
        if total_count == 0:
            print_warning("No scores found matching your search criteria.")
            print()
            return

        # Pagination info
        total_pages = (total_count + limit - 1) // limit
        print(f"{Fore.CYAN}Results:{Style.RESET_ALL} Showing {offset + 1}-{min(offset + len(results), total_count)} of {total_count} scores (Page {page}/{total_pages})")
        print()

        # Display each result
        for i, score in enumerate(results, start=1):
            # Song info
            song_title = score.get('title') or '[Unknown Song]'
            artist = score.get('artist')
            chart_hash_short = score.get('chart_hash', '')[:8]

            # Score details
            score_value = score.get('score', 0)
            stars = score.get('stars', 0)
            completion = score.get('completion_percent', 0.0)
            rank = score.get('rank', 0)
            is_record = score.get('is_record', False)
            is_fc = score.get('is_fc', False)

            # Instrument & difficulty
            inst_name = get_instrument_name(score.get('instrument_id', 0))
            diff_name = ['Easy', 'Medium', 'Hard', 'Expert'][score.get('difficulty_id', 3)]

            # Date
            submitted_at = score.get('submitted_at', '')
            if submitted_at:
                try:
                    dt = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    date_str = submitted_at[:10]
            else:
                date_str = 'Unknown'

            # Print result
            print(f"{Fore.CYAN}#{offset + i}{Style.RESET_ALL}  {song_title}")
            if artist:
                print(f"    Artist: {artist}")
            print(f"    {diff_name} {inst_name} | Score: {score_value:,} pts | {'⭐' * stars}")

            # Status indicators
            status_parts = []
            if is_fc:
                status_parts.append("FC")
            if is_record:
                status_parts.append("RECORD HOLDER")
            else:
                status_parts.append(f"Rank #{rank}")
            status_parts.append(f"{completion:.1f}%")
            status_parts.append(f"Played: {date_str}")

            print(f"    {' | '.join(status_parts)}")
            print(f"    Chart: [{chart_hash_short}]")
            print()

        # Pagination controls
        if total_pages > 1:
            print(f"{Fore.CYAN}Pagination:{Style.RESET_ALL}")
            if page > 1:
                print(f"  Previous page: search <same filters> --page {page - 1}")
            if page < total_pages:
                print(f"  Next page: search <same filters> --page {page + 1}")
            print()

    except requests.exceptions.Timeout:
        print_error("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        print_error(f"Network error: {str(e)}")
    except Exception as e:
        print_error(f"Error: {str(e)}")

    print("=" * 60)
    print()


def compare_command(user2_discord_id):
    """
    Compare your scores head-to-head with another user (v2.6.4)

    Args:
        user2_discord_id: Discord ID of the user to compare against
    """
    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    print_header("HEAD-TO-HEAD COMPARISON")
    print()

    try:
        # Fetch comparison from API
        response = requests.get(
            f"{bot_url}/api/compare",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={'user2': user2_discord_id},
            timeout=30
        )

        if response.status_code == 401:
            print_error("Authentication failed. Try re-pairing with /pair in Discord.")
            return
        elif response.status_code == 404:
            print_error("User not found. Make sure they have paired their tracker with Discord.")
            return
        elif response.status_code != 200:
            print_error(f"API request failed: {response.status_code}")
            if response.text:
                print(f"Error: {response.text}")
            return

        data = response.json()
        if not data.get('success'):
            print_error(f"Error: {data.get('error', 'Unknown error')}")
            return

        result = data.get('data', {})

        # Check for message (no common songs)
        if 'message' in result:
            print_warning(result['message'])
            print()
            return

        # Display users
        user1 = result.get('user1', {})
        user2 = result.get('user2', {})
        user1_name = user1.get('username', 'Unknown')
        user2_name = user2.get('username', 'Unknown')

        print(f"{Fore.CYAN}You vs. {user2_name}{Style.RESET_ALL}")
        print()

        # Overall record
        overall = result.get('overall', {})
        user1_wins = overall.get('user1_records', 0)
        user2_wins = overall.get('user2_records', 0)
        tied = overall.get('tied', 0)
        win_rate = overall.get('user1_win_rate', 0)

        print(f"{Fore.CYAN}OVERALL RECORD:{Style.RESET_ALL}")
        print(f"  Songs where you're #1: {user1_wins}")
        print(f"  Songs where they're #1: {user2_wins}")
        print(f"  Tied: {tied}")
        print()
        print(f"  Your win rate: {win_rate:.1f}%")
        print()

        # Breakdown by instrument
        by_instrument = result.get('by_instrument', [])
        if by_instrument:
            print(f"{Fore.CYAN}BREAKDOWNS:{Style.RESET_ALL}")
            for inst_stat in by_instrument:
                inst_id = inst_stat.get('instrument_id', 0)
                inst_name = get_instrument_name(inst_id)
                u1_w = inst_stat.get('user1_wins', 0)
                u2_w = inst_stat.get('user2_wins', 0)
                t = inst_stat.get('tied', 0)
                print(f"  {inst_name:15} You: {u1_w:2} | Them: {u2_w:2} | Tied: {t:2}")
            print()

        # User1's biggest wins
        user1_biggest = result.get('user1_biggest_wins', [])
        if user1_biggest:
            print(f"{Fore.CYAN}YOUR BIGGEST WINS (Score Difference):{Style.RESET_ALL}")
            for i, match in enumerate(user1_biggest[:5], 1):
                song_title = match.get('song_title') or '[Unknown]'
                inst_name = get_instrument_name(match.get('instrument_id', 0))
                diff_name = ['Easy', 'Medium', 'Hard', 'Expert'][match.get('difficulty_id', 3)]

                u1_score = match.get('user1_score', 0)
                u2_score = match.get('user2_score', 0)
                diff_pts = match.get('diff_points', 0)
                diff_pct = match.get('diff_percent', 0)

                print(f"  #{i}  {song_title} ({diff_name} {inst_name})")
                print(f"      You: {u1_score:,} pts | Them: {u2_score:,} pts | {diff_pts:+,} ({diff_pct:+.1f}%)")
                print()

        # User2's biggest wins
        user2_biggest = result.get('user2_biggest_wins', [])
        if user2_biggest:
            print(f"{Fore.CYAN}THEIR BIGGEST WINS:{Style.RESET_ALL}")
            for i, match in enumerate(user2_biggest[:5], 1):
                song_title = match.get('song_title') or '[Unknown]'
                inst_name = get_instrument_name(match.get('instrument_id', 0))
                diff_name = ['Easy', 'Medium', 'Hard', 'Expert'][match.get('difficulty_id', 3)]

                u1_score = match.get('user1_score', 0)
                u2_score = match.get('user2_score', 0)
                diff_pts = match.get('diff_points', 0)
                diff_pct = match.get('diff_percent', 0)

                print(f"  #{i}  {song_title} ({diff_name} {inst_name})")
                print(f"      Them: {u2_score:,} pts | You: {u1_score:,} pts | {diff_pts:,} ({diff_pct:.1f}%)")
                print()

        # Close matches
        close_matches = result.get('close_matches', [])
        if close_matches:
            print(f"{Fore.CYAN}CLOSE MATCHES (<1% difference):{Style.RESET_ALL}")
            for match in close_matches[:5]:
                song_title = match.get('song_title') or '[Unknown]'
                inst_name = get_instrument_name(match.get('instrument_id', 0))
                diff_name = ['Easy', 'Medium', 'Hard', 'Expert'][match.get('difficulty_id', 3)]

                u1_score = match.get('user1_score', 0)
                u2_score = match.get('user2_score', 0)
                diff_pts = match.get('diff_points', 0)
                diff_pct = match.get('diff_percent', 0)

                print(f"  • {song_title} ({diff_name} {inst_name})")
                print(f"    You: {u1_score:,} | Them: {u2_score:,} ({diff_pts:+,}, {diff_pct:+.2f}%)")
            print()

    except requests.exceptions.Timeout:
        print_error("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        print_error(f"Network error: {str(e)}")
    except Exception as e:
        print_error(f"Error: {str(e)}")

    print("=" * 60)
    print()


def parse_command(query):
    """
    Parse a chart file and display comprehensive metadata

    Args:
        query: Search query (song title, artist, or hash)

    This command searches the local chart index and displays all available
    metadata for a chart including notes, NPS, difficulty, etc.
    """
    print()
    print_header("PARSE CHART", width=70)
    print()

    if not query:
        print_error("No search query provided!")
        print_info("Usage: parse <search query>")
        print_info("Example: parse through the fire")
        print_info("Example: parse 3dfe89a1")
        print()
        return

    # Load chart index
    chart_index = load_chart_index()
    charts = chart_index.get('charts', {})

    if not charts:
        print_warning("Chart index is empty!")
        print()
        print_info("Run 'scancharts' first to build the chart index.")
        print_info("This will scan your Clone Hero songs and cache metadata.")
        print()
        return

    # Search for matches (fuzzy search on title, artist, charter, and hash)
    query_lower = query.lower()
    matches = []

    for chart_hash, chart_info in charts.items():
        title = chart_info.get('title', '').lower()
        artist = chart_info.get('artist', '').lower()
        charter = chart_info.get('charter', '').lower()

        # Match on hash (full or partial)
        if query_lower in chart_hash.lower():
            matches.append((chart_hash, chart_info, 'hash'))
            continue

        # Match on title, artist, or charter
        if query_lower in title or query_lower in artist or query_lower in charter:
            matches.append((chart_hash, chart_info, 'metadata'))

    # Handle results
    if len(matches) == 0:
        print_warning(f"No charts found matching: {query}")
        print()
        print_info("Try a different search term or run 'scancharts' to update the index.")
        print()
        return

    elif len(matches) == 1:
        # Auto-select single match
        chart_hash, chart_info, match_type = matches[0]
        print_success(f"Found 1 match!")
        print()
        _display_chart_metadata(chart_hash, chart_info)

    else:
        # Multiple matches - show selection menu
        print_info(f"Found {len(matches)} matching charts:")
        print()

        for i, (chart_hash, chart_info, match_type) in enumerate(matches, 1):
            title = chart_info.get('title', 'Unknown')
            artist = chart_info.get('artist', 'Unknown')
            charter = chart_info.get('charter', 'Unknown')
            print(f"  [{i:2}] {title}")
            print(f"      Artist: {artist} | Charter: {charter}")
            print(f"      Hash: [{chart_hash[:8]}]")
            print()

        # Limit to first 20 matches
        if len(matches) > 20:
            print_warning(f"Showing first 20 of {len(matches)} matches. Refine your search for better results.")
            matches = matches[:20]
            print()

        while True:
            try:
                choice = input("Select chart number (or 'cancel'): ").strip()

                if choice.lower() in ['cancel', 'c', 'q', 'quit']:
                    print_info("Cancelled.")
                    print()
                    return

                choice_num = int(choice)
                if 1 <= choice_num <= len(matches):
                    chart_hash, chart_info, match_type = matches[choice_num - 1]
                    print()
                    _display_chart_metadata(chart_hash, chart_info)
                    break
                else:
                    print_warning(f"Invalid choice. Enter 1-{len(matches)}")
            except ValueError:
                print_warning("Invalid input. Enter a number or 'cancel'")

    print()


def _display_chart_metadata(chart_hash, chart_info):
    """
    Parse and display comprehensive chart metadata in real-time

    Args:
        chart_hash: The chart hash
        chart_info: Dict containing chart metadata from index (used for file path)
    """
    from pathlib import Path
    from shared.chart_parser import parse_chart_file, Instrument, Difficulty

    # Get file path from index
    file_path = chart_info.get('file_path', '')

    if not file_path:
        print_error("Chart file path not found in index!")
        return

    chart_path = Path(file_path)

    # Check if file exists
    if not chart_path.exists():
        print_error(f"Chart file not found: {file_path}")
        print_warning("File may have been moved or deleted since last scan.")
        return

    # Parse the chart file
    print_info(f"Parsing chart file: {chart_path.name}")
    print()

    chart_data = parse_chart_file(chart_path)

    if not chart_data:
        print_error("Failed to parse chart file!")
        print_info("The file may be corrupted or in an unsupported format.")
        return

    # Extract metadata
    title = chart_data.song_name or chart_info.get('title', 'Unknown Title')
    artist = chart_data.artist or chart_info.get('artist', 'Unknown Artist')
    charter = chart_data.charter or chart_info.get('charter', 'Unknown Charter')

    # Header
    print("=" * 70)
    print(f"  📊 CHART ANALYSIS:")
    print("=" * 70)

    # Song Info Section
    print()
    print(f"{Fore.CYAN}SONG INFORMATION:{Style.RESET_ALL}")
    print(f"  🎵 Title:   {title}")
    print(f"  🎤 Artist:  {artist}")
    print(f"  👤 Charter: {charter}")

    if chart_data.genre:
        print(f"  🎸 Genre:   {chart_data.genre}")

    if chart_data.song_length_ms > 0:
        length_seconds = chart_data.song_length_ms / 1000
        minutes = int(length_seconds // 60)
        seconds = int(length_seconds % 60)
        print(f"  ⏱️  Length:  {minutes}:{seconds:02d}")

    # Available Charts Section
    print()
    print(f"{Fore.CYAN}AVAILABLE CHARTS:{Style.RESET_ALL}")

    instrument_names = {
        Instrument.LEAD: "Lead Guitar",
        Instrument.BASS: "Bass",
        Instrument.RHYTHM: "Rhythm Guitar",
        Instrument.KEYS: "Keys",
        Instrument.DRUMS: "Drums",
        Instrument.GHL_LEAD: "GHL Guitar",
        Instrument.GHL_BASS: "GHL Bass",
    }

    difficulty_names = {
        Difficulty.EASY: "Easy",
        Difficulty.MEDIUM: "Medium",
        Difficulty.HARD: "Hard",
        Difficulty.EXPERT: "Expert",
    }

    # Group by instrument
    instruments_found = {}
    for (instrument, difficulty), inst_data in chart_data.instruments.items():
        if instrument not in instruments_found:
            instruments_found[instrument] = []
        instruments_found[instrument].append((difficulty, inst_data))

    if not instruments_found:
        print(f"  ⚠️  No chart data found")
    else:
        for instrument in sorted(instruments_found.keys(), key=lambda x: x.value):
            inst_name = instrument_names.get(instrument, f"Unknown ({instrument})")
            difficulties = sorted(instruments_found[instrument], key=lambda x: x[0].value, reverse=True)
            diff_list = ", ".join(difficulty_names.get(d, f"Unknown") for d, _ in difficulties)
            print(f"  🎸 {inst_name}: {diff_list}")

    # Chart Statistics Section - Show Expert Lead/Bass if available
    print()
    print(f"{Fore.CYAN}CHART STATISTICS (Expert Lead):{Style.RESET_ALL}")

    # Try to find Expert Lead, fall back to other instruments/difficulties
    stat_data = None
    stat_instrument = None
    stat_difficulty = None

    # Priority order: Expert Lead > Expert Bass > any Expert > any chart
    priority_order = [
        (Instrument.LEAD, Difficulty.EXPERT),
        (Instrument.BASS, Difficulty.EXPERT),
        (Instrument.RHYTHM, Difficulty.EXPERT),
    ]

    for inst, diff in priority_order:
        stat_data = chart_data.get_instrument_data(inst, diff)
        if stat_data:
            stat_instrument = inst
            stat_difficulty = diff
            break

    # If still nothing, grab any available chart
    if not stat_data and chart_data.instruments:
        (stat_instrument, stat_difficulty), stat_data = next(iter(chart_data.instruments.items()))

    if stat_data:
        # Update header if not Expert Lead
        if stat_instrument != Instrument.LEAD or stat_difficulty != Difficulty.EXPERT:
            inst_name = instrument_names.get(stat_instrument, "Unknown")
            diff_name = difficulty_names.get(stat_difficulty, "Unknown")
            print(f"{Fore.YELLOW}  (Showing {diff_name} {inst_name} - Expert Lead not available){Style.RESET_ALL}")

        print(f"  🎵 Total Notes: {stat_data.total_notes:,}")

        # Calculate NPS for this specific chart
        note_density = chart_data.calculate_note_density(stat_instrument, stat_difficulty)
        print(f"  📈 Average NPS: {note_density:.2f}")

        peak_note_density = chart_data.calculate_peak_note_density(stat_instrument, stat_difficulty, window_seconds=1.0)
        print(f"  🔥 Peak NPS:    {peak_note_density:.2f}")

        if stat_data.star_power_phrases:
            print(f"  ⭐ Star Power:  {len(stat_data.star_power_phrases)} phrases")
    else:
        print(f"  ⚠️  No chart statistics available")

    # Chart Hash
    print()
    print(f"{Fore.CYAN}IDENTIFICATION:{Style.RESET_ALL}")
    print(f"  🔖 Hash (Full):        {chart_hash}")
    print(f"  🔖 Hash (Abbreviated): [{chart_hash[:8]}]")

    # File Location
    print()
    print(f"{Fore.CYAN}FILE LOCATION:{Style.RESET_ALL}")
    print(f"  📁 Path: {file_path}")
    print(f"  ✅ Status: File exists and parsed successfully")

    print("=" * 70)


def resolve_hashes_command():
    """
    Resolve chart hashes by scanning local songs folder
    and updating the server database with metadata
    """
    import hashlib

    print_header("RESOLVE CHART HASHES")
    print()
    print("This will:")
    print("  1. Get list of unresolved hashes from server")
    print("  2. Scan your Clone Hero songs folder")
    print("  3. Match hashes and extract song metadata")
    print("  4. Send updates to server (with your confirmation)")
    print()

    # Check auth token
    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    # Step 1: Get unresolved hashes from server
    print("[*] Fetching unresolved hashes from server...")
    try:
        response = requests.get(
            f"{bot_url}/api/unresolved_hashes",
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"Server error: {response.status_code}")
            return

        data = response.json()
        if not data.get('success'):
            print_error(f"Server error: {data.get('error', 'Unknown')}")
            return

        unresolved_hashes = set(data.get('hashes', []))
        print_success(f"Found {len(unresolved_hashes)} unresolved hashes")

        if not unresolved_hashes:
            print_info("No hashes to resolve! All your scores have metadata.")
            return

    except Exception as e:
        print_error(f"Failed to get unresolved hashes: {e}")
        return

    # Step 2: Find Clone Hero's song folders from settings.ini
    print()
    print("[*] Looking for Clone Hero's settings...")

    # Try to find Clone Hero's settings.ini
    ch_docs = get_clone_hero_documents_dir()
    settings_path = (ch_docs / "settings.ini") if ch_docs else None

    song_folders = []

    if not settings_path:
        print_warning("Could not locate Clone Hero documents directory")
        logger.warning("scancharts: Clone Hero documents directory not found")
    elif not settings_path.exists():
        print_warning(f"settings.ini not found at: {settings_path}")
        logger.warning(f"scancharts: settings.ini not found at {settings_path}")
    else:
        print_info(f"  Reading: {settings_path}")
        logger.info(f"scancharts: reading settings.ini from {settings_path}")
        try:
            # Parse settings.ini using configparser to handle sections properly
            config = configparser.ConfigParser()
            config.read(str(settings_path))

            path_entries_found = 0
            # Look for path entries in all sections
            for section in config.sections():
                for key in config.options(section):
                    if key.startswith('path') and key[4:].isdigit():
                        folder = config.get(section, key)
                        path_entries_found += 1
                        if folder:
                            if Path(folder).exists():
                                song_folders.append(Path(folder))
                                print_success(f"  Found song folder: {folder}")
                                logger.info(f"scancharts: folder added: {folder}")
                            else:
                                print_warning(f"  Path in settings.ini not found on disk: {folder}")
                                logger.warning(f"scancharts: settings.ini path does not exist: {folder}")

            if path_entries_found == 0:
                print_warning("No song path entries found in settings.ini")
                print_info("  (Clone Hero may not have a songs folder configured yet)")
                logger.warning("scancharts: settings.ini has no path0/path1/... entries")

        except Exception as e:
            print_warning(f"Could not parse Clone Hero settings: {e}")
            logger.error(f"scancharts: failed to parse settings.ini: {e}")

    # Fallback: Use tracker's configured songs folder
    if not song_folders:
        print_info("Trying tracker's configured songs folder...")
        logger.info("scancharts: falling back to tracker's configured songs_folder")

        settings = load_settings()
        fallback_folder = settings.get('songs_folder')

        if fallback_folder and Path(fallback_folder).exists():
            song_folders.append(Path(fallback_folder))
            print_success(f"  Using tracker folder: {fallback_folder}")
            logger.info(f"scancharts: using tracker fallback folder: {fallback_folder}")
        elif fallback_folder:
            print_warning(f"  Tracker songs folder configured but not found: {fallback_folder}")
            logger.warning(f"scancharts: tracker songs_folder does not exist: {fallback_folder}")

    if not song_folders:
        print_error("No song folders found!")
        logger.error("scancharts: no song folders found - aborting")
        print_info("")
        print_info("You can either:")
        print_info("  1. Configure a songs folder in Clone Hero's settings")
        print_info("  2. Configure a songs folder in the tracker's settings")
        print_info("")
        return

    # Ask if user wants to add more folders (for multiple Clone Hero installs)
    print()
    while True:
        add_more = input("Add another songs folder? (yes/no): ").strip().lower()
        if add_more == 'yes' or add_more == 'y':
            folder_path = input("Enter full path to songs folder: ").strip()
            if folder_path:
                # Remove quotes if user pasted a path with quotes
                folder_path = folder_path.strip('"').strip("'")
                if Path(folder_path).exists():
                    song_folders.append(Path(folder_path))
                    print_success(f"  Added folder: {folder_path}")
                else:
                    print_error(f"  Folder not found: {folder_path}")
        else:
            break

    print()
    print(f"[*] Will scan {len(song_folders)} song folder(s)")
    print_warning("This may take a few minutes for large libraries...")
    print()

    # Step 3: Scan all songs folders
    resolved_metadata = []
    scanned = 0
    found = 0

    for songs_path in song_folders:
        print(f"[*] Scanning: {songs_path}")
        for root, dirs, files in os.walk(songs_path):
            # Look for chart files
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if not chart_files:
                continue

            scanned += 1

            # Show progress
            if scanned % 100 == 0:
                print(f"  Scanned {scanned} songs... (found {found} matches)", end='\r')

            chart_path = Path(root) / chart_files[0]

            # Calculate MD5 hash
            try:
                with open(chart_path, 'rb') as f:
                    chart_hash = hashlib.md5(f.read()).hexdigest()

                # Check if this is an unresolved hash (exact match)
                is_match = chart_hash in unresolved_hashes

                if not is_match:
                    # Also try matching if calculated hash starts with any server hash
                    # (in case server has partial hashes)
                    for server_hash in unresolved_hashes:
                        if chart_hash.startswith(server_hash):
                            is_match = True
                            break

                if not is_match:
                    continue

                # Found a match! Get metadata
                ini_data = parse_song_ini(str(chart_path))

                if ini_data:
                    title = ini_data.get('name', ini_data.get('title', ''))
                    artist = ini_data.get('artist', '')
                    charter = ini_data.get('charter', ini_data.get('frets', ''))

                    if not title:
                        title = Path(root).name

                    resolved_metadata.append({
                        'chart_hash': chart_hash,
                        'title': title,
                        'artist': artist,
                        'charter': charter
                    })

                    found += 1
                    print(f"  [+] Found: {title} - {artist}")

            except Exception as e:
                continue

    print(f"\n\n[*] Scan complete: {scanned} songs scanned")
    print()

    if not resolved_metadata:
        print_warning("No matches found!")
        print()
        print_info("Possible reasons:")
        print("  • Your unresolved hashes are from songs you've deleted")
        print("  • Clone Hero song folders might have changed")
        print("  • Songs were from a different PC")
        print()
        print_info("What you can do:")
        print("  • Check Settings > Clone Hero Path")
        print("  • Run 'resync' to refresh your scores")
        print("  • Re-download missing charts from Bridge")
        print()
        return

    # Step 4: Show preview and confirm
    print_header(f"FOUND METADATA FOR {len(resolved_metadata)} SONGS")
    print()

    # Show first 10 as preview
    for i, item in enumerate(resolved_metadata[:10], 1):
        print(f"{i}. {item['title']}")
        if item['artist']:
            print(f"   Artist: {item['artist']}")
        if item['charter']:
            print(f"   Charter: {item['charter']}")
        print(f"   Hash: [{item['chart_hash'][:8]}...]")
        print()

    if len(resolved_metadata) > 10:
        print(f"... and {len(resolved_metadata) - 10} more")
        print()

    print("="*60)
    print()
    confirm = input(f"Send these {len(resolved_metadata)} updates to server? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("  Cancelled.")
        return

    # Step 5: Send to server
    print()
    print(f"[*] Sending updates to server...")

    try:
        response = requests.post(
            f"{bot_url}/api/resolve_hashes",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={'metadata': resolved_metadata},
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Server error: {response.status_code}")
            return

        data = response.json()
        if data.get('success'):
            updated_count = data.get('updated_count', 0)
            print_success(f"Updated {updated_count} songs in database!")
            print_info("Your mystery hashes now have song names!")
        else:
            print_error(f"Server error: {data.get('error', 'Unknown')}")

    except Exception as e:
        print_error(f"Failed to send updates: {e}")


# ============================================================================
# Chart Index System (v2.6.4)
# ============================================================================

def get_chart_index_path():
    """Get path to chart index file"""
    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    return ch_dir / '.score_tracker_chart_index.json'


def load_chart_index():
    """
    Load chart index from disk

    Returns:
        dict: Chart index with structure:
            {
                "version": 1,
                "last_full_scan": "ISO timestamp",
                "scan_count": int,
                "charts": {
                    "chart_hash": {
                        "file_path": str,
                        "last_modified": float,
                        "title": str,
                        "artist": str,
                        "charter": str,
                        "total_notes": int,
                        "note_density": float,
                        "peak_note_density": float,
                        "scanned_at": "ISO timestamp"
                    }
                }
            }
    """
    index_path = get_chart_index_path()

    if not index_path.exists():
        return {
            "version": 1,
            "last_full_scan": None,
            "scan_count": 0,
            "charts": {}
        }

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load chart index: {e}")
        return {
            "version": 1,
            "last_full_scan": None,
            "scan_count": 0,
            "charts": {}
        }


def save_chart_index(index):
    """Save chart index to disk"""
    index_path = get_chart_index_path()

    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save chart index: {e}")
        print_warning(f"Could not save chart index: {e}")


def lookup_chart_in_index(chart_hash):
    """
    Look up a chart in the local index

    Args:
        chart_hash: The chart hash to look up

    Returns:
        dict or None: Chart metadata if found, None otherwise
    """
    index = load_chart_index()
    return index.get('charts', {}).get(chart_hash)


def add_chart_to_index(chart_hash, chart_info):
    """
    Add or update a chart in the index

    Args:
        chart_hash: The chart hash
        chart_info: Dict with chart metadata
    """
    index = load_chart_index()
    index['charts'][chart_hash] = chart_info
    save_chart_index(index)


def find_chart_by_hash_on_demand(target_hash, max_duration=60):
    """
    Search for a specific chart hash in song folders (on-demand scan)

    Args:
        target_hash: The chart hash to find
        max_duration: Maximum search time in seconds (default 60)
                      Large libraries (35k+ songs) may need 60-120s on SSD,
                      longer on HDD. Run 'scancharts' for instant lookups.

    Returns:
        Path or None: Path to chart file if found, None otherwise
    """
    import hashlib
    from datetime import datetime

    start_time = time.time()

    # Get song folders from settings using the documented helper
    ch_docs = get_clone_hero_documents_dir()
    settings_path = (ch_docs / "settings.ini") if ch_docs else None
    song_folders = []

    if not settings_path or not settings_path.exists():
        logger.debug(f"  On-demand scan: settings.ini not found, will try tracker fallback")
    else:
        try:
            config = configparser.ConfigParser()
            config.read(str(settings_path))

            for section in config.sections():
                for key in config.options(section):
                    if key.startswith('path') and key[4:].isdigit():
                        folder = config.get(section, key)
                        if folder and Path(folder).exists():
                            song_folders.append(Path(folder))
        except Exception as e:
            logger.debug(f"  On-demand scan: failed to parse settings.ini: {e}")

    # Fallback to tracker's configured folder
    if not song_folders:
        try:
            fallback_folder = load_settings().get('songs_folder')
            if fallback_folder and Path(fallback_folder).exists():
                song_folders.append(Path(fallback_folder))
                logger.debug(f"  On-demand scan: using tracker fallback folder: {fallback_folder}")
        except Exception:
            pass

    if not song_folders:
        logger.warning(f"  On-demand scan: no song folders found for [{target_hash[:8]}]")
        return None

    print_info(f"Searching for chart [{target_hash[:8]}]...")
    logger.info(f"  On-demand scan started for [{target_hash[:8]}] across {len(song_folders)} folder(s), timeout={max_duration}s")

    charts_checked = 0

    for folder in song_folders:
        logger.info(f"  On-demand scan: searching in {str(folder)}")
        print(f"  Searching in: {str(folder)}...    ", end='\r')

        for root, dirs, files in os.walk(folder):
            # Check timeout
            if time.time() - start_time > max_duration:
                elapsed = time.time() - start_time
                print()
                logger.warning(
                    f"  On-demand scan timeout after {elapsed:.0f}s — "
                    f"{charts_checked:,} charts checked in {str(folder)}"
                )
                print_warning(f"  Scan timeout after {elapsed:.0f}s ({charts_checked:,} charts scanned)")
                if charts_checked > 5000:
                    print_info("  Your library is very large. Run 'scancharts' to build a full index for instant lookups.")
                return None

            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]
            if not chart_files:
                continue

            charts_checked += 1
            if charts_checked % 100 == 0:
                elapsed = time.time() - start_time
                print(f"  Searching: {str(folder)} ({charts_checked:,} charts, {elapsed:.0f}s)...    ", end='\r')

            chart_path = Path(root) / chart_files[0]

            # Quick hash calculation
            try:
                with open(chart_path, 'rb') as f:
                    chart_hash = hashlib.md5(f.read()).hexdigest()

                if chart_hash == target_hash:
                    print()
                    print_success(f"  Found chart in: {chart_path.parent.name}/")

                    # Populate in-memory cache so STEP 4 (get_total_notes_from_chart)
                    # finds it instantly via _chart_file_cache instead of re-walking
                    _chart_file_cache[target_hash] = chart_path

                    # Parse and add to index for future use
                    try:
                        chart_data = parse_chart_file(chart_path)
                        ini_data = parse_song_ini(str(chart_path))

                        song_name = ''
                        artist = ''
                        charter = ''

                        if ini_data:
                            song_name = ini_data.get('name', ini_data.get('title', ''))
                            artist = ini_data.get('artist', '')
                            charter = ini_data.get('charter', ini_data.get('frets', ''))

                        if not song_name:
                            song_name = Path(root).name

                        # Add to index
                        chart_info = {
                            'file_path': str(chart_path),
                            'last_modified': chart_path.stat().st_mtime,
                            'title': song_name,
                            'artist': artist,
                            'charter': charter,
                            'scanned_at': datetime.now().isoformat()
                        }

                        add_chart_to_index(chart_hash, chart_info)
                        print_info("  Added to chart index for future lookups")
                    except Exception as e:
                        logger.debug(f"Failed to parse found chart: {e}")

                    return chart_path
            except Exception as e:
                continue

    print()
    logger.info(f"  On-demand scan: [{target_hash[:8]}] not found after checking {charts_checked:,} charts")
    print_warning(f"  Chart not found in {len(song_folders)} song folder(s) ({charts_checked:,} charts scanned)")
    return None


def format_progress_bar(current, total, width=20):
    """
    Create ASCII progress bar

    Args:
        current: Current progress value
        total: Total value
        width: Width of progress bar in characters (default: 20)

    Returns:
        str: ASCII progress bar like [████████░░░░] 67%
    """
    if total == 0:
        return "[" + "░" * width + "] 0%"

    percentage = min(100, int((current / total) * 100))
    filled = int((current / total) * width)
    empty = width - filled

    bar = "[" + "█" * filled + "░" * empty + "]"
    return f"{bar} {percentage}%"


def format_time(seconds):
    """
    Format seconds into human-readable time

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted time like "5m 32s" or "1h 23m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def scancharts_command(force_full=False, silent=False):
    """
    Scan all local charts and upload metadata to server (v2.6.4)

    Args:
        force_full: Force complete re-scan (ignore index)
        silent: Suppress prompts and run quietly

    This command parses charts in your Clone Hero song folders and sends
    detailed metadata (total notes, NPS, chord count, etc.) to the server.

    v2.6.4: Now supports incremental scanning (only scans new/changed charts)

    Features enabled:
    - /hardest command (shows hardest songs by NPS)
    - Chart Intensity badges in announcements
    - Accurate note counts
    - Local chart index for offline score metadata
    """
    if not silent:
        print_header("SCAN CHARTS FOR METADATA")
        print()
        if force_full:
            print("Mode: FULL SCAN (re-scanning all charts)")
        else:
            print("Mode: INCREMENTAL SCAN (only new/changed charts)")
        print()
        print("This will:")
        print("  1. Scan charts in your Clone Hero songs folder(s)")
        print("  2. Parse note data for each instrument/difficulty")
        print("  3. Calculate note density (NPS)")
        print("  4. Build local chart index")
        print("  5. Upload metadata to server")
        print()
        if force_full:
            print_warning("Full scan may take several minutes for large libraries!")
        else:
            print_info("Incremental scan only processes new/modified charts (much faster!)")
        print()

    # Load existing index (for incremental scan)
    from datetime import datetime
    chart_index = load_chart_index()
    existing_charts = chart_index.get('charts', {}) if not force_full else {}

    # Build lookup: file_path -> (hash, last_modified)
    path_lookup = {}
    if not force_full:
        for chart_hash, info in existing_charts.items():
            file_path = info.get('file_path')
            last_modified = info.get('last_modified')
            if file_path and last_modified:
                path_lookup[file_path] = (chart_hash, last_modified)

    # Check auth token
    config = load_config()
    auth_token = config.get('auth_token')
    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    bot_url = get_bot_url()

    # Step 1: Find Clone Hero's song folders from settings.ini
    print("[*] Looking for Clone Hero's settings...")

    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    settings_path = ch_dir / "settings.ini"

    song_folders = []

    if settings_path.exists():
        try:
            # Parse settings.ini using configparser
            config_parser = configparser.ConfigParser()
            config_parser.read(str(settings_path))

            # Look for path entries in all sections
            for section in config_parser.sections():
                for key in config_parser.options(section):
                    if key.startswith('path') and key[4:].isdigit():
                        folder = config_parser.get(section, key)

                        if folder and Path(folder).exists():
                            song_folders.append(Path(folder))
                            print_success(f"  Found song folder: {folder}")
        except Exception as e:
            print_warning(f"Could not parse Clone Hero settings: {e}")

    # Fallback: Use tracker's configured songs folder
    if not song_folders:
        print_warning("Could not find folders in Clone Hero settings.ini")
        print_info("Trying tracker's configured songs folder...")

        settings = load_settings()
        fallback_folder = settings.get('songs_folder')

        if fallback_folder and Path(fallback_folder).exists():
            song_folders.append(Path(fallback_folder))
            print_success(f"  Using tracker folder: {fallback_folder}")

    if not song_folders:
        print_error("No song folders found!")
        print_info("")
        print_info("You can either:")
        print_info("  1. Configure a songs folder in Clone Hero's settings")
        print_info("  2. Configure a songs folder in the tracker's settings")
        print_info("")
        return

    # Ask if user wants to add more folders
    print()
    while True:
        add_more = input("Add another songs folder? (yes/no): ").strip().lower()
        if add_more == 'yes' or add_more == 'y':
            folder_path = input("Enter full path to songs folder: ").strip()
            if folder_path:
                folder_path = folder_path.strip('"').strip("'")
                if Path(folder_path).exists():
                    song_folders.append(Path(folder_path))
                    print_success(f"  Added folder: {folder_path}")
                else:
                    print_error(f"  Folder not found: {folder_path}")
        else:
            break

    print()
    print(f"[*] Will scan {len(song_folders)} song folder(s)")

    # v2.6.4: Pre-scan to count total charts (for progress bar and ETA)
    if not silent:
        print()
        print("[*] Quick pre-scan to count charts...")

    total_chart_files = 0
    for songs_path in song_folders:
        for root, dirs, files in os.walk(songs_path):
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]
            if chart_files:
                total_chart_files += 1

    if not silent and total_chart_files > 0:
        print_success(f"    Found {total_chart_files:,} chart files in {len(song_folders)} song folder(s)")

        # Estimate time based on chart count
        if force_full or len(existing_charts) == 0:
            # First-time scan estimate: ~1.5 seconds per chart
            estimated_seconds = total_chart_files * 1.5
            if estimated_seconds > 300:  # More than 5 minutes
                minutes = int(estimated_seconds / 60)
                print()
                print("=" * 60)
                print_warning(f"IMPORTANT: First-time scan may take {minutes}-{minutes+15} minutes!")
                print_info(f"Processing {total_chart_files:,} charts...")
                print_info("Future scans will be much faster (incremental mode).")
                print("=" * 60)
        else:
            # Incremental scan - much faster
            print_info("Incremental mode: Most charts will be skipped (unchanged)")

    print()

    # Step 2: Scan all charts and parse metadata
    chart_metadata = []
    scanned = 0
    parsed = 0
    skipped = 0
    updated = 0
    new_charts = 0
    failed = 0

    # Progress tracking
    scan_start_time = time.time()
    last_progress_update = time.time()

    for songs_path in song_folders:
        if not silent:
            print(f"[*] Scanning: {songs_path}")
        for root, dirs, files in os.walk(songs_path):
            # Look for chart files
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if not chart_files:
                continue

            scanned += 1
            chart_path = Path(root) / chart_files[0]
            chart_path_str = str(chart_path)

            # Check if we should skip this chart (incremental scan)
            if not force_full and chart_path_str in path_lookup:
                # Check if file was modified
                try:
                    current_mtime = chart_path.stat().st_mtime
                    cached_hash, cached_mtime = path_lookup[chart_path_str]

                    # Skip if file timestamp matches (not modified)
                    if current_mtime == cached_mtime:
                        skipped += 1
                        # Update progress display every 100 charts (reduced frequency for cleaner output)
                        if not silent and scanned % 100 == 0 and total_chart_files > 0:
                            elapsed = time.time() - scan_start_time
                            charts_per_sec = scanned / elapsed if elapsed > 0 else 0
                            remaining = total_chart_files - scanned
                            eta_seconds = remaining / charts_per_sec if charts_per_sec > 0 else 0

                            progress_bar = format_progress_bar(scanned, total_chart_files)
                            # Use newline for reliable Windows terminal output
                            print(f"Progress: {progress_bar} ({scanned:,}/{total_chart_files:,}) | Skip:{skipped} New:{new_charts} Upd:{updated} Fail:{failed} | {charts_per_sec:.1f} ch/s ETA:{format_time(eta_seconds)} Elapsed:{format_time(elapsed)}")
                        continue
                except:
                    pass  # File might be deleted, parse anyway

            # Show progress every 100 charts (for charts being processed)
            if not silent and scanned % 100 == 0 and total_chart_files > 0:
                elapsed = time.time() - scan_start_time
                charts_per_sec = scanned / elapsed if elapsed > 0 else 0
                remaining = total_chart_files - scanned
                eta_seconds = remaining / charts_per_sec if charts_per_sec > 0 else 0

                progress_bar = format_progress_bar(scanned, total_chart_files)
                # Use newline for reliable Windows terminal output
                print(f"Progress: {progress_bar} ({scanned:,}/{total_chart_files:,}) | Skip:{skipped} New:{new_charts} Upd:{updated} Fail:{failed} | {charts_per_sec:.1f} ch/s ETA:{format_time(eta_seconds)} Elapsed:{format_time(elapsed)}")

            # Calculate MD5 hash
            try:
                with open(chart_path, 'rb') as f:
                    chart_hash = hashlib.md5(f.read()).hexdigest()

                # Track if this is new or updated
                is_new = chart_hash not in existing_charts
                if is_new:
                    new_charts += 1
                else:
                    updated += 1

                # Parse chart file for metadata
                chart_data = parse_chart_file(chart_path)

                # Get song metadata from song.ini
                ini_data = parse_song_ini(str(chart_path))

                song_name = ''
                artist = ''
                charter = ''
                genre = ''

                if ini_data:
                    song_name = ini_data.get('name', ini_data.get('title', ''))
                    artist = ini_data.get('artist', '')
                    charter = ini_data.get('charter', ini_data.get('frets', ''))
                    genre = ini_data.get('genre', '')

                # Fallback to folder name if no title
                if not song_name:
                    song_name = Path(root).name

                # Extract metadata for each instrument/difficulty combo
                for (instrument, difficulty), inst_data in chart_data.instruments.items():
                    # Calculate note density (NPS)
                    song_length_ms = chart_data.song_length_ms or 1000  # Avoid division by zero
                    note_density = (inst_data.total_notes / song_length_ms) * 1000.0

                    # v2.6.3: Calculate peak NPS (1-second window)
                    peak_note_density = chart_data.calculate_peak_note_density(instrument, difficulty, window_seconds=1.0)

                    chart_metadata.append({
                        'chart_hash': chart_hash,
                        'instrument_id': instrument.value,
                        'difficulty_id': difficulty.value,
                        'total_notes': inst_data.total_notes,
                        'chord_count': inst_data.chord_count,
                        'tap_count': inst_data.tap_count,
                        'open_note_count': inst_data.open_note_count,
                        'star_power_phrases': len(inst_data.star_power_phrases),
                        'song_length_ms': chart_data.song_length_ms,
                        'note_density': round(note_density, 2),
                        'peak_note_density': round(peak_note_density, 2),  # v2.6.3: Peak Intensity
                        'song_name': song_name,
                        'artist': artist,
                        'charter': charter,
                        'genre': genre,
                        'chart_file_path': str(chart_path)
                    })

                parsed += 1

                # v2.6.4: Update chart index
                chart_index['charts'][chart_hash] = {
                    'file_path': chart_path_str,
                    'last_modified': chart_path.stat().st_mtime,
                    'title': song_name,
                    'artist': artist,
                    'charter': charter,
                    'scanned_at': datetime.now().isoformat()
                }

            except Exception as e:
                failed += 1
                logger.debug(f"Failed to parse {chart_path}: {e}")
                continue

    # Update index metadata and save
    chart_index['last_full_scan'] = datetime.now().isoformat()
    chart_index['scan_count'] = chart_index.get('scan_count', 0) + 1
    save_chart_index(chart_index)

    if not silent:
        # Clear progress bar line
        print()  # Move to new line after progress bar

        # Show final progress summary (100%)
        if total_chart_files > 0:
            total_elapsed = time.time() - scan_start_time
            final_speed = scanned / total_elapsed if total_elapsed > 0 else 0
            progress_bar = format_progress_bar(scanned, total_chart_files)
            print(f"Final Progress: {progress_bar} ({scanned:,}/{total_chart_files:,})")
            print(f"  • Skipped: {skipped}  • New: {new_charts}  • Updated: {updated}  • Failed: {failed}")
            print(f"  • Speed: {final_speed:.1f} charts/sec  • Total Time: {format_time(total_elapsed)}")
            print()

        print("[*] Scan complete!")
        print(f"  • Charts encountered: {scanned:,}")
        if not force_full and skipped > 0:
            print(f"  • Skipped (unchanged): {skipped:,}")
            print(f"  • New charts: {new_charts:,}")
            print(f"  • Updated charts: {updated:,}")
        print(f"  • Successfully parsed: {parsed:,}")
        print(f"  • Failed to parse: {failed:,}")
        print(f"  • Total metadata entries: {len(chart_metadata):,}")
        print(f"  • Chart index updated ({len(chart_index['charts']):,} total charts)")
        print()

    if not chart_metadata:
        if not silent:
            print_warning("No new/updated charts to upload!")
        return

    # Step 3: Confirm upload
    print("="*60)
    print()
    confirm = input(f"Upload {len(chart_metadata)} metadata entries to server? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("  Cancelled.")
        return

    # Step 4: Send to server in batches (to avoid timeouts)
    print()
    print(f"[*] Uploading metadata to server...")

    batch_size = 500
    total_inserted = 0
    total_updated = 0
    total_failed = 0

    for i in range(0, len(chart_metadata), batch_size):
        batch = chart_metadata[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(chart_metadata) + batch_size - 1) // batch_size

        print(f"  Uploading batch {batch_num}/{total_batches} ({len(batch)} entries)...", end='\r')

        try:
            response = requests.post(
                f"{bot_url}/api/chart_metadata",
                headers={'Authorization': f'Bearer {auth_token}'},
                json={'charts': batch},
                timeout=60
            )

            if response.status_code != 200:
                print_error(f"\n  Server error on batch {batch_num}: {response.status_code}")
                total_failed += len(batch)
                continue

            data = response.json()
            if data.get('success'):
                total_inserted += data.get('inserted', 0)
                total_updated += data.get('updated', 0)
                total_failed += data.get('failed', 0)
            else:
                print_error(f"\n  Server error on batch {batch_num}: {data.get('error', 'Unknown')}")
                total_failed += len(batch)

        except Exception as e:
            print_error(f"\n  Failed to upload batch {batch_num}: {e}")
            total_failed += len(batch)

    print()
    print()
    print_header("UPLOAD COMPLETE", width=60)
    print_success(f"  • Inserted: {total_inserted}")
    print_success(f"  • Updated: {total_updated}")
    if total_failed > 0:
        print_warning(f"  • Failed: {total_failed}")
    print()
    print_info("Your charts are now indexed!")
    print_info("Features now available:")
    print("  • /hardest - See hardest songs by NPS")
    print("  • Chart Intensity badges in announcements")
    print("  • Accurate note counts")
    print()


def backup_config_command():
    """Backup current configuration"""
    try:
        config_path = get_config_path()
        settings_path = get_settings_path()

        if not config_path or not settings_path:
            print_error("Could not determine config paths")
            return

        # Create backups
        backup_config = config_path.parent / f"{config_path.name}.backup"
        backup_settings = settings_path.parent / f"{settings_path.name}.backup"

        backed_up = []

        if config_path.exists():
            import shutil
            shutil.copy2(config_path, backup_config)
            backed_up.append(f"Config: {backup_config.name}")

        if settings_path.exists():
            import shutil
            shutil.copy2(settings_path, backup_settings)
            backed_up.append(f"Settings: {backup_settings.name}")

        if backed_up:
            print_header("BACKUP COMPLETE", width=50)
            print_success("Backed up:")
            for item in backed_up:
                print(f"  • {item}")
            print()
            print(f"Location: {config_path.parent}")
        else:
            print_warning("No configuration files found to backup")

    except Exception as e:
        print_error(f"Backup failed: {e}")


def restore_config_command():
    """Restore configuration from backup"""
    try:
        config_path = get_config_path()
        settings_path = get_settings_path()

        if not config_path or not settings_path:
            print_error("Could not determine config paths")
            return

        backup_config = config_path.parent / f"{config_path.name}.backup"
        backup_settings = settings_path.parent / f"{settings_path.name}.backup"

        if not backup_config.exists() and not backup_settings.exists():
            print_error("No backup files found")
            print(f"  Looking for: {backup_config.name} or {backup_settings.name}")
            print(f"  Location: {config_path.parent}")
            return

        print_header("RESTORE FROM BACKUP", width=50)
        print_warning("This will overwrite your current configuration!")
        print()
        confirm = input("Continue? (yes/no): ").strip().lower()

        if confirm != "yes":
            print_info("Restore cancelled")
            return

        restored = []

        if backup_config.exists():
            import shutil
            shutil.copy2(backup_config, config_path)
            restored.append("Config restored")

        if backup_settings.exists():
            import shutil
            shutil.copy2(backup_settings, settings_path)
            restored.append("Settings restored")

        if restored:
            print_success("Restore complete!")
            for item in restored:
                print(f"  • {item}")
            print()
            print_info("Restart the tracker for changes to take effect")

    except Exception as e:
        print_error(f"Restore failed: {e}")


def export_logs_command():
    """Export debug logs to a zip file"""
    try:
        import zipfile
        from datetime import datetime

        ch_dir = find_clone_hero_directory_internal()
        if not ch_dir:
            print_error("Could not find Clone Hero directory")
            return

        log_file = ch_dir / 'score_tracker.log'
        if not log_file.exists():
            print_warning("No log file found")
            return

        # Create zip file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"score_tracker_logs_{timestamp}.zip"
        zip_path = ch_dir / zip_name

        print_info(f"Creating log archive: {zip_name}...")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add main log
            zf.write(log_file, log_file.name)

            # Add any backup logs (from rotation)
            for i in range(1, 6):
                backup_log = ch_dir / f'score_tracker.log.{i}'
                if backup_log.exists():
                    zf.write(backup_log, backup_log.name)

        print_success(f"Logs exported to: {zip_path}")
        print_info(f"File size: {zip_path.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        print_error(f"Export failed: {e}")


def bugreport_command():
    """Generate a self-contained bug report file and guide user to GitHub Issues."""
    import platform
    from datetime import datetime

    print_info("Collecting diagnostics...")
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')

    lines = []
    lines.append("=" * 60)
    lines.append("Clone Hero Score Tracker - Bug Report")
    lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    # --- Version & System ---
    lines.append("[VERSION & SYSTEM]")
    lines.append(f"Tracker Version: {VERSION}")
    lines.append(f"OS: {platform.system()} {platform.release()} (build {platform.version()})")
    lines.append(f"Architecture: {platform.machine()}")
    lines.append(f"Python: {platform.python_version()} ({platform.python_implementation()})")
    lines.append("")

    # --- Paths ---
    lines.append("[PATHS]")

    ch_dir = find_clone_hero_directory()
    if ch_dir:
        lines.append(f"Data dir:   {ch_dir} [EXISTS]")
    else:
        lines.append("Data dir:   NOT FOUND")

    ch_docs = get_clone_hero_documents_dir()
    if ch_docs:
        lines.append(f"Docs dir:   {ch_docs} [EXISTS]")
    else:
        lines.append(f"Docs dir:   NOT FOUND")

    log_path = None
    for _h in logger.handlers:
        if hasattr(_h, 'baseFilename'):
            log_path = Path(_h.baseFilename)
            break

    if log_path and log_path.exists():
        size_kb = log_path.stat().st_size / 1024
        lines.append(f"Log file:   {log_path} [EXISTS, {size_kb:.1f} KB]")
    elif log_path:
        lines.append(f"Log file:   {log_path} [MISSING]")
    else:
        lines.append("Log file:   UNKNOWN")

    if ch_dir:
        state_file = ch_dir / '.score_tracker_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                score_count = len(state.get('known_scores', {}))
                lines.append(f"State file: {state_file} [EXISTS, {score_count:,} scores tracked]")
            except Exception:
                lines.append(f"State file: {state_file} [EXISTS, unreadable]")
        else:
            lines.append(f"State file: {state_file} [MISSING]")

        songcache = ch_dir / 'songcache.bin'
        if songcache.exists():
            size_mb = songcache.stat().st_size / (1024 * 1024)
            lines.append(f"Song cache: {songcache} [EXISTS, {size_mb:.1f} MB]")
        else:
            lines.append(f"Song cache: {ch_dir / 'songcache.bin'} [MISSING]")

    index_path = get_chart_index_path()
    if index_path.exists():
        try:
            index = load_chart_index()
            lines.append(f"Chart idx:  {index_path} [EXISTS, {len(index):,} entries]")
        except Exception:
            lines.append(f"Chart idx:  {index_path} [EXISTS, unreadable]")
    else:
        lines.append(f"Chart idx:  {index_path} [MISSING]")

    lines.append("")

    # --- Settings (sanitized) ---
    lines.append("[SETTINGS]")
    settings = load_settings()
    safe_keys = [
        'bot_url', 'ocr_enabled', 'start_with_windows', 'minimize_to_tray',
        'songs_folder', 'auto_update', 'bridge_integration'
    ]
    for key in safe_keys:
        if key in settings:
            lines.append(f"  {key}: {settings[key]}")
    lines.append("")

    # --- Config (sanitized, no tokens) ---
    lines.append("[CONFIG]")
    config = load_config()
    client_id = config.get('client_id', '')
    lines.append(f"  paired:    {'yes' if config.get('auth_token') else 'no'}")
    if client_id:
        lines.append(f"  client_id: {client_id[:8]}... (truncated for security)")
    lines.append("")

    # --- Recent Log ---
    lines.append("[RECENT LOG (last 200 lines)]")
    if log_path and log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                log_lines = f.readlines()
            recent = log_lines[-200:]
            lines.extend(ln.rstrip() for ln in recent)
            if len(log_lines) > 200:
                lines.insert(-len(recent), f"  ... ({len(log_lines) - 200} earlier lines omitted) ...")
        except Exception as e:
            lines.append(f"  (Could not read log file: {e})")
    else:
        lines.append("  (No log file found - have you played a score yet?)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF REPORT")
    lines.append("=" * 60)

    content = "\n".join(lines)
    filename = f"CH_BugReport_{timestamp}.txt"

    # Try Desktop first (registry-based for OneDrive users), then Clone Hero docs, then cwd
    output_path = None
    try:
        if sys.platform == 'win32':
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            ) as key:
                desktop_str, _ = winreg.QueryValueEx(key, 'Desktop')
                desktop = Path(desktop_str)
            if desktop.exists():
                output_path = desktop / filename
        else:
            desktop = Path.home() / 'Desktop'
            if desktop.exists():
                output_path = desktop / filename
    except Exception:
        pass

    if not output_path:
        if ch_docs:
            output_path = ch_docs / filename
        elif ch_dir:
            output_path = ch_dir / filename
        else:
            output_path = Path(filename)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f"Bug report saved to:")
        print(f"  {output_path}")
    except Exception as e:
        print_error(f"Could not save report: {e}")
        return

    print()
    print_header("HOW TO REPORT A BUG", width=50)
    print("  1. Go to: https://github.com/Dr-Goofenthol/CH_HiScore/issues/new")
    print("  2. Describe what happened and what you expected")
    print("  3. Drag and drop the bug report file into the issue")
    print("  4. Add a screenshot of this console window if relevant")
    print("=" * 50)
    print()

    try:
        open_browser = input("Open GitHub issues page now? [Y/n]: ").strip().lower()
        if open_browser != 'n':
            import webbrowser
            webbrowser.open("https://github.com/Dr-Goofenthol/CH_HiScore/issues/new")
            print_info("Opened in browser.")
    except Exception:
        pass


def bridge_status_command():
    """Check Bridge integration status"""
    from client.bridge_integration import (
        is_bridge_installed, is_bridge_running,
        is_cdp_available, is_protocol_registered
    )

    print_header("BRIDGE INTEGRATION STATUS", width=50)

    # Check installation
    is_installed, bridge_path = is_bridge_installed()
    if is_installed:
        print_success(f"Bridge Installed: {bridge_path}")
    else:
        print_error("Bridge Not Installed")

    # Check protocol registration
    if is_protocol_registered():
        print_success("Protocol Registered: chbridge:// is registered")
    else:
        print_error("Protocol Not Registered: chbridge:// not found")

    # Check if Bridge is running
    if is_bridge_running():
        print_success("Bridge Status: Running")

        # Check CDP
        if is_cdp_available():
            print_success("Remote Debugging: Enabled (port 9222)")
        else:
            print_warning("Remote Debugging: Not available")
            print("  Bridge is running but remote debugging is disabled")
    else:
        print_info("Bridge Status: Not running")

    # Check settings
    settings = load_settings()
    bridge_config = settings.get('bridge_integration', {})
    enabled = bridge_config.get('enabled', False)

    if enabled:
        print_success("Integration: Enabled in settings")
    else:
        print_warning("Integration: Disabled in settings")

    print()


# Detailed help functions for --help flag
def show_command_help(command):
    """Display detailed help for a specific command"""
    help_functions = {
        'parse': show_parse_help,
        'resolvehashes': show_resolvehashes_help,
        'scancharts': show_scancharts_help,
        'resync': show_resync_help,
        'reset': show_reset_help,
        'settings': show_settings_help,
        'backup': show_backup_help,
        'restore': show_restore_help,
        'unpair': show_unpair_help,
        'status': show_status_help,
        'stats': show_stats_help,
        'update': show_update_help,
        'bridgestatus': show_bridgestatus_help,
        'recordsreport': show_recordsreport_help,
        'session': show_session_help,
        'mystats': show_mystats_help,
        'search': show_search_help,
        'compare': show_compare_help,
    }

    help_func = help_functions.get(command)
    if help_func:
        help_func()
        return True
    else:
        print_warning(f"No detailed help available for '{command}'")
        print_info("Type 'help' to see all available commands")
        print()
        return False


def show_parse_help():
    print_header("COMMAND: parse", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Manually parse and inspect a chart file to view all available")
    print("  metadata including notes, NPS, difficulty, and intensity.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Searches local chart index for matching charts")
    print("  2. Uses fuzzy search on title, artist, charter, or hash")
    print("  3. Displays comprehensive metadata for selected chart")
    print("  4. Shows multiple matches if found (you select one)")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • Want to inspect chart difficulty before playing")
    print("  • Check NPS and intensity ratings")
    print("  • Verify chart metadata is correct")
    print("  • Debugging chart information")
    print("  • Find chart file location on disk")
    print()
    print(f"{Fore.CYAN}DATA DISPLAYED:{Style.RESET_ALL}")
    print("  • Song title, artist, charter")
    print("  • Chart hash (full and abbreviated)")
    print("  • Total notes, average NPS, peak NPS")
    print("  • File path and existence status")
    print("  • Scan timestamp")
    print()
    print(f"{Fore.CYAN}REQUIREMENTS:{Style.RESET_ALL}")
    print("  • Chart index must exist (run 'scancharts' first)")
    print("  • Chart must be in your library")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > parse <search query>")
    print()
    print(f"{Fore.CYAN}EXAMPLES:{Style.RESET_ALL}")
    print("  > parse through the fire")
    print("    Search by song title")
    print()
    print("  > parse dragonforce")
    print("    Search by artist")
    print()
    print("  > parse 3dfe89a1")
    print("    Search by chart hash (partial or full)")
    print()
    print("  > parse frosted")
    print("    Search by charter name")
    print()
    print(f"{Fore.CYAN}NOTE:{Style.RESET_ALL}")
    print("  This command does NOT submit scores or modify anything.")
    print("  It only displays metadata from the local chart index.")
    print("  Data shown is read-only for inspection purposes.")
    print()


def show_resolvehashes_help():
    print_header("COMMAND: resolvehashes", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Fix old mystery hashes by replacing them with song names.")
    print("  This updates PAST scores that were submitted as [abc12345].")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Fetches list of unresolved hashes from server")
    print("     (only charts YOU have played)")
    print("  2. Scans your Clone Hero songs folder(s)")
    print("  3. Matches hashes and extracts song metadata")
    print("  4. Sends updates to server (with your confirmation)")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • You have old mystery hashes in score history")
    print("  • Leaderboards show [abc12345] instead of song names")
    print("  • You want to fix existing database entries")
    print()
    print(f"{Fore.CYAN}DATA COLLECTED:{Style.RESET_ALL}")
    print("  • Song title, artist, charter (from song.ini)")
    print()
    print(f"{Fore.CYAN}NOTE:{Style.RESET_ALL}")
    print("  This only affects PAST scores. For future offline")
    print("  scores, use 'scancharts' instead.")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > resolvehashes")
    print()


def show_scancharts_help():
    print_header("COMMAND: scancharts", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Upload comprehensive chart metadata to prepare for")
    print("  FUTURE offline scores with full song information.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Scans ALL charts in your library")
    print("  2. Parses full chart data (notes, NPS, difficulty)")
    print("  3. Builds local index for fast lookups")
    print("  4. Uploads metadata to server database")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • First time setup (runs automatically)")
    print("  • After adding new charts to library")
    print("  • Want offline scores to have full metadata")
    print()
    print(f"{Fore.CYAN}DATA COLLECTED:{Style.RESET_ALL}")
    print("  • Song title, artist, charter, genre")
    print("  • NPS, peak NPS, note counts, chord counts")
    print("  • Per-difficulty/instrument data")
    print()
    print(f"{Fore.CYAN}SCANNING:{Style.RESET_ALL}")
    print("  • Incremental: skips unchanged files")
    print("  • Progress bar with ETA")
    print("  • Use --full to force complete rescan")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > scancharts          # Incremental scan")
    print("  > scancharts --full   # Full rescan")
    print()


def show_resync_help():
    print_header("COMMAND: resync", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Scan for scores that were achieved while the bot was")
    print("  offline or disconnected.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Reads entire scoredata.bin file")
    print("  2. Compares against local known scores cache")
    print("  3. Submits any new/improved scores to server")
    print("  4. Updates local cache with new scores")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • After playing Clone Hero with tracker closed")
    print("  • After bot/server was offline")
    print("  • Suspect some scores weren't submitted")
    print("  • After tracker crash or restart")
    print()
    print(f"{Fore.CYAN}NOTE:{Style.RESET_ALL}")
    print("  Offline scores may show as [abc12345] if chart")
    print("  metadata is missing. Run 'scancharts' first to")
    print("  ensure proper metadata for offline plays.")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > resync")
    print()


def show_reset_help():
    print_header("COMMAND: reset", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Clear all tracked score history and re-submit")
    print("  ALL your scores to the server from scratch.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Clears local known_scores cache")
    print("  2. Reads entire scoredata.bin file")
    print("  3. Submits every score as 'new'")
    print("  4. Rebuilds local cache")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • Connecting to a NEW server")
    print("  • Your scores are completely out of sync")
    print("  • Server database was reset")
    print("  • Starting fresh after major issues")
    print()
    print(f"{Fore.CYAN}WARNING:{Style.RESET_ALL}")
    print("  This will re-submit HUNDREDS or THOUSANDS of scores.")
    print("  Only use when absolutely necessary!")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > reset")
    print("  (Requires 'yes' confirmation)")
    print()


def show_settings_help():
    print_header("COMMAND: settings", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Configure tracker settings including bot URL,")
    print("  paths, features, and integrations.")
    print()
    print(f"{Fore.CYAN}AVAILABLE SETTINGS:{Style.RESET_ALL}")
    print("  • Bot URL - Server connection endpoint")
    print("  • Clone Hero Path - Installation directory")
    print("  • Songs Folder - Custom songs location")
    print("  • OCR Settings - Results screen capture")
    print("  • Minimize to Tray - System tray integration")
    print("  • Start with Windows - Auto-launch on boot")
    print("  • Bridge Integration - Clone Hero Bridge support")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > settings")
    print("  (Opens interactive menu)")
    print()


def show_backup_help():
    print_header("COMMAND: backup", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Create a backup of your current configuration")
    print("  to protect against data loss or corruption.")
    print()
    print(f"{Fore.CYAN}WHAT GETS BACKED UP:{Style.RESET_ALL}")
    print("  • Configuration (.score_tracker_config.json)")
    print("  • Settings (.score_tracker_settings.json)")
    print("  • Known scores state (.score_tracker_state.json)")
    print("  • Chart index (.score_tracker_chart_index.json)")
    print()
    print(f"{Fore.CYAN}BACKUP LOCATION:{Style.RESET_ALL}")
    print("  Saved to: Documents\\Clone Hero\\backups\\")
    print("  Filename: tracker_backup_YYYYMMDD_HHMMSS.zip")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > backup")
    print()


def show_restore_help():
    print_header("COMMAND: restore", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Restore configuration from a previous backup.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Lists available backups")
    print("  2. You select which backup to restore")
    print("  3. Extracts backup files to tracker directory")
    print("  4. Tracker restarts with restored config")
    print()
    print(f"{Fore.CYAN}WHAT GETS RESTORED:{Style.RESET_ALL}")
    print("  • All configuration files")
    print("  • Known scores state")
    print("  • Chart index (if exists)")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > restore")
    print("  (Shows interactive backup selection)")
    print()


def show_unpair_help():
    print_header("COMMAND: unpair", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Disconnect this tracker from your Discord account.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Removes auth_token from configuration")
    print("  2. Tracker will prompt for pairing on next restart")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • Switching to different Discord account")
    print("  • Giving PC to someone else")
    print("  • Troubleshooting pairing issues")
    print()
    print(f"{Fore.CYAN}NOTE:{Style.RESET_ALL}")
    print("  Your scores remain on server. This only affects")
    print("  the link between this PC and your Discord account.")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > unpair")
    print("  (Requires 'yes' confirmation)")
    print()


def show_status_help():
    print_header("COMMAND: status", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Comprehensive diagnostic view of tracker status.")
    print()
    print(f"{Fore.CYAN}INFORMATION SHOWN:{Style.RESET_ALL}")
    print("  • Server Connection - Live connectivity test")
    print("  • Score Tracking - Known scores count")
    print("  • OCR Status - Detailed OCR performance stats")
    print("  • Features - Individual feature enable/disable status")
    print()
    print(f"{Fore.CYAN}USE CASE:{Style.RESET_ALL}")
    print("  Troubleshooting - 'Is everything working correctly?'")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > status")
    print()


def show_stats_help():
    print_header("COMMAND: stats", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Quick at-a-glance summary of your activity.")
    print()
    print(f"{Fore.CYAN}INFORMATION SHOWN:{Style.RESET_ALL}")
    print("  • Total Scores Tracked - Overall count")
    print("  • Last Score - Timestamp + relative time")
    print("  • OCR - One-line summary")
    print("  • Features - Comma-separated enabled features")
    print()
    print(f"{Fore.CYAN}USE CASE:{Style.RESET_ALL}")
    print("  Quick glance - 'What's my recent activity?'")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > stats")
    print()


def show_update_help():
    print_header("COMMAND: update", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Check for and download tracker updates.")
    print()
    print(f"{Fore.CYAN}HOW IT WORKS:{Style.RESET_ALL}")
    print("  1. Checks GitHub for latest release")
    print("  2. Compares against current version")
    print("  3. Downloads new exe if update available")
    print("  4. Prompts to restart with new version")
    print()
    print(f"{Fore.CYAN}AUTO-UPDATE:{Style.RESET_ALL}")
    print("  Tracker automatically checks for updates on startup.")
    print("  This command forces an immediate check.")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > update")
    print()


def show_bridgestatus_help():
    print_header("COMMAND: bridgestatus", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Check Clone Hero Bridge integration status.")
    print()
    print(f"{Fore.CYAN}INFORMATION SHOWN:{Style.RESET_ALL}")
    print("  • Bridge Path - Installation location")
    print("  • Protocol Registration - chhb:// URL handler status")
    print("  • Integration Setting - Enabled/Disabled")
    print()
    print(f"{Fore.CYAN}WHAT IS BRIDGE:{Style.RESET_ALL}")
    print("  Clone Hero Bridge allows you to download songs")
    print("  directly from Discord links or websites.")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > bridgestatus")
    print()


def show_recordsreport_help():
    print_header("COMMAND: recordsreport", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Generate comprehensive reports of all #1 records")
    print("  you currently hold on the server.")
    print()
    print(f"{Fore.CYAN}WHAT IT SHOWS:{Style.RESET_ALL}")
    print("  • Song Information - Title, artist, charter, album, genre")
    print("  • Chart Details - Instrument, difficulty, length, NPS, peak NPS")
    print("  • Your Performance - Score, accuracy, FC status, stars")
    print("  • Record Context - Previous holder, improvement %, held duration")
    print("  • Quick Links - Enchor.us URL for easy chart access")
    print()
    print(f"{Fore.CYAN}OUTPUT FORMATS:{Style.RESET_ALL}")
    print("  • Text (default) - Human-readable with ASCII formatting")
    print("  • CSV - Spreadsheet format (Excel, Google Sheets)")
    print("  • JSON - Programmatic format for custom tools")
    print("  • All - Generate all three formats at once")
    print()
    print(f"{Fore.CYAN}SAVE LOCATION:{Style.RESET_ALL}")
    print("  Reports saved to: Documents\\Clone Hero\\records\\")
    print("  Filename format: {username}_records_{timestamp}.{ext}")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • Track your overall #1 record count")
    print("  • Share accomplishments with friends/community")
    print("  • Analyze your strengths (instruments, difficulties)")
    print("  • Export data for custom analysis or spreadsheets")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > recordsreport            # Interactive mode (prompts for format)")
    print("  > recordsreport --text     # Text format only")
    print("  > recordsreport --csv      # CSV format only")
    print("  > recordsreport --json     # JSON format only")
    print("  > recordsreport --all      # Generate all 3 formats")
    print()
    print(f"{Fore.CYAN}OPTIONS:{Style.RESET_ALL}")
    print("  --text    Generate human-readable text report")
    print("  --csv     Generate spreadsheet-compatible CSV report")
    print("  --json    Generate programmatic JSON report")
    print("  --all     Generate all three formats at once")
    print()


def show_session_help():
    print_header("COMMAND: session", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  View statistics for your current play session.")
    print()
    print(f"{Fore.CYAN}WHAT IT SHOWS:{Style.RESET_ALL}")
    print("  • Session duration and start time")
    print("  • Total scores submitted this session")
    print("  • Records broken, new FCs, personal bests")
    print("  • Recent scores with timestamps (last 5)")
    print("  • Average accuracy and best score")
    print("  • Instruments played and total notes hit")
    print()
    print(f"{Fore.CYAN}WHEN TO USE:{Style.RESET_ALL}")
    print("  • Check progress during long play sessions")
    print("  • Review what you've accomplished today")
    print("  • Quick 'how am I doing right now?' check")
    print()
    print(f"{Fore.CYAN}AUTO-SUMMARY ON EXIT:{Style.RESET_ALL}")
    print("  When you type 'quit', a session summary is shown")
    print("  automatically (if you submitted any scores).")
    print("  This can be toggled in Settings.")
    print()
    print(f"{Fore.CYAN}SESSION TRACKING:{Style.RESET_ALL}")
    print("  • Session starts when tracker launches")
    print("  • Resets when you close and restart tracker")
    print("  • All stats are client-side (instant, no API calls)")
    print()
    print(f"{Fore.CYAN}USAGE:{Style.RESET_ALL}")
    print("  > session")
    print()


def show_mystats_help():
    print_header("COMMAND: mystats", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  View comprehensive statistics from the server about all")
    print("  your scores, records, and achievements.")
    print()
    print(f"{Fore.CYAN}WHAT IT SHOWS:{Style.RESET_ALL}")
    print("  • Overall performance (total scores, records, FCs, avg accuracy)")
    print("  • Breakdown by instrument")
    print("  • Breakdown by difficulty (with --full flag)")
    print("  • Top achievements (hardest FC, highest score, most played)")
    print("  • Recent activity (last 7 days)")
    print()
    print(f"{Fore.CYAN}FILTERS:{Style.RESET_ALL}")
    print("  --timeframe, -t  Limit to specific time period:")
    print("                   7d (last 7 days)")
    print("                   30d (last 30 days)")
    print("                   90d (last 90 days)")
    print("                   all (all-time, default)")
    print()
    print("  --instrument, -i  Filter to specific instrument:")
    print("                   0 (Lead Guitar)")
    print("                   1 (Bass)")
    print("                   2 (Rhythm)")
    print("                   3 (Keys)")
    print("                   4 (Drums)")
    print()
    print("  --full, -f       Show extended details including difficulty")
    print("                   breakdown (larger output)")
    print()
    print(f"{Fore.CYAN}EXAMPLES:{Style.RESET_ALL}")
    print("  > mystats")
    print("    View all-time stats for all instruments")
    print()
    print("  > mystats --timeframe 30d")
    print("    View stats for last 30 days only")
    print()
    print("  > mystats --instrument 0")
    print("    View stats for Lead Guitar only")
    print()
    print("  > mystats -t 7d -i 4")
    print("    View last week's Drums stats")
    print()
    print("  > mystats --full")
    print("    View all-time stats with full difficulty breakdown")
    print()
    print(f"{Fore.CYAN}DIFFERENCE FROM SESSION:{Style.RESET_ALL}")
    print("  session  = Current play session (resets on restart)")
    print("  mystats  = All-time server statistics (persistent)")
    print()


def show_search_help():
    print_header("COMMAND: search", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Search your scores with flexible filters including text")
    print("  search, instrument, difficulty, and full combo status.")
    print()
    print(f"{Fore.CYAN}SEARCH SYNTAX:{Style.RESET_ALL}")
    print("  search [query] [filters]")
    print()
    print("  The query is any text after 'search' that doesn't start")
    print("  with '--'. It will match song titles and artist names.")
    print()
    print(f"{Fore.CYAN}FILTERS:{Style.RESET_ALL}")
    print("  --instrument, -i  Filter by instrument ID:")
    print("                   0 (Lead Guitar)")
    print("                   1 (Bass)")
    print("                   2 (Rhythm)")
    print("                   3 (Keys)")
    print("                   4 (Drums)")
    print()
    print("  --difficulty, -d  Filter by difficulty ID:")
    print("                   0 (Easy)")
    print("                   1 (Medium)")
    print("                   2 (Hard)")
    print("                   3 (Expert)")
    print()
    print("  --fc             Show only full combos")
    print()
    print("  --page, -p       Jump to specific page (10 results per page)")
    print()
    print(f"{Fore.CYAN}EXAMPLES:{Style.RESET_ALL}")
    print("  > search")
    print("    Show all your scores (paginated)")
    print()
    print("  > search dragonforce")
    print("    Find all your Dragonforce scores")
    print()
    print("  > search --instrument 0")
    print("    Show all Lead Guitar scores")
    print()
    print("  > search --instrument 0 --difficulty 3")
    print("    Show all Expert Lead Guitar scores")
    print()
    print("  > search --fc")
    print("    Show all your full combos")
    print()
    print("  > search ttfaf --instrument 0 --page 2")
    print("    Search for 'ttfaf' on Lead Guitar, page 2")
    print()
    print(f"{Fore.CYAN}PAGINATION:{Style.RESET_ALL}")
    print("  Results show 10 scores per page. Use --page to navigate.")
    print("  The command will show you the page range and total results.")
    print()
    print(f"{Fore.CYAN}RESULT DISPLAY:{Style.RESET_ALL}")
    print("  Each result shows:")
    print("  • Song title, artist, difficulty, instrument")
    print("  • Your score, stars, and rank")
    print("  • FC status and date played")
    print("  • Chart hash for reference")
    print()


def show_compare_help():
    print_header("COMMAND: compare", width=60)
    print()
    print(f"{Fore.CYAN}PURPOSE:{Style.RESET_ALL}")
    print("  Compare your scores head-to-head with another user to")
    print("  see who's winning on which songs and instruments.")
    print()
    print(f"{Fore.CYAN}SYNTAX:{Style.RESET_ALL}")
    print("  compare <discord_user_id>")
    print()
    print(f"{Fore.CYAN}GETTING A DISCORD USER ID:{Style.RESET_ALL}")
    print("  1. Enable Developer Mode in Discord:")
    print("     • Settings > App Settings > Advanced")
    print("     • Toggle 'Developer Mode' ON")
    print()
    print("  2. Copy the user's ID:")
    print("     • Right-click their profile or message")
    print("     • Select 'Copy User ID'")
    print()
    print(f"{Fore.CYAN}WHAT IT SHOWS:{Style.RESET_ALL}")
    print("  • Overall record (who's winning more songs)")
    print("  • Your win rate percentage")
    print("  • Breakdown by instrument")
    print("  • Your biggest wins (largest score gaps)")
    print("  • Their biggest wins")
    print("  • Close matches (within 1% difference)")
    print()
    print(f"{Fore.CYAN}EXAMPLES:{Style.RESET_ALL}")
    print("  > compare 123456789012345678")
    print("    Compare your scores with user ID 123456789012345678")
    print()
    print(f"{Fore.CYAN}REQUIREMENTS:{Style.RESET_ALL}")
    print("  • Both you and the other user must be paired")
    print("  • You must have played at least one common song")
    print("  • Comparisons are per chart/instrument/difficulty")
    print()
    print(f"{Fore.CYAN}NOTE:{Style.RESET_ALL}")
    print("  Only songs you've BOTH played on the same instrument")
    print("  and difficulty are compared. If you haven't played any")
    print("  common songs, the command will tell you.")
    print()


def main():
    import sys

    # Check for --bridge-deeplink command-line argument
    if len(sys.argv) > 1 and sys.argv[1] == '--bridge-deeplink':
        # Handle Bridge deeplink
        if len(sys.argv) > 2:
            bridge_url = sys.argv[2]

            # Load settings to get Bridge configuration
            settings = load_settings()
            bridge_config = settings.get('bridge_integration', {})
            bridge_enabled = bridge_config.get('enabled', False)
            bridge_path = bridge_config.get('bridge_path')

            if not bridge_enabled:
                print_error("Bridge Integration is disabled.")
                print_info("Enable it in Settings to use Bridge links.")
                input("\nPress Enter to exit...")
                return

            # Handle the deeplink
            from client.bridge_integration import handle_bridge_deeplink

            print_info("Connecting to Bridge...")

            if bridge_path:
                success, message = handle_bridge_deeplink(bridge_url, Path(bridge_path))
            else:
                success, message = handle_bridge_deeplink(bridge_url)

            if success:
                print_success(message)
                print_info("Closing in 2 seconds...")
                time.sleep(2)
                return
            else:
                print_error(f"Bridge link failed: {message}")
                print_info("You can try:")
                print("  1. Make sure Bridge is installed")
                print("  2. Check Bridge integration settings")
                print("  3. Close Bridge and try again")
                input("\nPress Enter to exit...")
                return
        else:
            print_error("No Bridge URL provided")
            input("\nPress Enter to exit...")
            return

    # Check for single instance
    success, message, stale_pid = acquire_instance_lock()
    if not success:
        print_error("Another instance of Clone Hero Score Tracker is already running!")
        print_info("Check your system tray for the existing instance.")
        print_info(f"Details: {message}")
        print()
        print("If you're sure no other instance is running:")
        print(f"  1. Open Task Manager and look for PID {stale_pid if stale_pid else 'unknown'}")
        print(f"  2. Or delete: {get_lock_file_path()}")
        print()
        input("Press Enter to exit...")
        return

    # Check for updates on startup
    print_info("Checking for updates...")
    check_and_prompt_update(silent_if_current=True)

    # Check if first run - show welcome message
    settings = load_settings()
    settings_path = get_settings_path()
    is_first_run = not (settings_path and settings_path.exists())

    if is_first_run:
        show_welcome_message()
        settings = load_settings()  # Reload after welcome

        # Prompt for server URL on first run
        print("\n" + "=" * 50)
        print("SERVER CONFIGURATION")
        print("=" * 50)
        print("\nEnter the bot server URL (provided by your server host).")
        print(f"Press Enter to use default: {DEFAULT_BOT_URL}")
        print()
        new_url = input("Server URL: ").strip()

        if new_url:
            # Basic validation
            if not new_url.startswith('http'):
                new_url = 'http://' + new_url
            settings['bot_url'] = new_url
            save_settings(settings)
            print_success(f"Server URL saved: {new_url}")
        else:
            print_info(f"Using default: {DEFAULT_BOT_URL}")
        print()

    # Show current settings
    bot_url = settings.get('bot_url', DEFAULT_BOT_URL)
    print_info(f"Server: {bot_url}")

    # Check if bot is running with retry
    connected, error = check_connection_with_retry(bot_url)

    if not connected:
        print(f"\n[!] {error}")
        print("\n" + "-" * 50)
        print("TROUBLESHOOTING:")
        print("-" * 50)
        print("  1. Make sure the Discord bot is running")
        print("  2. Check if the server URL is correct")
        print("  3. Verify your network connection")
        print(f"\n  Current server: {bot_url}")
        print("-" * 50)
        print("\nOptions:")
        print("  [S] Open Settings (change server URL)")
        print("  [R] Retry connection")
        print("  [Q] Quit")

        choice = input("\nChoice: ").strip().lower()
        if choice == 's':
            settings_menu()
            release_instance_lock()  # v2.5.1: Release lock before restart
            return main()
        elif choice == 'r':
            release_instance_lock()  # v2.5.1: Release lock before restart
            return main()
        return

    print_success("Connected to bot server!")

    # Check for existing auth token or start pairing
    auth_token = get_auth_token()

    if not auth_token:
        # First time setup - ask if new or existing user
        user_type = first_time_setup()
        is_existing = (user_type == 'existing')

        auth_token = do_pairing(is_existing_user=is_existing)
        if not auth_token:
            print_error("Pairing failed. Exiting.")
            input("\nPress Enter to exit...")
            return

    else:
        print_success("Already paired (auth token found)")

    # Find Clone Hero directory
    ch_dir = find_clone_hero_directory()
    if not ch_dir:
        print("\n" + "-" * 50)
        print("CLONE HERO NOT FOUND")
        print("-" * 50)
        print("\nCould not find Clone Hero data directory.")
        print("\nTo fix this:")
        print("  1. Install Clone Hero from clonehero.net")
        print("  2. Run Clone Hero at least once")
        print("  3. Or use 'settings' to set a custom path")
        print("\nExpected locations:")
        print("  Windows: %USERPROFILE%\\AppData\\LocalLow\\srylain Inc_\\Clone Hero")
        print("  Mac: ~/Library/Application Support/com.srylain.CloneHero")
        print("  Linux: ~/.config/unity3d/srylain Inc_/Clone Hero")
        print("-" * 50)
        print("\nOptions:")
        print("  [S] Open Settings (set custom path)")
        print("  [Q] Quit")
        choice = input("\nChoice: ").strip().lower()
        if choice == 's':
            settings_menu()
            release_instance_lock()  # v2.5.1: Release lock before restart
            return main()
        return

    # Check Clone Hero settings
    ch_settings = check_clone_hero_settings()
    if ch_settings['warnings']:
        print()
        print_header("CLONE HERO SETTINGS WARNING", width=50)
        for warning in ch_settings['warnings']:
            print_warning(warning, indent=1)
        print("=" * 50)
        print()

    # --- Startup log header ---
    logger.info(f"{'='*60}")
    logger.info(f"Clone Hero Score Tracker v{VERSION} starting")
    logger.info(f"  Data dir:  {ch_dir}")
    ch_docs_dir_startup = get_clone_hero_documents_dir()
    logger.info(f"  Docs dir:  {ch_docs_dir_startup}")

    # Print the log file path so users can always find it
    for _handler in logger.handlers:
        if hasattr(_handler, 'baseFilename'):
            print_info(f"Debug log: {_handler.baseFilename}")
            break

    # Load song cache for metadata
    song_cache = {}
    songcache_path = ch_dir / 'songcache.bin'
    if songcache_path.exists():
        try:
            parser = SongCacheParser(str(songcache_path))
            song_cache = parser.parse()
            print_success(f"Song cache loaded ({len(song_cache)} songs)")
            logger.info(f"  Song cache: {len(song_cache)} songs loaded")
        except Exception as e:
            print_warning("Could not load song cache - songs will show as hashes")
            log_exception(logger, "Failed to load song cache", e)
    else:
        logger.info("  Song cache: not found (songcache.bin missing)")

    # Check OCR availability
    ocr_enabled = settings.get('ocr_enabled', False)
    if ocr_enabled:
        ocr_ok, ocr_msg = check_ocr_available()
        if ocr_ok:
            print_success(f"OCR enabled: {ocr_msg}")
            logger.info(f"  OCR: enabled ({ocr_msg})")
        else:
            print_warning(f"OCR disabled: {ocr_msg}")
            logger.info(f"  OCR: disabled ({ocr_msg})")
            ocr_enabled = False
    else:
        logger.info("  OCR: disabled (user setting)")

    # Start system tray if enabled
    tray_enabled = settings.get('minimize_to_tray', False)
    if tray_enabled:
        if HAS_TRAY_SUPPORT:
            # Show startup notification if program is set to start with Windows
            show_notification = settings.get('start_with_windows', False)
            start_tray_icon(show_startup_notification=show_notification)
            # Start monitoring for window minimize to hide to tray
            monitor_window_minimize()
            print_info("Tip: Click the minimize button (-) to minimize to tray")
        else:
            print_warning("Minimize to tray enabled but pystray not installed")
            tray_enabled = False

    # Ensure Windows startup registry points to current exe (v2.6.4 fix)
    ensure_startup_entry_current()

    # State file to track which scores we've already seen
    # Store in Clone Hero directory so it persists across EXE runs
    state_file = ch_dir / '.score_tracker_state.json'

    # Create score handler with auth token and song cache
    score_handler = create_score_handler(auth_token, song_cache, ocr_enabled=ocr_enabled)

    try:
        # Create watcher
        watcher = CloneHeroWatcher(
            clone_hero_dir=str(ch_dir),
            state_file=str(state_file),
            on_new_score=score_handler
        )

        # Check if this is first run, migration needed, or returning
        if not state_file.exists():
            print("\n[*] First run detected!")
            print_info("Initializing with existing scores...")
            print_info("Only NEW scores from this point forward will be detected.\n")
            logger.info("  State: first run - initializing from current scoredata.bin")
            watcher.initialize_state()
        elif watcher.needs_state_migration():
            # Old format state file - re-initialize silently without submitting
            print_info("Migrating state file...")
            logger.info("  State: migrating from old format")
            watcher.initialize_state(silent=True)
        else:
            logger.info(f"  State: {len(watcher.state.known_scores)} known scores loaded")
            # Scan for any scores made while tracker was offline
            watcher.catch_up_scan()

        logger.info(f"Tracker ready - monitoring {ch_dir}")

        # Start watching in background thread
        import threading

        watcher.start()

        # Start background polling of currentsong.txt for song metadata caching
        start_song_cache_polling()

        # Clear screen by adding blank lines (startup messages still accessible by scrolling up)
        print("\n" * 15)

        # Show ASCII banner
        show_ascii_banner()

        # Show ready message with available commands
        print("=" * 50)
        print("READY! Monitoring for new scores...")
        print("=" * 50)
        print("\nType 'help' for available commands")
        print("-" * 50)

        # Command loop
        while True:
            try:
                cmd = input("> ").strip().lower()

                if not cmd:
                    continue

                # Parse --help flag
                if ' --help' in cmd or cmd.endswith('--help'):
                    # Extract base command (remove --help)
                    base_cmd = cmd.replace(' --help', '').replace('--help', '').strip()
                    if base_cmd:
                        show_command_help(base_cmd)
                    else:
                        # Just "--help" with no command
                        print_info("Usage: COMMAND --help")
                        print_info("Example: resolvehashes --help")
                        print()
                    continue

                elif cmd == "help" or cmd == "?":
                    print_header("AVAILABLE COMMANDS", width=50)

                    print(f"{Fore.CYAN}Monitoring & Status:{Style.RESET_ALL}")
                    print_plain("  status         Check server connection and score tracking status")
                    print_plain("  stats          View quick stats (tracked scores, OCR, features)")

                    print(f"\n{Fore.CYAN}Score Management:{Style.RESET_ALL}")
                    print_plain("  resync         Scan for scores made while bot was offline")
                    print_plain("  reset          Clear state and re-submit ALL scores to server")

                    print(f"\n{Fore.CYAN}Chart Metadata:{Style.RESET_ALL}")
                    print_plain("  parse          Manually parse a chart and display all metadata")
                    print_plain("  resolvehashes  Fix old mystery hashes with song names (past scores)")
                    print_plain("  scancharts     Upload chart data for future offline scores")
                    print_plain("  refreshcache   Reload song metadata from Clone Hero")

                    print(f"\n{Fore.CYAN}Configuration:{Style.RESET_ALL}")
                    print_plain("  settings       Configure bot URL, paths, and options")
                    print_plain("  backup         Backup current configuration to file")
                    print_plain("  restore        Restore configuration from backup file")
                    print_plain("  update         Check for and download tracker updates")

                    print(f"\n{Fore.CYAN}Analysis & Stats:{Style.RESET_ALL}")
                    print_plain("  mystats        View comprehensive server statistics")
                    print_plain("  search         Search your scores with filters")
                    print_plain("  compare        Head-to-head comparison with another user")
                    print_plain("  session        View current session summary")
                    print_plain("  recordsreport  Generate comprehensive records report")

                    print(f"\n{Fore.CYAN}Utilities:{Style.RESET_ALL}")
                    print_plain("  bridgestatus   Check Bridge integration status")
                    print_plain("  exportlogs     Export debug logs to zip file")
                    print_plain("  bugreport      Generate a bug report file for GitHub Issues")
                    print_plain("  unpair         Disconnect from Discord account")
                    if tray_enabled:
                        print_plain("  minimize       Minimize to system tray (if enabled)")
                    print_plain("  debug          Enter debug mode (password required)")

                    print(f"\n{Fore.CYAN}General:{Style.RESET_ALL}")
                    print_plain("  help           Show this help message")
                    print_plain("  quit           Exit the tracker")

                    print("\n" + "=" * 50)
                    print("Type 'COMMAND --help' for detailed info")
                    print("Example: resolvehashes --help")
                    print("=" * 50 + "\n")

                elif cmd == "status":
                    bot_url = get_bot_url()
                    print_header("STATUS OVERVIEW", width=50)

                    # Connection status
                    print(f"{Fore.CYAN}Server Connection:{Style.RESET_ALL}")
                    print_plain(f"  URL: {bot_url}")
                    try:
                        response = requests.get(f"{bot_url}/health", timeout=5)
                        if response.status_code == 200:
                            print_success("Status: Connected", indent=1)
                        else:
                            print_warning(f"Status: Error (HTTP {response.status_code})", indent=1)
                    except Exception:
                        print_error("Status: Disconnected", indent=1)

                    # Score tracking
                    print(f"\n{Fore.CYAN}Score Tracking:{Style.RESET_ALL}")
                    print_plain(f"  Known Scores: {len(watcher.state.known_scores)}")

                    # OCR status
                    print(f"\n{Fore.CYAN}OCR Status:{Style.RESET_ALL}")
                    if settings.get('ocr_enabled', False):
                        ocr_ok, ocr_msg = check_ocr_available()
                        if ocr_ok:
                            print_success("Enabled", indent=1)
                            if _ocr_stats['attempts'] > 0:
                                success_rate = (_ocr_stats['successes'] / _ocr_stats['attempts']) * 100
                                print_plain(f"  Attempts: {_ocr_stats['attempts']}")
                                print_plain(f"  Successes: {_ocr_stats['successes']} ({success_rate:.1f}%)")
                            else:
                                print_info("No attempts yet", indent=1)
                        else:
                            print_warning(f"Disabled: {ocr_msg}", indent=1)
                    else:
                        print_info("Disabled", indent=1)

                    # System tray status
                    print(f"\n{Fore.CYAN}Features:{Style.RESET_ALL}")
                    tray_status = "Enabled" if settings.get('minimize_to_tray', False) else "Disabled"
                    print_plain(f"  System Tray: {tray_status}")
                    startup_status = "Enabled" if settings.get('start_with_windows', False) else "Disabled"
                    print_plain(f"  Auto-Start: {startup_status}")

                    # Bridge integration status
                    bridge_config = settings.get('bridge_integration', {})
                    bridge_enabled = bridge_config.get('enabled', False)
                    bridge_status = "Enabled" if bridge_enabled else "Disabled"
                    print_plain(f"  Bridge Integration: {bridge_status}")

                    print()

                elif cmd == "resync":
                    print("\n[*] Scanning for missed scores...")
                    watcher.catch_up_scan()
                    print()

                elif cmd == "resolvehashes":
                    resolve_hashes_command()

                elif cmd == "scancharts" or cmd.startswith("scancharts "):
                    # v2.6.4: Support --full flag
                    force_full = "--full" in cmd
                    scancharts_command(force_full=force_full)

                elif cmd == "parse" or cmd.startswith("parse "):
                    # Extract search query
                    if cmd == "parse":
                        print_error("No search query provided!")
                        print_info("Usage: parse <search query>")
                        print_info("Example: parse through the fire")
                        print()
                    else:
                        # Extract query after "parse "
                        query = cmd[6:].strip()
                        parse_command(query)

                elif cmd == "reset":
                    print("\n" + "=" * 50)
                    print("RESET SCORE STATE")
                    print("=" * 50)
                    print("\nThis will:")
                    print("  1. Clear all tracked score history")
                    print("  2. Re-submit ALL your scores to the server")
                    print("\nUse this when connecting to a new server or if")
                    print("your scores are out of sync.")
                    print()
                    confirm = input("Are you sure? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        print("\n[*] Clearing score state...")
                        # Clear the known scores
                        watcher.state.known_scores = {}
                        watcher.state.save_state()
                        print_success("State cleared!")
                        print("\n[*] Re-submitting all scores...")
                        # Now catch_up_scan will submit everything as "new"
                        watcher.catch_up_scan()
                        print("\n[+] Reset complete!")
                    else:
                        print("  Cancelled.")
                    print()

                elif cmd == "settings":
                    watcher.stop()
                    settings_menu()
                    print("\n[*] Restarting tracker with new settings...")
                    release_instance_lock()  # v2.5.1: Release lock before restart
                    return main()  # Restart with new settings

                elif cmd == "update":
                    check_and_prompt_update(silent_if_current=False)

                elif cmd == "stats":
                    print()
                    print_header("QUICK STATS", width=50)
                    print_plain(f"  Total Scores Tracked: {len(watcher.state.known_scores)}")

                    # Last score submitted (from state file timestamp)
                    state_file_path = ch_dir / '.score_tracker_state.json'
                    if state_file_path.exists():
                        try:
                            with open(state_file_path, 'r') as f:
                                state_data = json.load(f)
                                last_updated = state_data.get('last_updated')
                                if last_updated:
                                    from datetime import datetime
                                    dt = datetime.fromtimestamp(last_updated)
                                    time_ago = time.time() - last_updated
                                    if time_ago < 60:
                                        time_str = f"{int(time_ago)}s ago"
                                    elif time_ago < 3600:
                                        time_str = f"{int(time_ago / 60)}m ago"
                                    else:
                                        time_str = f"{int(time_ago / 3600)}h ago"
                                    print_plain(f"  Last Score: {dt.strftime('%Y-%m-%d %H:%M:%S')} ({time_str})")
                        except Exception:
                            pass

                    # OCR status
                    if settings.get('ocr_enabled', False):
                        if _ocr_stats['attempts'] > 0:
                            success_rate = (_ocr_stats['successes'] / _ocr_stats['attempts']) * 100
                            print_plain(f"  OCR: {_ocr_stats['successes']}/{_ocr_stats['attempts']} successful ({success_rate:.1f}%)")
                        else:
                            print_plain("  OCR: Enabled (no attempts yet)")
                    else:
                        print_plain("  OCR: Disabled")

                    # Features
                    features_enabled = []
                    if settings.get('minimize_to_tray', False):
                        features_enabled.append("System Tray")
                    if settings.get('start_with_windows', False):
                        features_enabled.append("Auto-Start")
                    bridge_config = settings.get('bridge_integration', {})
                    if bridge_config.get('enabled', False):
                        features_enabled.append("Bridge")

                    if features_enabled:
                        print_plain(f"  Features: {', '.join(features_enabled)}")
                    else:
                        print_plain("  Features: None enabled")

                    print()

                elif cmd == "backup":
                    print()
                    backup_config_command()
                    print()

                elif cmd == "restore":
                    print()
                    restore_config_command()
                    print()

                elif cmd == "exportlogs":
                    print()
                    export_logs_command()
                    print()

                elif cmd == "bugreport":
                    print()
                    bugreport_command()
                    print()

                elif cmd == "bridgestatus":
                    print()
                    bridge_status_command()
                    print()

                elif cmd == "recordsreport" or cmd.startswith("recordsreport "):
                    # v2.6.4: Support format flags (--text, --csv, --json, --all)
                    format_option = None
                    if "--text" in cmd:
                        format_option = "text"
                    elif "--csv" in cmd:
                        format_option = "csv"
                    elif "--json" in cmd:
                        format_option = "json"
                    elif "--all" in cmd:
                        format_option = "all"

                    print()
                    recordsreport_command(format_option=format_option)
                    print()

                elif cmd == "session":
                    print()
                    session_command()
                    print()

                elif cmd == "mystats" or cmd.startswith("mystats "):
                    # v2.6.4: Support timeframe and instrument flags
                    timeframe = 'all'
                    instrument_id = None
                    full = False

                    if "--timeframe" in cmd or "-t" in cmd:
                        # Extract timeframe value
                        parts = cmd.split()
                        for i, part in enumerate(parts):
                            if part in ("--timeframe", "-t") and i + 1 < len(parts):
                                timeframe = parts[i + 1]
                                break

                    if "--instrument" in cmd or "-i" in cmd:
                        # Extract instrument ID
                        parts = cmd.split()
                        for i, part in enumerate(parts):
                            if part in ("--instrument", "-i") and i + 1 < len(parts):
                                try:
                                    instrument_id = int(parts[i + 1])
                                except ValueError:
                                    print_warning(f"Invalid instrument ID: {parts[i + 1]}")

                    if "--full" in cmd or "-f" in cmd:
                        full = True

                    print()
                    mystats_command(timeframe=timeframe, instrument_id=instrument_id, full=full)
                    print()

                elif cmd == "search" or cmd.startswith("search "):
                    # v2.6.4: Search user's scores with filters
                    query = None
                    instrument_id = None
                    difficulty_id = None
                    fc_only = False
                    page = 1

                    # Extract query (any text not starting with --)
                    parts = cmd.split()
                    query_parts = []
                    i = 1  # Skip "search"
                    while i < len(parts) and not parts[i].startswith('-'):
                        query_parts.append(parts[i])
                        i += 1
                    if query_parts:
                        query = ' '.join(query_parts)

                    if "--instrument" in cmd or "-i" in cmd:
                        parts = cmd.split()
                        for j, part in enumerate(parts):
                            if part in ("--instrument", "-i") and j + 1 < len(parts):
                                try:
                                    instrument_id = int(parts[j + 1])
                                except ValueError:
                                    print_warning(f"Invalid instrument ID: {parts[j + 1]}")

                    if "--difficulty" in cmd or "-d" in cmd:
                        parts = cmd.split()
                        for j, part in enumerate(parts):
                            if part in ("--difficulty", "-d") and j + 1 < len(parts):
                                try:
                                    difficulty_id = int(parts[j + 1])
                                except ValueError:
                                    print_warning(f"Invalid difficulty ID: {parts[j + 1]}")

                    if "--fc" in cmd:
                        fc_only = True

                    if "--page" in cmd or "-p" in cmd:
                        parts = cmd.split()
                        for j, part in enumerate(parts):
                            if part in ("--page", "-p") and j + 1 < len(parts):
                                try:
                                    page = int(parts[j + 1])
                                    if page < 1:
                                        page = 1
                                except ValueError:
                                    print_warning(f"Invalid page number: {parts[j + 1]}")

                    print()
                    search_command(query=query, instrument_id=instrument_id, difficulty_id=difficulty_id,
                                   fc_only=fc_only, page=page)
                    print()

                elif cmd == "compare" or cmd.startswith("compare "):
                    # v2.6.4: Compare scores with another user
                    # Extract Discord user ID from command
                    parts = cmd.split()
                    if len(parts) < 2:
                        print_warning("Usage: compare <discord_user_id>")
                        print()
                        print("To get a user's Discord ID:")
                        print("  1. Enable Developer Mode in Discord (Settings > Advanced)")
                        print("  2. Right-click the user's profile or message")
                        print("  3. Select 'Copy User ID'")
                        print()
                    else:
                        user2_discord_id = parts[1]
                        print()
                        compare_command(user2_discord_id)
                        print()

                elif cmd == "refreshcache":
                    print()
                    print_info("Reloading song metadata from Clone Hero...")
                    try:
                        songcache_path = ch_dir / 'songcache.bin'
                        if songcache_path.exists():
                            parser = SongCacheParser(str(songcache_path))
                            song_cache = parser.parse()
                            print_success(f"Refreshed! Loaded {len(song_cache)} songs from cache")
                        else:
                            print_error("songcache.bin not found")
                            print_info("Launch Clone Hero to generate the song cache")
                    except Exception as e:
                        print_error(f"Failed to refresh cache: {e}")
                    print()

                elif cmd == "unpair":
                    print("\n  This will disconnect this machine from your Discord account.")
                    confirm = input("  Are you sure? (yes/no): ").strip().lower()
                    if confirm == "yes":
                        config = load_config()
                        config.pop('auth_token', None)
                        save_config(config)
                        print("\n[+] Unpaired successfully!")
                        print_info("Restart the tracker to pair again.")
                        watcher.stop()
                        input("\nPress Enter to exit...")
                        return
                    else:
                        print("  Cancelled.")
                    print()

                elif cmd == "minimize":
                    if tray_enabled:
                        print("\n[*] Minimizing to system tray...")
                        print_info("Right-click the tray icon to restore or exit.")
                        hide_console_window()
                    else:
                        print("\n[!] Minimize to tray is not enabled.")
                        print("    Enable it in Settings > Minimize to Tray")
                    print()

                elif cmd == "debug":
                    password = getpass.getpass("  Enter debug password: ").strip()

                    # Send password to server for authorization
                    try:
                        response = requests.post(
                            f"{get_bot_url()}/api/debug/authorize",
                            json={"password": password},
                            timeout=5
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data.get('authorized'):
                                watcher.stop()
                                stop_tray_icon()
                                debug_mode(auth_token)
                                print_info("Restarting tracker...")
                                release_instance_lock()  # v2.5.1: Release lock before restart
                                return main()
                            else:
                                print_error("Invalid password.")
                        elif response.status_code == 401:
                            print_error("Invalid password.")
                        else:
                            print_error(f"Authorization failed: HTTP {response.status_code}")
                            print_info("Check server connection and try again.")
                    except requests.exceptions.ConnectionError:
                        print_error("Could not connect to server for authorization.")
                    except Exception as e:
                        print_error(f"Authorization error: {e}")
                        log_exception(logger, "Debug authorization failed", e)
                    print()

                elif cmd == "quit" or cmd == "exit":
                    # Show session summary if enabled (v2.6.4)
                    settings = load_settings()
                    show_summary = settings.get('show_session_summary_on_exit', True)

                    if show_summary and session_tracker.has_activity():
                        from datetime import datetime
                        print()
                        print("=" * 60)
                        print(f"  {Fore.CYAN}SESSION COMPLETE{Style.RESET_ALL}")
                        print("=" * 60)

                        # Duration
                        hours, minutes, seconds = session_tracker.get_session_duration()
                        if hours > 0:
                            duration_str = f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
                        elif minutes > 0:
                            duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
                        else:
                            duration_str = f"{seconds} second{'s' if seconds != 1 else ''}"

                        print(f"  Duration: {duration_str}")
                        print()

                        # Summary stats
                        print(f"  Great session! You submitted {Fore.WHITE}{len(session_tracker.scores)}{Style.RESET_ALL} scores:")
                        if session_tracker.records_broken:
                            print(f"    • {Fore.RED}{len(session_tracker.records_broken)} new record{'s' if len(session_tracker.records_broken) != 1 else ''} 🏆{Style.RESET_ALL}")
                        if session_tracker.new_fcs:
                            print(f"    • {Fore.GREEN}{len(session_tracker.new_fcs)} new full combo{'s' if len(session_tracker.new_fcs) != 1 else ''} ⭐{Style.RESET_ALL}")
                        if session_tracker.personal_bests:
                            print(f"    • {len(session_tracker.personal_bests)} personal best{'s' if len(session_tracker.personal_bests) != 1 else ''}")

                        avg_acc = session_tracker.get_average_accuracy()
                        print(f"    • Average accuracy: {avg_acc:.1f}%")

                        # Top moment
                        if session_tracker.records_broken:
                            top_record = max(session_tracker.records_broken, key=lambda s: s.get('score', 0))
                            top_song = top_record.get('song_title', f"[{top_record['chart_hash'][:8]}]")
                            print()
                            print(f"  {Fore.YELLOW}Top moment:{Style.RESET_ALL} Broke the record on {top_song}!")
                        elif session_tracker.new_fcs:
                            top_fc = max(session_tracker.new_fcs, key=lambda s: s.get('score', 0))
                            top_song = top_fc.get('song_title', f"[{top_fc['chart_hash'][:8]}]")
                            print()
                            print(f"  {Fore.YELLOW}Top moment:{Style.RESET_ALL} First FC on {top_song}!")

                        print()
                        print("  See you next time! 👋")
                        print()
                        print("=" * 60)
                        print()

                        input("Press Enter to exit...")

                    print("\n[*] Shutting down...")
                    watcher.stop()
                    stop_tray_icon()
                    break

                else:
                    print(f"  Unknown command: {cmd}")
                    print("  Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n\n[*] Shutting down...")
                watcher.stop()
                stop_tray_icon()
                break

    except FileNotFoundError as e:
        print(f"\n[!] Error: {e}")
        print("Play some songs in Clone Hero to generate score data.")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print("\n[*] Stopped by user")
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")


if __name__ == '__main__':
    try:
        main()
    finally:
        # Always release lock on exit
        release_instance_lock()

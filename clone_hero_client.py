"""
Clone Hero High Score Client

Monitors your Clone Hero scores and submits them to the Discord scoreboard.
"""

VERSION = "2.6.2"

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

        # Offer Bridge integration setup for new users
        from client.bridge_integration import is_bridge_installed, run_bridge_setup
        import sys

        print_header("BRIDGE INTEGRATION SETUP", width=50)
        print("\nBridge Integration allows you to search for charts directly")
        print("in the Bridge desktop app by clicking links in Discord.")

        # Check for admin rights
        if not is_admin():
            print_warning("\nWARNING: Not running as Administrator!")
            print("         Bridge Integration requires Administrator rights to:")
            print("         - Register the chbridge:// protocol")
            print("         - Modify Windows shortcuts")
            print()
            print("To enable Bridge Integration:")
            print("  1. Close this tracker")
            print("  2. Right-click the tracker exe")
            print("  3. Select 'Run as administrator'")
            print("  4. Complete setup again")
            print()

        print("\nEnable Bridge Integration? (Y/n)")
        print("(You can change this later in Settings)")

        choice = input("> ").strip().lower()

        if choice in ['y', 'yes', '']:
            print_info("\nRunning Bridge integration setup...")

            # Get tracker exe path
            if getattr(sys, 'frozen', False):
                tracker_exe = sys.executable
            else:
                tracker_exe = str(Path(__file__).resolve())

            # Check if Bridge is installed
            is_installed, bridge_path = is_bridge_installed()

            if not is_installed:
                print_warning("\nBridge not found in common installation locations.")
                print("Please enter the full path to Bridge.exe:")
                print("(or press Enter to skip setup)")

                custom_path = input("> ").strip()

                if custom_path:
                    bridge_path = Path(custom_path)
                    if not bridge_path.exists():
                        print_error(f"Path does not exist: {custom_path}")
                        print_info("Skipping Bridge setup. You can enable it later in Settings.")
                    elif not bridge_path.name.lower() == 'bridge.exe':
                        print_error("File must be Bridge.exe")
                        print_info("Skipping Bridge setup. You can enable it later in Settings.")
                    else:
                        # Run setup with custom path
                        try:
                            success, message = run_bridge_setup(tracker_exe)
                            if success:
                                settings = load_settings()
                                if 'bridge_integration' not in settings:
                                    settings['bridge_integration'] = {}
                                settings['bridge_integration']['enabled'] = True
                                settings['bridge_integration']['bridge_path'] = str(bridge_path)
                                settings['bridge_integration']['protocol_registered'] = True
                                settings['bridge_integration']['prompted'] = True
                                save_settings(settings)
                                print_success(f"\n{message}")
                                print_success("Bridge Integration enabled!")
                            else:
                                print_error(f"\nSetup failed: {message}")
                                print_info("You can enable it later in Settings.")
                        except PermissionError:
                            print_error("\nSetup failed: Permission denied")
                            print_warning("Re-launch the tracker as Administrator to enable Bridge integration.")
                else:
                    print_info("Skipping Bridge setup. You can enable it later in Settings.")
            else:
                # Run setup with auto-detected path
                try:
                    success, message = run_bridge_setup(tracker_exe)
                    if success:
                        settings = load_settings()
                        if 'bridge_integration' not in settings:
                            settings['bridge_integration'] = {}
                        settings['bridge_integration']['enabled'] = True
                        settings['bridge_integration']['bridge_path'] = str(bridge_path)
                        settings['bridge_integration']['protocol_registered'] = True
                        settings['bridge_integration']['prompted'] = True
                        save_settings(settings)
                        print_success(f"\n{message}")
                        print_success("Bridge Integration enabled!")
                    else:
                        print_error(f"\nSetup failed: {message}")
                        print_info("You can enable it later in Settings.")
                except PermissionError:
                    print_error("\nSetup failed: Permission denied")
                    print_warning("Re-launch the tracker as Administrator to enable Bridge integration.")
        else:
            print_info("Bridge Integration skipped. You can enable it later in Settings.")

        # Always mark as prompted to prevent repeated asking
        settings = load_settings()
        if 'bridge_integration' not in settings:
            settings['bridge_integration'] = {}
        settings['bridge_integration']['prompted'] = True
        save_settings(settings)

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
        if settings.get('bridge_integration', {}).get('enabled'):
            print_success("  + Bridge Integration")
        else:
            print_plain("  - Bridge Integration (disabled)")
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
    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    settings_path = ch_dir / "settings.ini"

    song_folders = []

    if settings_path.exists():
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

    if not song_folders:
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
        nps = chart_data.calculate_note_density(instrument, difficulty)
        return {
            'total_notes': inst_diff_data.total_notes,
            'nps': nps
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
                days_held = 0  # TODO: Calculate from dates
                print(f"  {Fore.CYAN}Result{Style.RESET_ALL}     {result_text}")
                print(f"             Previous record: {prev_score:,} pts ({prev_holder})")
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

    def on_new_score(score):
        """
        Callback function that gets called when a new score is detected

        Sends the score to the Discord bot API.
        Score types: "raw" (chart hash only) or "rich" (has metadata from currentsong.txt or OCR)
        """
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

        # =====================================================
        # STEP 2: Attempt OCR for additional data (notes, streak)
        # =====================================================
        ocr_result = None

        if ocr_enabled:
            print_info("Attempting OCR capture of results screen...")
            _ocr_stats['attempts'] += 1
            _ocr_stats['last_attempt'] = time.time()
            ocr_result = capture_and_extract(delay_ms=500, save_debug=False)

            if ocr_result.success:
                _ocr_stats['successes'] += 1
                print_success("OCR extraction successful")

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
                else:
                    print_warning("Song not found in cache (may need to refresh songcache in Clone Hero)")
            except Exception as e:
                print_warning(f"Failed to check songcache.bin: {e}")

        # =====================================================
        # STEP 4: Parse chart file for accurate note count (v2.6.0)
        # =====================================================
        total_notes_in_chart = None
        nps = None

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
                    print_success(f"Chart parsed! Total notes: {total_notes_in_chart:,}, NPS: {nps:.1f}")
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
                is_fc = False

        except Exception as e:
            logger.warning(f"Chart parsing failed: {e}")
            print_warning(f"Chart parsing failed: {e}")
            is_fc = False

        # Calculate notes_hit from completion_percent if we have total notes
        if notes_hit is None and notes_total is not None and score.completion_percent > 0:
            notes_hit = int(notes_total * (score.completion_percent / 100.0))

        # Send score to bot API
        try:
            print()  # Newline for spacing
            print_info("Submitting to bot API...")

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

            response = requests.post(
                f"{get_bot_url()}/api/score",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()

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
            else:
                print_error(f"Error submitting score: {response.status_code}")
                print(f"    {response.text}")

        except requests.exceptions.ConnectionError:
            print_error("Could not connect to bot API")
            print("    Make sure the bot is running!")
        except Exception as e:
            print_error(f"Error sending score to API: {e}")

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

        print_plain(f"\n[0] Back to main menu")
        print("\n" + "=" * 50)

        choice = input("Select option (0-6): ").strip()

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
    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    settings_path = ch_dir / "settings.ini"

    song_folders = []

    if settings_path.exists():
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


def scancharts_command():
    """
    Scan all local charts and upload metadata to server (v2.6.0)

    This command parses ALL charts in your Clone Hero song folders and sends
    detailed metadata (total notes, NPS, chord count, etc.) to the server.
    This enables features like:
    - /hardest command (shows hardest songs by NPS)
    - Chart Intensity badges in announcements
    - Accurate note counts
    """
    print_header("SCAN CHARTS FOR METADATA")
    print()
    print("This will:")
    print("  1. Scan ALL charts in your Clone Hero songs folder(s)")
    print("  2. Parse note data for each instrument/difficulty")
    print("  3. Calculate note density (NPS)")
    print("  4. Upload metadata to server")
    print()
    print_warning("This may take several minutes for large libraries!")
    print()

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
    print()

    # Step 2: Scan all charts and parse metadata
    chart_metadata = []
    scanned = 0
    parsed = 0
    failed = 0

    for songs_path in song_folders:
        print(f"[*] Scanning: {songs_path}")
        for root, dirs, files in os.walk(songs_path):
            # Look for chart files
            chart_files = [f for f in files if f.lower() in ['notes.chart', 'notes.mid', 'notes.midi']]

            if not chart_files:
                continue

            scanned += 1

            # Show progress every 100 charts
            if scanned % 100 == 0:
                print(f"  Scanned {scanned} songs... ({parsed} parsed, {failed} failed)", end='\r')

            chart_path = Path(root) / chart_files[0]

            # Calculate MD5 hash
            try:
                with open(chart_path, 'rb') as f:
                    chart_hash = hashlib.md5(f.read()).hexdigest()

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
                        'song_name': song_name,
                        'artist': artist,
                        'charter': charter,
                        'genre': genre,
                        'chart_file_path': str(chart_path)
                    })

                parsed += 1

            except Exception as e:
                failed += 1
                logger.debug(f"Failed to parse {chart_path}: {e}")
                continue

    print(f"\n\n[*] Scan complete!")
    print(f"  • Charts scanned: {scanned}")
    print(f"  • Successfully parsed: {parsed}")
    print(f"  • Failed to parse: {failed}")
    print(f"  • Total metadata entries: {len(chart_metadata)}")
    print()

    if not chart_metadata:
        print_warning("No charts were successfully parsed!")
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

        # Check if Bridge integration setup is needed (upgrade detection)
        bridge_config = settings.get('bridge_integration', {})
        bridge_prompted = bridge_config.get('prompted', False)

        if not bridge_prompted:
            # This is an existing user who hasn't been prompted about Bridge yet
            from client.bridge_integration import is_protocol_registered

            if not is_protocol_registered():
                print("\n" + "=" * 50)
                print_header("NEW FEATURE: Bridge Integration", width=50)
                print("\nBridge Integration allows you to search for charts directly")
                print("in the Bridge desktop app by clicking links in Discord.")
                print("\nThis is a one-time setup that requires:")
                print("  - Bridge desktop app installed (optional)")
                print("  - Protocol registration (chbridge://)")
                print("  - Shortcut modifications")
                print("  - **Administrator rights**")

                # Check for admin rights
                if not is_admin():
                    print_warning("\nWARNING: Not running as Administrator!")
                    print("         Bridge Integration requires Administrator rights.")
                    print()
                    print("To enable Bridge Integration:")
                    print("  1. Close this tracker")
                    print("  2. Right-click the tracker exe")
                    print("  3. Select 'Run as administrator'")
                    print("  4. Answer 'Yes' when prompted")
                    print()

                print("\n" + "=" * 50)
                print("\nEnable Bridge Integration now? (Y/n)")
                print("(You can change this later in Settings)")

                choice = input("> ").strip().lower()

                if choice in ['y', 'yes', '']:
                    # Run setup
                    from client.bridge_integration import run_bridge_setup, is_bridge_installed
                    import sys

                    print_info("\nRunning Bridge integration setup...")

                    # Get tracker exe path
                    if getattr(sys, 'frozen', False):
                        tracker_exe = sys.executable
                    else:
                        tracker_exe = str(Path(__file__).resolve())

                    # Check if Bridge is installed
                    is_installed, bridge_path = is_bridge_installed()

                    if not is_installed:
                        print_warning("\nBridge not found in common installation locations.")
                        print("Please enter the full path to Bridge.exe:")
                        print("(or press Enter to skip setup)")

                        custom_path = input("> ").strip()

                        if custom_path:
                            bridge_path = Path(custom_path)
                            if not bridge_path.exists():
                                print_error(f"Path does not exist: {custom_path}")
                                print_info("Skipping Bridge setup. You can enable it later in Settings.")
                                # Mark as prompted to not ask again
                                if 'bridge_integration' not in settings:
                                    settings['bridge_integration'] = {}
                                settings['bridge_integration']['prompted'] = True
                                settings['bridge_integration']['enabled'] = False
                                save_settings(settings)
                            elif not bridge_path.name.lower() == 'bridge.exe':
                                print_error("File must be Bridge.exe")
                                print_info("Skipping Bridge setup. You can enable it later in Settings.")
                                if 'bridge_integration' not in settings:
                                    settings['bridge_integration'] = {}
                                settings['bridge_integration']['prompted'] = True
                                settings['bridge_integration']['enabled'] = False
                                save_settings(settings)
                            else:
                                # Run setup with custom path
                                try:
                                    success, message = run_bridge_setup(tracker_exe)
                                    if success:
                                        if 'bridge_integration' not in settings:
                                            settings['bridge_integration'] = {}
                                        settings['bridge_integration']['enabled'] = True
                                        settings['bridge_integration']['bridge_path'] = str(bridge_path)
                                        settings['bridge_integration']['protocol_registered'] = True
                                        settings['bridge_integration']['prompted'] = True
                                        save_settings(settings)
                                        print_success(f"\n{message}")
                                        print_success("Bridge Integration enabled!")
                                    else:
                                        print_error(f"\nSetup failed: {message}")
                                        print_info("You can retry from Settings menu later.")
                                        print_info("TIP: Run tracker as Administrator for Bridge integration.")
                                        settings['bridge_integration']['prompted'] = True
                                        save_settings(settings)
                                except PermissionError:
                                    print_error("\nSetup failed: Permission denied")
                                    print_info("Bridge Integration requires Administrator rights.")
                                    print("You can retry from Settings menu after relaunching as admin:")
                                    print("  1. Right-click CloneHeroScoreTracker.exe")
                                    print("  2. Select 'Run as administrator'")
                                    print("  3. Open Settings > Bridge Integration")
                                    settings['bridge_integration']['prompted'] = True
                                    save_settings(settings)
                        else:
                            print_info("Skipping Bridge setup. You can enable it later in Settings.")
                            if 'bridge_integration' not in settings:
                                settings['bridge_integration'] = {}
                            settings['bridge_integration']['prompted'] = True
                            settings['bridge_integration']['enabled'] = False
                            save_settings(settings)
                    else:
                        # Run setup with auto-detected path
                        try:
                            success, message = run_bridge_setup(tracker_exe)
                            if success:
                                if 'bridge_integration' not in settings:
                                    settings['bridge_integration'] = {}
                                settings['bridge_integration']['enabled'] = True
                                settings['bridge_integration']['bridge_path'] = str(bridge_path)
                                settings['bridge_integration']['protocol_registered'] = True
                                settings['bridge_integration']['prompted'] = True
                                save_settings(settings)
                                print_success(f"\n{message}")
                                print_success("Bridge Integration enabled!")
                            else:
                                print_error(f"\nSetup failed: {message}")
                                print_info("You can retry from Settings menu later.")
                                print_info("TIP: Run tracker as Administrator for Bridge integration.")
                                settings['bridge_integration']['prompted'] = True
                                save_settings(settings)
                        except PermissionError:
                            print_error("\nSetup failed: Permission denied")
                            print_info("Bridge Integration requires Administrator rights.")
                            print("You can retry from Settings menu after relaunching as admin:")
                            print("  1. Right-click CloneHeroScoreTracker.exe")
                            print("  2. Select 'Run as administrator'")
                            print("  3. Open Settings > Bridge Integration")
                            settings['bridge_integration']['prompted'] = True
                            save_settings(settings)
                else:
                    print_info("Bridge Integration skipped. You can enable it later in Settings.")
                    if 'bridge_integration' not in settings:
                        settings['bridge_integration'] = {}
                    settings['bridge_integration']['prompted'] = True
                    settings['bridge_integration']['enabled'] = False
                    save_settings(settings)

                print()

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

    # Load song cache for metadata
    song_cache = {}
    songcache_path = ch_dir / 'songcache.bin'
    if songcache_path.exists():
        try:
            parser = SongCacheParser(str(songcache_path))
            song_cache = parser.parse()
            print_success(f"Song cache loaded ({len(song_cache)} songs)")
        except Exception as e:
            print_warning("Could not load song cache - songs will show as hashes")
            log_exception(logger, "Failed to load song cache", e)

    # Check OCR availability
    ocr_enabled = settings.get('ocr_enabled', False)
    if ocr_enabled:
        ocr_ok, ocr_msg = check_ocr_available()
        if ocr_ok:
            print_success(f"OCR enabled: {ocr_msg}")
        else:
            print_warning(f"OCR disabled: {ocr_msg}")
            ocr_enabled = False

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
            watcher.initialize_state()
        elif watcher.needs_state_migration():
            # Old format state file - re-initialize silently without submitting
            print_info("Migrating state file...")
            watcher.initialize_state(silent=True)
        else:
            # Scan for any scores made while tracker was offline
            watcher.catch_up_scan()

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

                elif cmd == "help" or cmd == "?":
                    print_header("AVAILABLE COMMANDS", width=50)

                    print(f"{Fore.CYAN}Monitoring:{Style.RESET_ALL}")
                    print_plain("  status         Check connection and score tracking status")
                    print_plain("  stats          Quick stats overview")
                    print_plain("  resync         Scan for scores made while offline")
                    print_plain("  resolvehashes  Fix mystery hashes by scanning songs")
                    print_plain("  scancharts     Upload chart metadata (notes, NPS) to server")
                    print_plain("  reset          Clear state and re-submit ALL scores")

                    print(f"\n{Fore.CYAN}Configuration:{Style.RESET_ALL}")
                    print_plain("  settings       Configure bot URL, paths, and options")
                    print_plain("  backup         Backup current configuration")
                    print_plain("  restore        Restore configuration from backup")
                    print_plain("  update         Check for and download updates")

                    print(f"\n{Fore.CYAN}Utilities:{Style.RESET_ALL}")
                    print_plain("  refreshcache   Reload song metadata from Clone Hero")
                    print_plain("  bridgestatus   Check Bridge integration status")
                    print_plain("  exportlogs     Export debug logs to zip file")
                    print_plain("  unpair         Disconnect from Discord account")
                    if tray_enabled:
                        print_plain("  minimize       Minimize to system tray")
                    print_plain("  debug          Enter debug mode (password required)")

                    print(f"\n{Fore.CYAN}General:{Style.RESET_ALL}")
                    print_plain("  help           Show this help message")
                    print_plain("  quit           Exit the tracker")

                    print("\n" + "=" * 50)
                    print("Type any command at the > prompt")
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

                elif cmd == "scancharts":
                    scancharts_command()

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

                elif cmd == "bridgestatus":
                    print()
                    bridge_status_command()
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

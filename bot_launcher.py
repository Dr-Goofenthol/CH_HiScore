"""
Clone Hero High Score Bot Launcher

Standalone executable for the Discord bot with first-time setup.
"""

VERSION = "2.4.14"

# GitHub repository for auto-updates
GITHUB_REPO = "Dr-Goofenthol/CH_HiScore"

import os
import sys
import json
import zipfile
import tempfile
import shutil
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from shared.console import print_success, print_info, print_warning, print_error, print_header
from shared.logger import get_bot_logger, log_exception

# Initialize colorama for Windows
try:
    import colorama
    colorama.init()
except ImportError:
    pass

# Initialize logger
logger = get_bot_logger()


# ============================================================================
# CONFIG PERSISTENCE - Store in %APPDATA% for persistence across updates
# ============================================================================

def get_config_dir() -> Path:
    """Get persistent config directory in AppData"""
    if sys.platform == 'win32':
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        config_dir = appdata / 'CloneHeroScoreBot'
    else:
        config_dir = Path.home() / '.config' / 'CloneHeroScoreBot'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get persistent config file path"""
    return get_config_dir() / 'bot_config.json'


def migrate_old_config():
    """Check for config next to exe and migrate to AppData"""
    # Check for old config location (next to exe)
    if getattr(sys, 'frozen', False):
        old_config = Path(sys.executable).parent / 'bot_config.json'
    else:
        old_config = Path(__file__).parent / 'bot_config.json'

    new_config = get_config_path()

    if old_config.exists() and not new_config.exists():
        try:
            shutil.copy(old_config, new_config)
            print_success(f"Migrated config to: {new_config}")
            # Optionally remove old config after successful migration
            # old_config.unlink()
        except Exception as e:
            print_warning(f"Could not migrate config: {e}")
    elif old_config.exists() and new_config.exists():
        print_info("Config already exists in AppData, using that location")


# Config file location (persistent in AppData)
CONFIG_FILE = get_config_path()


# ============================================================================
# AUTO-UPDATE FUNCTIONS
# ============================================================================

def check_for_updates() -> dict:
    """
    Check GitHub releases for a newer version.

    Returns:
        dict with update info if available, None if up to date or check failed
    """
    if not HAS_REQUESTS:
        return None

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
            # Find the bot asset (look for "Bot" in name, prefer .exe over .zip)
            download_url = None
            filename = None
            for asset in release.get("assets", []):
                if "Bot" in asset["name"]:
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

    except Exception:
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
            print("[*] Extracting...")

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
        print(f"\n[!] Download failed: {e}")
        return None


def prompt_for_update(update_info: dict) -> bool:
    """
    Show update prompt and ask user if they want to update.

    Returns:
        True if user wants to update, False otherwise
    """
    print("\n" + "=" * 50)
    print("UPDATE AVAILABLE")
    print("=" * 50)
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
    print(f"    1. Close this program (Ctrl+C or close window)")
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
    if not HAS_REQUESTS:
        if not silent_if_current:
            print("[!] Update check unavailable (requests module not found)")
        return False

    if not silent_if_current:
        print("[*] Checking for updates...")

    update_info = check_for_updates()

    if update_info:
        if prompt_for_update(update_info):
            new_exe = download_update(update_info)
            if new_exe:
                show_update_complete_message(new_exe)
                return True
            else:
                print("[!] Update download failed. Continuing with current version.")
    elif not silent_if_current:
        print("[+] You're running the latest version!")

    return False


def load_config():
    """Load bot configuration from JSON file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return None


def save_config(config):
    """Save bot configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def first_time_setup():
    """Run first-time setup wizard"""
    print("\n" + "=" * 60)
    print("   CLONE HERO HIGH SCORE BOT - FIRST TIME SETUP")
    print("=" * 60)
    print("""
Welcome! This wizard will help you configure the bot.

You'll need:
1. A Discord Bot Token (from Discord Developer Portal)
2. Your Discord Application ID
3. Your Discord Server ID (Guild ID) - OPTIONAL but recommended
4. The Channel ID where scores should be announced
5. A debug password for client testing features

If you don't have these yet:
1. Go to https://discord.com/developers/applications
2. Create a new application (or use existing)
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Copy the Application ID from "General Information"
6. In Discord, enable Developer Mode (Settings > Advanced > Developer Mode)
7. Right-click your server icon and "Copy Server ID"
8. Right-click your announcement channel and "Copy Channel ID"
""")
    print("=" * 60)
    input("\nPress Enter to continue...")

    config = {}

    # Discord Token
    print("\n" + "-" * 50)
    print("STEP 1: Discord Bot Token")
    print("-" * 50)
    print("This is the secret token from your bot's settings.")
    print("Keep this private - anyone with this token can control your bot!")
    while True:
        token = input("\nEnter your Discord Bot Token: ").strip()
        if token and len(token) > 50:
            config['DISCORD_TOKEN'] = token
            break
        print("[!] Token seems too short. Please enter the full token.")

    # Application ID
    print("\n" + "-" * 50)
    print("STEP 2: Discord Application ID")
    print("-" * 50)
    print("This is the numeric ID from your app's General Information page.")
    while True:
        app_id = input("\nEnter your Discord Application ID: ").strip()
        if app_id and app_id.isdigit():
            config['DISCORD_APP_ID'] = app_id
            break
        print("[!] Application ID should be a number.")

    # Guild ID (Server ID)
    print("\n" + "-" * 50)
    print("STEP 3: Discord Server ID (Guild ID) - OPTIONAL")
    print("-" * 50)
    print("This is your Discord server's ID (right-click server icon > Copy Server ID).")
    print("")
    print("WHY THIS MATTERS:")
    print("  - WITH Guild ID: New commands appear INSTANTLY after bot restart")
    print("  - WITHOUT Guild ID: New commands take up to 1 HOUR to appear")
    print("")
    print("Recommended: Enter your Guild ID for faster command updates!")
    guild_id = input("\nEnter Guild ID (or press Enter to skip): ").strip()
    if guild_id:
        if guild_id.isdigit():
            config['DISCORD_GUILD_ID'] = guild_id
            print("[+] Guild ID set - commands will sync instantly!")
        else:
            print("[!] Invalid Guild ID (should be a number). Skipping...")
    else:
        print("[*] Skipped - commands will sync globally (slower)")

    # Channel ID
    print("\n" + "-" * 50)
    print("STEP 4: Announcement Channel ID")
    print("-" * 50)
    print("This is the channel where high score announcements will be posted.")
    print("Right-click the channel in Discord and select 'Copy Channel ID'.")
    while True:
        channel_id = input("\nEnter the Channel ID: ").strip()
        if channel_id and channel_id.isdigit():
            config['DISCORD_CHANNEL_ID'] = channel_id
            break
        print("[!] Channel ID should be a number.")

    # Debug Password
    print("\n" + "-" * 50)
    print("STEP 5: Client Debug Password")
    print("-" * 50)
    print("This password is required when clients want to enter debug mode.")
    print("Debug mode allows testing features like sending test scores.")
    print("")
    print("Security tip: Use a strong password if your bot is public!")
    debug_password = input("\nEnter debug password [admin123]: ").strip()
    if debug_password:
        config['DEBUG_PASSWORD'] = debug_password
        print("[+] Custom debug password set")
    else:
        config['DEBUG_PASSWORD'] = 'admin123'
        print("[*] Using default password: admin123")

    # API Port
    print("\n" + "-" * 50)
    print("STEP 6: API Port")
    print("-" * 50)
    print("The port that clients will connect to (default: 8080).")
    print("Make sure to forward this port on your router if hosting externally.")
    port_input = input("\nEnter API Port [8080]: ").strip()
    config['API_PORT'] = int(port_input) if port_input.isdigit() else 8080

    # External URL (optional)
    print("\n" + "-" * 50)
    print("STEP 7: External URL (Optional)")
    print("-" * 50)
    print("If hosting on a home server with a domain, enter the URL clients should use.")
    print("Example: http://myhome.duckdns.org:8080")
    print("Leave blank if only using on local network (http://localhost:8080)")
    external_url = input("\nEnter External URL (or press Enter to skip): ").strip()
    if external_url:
        config['EXTERNAL_URL'] = external_url

    # Save config
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"  Discord App ID: {config['DISCORD_APP_ID']}")
    print(f"  Discord Token: {'*' * 20}...")
    if config.get('DISCORD_GUILD_ID'):
        print(f"  Guild ID: {config['DISCORD_GUILD_ID']} (fast command sync)")
    else:
        print(f"  Guild ID: (not set - global sync, slower)")
    print(f"  Channel ID: {config['DISCORD_CHANNEL_ID']}")
    print(f"  Debug Password: {'*' * len(config.get('DEBUG_PASSWORD', 'admin123'))}")
    print(f"  API Port: {config['API_PORT']}")
    if config.get('EXTERNAL_URL'):
        print(f"  External URL: {config['EXTERNAL_URL']}")
    print("=" * 60)

    confirm = input("\nSave this configuration? (yes/no): ").strip().lower()
    if confirm == 'yes' or confirm == 'y':
        save_config(config)
        print(f"\n[+] Configuration saved to: {CONFIG_FILE}")
        return config
    else:
        print("\n[!] Configuration not saved. Please run setup again.")
        return None


def setup_environment(config):
    """Set environment variables from config for the bot modules"""
    os.environ['DISCORD_TOKEN'] = config.get('DISCORD_TOKEN', '')
    os.environ['DISCORD_APP_ID'] = config.get('DISCORD_APP_ID', '')
    os.environ['DISCORD_CHANNEL_ID'] = config.get('DISCORD_CHANNEL_ID', '')
    os.environ['API_PORT'] = str(config.get('API_PORT', 8080))
    os.environ['API_HOST'] = '0.0.0.0'  # Listen on all interfaces

    # Optional: Guild ID for fast command sync
    if config.get('DISCORD_GUILD_ID'):
        os.environ['DISCORD_GUILD_ID'] = config.get('DISCORD_GUILD_ID')

    # Debug password for client authorization
    os.environ['DEBUG_PASSWORD'] = config.get('DEBUG_PASSWORD', 'admin123')


def main():
    print()
    print("=" * 60)
    print(f"   Clone Hero High Score Bot v{VERSION}")
    print("=" * 60)

    # Check for updates on startup
    print("\n[*] Checking for updates...")
    check_and_prompt_update(silent_if_current=True)

    # Migrate old config if needed (from exe directory to AppData)
    migrate_old_config()

    # Check for existing config
    config = load_config()

    if not config:
        # First time setup
        config = first_time_setup()
        if not config:
            print("[!] Setup cancelled. Exiting.")
            input("\nPress Enter to exit...")
            return

    # Show current config
    print("\n[+] Configuration loaded")
    print(f"    App ID: {config.get('DISCORD_APP_ID')}")
    if config.get('DISCORD_GUILD_ID'):
        print(f"    Guild ID: {config.get('DISCORD_GUILD_ID')} (fast sync)")
    print(f"    Channel: {config.get('DISCORD_CHANNEL_ID')}")
    print(f"    API Port: {config.get('API_PORT', 8080)}")
    if config.get('EXTERNAL_URL'):
        print(f"    External URL: {config.get('EXTERNAL_URL')}")

    # Set environment variables
    setup_environment(config)

    # Run database migrations before starting the bot
    print("\n[*] Running database migrations...")
    try:
        from bot.migrations import run_migrations
        db_path = get_config_dir() / 'scores.db'
        run_migrations(db_path)
    except Exception as e:
        print_error(f"Migration failed: {e}")
        print("[!] Bot may not function correctly")
        import traceback
        traceback.print_exc()

    # Start the bot
    print("\n[*] Starting Discord bot...")
    print("[*] Press Ctrl+C to stop\n")

    try:
        # Import and run the bot
        from bot.bot import bot
        bot.run(config['DISCORD_TOKEN'])
    except KeyboardInterrupt:
        print("\n[*] Bot stopped by user")
    except Exception as e:
        print(f"\n[!] Error starting bot: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")


if __name__ == '__main__':
    main()

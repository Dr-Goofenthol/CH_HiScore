"""
Clone Hero High Score Bot Launcher

Standalone executable for the Discord bot with first-time setup.
"""

VERSION = "2.6.2"

# GitHub repository for auto-updates
GITHUB_REPO = "Dr-Goofenthol/CH_HiScore"

import os
import sys
import json
import zipfile
import tempfile
import shutil
import asyncio
import signal
import threading
from pathlib import Path

# Suppress Windows ProactorEventLoop connection errors (Discord.py known issue)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
            except Exception:
                pass  # Cleanup failures are non-critical
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
    """Load bot configuration using ConfigManager"""
    from bot.config_manager import ConfigManager

    config_manager = ConfigManager()
    try:
        config_manager.load()
        return config_manager.config
    except Exception as e:
        print_warning(f"[Config] Error loading config: {e}")
        return None


def save_config(config):
    """Save bot configuration using ConfigManager"""
    from bot.config_manager import ConfigManager

    config_manager = ConfigManager()
    config_manager.config = config
    config_manager.save()


def first_time_setup():
    """Run first-time setup wizard using ConfigManager"""
    from bot.config_manager import ConfigManager

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

    # Create config manager and start with defaults
    config_manager = ConfigManager()
    config = config_manager._create_default_config()

    # ==================== DISCORD SETTINGS ====================

    # Discord Token
    print("\n" + "-" * 60)
    print("STEP 1: Discord Bot Token")
    print("-" * 60)
    print("This is the secret token from your bot's settings.")
    print("Keep this private - anyone with this token can control your bot!")
    while True:
        token = input("\nEnter your Discord Bot Token: ").strip()
        if token and len(token) > 50:
            config['discord']['bot_token'] = token
            break
        print("[!] Token seems too short. Please enter the full token.")

    # Application ID
    print("\n" + "-" * 60)
    print("STEP 2: Discord Application ID")
    print("-" * 60)
    print("This is the numeric ID from your app's General Information page.")
    while True:
        app_id = input("\nEnter your Discord Application ID: ").strip()
        if app_id and app_id.isdigit():
            config['discord']['app_id'] = app_id
            break
        print("[!] Application ID should be a number.")

    # Guild ID (Server ID)
    print("\n" + "-" * 60)
    print("STEP 3: Discord Server ID (Guild ID) - OPTIONAL")
    print("-" * 60)
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
            config['discord']['guild_id'] = guild_id
            print("[+] Guild ID set - commands will sync instantly!")
        else:
            print("[!] Invalid Guild ID (should be a number). Skipping...")
    else:
        print("[*] Skipped - commands will sync globally (slower)")

    # Channel ID
    print("\n" + "-" * 60)
    print("STEP 4: Announcement Channel ID")
    print("-" * 60)
    print("This is the channel where high score announcements will be posted.")
    print("Right-click the channel in Discord and select 'Copy Channel ID'.")
    while True:
        channel_id = input("\nEnter the Channel ID: ").strip()
        if channel_id and channel_id.isdigit():
            config['discord']['announcement_channel_id'] = channel_id
            break
        print("[!] Channel ID should be a number.")

    # ==================== API SETTINGS ====================

    # Debug Password
    print("\n" + "-" * 60)
    print("STEP 5: Client Debug Password")
    print("-" * 60)
    print("This password is required when clients want to enter debug mode.")
    print("Debug mode allows testing features like sending test scores.")
    print("")
    print("SECURITY WARNING: Change this if your bot is accessible outside")
    print("your local network! The default 'admin123' is NOT secure.")
    debug_password = input("\nEnter debug password [admin123]: ").strip()
    if debug_password:
        config['api']['debug_password'] = debug_password
        print("[+] Custom debug password set")
    else:
        config['api']['debug_password'] = 'admin123'
        print("[!] WARNING: Using default password 'admin123'")

    # API Port
    print("\n" + "-" * 60)
    print("STEP 6: API Port")
    print("-" * 60)
    print("The port that clients will connect to (default: 8080).")
    print("Make sure to forward this port on your router if hosting externally.")
    port_input = input("\nEnter API Port [8080]: ").strip()
    config['api']['port'] = int(port_input) if port_input.isdigit() else 8080

    # ==================== DISPLAY SETTINGS ====================

    print("\n" + "-" * 60)
    print("STEP 7: Display Settings")
    print("-" * 60)
    print("Configure how timestamps and dates appear in Discord embeds.")
    print("")

    # Timezone
    print("Timezone options:")
    print("  - UTC (default)")
    print("  - US/Eastern")
    print("  - US/Central")
    print("  - US/Mountain")
    print("  - US/Pacific")
    print("  - Europe/London")
    print("  - Or any other IANA timezone (e.g., America/New_York)")
    timezone = input("\nEnter timezone [UTC]: ").strip()
    if timezone:
        config['display']['timezone'] = timezone
        print(f"[+] Timezone set to: {timezone}")
    else:
        print("[*] Using default timezone: UTC")

    # Time format
    print("\nTime format:")
    print("  [1] 12-hour (e.g., 2:30 PM) - default")
    print("  [2] 24-hour (e.g., 14:30)")
    time_choice = input("Choose time format [1]: ").strip()
    if time_choice == '2':
        config['display']['time_format'] = '24-hour'
        print("[+] Using 24-hour time format")
    else:
        config['display']['time_format'] = '12-hour'
        print("[*] Using 12-hour time format")

    # ==================== ANNOUNCEMENT SETTINGS ====================

    print("\n" + "-" * 60)
    print("STEP 8: Announcement Preferences")
    print("-" * 60)
    print("Choose which types of scores to announce in Discord.")
    print("")

    # Record breaks
    print("[Record Breaks] When someone beats an existing high score:")
    record_enabled = input("  Enable record break announcements? [yes]: ").strip().lower()
    if record_enabled in ('n', 'no'):
        config['announcements']['record_breaks']['enabled'] = False
        print("  [-] Record break announcements disabled")
    else:
        config['announcements']['record_breaks']['enabled'] = True
        print("  [+] Record break announcements enabled")

        # Ping previous holder
        ping_holder = input("  Ping (@mention) the previous record holder? [yes]: ").strip().lower()
        if ping_holder in ('n', 'no'):
            config['announcements']['record_breaks']['ping_previous_holder'] = False
            print("  [-] Will not ping previous holders")
        else:
            print("  [+] Will ping previous holders")

    # First-time scores
    print("\n[First-Time Scores] When someone plays a chart for the first time:")
    first_enabled = input("  Enable first-time score announcements? [yes]: ").strip().lower()
    if first_enabled in ('n', 'no'):
        config['announcements']['first_time_scores']['enabled'] = False
        print("  [-] First-time score announcements disabled")
    else:
        config['announcements']['first_time_scores']['enabled'] = True
        print("  [+] First-time score announcements enabled")

    # Personal bests
    print("\n[Personal Bests] When someone improves their own score (not server record):")
    print("  Note: This can be noisy if enabled for small improvements.")
    pb_enabled = input("  Enable personal best announcements? [no]: ").strip().lower()
    if pb_enabled in ('y', 'yes'):
        config['announcements']['personal_bests']['enabled'] = True
        print("  [+] Personal best announcements enabled")

        # Thresholds
        print("\n  To reduce spam, only announce improvements above a threshold:")
        percent_str = input("    Minimum improvement percent [5.0]: ").strip()
        points_str = input("    Minimum improvement points [10000]: ").strip()

        if percent_str:
            try:
                config['announcements']['personal_bests']['min_improvement_percent'] = float(percent_str)
            except ValueError:
                print("    [!] Invalid number, using default 5.0%")

        if points_str:
            try:
                config['announcements']['personal_bests']['min_improvement_points'] = int(points_str)
            except ValueError:
                print("    [!] Invalid number, using default 10000")
    else:
        print("  [*] Personal best announcements disabled (recommended)")

    # ==================== SUMMARY ====================

    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print("\nDiscord Settings:")
    print(f"  App ID: {config['discord']['app_id']}")
    print(f"  Bot Token: {'*' * 20}... (hidden)")
    if config['discord']['guild_id']:
        print(f"  Guild ID: {config['discord']['guild_id']} (fast command sync)")
    else:
        print(f"  Guild ID: (not set - global sync, slower)")
    print(f"  Channel ID: {config['discord']['announcement_channel_id']}")

    print("\nAPI Settings:")
    print(f"  Port: {config['api']['port']}")
    print(f"  Debug Password: {'*' * len(config['api']['debug_password'])} (hidden)")

    print("\nDisplay Settings:")
    print(f"  Timezone: {config['display']['timezone']}")
    print(f"  Time Format: {config['display']['time_format']}")

    print("\nAnnouncements:")
    print(f"  Record Breaks: {'Enabled' if config['announcements']['record_breaks']['enabled'] else 'Disabled'}")
    if config['announcements']['record_breaks']['enabled']:
        ping_status = "Yes" if config['announcements']['record_breaks']['ping_previous_holder'] else "No"
        print(f"    Ping previous holder: {ping_status}")
    print(f"  First-Time Scores: {'Enabled' if config['announcements']['first_time_scores']['enabled'] else 'Disabled'}")
    print(f"  Personal Bests: {'Enabled' if config['announcements']['personal_bests']['enabled'] else 'Disabled'}")
    if config['announcements']['personal_bests']['enabled']:
        print(f"    Min improvement: {config['announcements']['personal_bests']['min_improvement_percent']}% or {config['announcements']['personal_bests']['min_improvement_points']:,} points")

    print("=" * 60)
    print("\nNote: You can change these settings later using the Settings Menu")
    print("=" * 60)

    confirm = input("\nSave this configuration? (yes/no): ").strip().lower()
    if confirm in ('yes', 'y'):
        # Save using ConfigManager
        config_manager.config = config
        config_manager.save()
        print(f"\n[+] Configuration saved to: {config_manager.config_path}")
        return config
    else:
        print("\n[!] Configuration not saved. Please run setup again.")
        return None


def setup_environment(config):
    """Set environment variables from config for the bot modules"""
    # Handle both old flat format and new nested format for backward compatibility
    discord = config.get('discord', {})
    api = config.get('api', {})

    # Discord settings - try new format first, fall back to old format
    os.environ['DISCORD_TOKEN'] = str(discord.get('bot_token', config.get('DISCORD_TOKEN', '')))
    os.environ['DISCORD_APP_ID'] = str(discord.get('app_id', config.get('DISCORD_APP_ID', '')))
    os.environ['DISCORD_CHANNEL_ID'] = str(discord.get('announcement_channel_id', config.get('DISCORD_CHANNEL_ID', '')))

    # API settings
    os.environ['API_PORT'] = str(api.get('port', config.get('API_PORT', 8080)))
    os.environ['API_HOST'] = '0.0.0.0'  # Listen on all interfaces

    # Pass bot version to bot module
    os.environ['BOT_VERSION'] = VERSION

    # Guild ID for fast command sync - CRITICAL: must be set for slash commands to work quickly
    guild_id = discord.get('guild_id', config.get('DISCORD_GUILD_ID', ''))
    if guild_id:
        os.environ['DISCORD_GUILD_ID'] = str(guild_id)
    else:
        # Clear the env var if not set to avoid using stale value
        os.environ.pop('DISCORD_GUILD_ID', None)

    # Debug password for client authorization
    os.environ['DEBUG_PASSWORD'] = str(api.get('debug_password', config.get('DEBUG_PASSWORD', 'admin123')))


def send_manual_update_notification(config):
    """Manually send update notification to Discord"""
    print("\n" + "=" * 60)
    print("  Manual Update Notification")
    print("=" * 60)
    print()
    print(f"Current bot version: v{VERSION}")
    print()
    print("This will send an update notification to your Discord channel.")
    print()

    # Ask for confirmation
    choice = input("Send update notification? (yes/no): ").strip().lower()
    if choice != 'yes':
        print_info("Cancelled.")
        return

    # Ask if they want to force re-announcement
    force = input("\nForce announcement (bypass version check)? (yes/no): ").strip().lower()
    force_announce = (force == 'yes')

    print()
    print("[*] Connecting to Discord...")

    # Import Discord bot module
    import discord
    from bot.config import Config
    from bot.database import Database

    # Set up environment
    setup_environment(config)

    async def send_notification():
        """Async function to send notification"""
        try:
            # Create a simple bot client
            intents = discord.Intents.default()
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready():
                try:
                    print_success(f"Connected as {client.user}")

                    # Get announcement channel
                    channel_id = Config.DISCORD_CHANNEL_ID
                    if not channel_id:
                        print_error("No announcement channel configured!")
                        await client.close()
                        return

                    channel = client.get_channel(int(channel_id))
                    if not channel:
                        print_error(f"Could not find channel with ID {channel_id}")
                        await client.close()
                        return

                    # Check if already announced (unless forcing)
                    if not force_announce:
                        db = Database()
                        db.connect()
                        last_announced = db.get_metadata('last_announced_version')
                        if last_announced == VERSION:
                            print_warning(f"Version {VERSION} already announced.")
                            choice = input("Send anyway? (yes/no): ").strip().lower()
                            if choice != 'yes':
                                print_info("Cancelled.")
                                await client.close()
                                return
                        db.close()

                    # Fetch release info from GitHub
                    from bot.bot import fetch_github_release, extract_update_highlights
                    release_info = fetch_github_release(VERSION)
                    if not release_info:
                        print_warning(f"Could not fetch release info for v{VERSION} - using basic announcement")
                        release_info = {
                            'version': VERSION,
                            'release_url': f'https://github.com/Dr-Goofenthol/CH_HiScore/releases/tag/v{VERSION}',
                            'release_notes': ''
                        }

                    # Create announcement embed
                    embed = discord.Embed(
                        title="🔄 Server Updated!",
                        description=f"The score tracker server has been updated to **v{VERSION}**\n\nPlayers should update their clients to match!",
                        color=discord.Color.green()
                    )

                    # Extract highlights
                    highlights = ""
                    if release_info.get("release_notes"):
                        highlights = extract_update_highlights(release_info["release_notes"])

                    if highlights:
                        embed.add_field(
                            name="✨ What's New",
                            value=highlights,
                            inline=False
                        )

                    # Update instructions
                    embed.add_field(
                        name="📥 How to Update Your Client",
                        value=(
                            "**Option 1:** Type `update` in your tracker's terminal\n"
                            "**Option 2:** Right-click the system tray icon → Check for Updates\n"
                            "**Option 3:** [Download manually]({})".format(release_info['release_url'])
                        ),
                        inline=False
                    )

                    embed.set_footer(text=f"Server version: v{VERSION} • Keep your client up to date!")

                    # Send announcement
                    await channel.send(embed=embed)
                    print_success(f"Update notification sent to #{channel.name}")

                    # Mark as announced
                    db = Database()
                    db.connect()
                    db.set_metadata('last_announced_version', VERSION)
                    db.close()

                except Exception as e:
                    print_error(f"Error sending notification: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    await client.close()

            # Connect and send
            await client.start(Config.DISCORD_TOKEN)

        except Exception as e:
            print_error(f"Connection error: {e}")
            import traceback
            traceback.print_exc()

    # Run the async function
    try:
        asyncio.run(send_notification())
    except KeyboardInterrupt:
        print_info("\nCancelled by user")


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
        print(f"                            DISCORD BOT v{VERSION}")
        print("                        Track • Announce • Infuriate")
        print()
        print("=" * 80)
        print()
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback to simple ASCII if Unicode fails
        print()
        print("=" * 80)
        print(f"         CLONE HERO HIGH SCORE BOT v{VERSION}")
        print("                 Track • Announce • Infuriate")
        print("=" * 80)
        print()


def export_logs_command():
    """Export bot logs to a zip file"""
    try:
        import zipfile
        from datetime import datetime

        log_dir = get_config_dir()
        log_file = log_dir / 'bot.log'

        if not log_file.exists():
            print_warning("No log file found")
            return

        # Create zip file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"bot_logs_{timestamp}.zip"
        zip_path = log_dir / zip_name

        print_info(f"Creating log archive: {zip_name}...")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add main log
            zf.write(log_file, log_file.name)

            # Add any backup logs (from rotation)
            for i in range(1, 6):
                backup_log = log_dir / f'bot.log.{i}'
                if backup_log.exists():
                    zf.write(backup_log, backup_log.name)

        print_success(f"Logs exported to: {zip_path}")
        print_info(f"File size: {zip_path.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        print_error(f"Export failed: {e}")


def backup_database_command():
    """Manually create database backup"""
    try:
        from bot.database import Database

        db_path = get_config_dir() / 'scores.db'
        if not db_path.exists():
            print_error("Database not found")
            return

        print_info("Creating database backup...")
        db = Database(str(db_path))
        success = db.create_backup(keep_count=7)

        if success:
            print_success("Database backup created successfully")
            # Show backup info
            backup_dir = db_path.parent / 'backups'
            if backup_dir.exists():
                backups = list(backup_dir.glob('scores_*.db'))
                if backups:
                    print_info(f"Total backups: {len(backups)}")
                    latest = max(backups, key=lambda p: p.stat().st_mtime)
                    print_info(f"Latest: {latest.name} ({latest.stat().st_size / 1024:.1f} KB)")
        else:
            print_error("Backup failed")

    except Exception as e:
        print_error(f"Backup failed: {e}")


def show_stats_command():
    """Show quick stats overview"""
    try:
        from bot.database import Database

        db_path = get_config_dir() / 'scores.db'
        if not db_path.exists():
            print_error("Database not found")
            return

        print_header("BOT STATISTICS", width=60)

        db = Database(str(db_path))
        db.connect()

        # Get stats
        cursor = db.conn.cursor()

        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Total scores
        cursor.execute("SELECT COUNT(*) FROM scores")
        total_scores = cursor.fetchone()[0]

        # Total songs
        cursor.execute("SELECT COUNT(*) FROM songs WHERE title IS NOT NULL")
        total_songs = cursor.fetchone()[0]

        # Total record breaks
        cursor.execute("SELECT COUNT(*) FROM record_breaks")
        total_records = cursor.fetchone()[0]

        # Most recent score
        cursor.execute("SELECT submitted_at FROM scores ORDER BY submitted_at DESC LIMIT 1")
        recent_result = cursor.fetchone()

        db.close()

        print_info(f"  Total Users: {total_users}")
        print_info(f"  Total Scores: {total_scores:,}")
        print_info(f"  Total Songs: {total_songs:,}")
        print_info(f"  Record Breaks: {total_records:,}")

        if recent_result:
            from datetime import datetime
            recent_time = datetime.fromisoformat(recent_result[0])
            print_info(f"  Last Score: {recent_time.strftime('%Y-%m-%d %H:%M:%S')}")

        print()

    except Exception as e:
        print_error(f"Failed to get stats: {e}")


def verify_config_command():
    """Verify config has all required fields and offer to apply missing ones"""
    try:
        from bot.config_manager import ConfigManager

        print_header("CONFIG VERIFICATION", width=70)
        print()
        print_info("Checking configuration for missing or incomplete fields...")
        print()

        # Load config and verify
        config_manager = ConfigManager()
        config_manager.load()
        verification = config_manager.verify_config()

        if verification['is_complete']:
            print_success("✓ Configuration is complete!")
            print_info("  All required fields are present and configured")
            print()
            return

        # Show missing fields grouped by section
        print_warning(f"⚠ Found {verification['total_missing']} missing field(s)")
        print()

        incomplete_sections = verification['incomplete_sections']
        if incomplete_sections:
            print_info("Missing fields by section:")
            print()
            for section, fields in sorted(incomplete_sections.items()):
                section_display = section if section != "root" else "Top Level"
                print(f"  [{section_display}]")
                for field in fields:
                    print(f"    - {field}")
            print()

        # Offer to apply missing fields
        print_info("You can automatically apply default values for these missing fields.")
        print()
        apply = input("Apply missing fields from defaults? (yes/no): ").strip().lower()

        if apply not in ('yes', 'y'):
            print_info("Skipped. Configuration not modified.")
            return

        # Apply missing fields (dry run first to see what would change)
        print()
        print_info("Applying missing fields...")
        result = config_manager.apply_missing_fields(dry_run=False)

        # Show what was added
        if result['fields_added']:
            print()
            print_success(f"✓ Added {len(result['fields_added'])} field(s):")
            for field_path in sorted(result['fields_added']):
                print(f"    + {field_path}")

            # Save the updated config
            config_manager.save()
            print()
            print_success("✓ Configuration updated and saved!")
        else:
            print()
            print_info("No fields were added (config may have been fixed already)")

        print()

    except Exception as e:
        print_error(f"Config verification failed: {e}")
        import traceback
        traceback.print_exc()


def scan_historical_fcs_command(config):
    """Scan existing scores for historical Full Combos (v2.6.0)"""
    try:
        from bot.database import Database

        db_path = get_config_dir() / 'scores.db'
        if not db_path.exists():
            print_error("Database not found")
            return

        print_header("SCAN HISTORICAL FULL COMBOS", width=60)
        print()
        print_info("This will:")
        print("  1. Scan all scores with chart metadata")
        print("  2. Identify scores that were Full Combos")
        print("  3. Update the database with FC flags")
        print("  4. Optionally post retroactive FC announcements")
        print()
        print_warning("Note: Only scores with chart metadata can be checked")
        print_info("Run the client's 'scancharts' command first if needed")
        print()

        # Check if retroactive announcements are enabled
        fc_config = config.get('announcements', {}).get('full_combos', {})
        retroactive_enabled = fc_config.get('announce_retroactive_fcs', True)

        if retroactive_enabled:
            print_info("Retroactive FC announcements: ENABLED")
            print_warning("Historical FCs will be posted to Discord!")
            print()
        else:
            print_info("Retroactive FC announcements: DISABLED")
            print_info("FCs will be flagged in database but not announced")
            print()

        confirm = input("Continue with FC scan? (yes/no): ").strip().lower()
        if confirm != "yes":
            print_info("Cancelled.")
            return

        print()
        db = Database(str(db_path))
        db.connect()

        # Run the scan
        result = db.scan_historical_fcs(announce_to_discord=retroactive_enabled)

        db.close()

        print()
        print_header("SCAN COMPLETE", width=60)
        print_success(f"  Scores scanned: {result['scanned']}")
        print_success(f"  Full Combos found: {result['fcs_found']}")
        print()

        # If retroactive announcements are enabled and we found FCs, post them
        if retroactive_enabled and result.get('fcs_to_announce'):
            fcs_to_announce = result['fcs_to_announce']
            print_info(f"Found {len(fcs_to_announce)} historical FCs to announce")
            print()

            post_confirm = input(f"Post {len(fcs_to_announce)} FC announcements to Discord? (yes/no): ").strip().lower()
            if post_confirm == "yes":
                print()
                print_info("Posting FC announcements...")
                post_retroactive_fc_announcements(config, fcs_to_announce)
                print_success("Retroactive FC announcements posted!")
            else:
                print_info("Skipped Discord announcements")

        print()

    except Exception as e:
        print_error(f"Failed to scan historical FCs: {e}")
        import traceback
        traceback.print_exc()


def post_retroactive_fc_announcements(config, fcs_to_announce):
    """Post retroactive FC announcements to Discord (v2.6.0)"""
    import asyncio
    import discord
    from discord import Embed

    async def send_announcements():
        try:
            # Create Discord client
            bot_token = config.get('discord', {}).get('bot_token', config.get('DISCORD_BOT_TOKEN'))
            channel_id = config.get('discord', {}).get('announcement_channel_id', config.get('DISCORD_CHANNEL_ID'))

            if not bot_token or not channel_id:
                print_error("Discord credentials not configured")
                return

            # Create a minimal Discord client
            intents = discord.Intents.default()
            client = discord.Client(intents=intents)

            @client.event
            async def on_ready():
                try:
                    channel = client.get_channel(int(channel_id))
                    if not channel:
                        print_error(f"Channel not found: {channel_id}")
                        await client.close()
                        return

                    print_info(f"Connected to Discord. Posting {len(fcs_to_announce)} announcements...")

                    for i, fc in enumerate(fcs_to_announce, 1):
                        # Create embed based on FC type
                        if fc['is_fc_record_break']:
                            title = "👑 C-C-C-COMBO BREAKER!!!"
                            action_text = f"broke {fc['previous_holder']}'s FC record with an even higher Full Combo score!"
                        elif fc['is_first_fc']:
                            title = "👑 FIRST FULL COMBO ON CHART!"
                            action_text = "is the FIRST to FC this chart!"
                        else:
                            title = "👑 FULL COMBO!"
                            action_text = "hit every note perfectly!"

                        # Create embed
                        embed = Embed(
                            title=title,
                            description=f"**{fc['username']}** {action_text}",
                            color=0xFF0000  # RED
                        )

                        # Song title
                        song_display = fc['song_title']
                        if fc['song_artist']:
                            song_display += f" - {fc['song_artist']}"
                        embed.add_field(name="Song", value=song_display, inline=False)

                        # Score
                        embed.add_field(name="Score", value=f"{fc['score']:,}", inline=True)

                        # Add "RETROACTIVE" note in footer
                        embed.set_footer(text=f"⏪ Historical FC (from {fc['submitted_at'][:10]})")

                        await channel.send(embed=embed)

                        print_success(f"  [{i}/{len(fcs_to_announce)}] Posted: {fc['username']} - {fc['song_title']}")

                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)

                    print_success("All announcements posted!")
                    await client.close()

                except Exception as e:
                    print_error(f"Error posting announcements: {e}")
                    await client.close()

            # Run the client
            await client.start(bot_token)

        except Exception as e:
            print_error(f"Failed to connect to Discord: {e}")

    # Run async function
    asyncio.run(send_announcements())


def show_configuration_summary(config):
    """Show detailed configuration summary (read-only)"""
    print_header("CONFIGURATION SUMMARY", width=70)

    discord = config.get('discord', {})
    api = config.get('api', {})
    display = config.get('display', {})
    announcements = config.get('announcements', {})

    try:
        from colorama import Fore, Style
        has_colors = True
    except ImportError:
        has_colors = False

    # Discord Settings
    print(f"\n{Fore.CYAN}Discord Settings:{Style.RESET_ALL}" if has_colors else "\n=== Discord Settings ===")
    print(f"  Bot Token: {'*' * 40} (secured)")
    print(f"  App ID: {discord.get('app_id', config.get('DISCORD_APP_ID', 'Not set'))}")
    print(f"  Guild ID: {discord.get('guild_id', config.get('DISCORD_GUILD_ID', 'Not set (global sync)'))}")
    print(f"  Channel ID: {discord.get('announcement_channel_id', config.get('DISCORD_CHANNEL_ID', 'Not set'))}")

    # API Settings
    print(f"\n{Fore.CYAN}API Settings:{Style.RESET_ALL}" if has_colors else "\n=== API Settings ===")
    print(f"  Port: {api.get('port', config.get('API_PORT', 8080))}")
    print(f"  Host: 0.0.0.0 (all interfaces)")
    debug_pass = api.get('debug_password', config.get('DEBUG_PASSWORD', 'admin123'))
    print(f"  Debug Password: {'*' * len(debug_pass)}")

    # Display Settings
    print(f"\n{Fore.CYAN}Display Settings:{Style.RESET_ALL}" if has_colors else "\n=== Display Settings ===")
    print(f"  Timezone: {display.get('timezone', 'UTC')}")
    print(f"  Date Format: {display.get('date_format', 'MM/DD/YYYY')}")
    print(f"  Time Format: {display.get('time_format', '12-hour')}")
    print(f"  Show Timezone: {display.get('show_timezone_in_embeds', True)}")

    # Announcement Settings
    print(f"\n{Fore.CYAN}Announcement Settings:{Style.RESET_ALL}" if has_colors else "\n=== Announcement Settings ===")
    record_breaks = announcements.get('record_breaks', {})
    first_time = announcements.get('first_time_scores', {})
    personal_bests = announcements.get('personal_bests', {})

    print(f"  Record Breaks: {'Enabled' if record_breaks.get('enabled', True) else 'Disabled'}")
    if record_breaks.get('enabled'):
        print(f"    Ping Previous Holder: {record_breaks.get('ping_previous_holder', True)}")

    print(f"  First-Time Scores: {'Enabled' if first_time.get('enabled', True) else 'Disabled'}")
    print(f"  Personal Bests: {'Enabled' if personal_bests.get('enabled', False) else 'Disabled'}")
    if personal_bests.get('enabled'):
        print(f"    Min Improvement: {personal_bests.get('min_improvement_percent', 5.0)}% or {personal_bests.get('min_improvement_points', 10000):,} points")

    # Database Settings
    database = config.get('database', {})
    print(f"\n{Fore.CYAN}Database Settings:{Style.RESET_ALL}" if has_colors else "\n=== Database Settings ===")
    print(f"  Auto Backup: {'Enabled' if database.get('auto_backup', True) else 'Disabled'}")
    print(f"  Backup Keep Count: {database.get('backup_keep_count', 7)}")

    # Activity Log
    activity_log = config.get('daily_activity_log', {})
    print(f"\n{Fore.CYAN}Activity Log:{Style.RESET_ALL}" if has_colors else "\n=== Activity Log ===")
    print(f"  Enabled: {'Yes' if activity_log.get('enabled', True) else 'No'}")
    if activity_log.get('enabled'):
        print(f"  Generation Time: {activity_log.get('generation_time', '00:00')}")
        print(f"  Keep Days: {activity_log.get('keep_days', 30)}")

    print()


def start_shutdown_listener(shutdown_flag):
    """
    Background thread to listen for shutdown commands in terminal.
    Allows typing 'quit', 'stop', or 'exit' to gracefully shut down the bot.
    """
    def listen():
        import time
        # Wait for bot to fully initialize before accepting shutdown commands
        # This prevents crashes from shutting down during startup
        time.sleep(5)

        while True:
            try:
                cmd = input().strip().lower()
                if cmd in ('quit', 'stop', 'exit'):
                    if not shutdown_flag['flag']:
                        print_info("\n[*] Shutdown command received - stopping bot...")
                        shutdown_flag['flag'] = True
                        # Flag is set - async shutdown monitor will handle graceful shutdown
                    break
            except (EOFError, KeyboardInterrupt):
                # Input stream closed or interrupted
                break
            except Exception as e:
                # On any other error, exit the listener
                # Don't print errors to avoid cluttering output
                break

    # Start listener in daemon thread (dies with main thread)
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return thread


def check_bot_status():
    """Check bot health and configuration status"""
    print_header("BOT STATUS CHECK", width=60)

    # Check config file
    config_path = get_config_path()
    if config_path.exists():
        print_success(f"Configuration: Found")
        print_info(f"  Location: {config_path}")
    else:
        print_error("Configuration: Not found")
        return

    # Check database
    db_path = get_config_dir() / 'scores.db'
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print_success(f"Database: Connected")
        print_info(f"  Size: {size_mb:.2f} MB")
        print_info(f"  Location: {db_path}")
    else:
        print_warning("Database: Not initialized")

    # Check Discord token
    config = load_config()
    if config:
        discord = config.get('discord', {})
        token = discord.get('bot_token', config.get('DISCORD_TOKEN', ''))
        if token:
            print_success("Discord Token: Configured")
        else:
            print_error("Discord Token: Missing")

        # Check channel
        channel_id = discord.get('announcement_channel_id', config.get('DISCORD_CHANNEL_ID', ''))
        if channel_id:
            print_success(f"Announcement Channel: {channel_id}")
        else:
            print_warning("Announcement Channel: Not configured")

        # Check API port
        api = config.get('api', {})
        port = api.get('port', config.get('API_PORT', 8080))
        print_info(f"API Port: {port}")

    print()


def fix_note_counts_utility():
    """
    Utility to fix incorrect note counts in the database.

    Displays detailed explanation, then runs the migration script to correct
    note_total values in scores table using data from chart_metadata table.
    """
    print_header("FIX NOTE COUNTS UTILITY", width=80)
    print()
    print("WHAT THIS UTILITY DOES:")
    print("=" * 80)
    print()
    print("Prior to v2.6.2, the chart parser incorrectly counted individual note events")
    print("instead of playable notes. For example, a chord with 3 frets was counted as")
    print("3 notes instead of 1 note.")
    print()
    print("This resulted in:")
    print("  - Inflated note counts (e.g., 902 notes instead of 450)")
    print("  - Incorrect NPS calculations (e.g., 7.1 NPS instead of 3.6 NPS)")
    print()
    print("This utility scans the scores table and compares note counts with the correct")
    print("values from the chart_metadata table. Any mismatches are identified and can be")
    print("corrected with your confirmation.")
    print()
    print("REQUIREMENTS:")
    print("  - chart_metadata table must be populated")
    print("  - Run 'scancharts' from a v2.6.2+ client first if you haven't already")
    print()
    print("SAFETY:")
    print("  - Shows preview of what will change before making any modifications")
    print("  - Requires explicit 'yes' confirmation before updating database")
    print("  - Only updates scores where correct chart_metadata exists")
    print("  - All other score data remains unchanged")
    print()
    print("=" * 80)
    print()

    response = input("Press Enter to continue, or type 'cancel' to go back: ").strip().lower()
    if response == 'cancel':
        return

    print()

    # Run the migration logic directly
    try:
        import sqlite3
        from datetime import datetime
        from typing import Dict, List, Tuple

        # Get database path
        db_path = get_config_dir() / 'scores.db'

        if not db_path.exists():
            print_error(f"Database not found: {db_path}")
            print()
            print("Make sure the bot has been run at least once to create the database.")
            return

        print(f"[*] Database: {db_path}")
        print()

        # Step 1: Analyze mismatches
        print("[*] Analyzing scores table...")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query scores with note counts and join with chart_metadata
        query = """
            SELECT
                s.id as score_id,
                s.chart_hash,
                s.instrument_id,
                s.difficulty_id,
                s.user_id,
                s.score,
                s.notes_total as current_notes,
                cm.total_notes as correct_notes,
                cm.note_density as correct_nps,
                u.discord_username
            FROM scores s
            LEFT JOIN chart_metadata cm
                ON s.chart_hash = cm.chart_hash
                AND s.instrument_id = cm.instrument_id
                AND s.difficulty_id = cm.difficulty_id
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.notes_total IS NOT NULL
            AND s.notes_total > 0
        """

        cursor.execute(query)
        results = cursor.fetchall()

        mismatches = []
        stats = {
            'total_scores_with_notes': 0,
            'scores_with_metadata': 0,
            'scores_without_metadata': 0,
            'mismatches_found': 0,
            'exact_matches': 0,
        }

        for row in results:
            stats['total_scores_with_notes'] += 1

            current = row['current_notes']
            correct = row['correct_notes']

            if correct is None:
                stats['scores_without_metadata'] += 1
                continue

            stats['scores_with_metadata'] += 1

            if current != correct:
                stats['mismatches_found'] += 1

                mismatches.append({
                    'score_id': row['score_id'],
                    'chart_hash': row['chart_hash'],
                    'instrument_id': row['instrument_id'],
                    'difficulty_id': row['difficulty_id'],
                    'user_id': row['user_id'],
                    'username': row['discord_username'],
                    'score': row['score'],
                    'current_notes': current,
                    'correct_notes': correct,
                    'difference': current - correct,
                    'correct_nps': row['correct_nps']
                })
            else:
                stats['exact_matches'] += 1

        conn.close()

        print()
        print("ANALYSIS RESULTS:")
        print("-" * 80)
        print(f"  Total scores with note data:     {stats['total_scores_with_notes']:,}")
        print(f"  Scores with chart metadata:      {stats['scores_with_metadata']:,}")
        print(f"  Scores missing chart metadata:   {stats['scores_without_metadata']:,}")
        print()
        print(f"  Exact matches (no change needed): {stats['exact_matches']:,}")
        print(f"  Mismatches found (need fixing):   {stats['mismatches_found']:,}")
        print()

        if stats['mismatches_found'] == 0:
            print_success("No mismatches found! All note counts are correct.")
            print()
            return

        if stats['scores_without_metadata'] > 0:
            print_warning("Some scores are missing chart metadata and cannot be fixed.")
            print_info("          Run 'scancharts' from the client to populate metadata.")
            print()

        # Step 2: Show sample mismatches
        print()
        print("=" * 80)
        print("  SAMPLE MISMATCHES (showing up to 10)")
        print("=" * 80)
        print()

        instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
        difficulties = {0: "Easy", 1: "Med", 2: "Hard", 3: "Exp"}

        print(f"{'User':<20} {'Inst':<6} {'Diff':<5} {'Current':<8} {'Correct':<8} {'Diff':<8} {'Hash':<10}")
        print("-" * 80)

        for i, m in enumerate(mismatches[:10]):
            inst = instruments.get(m['instrument_id'], f"Inst{m['instrument_id']}")
            diff = difficulties.get(m['difficulty_id'], f"Diff{m['difficulty_id']}")

            print(f"{m['username'][:20]:<20} {inst:<6} {diff:<5} "
                  f"{m['current_notes']:<8} {m['correct_notes']:<8} "
                  f"{m['difference']:+8} {m['chart_hash'][:8]:<10}")

        if len(mismatches) > 10:
            print(f"... and {len(mismatches) - 10} more")
        print()

        # Step 3: Confirm changes
        print("=" * 80)
        print()
        response = input(f"Apply corrections to {stats['mismatches_found']} scores? (yes/no): ").strip().lower()

        if response != 'yes':
            print()
            print_info("Cancelled. No changes made.")
            print()
            return

        # Step 4: Apply corrections
        print()
        print("[*] Applying corrections...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updated = 0

        for mismatch in mismatches:
            try:
                cursor.execute("""
                    UPDATE scores
                    SET notes_total = ?
                    WHERE id = ?
                """, (mismatch['correct_notes'], mismatch['score_id']))

                updated += cursor.rowcount
            except Exception as e:
                print_error(f"Error updating score {mismatch['score_id']}: {e}")

        conn.commit()
        conn.close()

        print()
        print("=" * 80)
        print("  MIGRATION COMPLETE")
        print("=" * 80)
        print()
        print_success(f"Updated {updated} score records")
        print()
        print("SUMMARY:")
        print(f"  + Scores corrected: {updated}")
        print(f"  + Database: {db_path}")
        print(f"  + Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    except Exception as e:
        print_error(f"Error running migration: {e}")
        import traceback
        traceback.print_exc()


def admin_utilities_menu():
    """Display and handle admin utilities submenu"""
    while True:
        print()
        print_header("ADMIN UTILITIES", width=80)
        print()
        print("Administrative tools for database maintenance, diagnostics, and special")
        print("operations. These utilities are used less frequently than the main menu")
        print("options and require careful attention to instructions.")
        print()
        print("+------------------------------------------------------------------------------+")
        print("|                                                                              |")
        print("|  [1] Fix Note Counts (Database Migration)                                   |")
        print("|      Corrects incorrect note counts in scores table using chart metadata.   |")
        print("|      Use this if you have scores from before v2.6.2.                        |")
        print("|                                                                              |")
        print("|  [2] Scan Historical FCs                                                    |")
        print("|      Scans existing 100% completion scores and marks them as FCs in the     |")
        print("|      database. Use once after upgrading to v2.6.0+.                         |")
        print("|                                                                              |")
        print("|  [3] Backup Database                                                        |")
        print("|      Manually create a timestamped backup of the scores database.           |")
        print("|      Backups are saved to the 'backups' folder.                             |")
        print("|                                                                              |")
        print("|  [4] Export Logs                                                            |")
        print("|      Creates a timestamped copy of the bot log file for sharing or          |")
        print("|      archival purposes.                                                     |")
        print("|                                                                              |")
        print("|  [5] Send Update Notification                                               |")
        print("|      Manually posts an update notification to the Discord announcement      |")
        print("|      channel. Use when releasing new bot/client versions.                   |")
        print("|                                                                              |")
        print("|  [6] Verify Configuration                                                   |")
        print("|      Runs diagnostic checks on bot configuration and reports any issues     |")
        print("|      with Discord connection, database, or API settings.                    |")
        print("|                                                                              |")
        print("|  [B] Back to Main Menu                                                      |")
        print("|                                                                              |")
        print("+------------------------------------------------------------------------------+")

        choice = input("\nChoice: ").strip().lower()

        if choice == '1':
            # Fix note counts
            print()
            fix_note_counts_utility()
            input("\nPress Enter to continue...")

        elif choice == '2':
            # Scan historical FCs
            print()
            # Need to load config for this command
            try:
                config = load_config()
                scan_historical_fcs_command(config)
            except Exception as e:
                print_error(f"Error loading config: {e}")
            input("\nPress Enter to continue...")

        elif choice == '3':
            # Backup database
            print()
            backup_database_command()
            input("\nPress Enter to continue...")

        elif choice == '4':
            # Export logs
            print()
            export_logs_command()
            input("\nPress Enter to continue...")

        elif choice == '5':
            # Send update notification
            print()
            try:
                config = load_config()
                send_manual_update_notification(config)
            except Exception as e:
                print_error(f"Error: {e}")
                print_info("Check log file for details")
            input("\nPress Enter to continue...")

        elif choice == '6':
            # Verify config
            print()
            verify_config_command()
            input("\nPress Enter to continue...")

        elif choice == 'b':
            # Back to main menu
            return

        else:
            print_warning("Invalid choice. Please try again.")
            input("\nPress Enter to continue...")


def main():
    # Check for updates on startup
    print("[*] Checking for updates...")
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

    # Show current config - handle both old and new formats
    discord = config.get('discord', {})
    api = config.get('api', {})
    display = config.get('display', {})

    print_header("CONFIGURATION LOADED", width=60)

    print(f"\n{Fore.CYAN}Discord Settings:{Style.RESET_ALL}" if 'Fore' in dir() else "\nDiscord Settings:")
    app_id = discord.get('app_id', config.get('DISCORD_APP_ID'))
    print_info(f"App ID: {app_id}")

    guild_id = discord.get('guild_id', config.get('DISCORD_GUILD_ID'))
    if guild_id:
        print_info(f"Guild ID: {guild_id} (fast sync)")

    channel_id = discord.get('announcement_channel_id', config.get('DISCORD_CHANNEL_ID'))
    print_info(f"Channel: {channel_id}")

    print(f"\n{Fore.CYAN}API Settings:{Style.RESET_ALL}" if 'Fore' in dir() else "\nAPI Settings:")
    port = api.get('port', config.get('API_PORT', 8080))
    print_info(f"Port: {port}")
    debug_pass = api.get('debug_password', config.get('DEBUG_PASSWORD', 'admin123'))
    print_info(f"Debug Password: {'*' * len(debug_pass)} (secured)")

    # Display settings if using new format
    if display.get('timezone'):
        print(f"\n{Fore.CYAN}Display Settings:{Style.RESET_ALL}" if 'Fore' in dir() else "\nDisplay Settings:")
        print_info(f"Timezone: {display.get('timezone')}")
        print_info(f"Time Format: {display.get('time_format', '12-hour')}")

    # Set environment variables
    setup_environment(config)

    # Show ASCII banner before menu
    show_ascii_banner()

    # Show startup menu
    print("+---------------------------------------------------+")
    print("|                  MAIN MENU                        |")
    print("+---------------------------------------------------+")
    print("|  [1] Start Bot                                    |")
    print("|  [2] Settings Menu                                |")
    print("|  [3] View Configuration                           |")
    print("|  [4] Check Status                                 |")
    print("|  [5] Show Statistics                              |")
    print("|  [6] Admin Utilities                              |")
    print("|  [Q] Quit                                         |")
    print("+---------------------------------------------------+")
    choice = input("\nChoice: ").strip().lower()

    if choice == '2':
        # Open settings menu
        try:
            from bot.settings_menu import SettingsMenu
            from bot.config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.load()  # Load configuration
            menu = SettingsMenu(config_manager)
            menu.run()
            print_info("\nReturning to launcher...")
            input("Press Enter to continue...")
            return main()  # Restart launcher to apply settings
        except Exception as e:
            print_error(f"Error opening settings menu: {e}")
            print_info("Check log file for details")
            input("\nPress Enter to continue...")
            return main()

    elif choice == '3':
        # View configuration (read-only)
        print()
        show_configuration_summary(config)
        input("\nPress Enter to continue...")
        return main()

    elif choice == '4':
        # Check status
        print()
        check_bot_status()
        input("\nPress Enter to continue...")
        return main()

    elif choice == '5':
        # Show statistics
        print()
        show_stats_command()
        input("\nPress Enter to continue...")
        return main()

    elif choice == '6':
        # Admin utilities submenu
        admin_utilities_menu()
        return main()

    elif choice == 'q':
        print_info("Exiting...")
        return

    # If choice == '1' or anything else, continue to start bot

    print_header("STARTING BOT", width=60)

    # Run database migrations before starting the bot
    print_info("Running database migrations...")
    try:
        from bot.migrations import run_migrations
        db_path = get_config_dir() / 'scores.db'
        run_migrations(db_path)
        print_success("  Migrations complete")
    except Exception as e:
        print_error(f"  Migration failed: {e}")
        print_warning("  Bot may not function correctly")
        import traceback
        traceback.print_exc()

    # Create database backup (if enabled)
    from bot.config_manager import ConfigManager
    config_manager = ConfigManager()
    config_manager.load()  # Load configuration
    auto_backup_enabled = config_manager.config.get('database', {}).get('auto_backup', True)
    backup_keep_count = config_manager.config.get('database', {}).get('backup_keep_count', 7)

    if auto_backup_enabled:
        print_info("Creating database backup...")
        try:
            from bot.database import Database
            db = Database(str(db_path))
            success = db.create_backup(keep_count=backup_keep_count)
            if success:
                print_success("  Backup created")
                # Show backup details
                backup_dir = db_path.parent / 'backups'
                if backup_dir.exists():
                    backups = list(backup_dir.glob('scores_*.db'))
                    print_info(f"  Keeping {len(backups)} backups (max {backup_keep_count})")
        except Exception as e:
            print_warning(f"  Backup failed: {e}")
            print_info("  Bot will continue without backup")

    # Show activity log status
    activity_log_config = config_manager.config.get('daily_activity_log', {})
    if activity_log_config.get('enabled', True):
        print_info(f"Activity Log: Enabled")
        print_info(f"  Generates at {activity_log_config.get('generation_time', '00:00')}")
        print_info(f"  Keeping logs for {activity_log_config.get('keep_days', 30)} days")

    # Start the bot
    print()
    print_success("Connecting to Discord...")
    print_info("Press Ctrl+C to return to launcher")
    print_info("(Terminal commands 'quit'/'stop'/'exit' available after startup)")
    print()

    # Set up signal handler for immediate Ctrl+C feedback
    shutdown_requested = {'flag': False}  # Use dict for mutability in nested function

    async def run_bot_async():
        """Run bot with proper async handling for Ctrl+C and shutdown commands"""
        # Reload bot module to get fresh instance with all commands registered
        import importlib
        import bot.bot
        importlib.reload(bot.bot)
        bot_instance = bot.bot.bot  # Get the global singleton from reloaded module

        async def run_bot_with_monitoring():
            """Run bot and monitor for shutdown requests"""
            try:
                async with bot_instance:
                    # Create task to start the bot
                    bot_task = asyncio.create_task(bot_instance.start(config['DISCORD_TOKEN']))

                    # Monitor for shutdown flag
                    while not shutdown_requested['flag']:
                        await asyncio.sleep(0.5)  # Check twice per second
                        if bot_task.done():
                            # Bot stopped on its own
                            return

                    # Shutdown requested - cancel the bot task and close gracefully
                    print_info("\n[*] Initiating graceful shutdown...")
                    bot_task.cancel()
                    try:
                        await bot_task
                    except asyncio.CancelledError:
                        pass  # Expected when we cancel

                    # Close the bot
                    await bot_instance.close()
            except KeyboardInterrupt:
                print("\n[*] Shutting down bot...")
                await bot_instance.close()
                raise  # Re-raise to be caught by outer handler

        try:
            await run_bot_with_monitoring()
        except KeyboardInterrupt:
            raise  # Re-raise to outer handler

    def signal_handler(signum, frame):
        """Provide immediate feedback on Ctrl+C - bypasses I/O blocking"""
        if not shutdown_requested['flag']:
            shutdown_requested['flag'] = True
            # Use sys.stdout.write for immediate output (bypasses print buffering)
            import sys
            sys.stdout.write("\n")
            # Use colorama for colored output
            from colorama import Fore, Style
            sys.stdout.write(f"{Fore.YELLOW}⚠ Shutdown requested - cleaning up, please wait...{Style.RESET_ALL}\n\n")
            sys.stdout.flush()  # Force immediate display
        # Let the KeyboardInterrupt propagate normally
        raise KeyboardInterrupt

    # Register the handler (save original to restore later)
    original_handler = signal.signal(signal.SIGINT, signal_handler)

    # Start background thread to listen for shutdown commands
    input_listener = start_shutdown_listener(shutdown_requested)

    try:
        import time
        bot_start_time = time.time()
        asyncio.run(run_bot_async())

        # v2.6.2: If we get here, bot stopped - check if it was via shutdown command
        # (If Ctrl+C was used, we would have hit the KeyboardInterrupt handler instead)
        if shutdown_requested['flag']:
            # Graceful shutdown via 'quit'/'stop'/'exit' command
            # Calculate uptime
            uptime_seconds = int(time.time() - bot_start_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60

            print()
            print_header("BOT SHUTDOWN", width=60)
            print_success("Bot stopped gracefully")
            print_info(f"  Session duration: {hours}h {minutes}m {seconds}s")
            print()
            print_info("Returning to launcher...")
            input("Press Enter to continue...")
            return main()  # Return to launcher menu

    except KeyboardInterrupt:
        # Calculate uptime
        uptime_seconds = int(time.time() - bot_start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60

        print()
        print_header("BOT SHUTDOWN", width=60)
        print_success("Bot stopped gracefully")
        print_info(f"  Session duration: {hours}h {minutes}m {seconds}s")
        print()
        print_info("Returning to launcher...")
        input("Press Enter to continue...")
        return main()  # Return to launcher menu
    except Exception as e:
        print()
        print_error(f"Error starting bot: {e}")
        print_info("Check log file for details")
        input("\nPress Enter to continue...")
        return main()  # Return to launcher menu even on error
    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_handler)


if __name__ == '__main__':
    main()

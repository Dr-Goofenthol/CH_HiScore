"""
Standalone script to test hash resolution functionality
Run with: py test_resolvehashes.py [bot_url]
Example: py test_resolvehashes.py http://192.168.1.100:5000
"""

import hashlib
import json
import os
import sys
import requests
from pathlib import Path

# ANSI color codes for output
def print_success(msg): print(f"\033[92m[+] {msg}\033[0m")
def print_error(msg): print(f"\033[91m[ERROR] {msg}\033[0m")
def print_info(msg): print(f"\033[94m[*] {msg}\033[0m")
def print_warning(msg): print(f"\033[93m[!] {msg}\033[0m")
def print_header(msg): print(f"\n{'='*60}\n   {msg}\n{'='*60}\n")


def parse_song_ini(chart_path):
    """Parse song.ini file to get metadata"""
    try:
        ini_path = Path(chart_path).parent / 'song.ini'
        if not ini_path.exists():
            return None

        metadata = {}
        with open(ini_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('['):
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    metadata[key] = value

        return metadata
    except Exception as e:
        return None


def get_unresolved_hashes(bot_url, auth_token):
    """Get list of unresolved hashes from server"""
    print_info("Fetching unresolved hashes from server...")

    try:
        response = requests.get(
            f"{bot_url}/api/unresolved_hashes",
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"Server error: {response.status_code}")
            return None

        data = response.json()
        if not data.get('success'):
            print_error(f"Server error: {data.get('error', 'Unknown')}")
            return None

        hashes = data.get('hashes', [])
        print_success(f"Found {len(hashes)} unresolved hashes")
        return set(hashes)

    except Exception as e:
        print_error(f"Failed to get unresolved hashes: {e}")
        return None


def get_song_folders():
    """Get list of song folders to scan"""
    print_info("Looking for Clone Hero's settings...")

    # Try to find Clone Hero's settings.ini
    ch_dir = Path.home() / 'Documents' / 'Clone Hero'
    settings_path = ch_dir / "settings.ini"

    song_folders = []

    if settings_path.exists():
        try:
            # Parse settings.ini manually
            with open(settings_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('path') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        folder = value.strip()

                        if key.startswith('path') and key[4:].isdigit():
                            if folder and Path(folder).exists():
                                song_folders.append(Path(folder))
                                print_success(f"  Found song folder: {folder}")
        except Exception as e:
            print_warning(f"Could not parse Clone Hero settings: {e}")

    if not song_folders:
        print_warning("No folders found in Clone Hero settings")

    # Ask if user wants to add more folders
    print()
    while True:
        add_more = input("Add a songs folder to scan? (yes/no): ").strip().lower()
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

    return song_folders


def scan_folders(song_folders, unresolved_hashes):
    """Scan song folders and match hashes"""
    print()
    print_info(f"Will scan {len(song_folders)} song folder(s)")
    print_warning("This may take a few minutes for large libraries...")
    print()

    resolved_metadata = []
    scanned = 0
    found = 0

    for songs_path in song_folders:
        print_info(f"Scanning: {songs_path}")

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

                # Check if this is an unresolved hash
                if chart_hash not in unresolved_hashes:
                    # Also check partial match (first 8 chars)
                    if not any(h.startswith(chart_hash[:8]) for h in unresolved_hashes):
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
                    print(f"\n  [+] Found: {title} - {artist}")

            except Exception as e:
                continue

    print(f"\n\n[*] Scan complete: {scanned} songs scanned")
    print()

    return resolved_metadata


def send_updates(bot_url, auth_token, metadata_list):
    """Send resolved metadata to server"""
    print_info(f"Sending updates to server...")

    try:
        response = requests.post(
            f"{bot_url}/api/resolve_hashes",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={'metadata': metadata_list},
            timeout=30
        )

        data = response.json()
        if data.get('success'):
            updated_count = data.get('updated_count', 0)
            print_success(f"Updated {updated_count} songs in database!")
            print_info("Your mystery hashes now have song names!")
            return True
        else:
            print_error(f"Server error: {data.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print_error(f"Failed to send updates: {e}")
        return False


def main():
    print_header("RESOLVE CHART HASHES - TEST SCRIPT")

    # Load config to get auth token
    config_path = Path.home() / 'AppData' / 'LocalLow' / 'srylain Inc_' / 'Clone Hero' / '.score_tracker_config.json'

    if not config_path.exists():
        print_error("Config file not found. Make sure the tracker is set up and paired.")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    auth_token = config.get('auth_token')

    if not auth_token:
        print_error("Not paired! Use Discord to pair first (/pair)")
        return

    # Get bot URL from command line or prompt
    if len(sys.argv) > 1:
        bot_url = sys.argv[1]
    else:
        bot_url = config.get('bot_url', '')
        if not bot_url or bot_url == 'http://localhost:5000':
            print_warning("No bot URL specified or localhost detected")
            bot_url = input("Enter bot URL (e.g., http://192.168.1.100:5000): ").strip()
            if not bot_url:
                print_error("Bot URL required!")
                return

    # Add http:// if no scheme specified
    if not bot_url.startswith(('http://', 'https://')):
        bot_url = 'http://' + bot_url

    # Remove trailing slash if present
    bot_url = bot_url.rstrip('/')

    print_info(f"Bot URL: {bot_url}")
    print()

    # Step 1: Get unresolved hashes
    unresolved_hashes = get_unresolved_hashes(bot_url, auth_token)
    if not unresolved_hashes:
        print_info("No hashes to resolve! All your scores have metadata.")
        return

    if not unresolved_hashes:
        return

    # Step 2: Get song folders
    song_folders = get_song_folders()
    if not song_folders:
        print_error("No song folders to scan!")
        return

    # Step 3: Scan folders
    resolved_metadata = scan_folders(song_folders, unresolved_hashes)

    if not resolved_metadata:
        print_warning("No matches found!")
        print_info("Your unresolved hashes might be for songs not in your current folder.")
        return

    # Step 4: Show preview
    print_header(f"FOUND METADATA FOR {len(resolved_metadata)} SONGS")

    for i, item in enumerate(resolved_metadata[:10], 1):
        print(f"{i}. {item['title']}")
        if item['artist']:
            print(f"   Artist: {item['artist']}")
        if item['charter']:
            print(f"   Charter: {item['charter']}")
        print(f"   Hash: [{item['chart_hash'][:8]}...]")

    if len(resolved_metadata) > 10:
        print(f"... and {len(resolved_metadata) - 10} more")

    print()

    # Step 5: Confirm and send
    confirm = input(f"Send these {len(resolved_metadata)} updates to server? (yes/no): ").strip().lower()

    if confirm != "yes":
        print_info("Cancelled.")
        return

    send_updates(bot_url, auth_token, resolved_metadata)


if __name__ == '__main__':
    main()

"""
Bridge Desktop App Integration Module

Handles integration with the Bridge desktop app for chart searching.
Provides functionality to:
- Auto-detect Bridge installation
- Register custom URL protocol (chbridge://)
- Modify shortcuts to enable remote debugging
- Launch Bridge and inject search JavaScript via Chrome DevTools Protocol
"""

import json
import os
import platform
import subprocess
import time
import winreg
from pathlib import Path
from typing import Optional, Tuple, Dict
from urllib.parse import urlparse, parse_qs, unquote

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False


# Constants
BRIDGE_PROCESS_NAME = "Bridge.exe"
CDP_PORT = 9222
BRIDGE_LAUNCH_WAIT = 3  # seconds to wait for Bridge to initialize


def is_bridge_installed() -> Tuple[bool, Optional[Path]]:
    """
    Check if Bridge is installed and return its path.

    Returns:
        Tuple of (is_installed: bool, path: Optional[Path])
    """
    # Common installation locations
    possible_paths = [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'bridge' / 'Bridge.exe',
        Path(os.environ.get('PROGRAMFILES', '')) / 'Bridge' / 'Bridge.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Bridge' / 'Bridge.exe',
        Path.home() / 'AppData' / 'Local' / 'Programs' / 'bridge' / 'Bridge.exe',
    ]

    for path in possible_paths:
        if path.exists():
            return True, path

    return False, None


def is_bridge_running() -> bool:
    """
    Check if Bridge is currently running.

    Returns:
        bool: True if Bridge process is found
    """
    if not PSUTIL_AVAILABLE:
        return False

    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == BRIDGE_PROCESS_NAME:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return False


def is_cdp_available() -> bool:
    """
    Check if Chrome DevTools Protocol endpoint is available.

    Returns:
        bool: True if CDP is accessible at localhost:9222
    """
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)

    try:
        result = sock.connect_ex(('localhost', CDP_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


def kill_bridge_process() -> bool:
    """
    Kill all Bridge.exe processes.

    Returns:
        bool: True if successful
    """
    if not PSUTIL_AVAILABLE:
        return False

    killed = False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == BRIDGE_PROCESS_NAME:
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        time.sleep(1)  # Wait for process to fully terminate

    return killed


def launch_bridge(bridge_path: Path) -> bool:
    """
    Launch Bridge with remote debugging enabled.

    Args:
        bridge_path: Path to Bridge.exe

    Returns:
        bool: True if launched successfully
    """
    if not bridge_path.exists():
        return False

    try:
        # Launch Bridge with remote debugging port and CORS allowance
        subprocess.Popen(
            [
                str(bridge_path),
                f'--remote-debugging-port={CDP_PORT}',
                '--remote-allow-origins=*'
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )

        # Poll for Bridge to be ready (max 10 seconds)
        max_wait = 10
        poll_interval = 0.5
        elapsed = 0

        while elapsed < max_wait:
            if is_cdp_available():
                # CDP is available, wait a bit more for page to load
                time.sleep(1)
                return True
            time.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout - Bridge didn't become ready
        return False
    except Exception as e:
        print(f"Error launching Bridge: {e}")
        return False


def find_shortcuts() -> list[Path]:
    """
    Find all Bridge shortcuts on the system.

    Returns:
        List of Path objects for .lnk files
    """
    shortcuts = []

    # Desktop
    desktop = Path.home() / 'Desktop' / 'Bridge.lnk'
    if desktop.exists():
        shortcuts.append(desktop)

    # Start Menu (user)
    start_menu_user = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Bridge.lnk'
    if start_menu_user.exists():
        shortcuts.append(start_menu_user)

    # Start Menu (all users)
    start_menu_all = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Bridge.lnk'
    if start_menu_all.exists():
        shortcuts.append(start_menu_all)

    # Taskbar pinned
    taskbar = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Internet Explorer' / 'Quick Launch' / 'User Pinned' / 'TaskBar' / 'Bridge.lnk'
    if taskbar.exists():
        shortcuts.append(taskbar)

    return shortcuts


def modify_shortcut(lnk_path: Path) -> bool:
    """
    Add remote debugging arguments to a shortcut.

    Args:
        lnk_path: Path to .lnk file

    Returns:
        bool: True if modified successfully
    """
    if not WIN32COM_AVAILABLE:
        return False

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(lnk_path))

        # Get current arguments
        current_args = shortcut.Arguments or ""

        # Required flags for Bridge integration
        required_flags = f'--remote-debugging-port={CDP_PORT} --remote-allow-origins=*'

        # Check if both flags are present
        has_debug_port = f'--remote-debugging-port={CDP_PORT}' in current_args
        has_allow_origins = '--remote-allow-origins=' in current_args

        if not has_debug_port or not has_allow_origins:
            # Remove old flags if present (to avoid duplicates)
            if has_debug_port:
                current_args = current_args.replace(f'--remote-debugging-port={CDP_PORT}', '').strip()
            if has_allow_origins:
                # Remove any existing --remote-allow-origins flag
                import re
                current_args = re.sub(r'--remote-allow-origins=\S+', '', current_args).strip()

            # Add both required flags
            shortcut.Arguments = f"{current_args} {required_flags}".strip()
            shortcut.save()
            return True

        # Already has both flags
        return True
    except Exception as e:
        print(f"Error modifying shortcut {lnk_path}: {e}")
        return False


def modify_all_shortcuts() -> Tuple[int, int]:
    """
    Modify all found Bridge shortcuts.

    Returns:
        Tuple of (success_count, total_count)
    """
    shortcuts = find_shortcuts()
    success_count = 0

    for shortcut in shortcuts:
        if modify_shortcut(shortcut):
            success_count += 1

    return success_count, len(shortcuts)


def is_protocol_registered() -> bool:
    """
    Check if chbridge:// protocol is registered in Windows Registry.

    Returns:
        bool: True if registered
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'chbridge', 0, winreg.KEY_READ)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def register_protocol(tracker_exe_path: str) -> bool:
    """
    Register chbridge:// protocol in Windows Registry.

    Args:
        tracker_exe_path: Full path to CloneHeroScoreTracker.exe

    Returns:
        bool: True if registered successfully
    """
    try:
        # Create main key
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, 'chbridge')
        winreg.SetValue(key, '', winreg.REG_SZ, 'URL:Bridge Search Protocol')
        winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
        winreg.CloseKey(key)

        # Create command key
        command_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'chbridge\shell\open\command')
        command = f'"{tracker_exe_path}" --bridge-deeplink "%1"'
        winreg.SetValue(command_key, '', winreg.REG_SZ, command)
        winreg.CloseKey(command_key)

        return True
    except Exception as e:
        print(f"Error registering protocol: {e}")
        return False


def unregister_protocol() -> bool:
    """
    Unregister chbridge:// protocol from Windows Registry.

    Returns:
        bool: True if unregistered successfully
    """
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'chbridge\shell\open\command')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'chbridge\shell\open')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'chbridge\shell')
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'chbridge')
        return True
    except Exception as e:
        print(f"Error unregistering protocol: {e}")
        return False


def parse_bridge_url(url: str) -> Dict[str, str]:
    """
    Parse a chbridge:// URL into search parameters.

    Args:
        url: chbridge://search?name=...&artist=...&charter=...

    Returns:
        Dict with 'name', 'artist', 'charter' keys
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    return {
        'name': unquote(params.get('name', [''])[0]),
        'artist': unquote(params.get('artist', [''])[0]),
        'charter': unquote(params.get('charter', [''])[0])
    }


def inject_search_script(name: str, artist: str, charter: str = "") -> bool:
    """
    Inject JavaScript into Bridge to perform search.
    Uses Chrome DevTools Protocol to execute search script.

    Args:
        name: Song name
        artist: Artist name
        charter: Charter name (optional)

    Returns:
        bool: True if injection successful
    """
    if not is_cdp_available():
        return False

    # Build the JavaScript to inject
    # Uses polling approach instead of fixed delays for reliability
    js_script = f"""
(async function() {{
    function sleep(ms) {{
        return new Promise(resolve => setTimeout(resolve, ms));
    }}

    // Polling helper: wait for element to exist
    async function waitForElement(selector, timeout = 5000) {{
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {{
            const element = selector();
            if (element) return element;
            await sleep(100);
        }}
        return null;
    }}

    // Step 1: Navigate to Browse tab if needed
    const browseTab = Array.from(document.querySelectorAll('[role="tab"], button, a')).find(el =>
        el.textContent.toLowerCase().includes('browse')
    );

    if (browseTab && !browseTab.classList.contains('active')) {{
        browseTab.click();
        await sleep(500);  // Brief wait for navigation
    }}

    // Step 2: Wait for and expand Advanced Search
    const advancedToggle = await waitForElement(() =>
        Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.trim().toUpperCase().includes('ADVANCED')
        )
    );

    if (!advancedToggle) return 'Advanced Search button not found';

    if (!advancedToggle.classList.contains('btn-active')) {{
        advancedToggle.click();
        await sleep(300);
    }}

    // Step 3: Wait for search input fields to be ready
    const nameInput = await waitForElement(() =>
        Array.from(document.querySelectorAll('input')).find(i => i.placeholder === 'Name')
    );
    const artistInput = await waitForElement(() =>
        Array.from(document.querySelectorAll('input')).find(i => i.placeholder === 'Artist')
    );
    const charterInput = await waitForElement(() =>
        Array.from(document.querySelectorAll('input')).find(i => i.placeholder === 'Charter')
    );

    if (!nameInput || !artistInput || !charterInput) {{
        return 'Search input fields not found';
    }}

    // Fill fields
    nameInput.value = {json.dumps(name)};
    artistInput.value = {json.dumps(artist)};
    charterInput.value = {json.dumps(charter)};

    // Trigger Angular change detection
    nameInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    nameInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
    artistInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    artistInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
    charterInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
    charterInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

    await sleep(200);

    // Step 4: Wait for Search button to be ready and click it
    const searchButton = await waitForElement(() =>
        Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.trim().toUpperCase() === 'SEARCH' ||
            b.textContent.trim() === 'Search'
        )
    );

    if (!searchButton) return 'Search button not found';

    searchButton.click();
    return 'Search executed successfully';
}})();
"""

    try:
        import websocket
        import json as json_module

        # Get list of targets from CDP
        import urllib.request
        response = urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json')
        targets = json_module.loads(response.read())

        # Find the Bridge page (not devtools or extensions)
        bridge_target = None
        for target in targets:
            if target.get('type') == 'page' and 'devtools' not in target.get('url', '').lower():
                bridge_target = target
                break

        if not bridge_target:
            return False

        # Connect to WebSocket
        ws_url = bridge_target['webSocketDebuggerUrl']
        ws = websocket.create_connection(ws_url)

        # Execute JavaScript
        command = {
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': js_script,
                'awaitPromise': True
            }
        }

        ws.send(json_module.dumps(command))
        result = ws.recv()
        ws.close()

        return True
    except Exception as e:
        print(f"Error injecting script: {e}")
        return False


def run_bridge_setup(tracker_exe_path: str) -> Tuple[bool, str]:
    """
    Run complete Bridge integration setup.

    Args:
        tracker_exe_path: Path to CloneHeroScoreTracker.exe

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check dependencies
    if not PSUTIL_AVAILABLE:
        return False, "psutil package not available"

    if not WIN32COM_AVAILABLE:
        return False, "pywin32 package not available"

    # Step 1: Check if Bridge is installed
    is_installed, bridge_path = is_bridge_installed()

    if not is_installed:
        # Prompt for manual path
        return False, "Bridge not found in common locations. Please set path manually."

    # Step 2: Register protocol
    if not register_protocol(tracker_exe_path):
        return False, "Failed to register chbridge:// protocol"

    # Step 3: Modify shortcuts
    success_count, total_count = modify_all_shortcuts()

    if total_count == 0:
        # No shortcuts found, but that's okay - we can still launch Bridge ourselves
        shortcut_msg = "No shortcuts found (will launch Bridge directly when needed)"
    elif success_count == total_count:
        shortcut_msg = f"Modified {success_count} shortcut(s) successfully"
    else:
        shortcut_msg = f"Modified {success_count}/{total_count} shortcuts"

    # Success!
    return True, f"Setup complete! {shortcut_msg}. Bridge path: {bridge_path}"


def handle_bridge_deeplink(url: str, bridge_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Handle a chbridge:// deeplink URL.

    Args:
        url: The chbridge:// URL to handle
        bridge_path: Optional path to Bridge.exe (will auto-detect if None)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Parse URL
    params = parse_bridge_url(url)
    name = params.get('name', '')
    artist = params.get('artist', '')
    charter = params.get('charter', '')

    if not name and not artist:
        return False, "Invalid Bridge link - no search parameters"

    # Check if Bridge is installed
    if not bridge_path:
        is_installed, bridge_path = is_bridge_installed()
        if not is_installed:
            return False, "Bridge not installed"

    # Check if Bridge is running
    bridge_running = is_bridge_running()
    cdp_available = is_cdp_available()

    if bridge_running and cdp_available:
        # Bridge is running with remote debugging - inject search
        success = inject_search_script(name, artist, charter)
        if success:
            return True, f"Search executed in Bridge: {name} - {artist}"
        else:
            return False, "Failed to inject search script"

    elif bridge_running and not cdp_available:
        # Bridge is running but without remote debugging
        return False, "Bridge is running without remote debugging. Please close Bridge and try again."

    else:
        # Bridge not running - launch it
        if launch_bridge(bridge_path):
            # Wait for Bridge to fully initialize
            time.sleep(2)

            # Inject search
            success = inject_search_script(name, artist, charter)
            if success:
                return True, f"Launched Bridge and executed search: {name} - {artist}"
            else:
                return False, "Launched Bridge but failed to inject search"
        else:
            return False, "Failed to launch Bridge"

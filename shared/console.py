"""
Console output utilities with color support and logging

Provides consistent message formatting and colors across client and bot.
"""

import sys
from enum import Enum

try:
    from colorama import Fore, Style
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    # Fallback no-op
    class Fore:
        GREEN = RED = YELLOW = CYAN = WHITE = MAGENTA = ''
    class Style:
        BRIGHT = RESET_ALL = ''


class MessageType(Enum):
    """Message type categories"""
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


def print_success(message: str, indent: int = 0):
    """Print success message in green with [+] prefix"""
    prefix = "  " * indent
    if HAS_COLOR:
        print(f"{prefix}{Fore.GREEN}[+] {message}{Style.RESET_ALL}")
    else:
        print(f"{prefix}[+] {message}")


def print_info(message: str, indent: int = 0):
    """Print info message in cyan with [*] prefix"""
    prefix = "  " * indent
    if HAS_COLOR:
        print(f"{prefix}{Fore.CYAN}[*] {message}{Style.RESET_ALL}")
    else:
        print(f"{prefix}[*] {message}")


def print_warning(message: str, indent: int = 0):
    """Print warning message in yellow with [!] prefix"""
    prefix = "  " * indent
    if HAS_COLOR:
        print(f"{prefix}{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")
    else:
        print(f"{prefix}[!] {message}")


def print_error(message: str, indent: int = 0):
    """Print error message in red with [ERROR] prefix"""
    prefix = "  " * indent
    if HAS_COLOR:
        print(f"{prefix}{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
    else:
        print(f"{prefix}[ERROR] {message}")


def print_debug(message: str, indent: int = 0):
    """Print debug message in magenta with [DEBUG] prefix"""
    prefix = "  " * indent
    if HAS_COLOR:
        print(f"{prefix}{Fore.MAGENTA}[DEBUG] {message}{Style.RESET_ALL}")
    else:
        print(f"{prefix}[DEBUG] {message}")


def print_header(title: str, width: int = 60, color=None):
    """Print a formatted header"""
    separator = "=" * width
    if HAS_COLOR and color:
        print(f"\n{color}{separator}")
        print(f"   {title}")
        print(f"{separator}{Style.RESET_ALL}\n")
    else:
        print(f"\n{separator}")
        print(f"   {title}")
        print(f"{separator}\n")


def print_section(title: str, width: int = 60):
    """Print a section divider"""
    separator = "-" * width
    print(f"\n{separator}")
    print(title)
    print(f"{separator}")


def print_plain(message: str, indent: int = 0):
    """Print plain message without prefix"""
    prefix = "  " * indent
    print(f"{prefix}{message}")


def format_key_value(key: str, value: str, width: int = 20) -> str:
    """Format key-value pair with alignment"""
    return f"{key:>{width}}: {value}"

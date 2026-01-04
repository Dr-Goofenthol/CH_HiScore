"""
Configuration loader for Discord bot

Loads settings from .env file
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


def get_default_db_path() -> str:
    """Get default database path in AppData"""
    if sys.platform == 'win32':
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        config_dir = appdata / 'CloneHeroScoreBot'
    else:
        config_dir = Path.home() / '.config' / 'CloneHeroScoreBot'

    config_dir.mkdir(parents=True, exist_ok=True)
    return str(config_dir / 'scores.db')


class ConfigMeta(type):
    """Metaclass to make Config properties read from environment dynamically"""

    @property
    def DISCORD_TOKEN(cls):
        return os.getenv('DISCORD_TOKEN')

    @property
    def DISCORD_APP_ID(cls):
        return os.getenv('DISCORD_APP_ID')

    @property
    def DISCORD_GUILD_ID(cls):
        return os.getenv('DISCORD_GUILD_ID')

    @property
    def DISCORD_CHANNEL_ID(cls):
        return os.getenv('DISCORD_CHANNEL_ID')

    @property
    def API_HOST(cls):
        return os.getenv('API_HOST', 'localhost')

    @property
    def API_PORT(cls):
        port = os.getenv('API_PORT', '8080')
        return int(port) if port else 8080

    @property
    def API_SECRET_KEY(cls):
        return os.getenv('API_SECRET_KEY', 'change_this_in_production')

    @property
    def DEBUG_PASSWORD(cls):
        return os.getenv('DEBUG_PASSWORD', 'admin123')

    @property
    def DATABASE_PATH(cls):
        return os.getenv('DATABASE_PATH', get_default_db_path())


class Config(metaclass=ConfigMeta):
    """Bot configuration - reads from environment variables dynamically"""
    pass

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is required in .env file")
        if not cls.DISCORD_APP_ID:
            errors.append("DISCORD_APP_ID is required in .env file")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    @classmethod
    def print_config(cls):
        """Print current configuration (safely)"""
        print("\n" + "=" * 50)
        print("BOT CONFIGURATION")
        print("=" * 50)
        print(f"Discord App ID: {cls.DISCORD_APP_ID}")
        print(f"Discord Token: {'*' * 20} (hidden)")
        print(f"Discord Guild ID: {cls.DISCORD_GUILD_ID or '(not set)'}")
        print(f"Discord Channel ID: {cls.DISCORD_CHANNEL_ID or '(not set)'}")
        print(f"API Host: {cls.API_HOST}")
        print(f"API Port: {cls.API_PORT}")
        print(f"Database Path: {cls.DATABASE_PATH}")
        print("=" * 50 + "\n")

"""
Configuration loader for Discord bot

Loads settings from .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Bot configuration"""

    # Discord settings
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    DISCORD_APP_ID = os.getenv('DISCORD_APP_ID')
    DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')
    DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

    # API settings
    API_HOST = os.getenv('API_HOST', 'localhost')
    API_PORT = int(os.getenv('API_PORT', 8080))
    API_SECRET_KEY = os.getenv('API_SECRET_KEY', 'change_this_in_production')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot/scores.db')

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

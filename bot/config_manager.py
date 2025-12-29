"""
Configuration Manager for Clone Hero Score Bot

Handles loading, saving, and migrating bot configuration with version tracking.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from shared.console import print_success, print_info, print_warning, print_error


class ConfigManager:
    """Manages bot configuration with version tracking and migrations"""

    CONFIG_VERSION = 5  # Current config version for v2.5.3
    BOT_VERSION = "2.5.3"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager

        Args:
            config_path: Path to config file (defaults to AppData/bot_config.json)
        """
        if config_path is None:
            config_path = self.get_default_config_path()

        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._ensure_config_directory()

    @staticmethod
    def get_default_config_path() -> Path:
        """Get default config path in AppData"""
        if sys.platform == 'win32':
            import os
            appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            config_dir = appdata / 'CloneHeroScoreBot'
        else:
            config_dir = Path.home() / '.config' / 'CloneHeroScoreBot'

        return config_dir / 'bot_config.json'

    def _ensure_config_directory(self):
        """Ensure config directory exists"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file, creating default if not exists

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            print_info(f"[Config] No config file found, creating default at {self.config_path}")
            self.config = self._create_default_config()
            self.save()
            return self.config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            # Check if migration needed
            current_version = self.config.get('config_version', 1)
            if current_version < self.CONFIG_VERSION:
                print_warning(f"[Config] Config version {current_version} is outdated, migrating to {self.CONFIG_VERSION}")
                self._migrate_config(current_version)
                self.save()

            print_success(f"[Config] Loaded configuration from {self.config_path}")
            return self.config

        except json.JSONDecodeError as e:
            print_error(f"[Config] Failed to parse config file: {e}")
            print_warning("[Config] Creating backup and using default config")
            self._backup_config()
            self.config = self._create_default_config()
            self.save()
            return self.config
        except Exception as e:
            print_error(f"[Config] Error loading config: {e}")
            print_warning("[Config] Using default config")
            self.config = self._create_default_config()
            return self.config

    def save(self):
        """Save configuration to file"""
        try:
            # Update metadata
            self.config['config_version'] = self.CONFIG_VERSION
            self.config['bot_version'] = self.BOT_VERSION
            self.config['last_updated'] = datetime.utcnow().isoformat() + 'Z'

            # Write to file with pretty formatting
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            print_success(f"[Config] Configuration saved to {self.config_path}")

        except Exception as e:
            print_error(f"[Config] Failed to save config: {e}")
            raise

    def _backup_config(self):
        """Create backup of current config file"""
        if not self.config_path.exists():
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.config_path.parent / f"bot_config_backup_{timestamp}.json"

        try:
            import shutil
            shutil.copy2(self.config_path, backup_path)
            print_info(f"[Config] Backup created: {backup_path}")
        except Exception as e:
            print_warning(f"[Config] Failed to create backup: {e}")

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "config_version": self.CONFIG_VERSION,
            "bot_version": self.BOT_VERSION,
            "last_updated": datetime.utcnow().isoformat() + 'Z',

            "discord": {
                "bot_token": "",
                "app_id": "",
                "guild_id": "",
                "announcement_channel_id": "",
                "command_privacy": {
                    "leaderboard": "public",
                    "mystats": "private",
                    "lookupsong": "public",
                    "recent": "public",
                    "updatesong": "private",
                    "setartist": "private",
                    "missingartists": "private"
                }
            },

            "display": {
                "timezone": "UTC",
                "date_format": "MM/DD/YYYY",
                "time_format": "12-hour",
                "show_timezone_in_embeds": True
            },

            "api": {
                "host": "localhost",
                "port": 8080,
                "debug_password": "admin123",
                "rate_limiting": {
                    "enabled": True,
                    "max_requests_per_minute": 60,
                    "failed_auth_limit": 5
                }
            },

            "logging": {
                "enabled": True,
                "level": "INFO",
                "rotation": {
                    "enabled": True,
                    "max_size_mb": 10,
                    "keep_backups": 5
                }
            },

            "announcements": {
                "record_breaks": {
                    "enabled": True,
                    "min_score_threshold": 0,
                    "ping_previous_holder": True,
                    "embed_color": "#FFD700",
                    "style": "full",
                    "full_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": True,
                        "accuracy": True,
                        "play_count": True,
                        "best_streak": True,
                        "previous_record": True,
                        "improvement": True,
                        "enchor_link": True,
                        "chart_hash": True,
                        "chart_hash_format": "full",
                        "timestamp": True,
                        "footer_show_previous_holder": True,
                        "footer_show_previous_score": True,
                        "footer_show_held_duration": True,
                        "footer_show_set_timestamp": True
                    },
                    "minimalist_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": True,
                        "accuracy": True,
                        "play_count": True,
                        "previous_record": True,
                        "improvement": True,
                        "enchor_link": False,
                        "chart_hash": True,
                        "chart_hash_format": "abbreviated",
                        "timestamp": True,
                        "footer_show_previous_holder": True,
                        "footer_show_previous_score": True,
                        "footer_show_held_duration": True,
                        "footer_show_set_timestamp": True
                    }
                },
                "first_time_scores": {
                    "enabled": True,
                    "style": "full",
                    "embed_color": "#4169E1",
                    "full_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": True,
                        "accuracy": True,
                        "play_count": True,
                        "enchor_link": True,
                        "chart_hash": True,
                        "chart_hash_format": "full",
                        "timestamp": True
                    },
                    "minimalist_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": False,
                        "accuracy": False,
                        "play_count": False,
                        "enchor_link": False,
                        "chart_hash": True,
                        "chart_hash_format": "abbreviated",
                        "timestamp": True
                    }
                },
                "personal_bests": {
                    "enabled": False,
                    "min_improvement_percent": 5.0,
                    "min_improvement_points": 10000,
                    "threshold_mode": "both",
                    "show_server_record_holder": True,
                    "embed_color": "#32CD32",
                    "style": "full",
                    "full_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": True,
                        "accuracy": True,
                        "play_count": True,
                        "previous_best": True,
                        "improvement": True,
                        "server_record_holder": True,
                        "enchor_link": True,
                        "chart_hash": True,
                        "chart_hash_format": "full",
                        "timestamp": True,
                        "footer_show_previous_best": True,
                        "footer_show_improvement": True
                    },
                    "minimalist_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": False,
                        "accuracy": True,
                        "play_count": False,
                        "previous_best": True,
                        "improvement": True,
                        "server_record_holder": True,
                        "enchor_link": False,
                        "chart_hash": True,
                        "chart_hash_format": "abbreviated",
                        "timestamp": True,
                        "footer_show_previous_best": True,
                        "footer_show_improvement": True
                    }
                },
                "formatting": {
                    "include_thumbnail": False,
                    "footer_style": "full"
                }
            },

            "database": {
                "path": "",  # Set by get_default_db_path()
                "backup": {
                    "enabled": True,
                    "frequency": "daily",
                    "time": "03:00",
                    "keep_days": 7,
                    "location": ""  # Set by get_default_backup_path()
                }
            }
        }

    def _migrate_config(self, from_version: int):
        """
        Migrate configuration from old version to current

        Args:
            from_version: Version to migrate from
        """
        print_info(f"[Config] Migrating config from v{from_version} to v{self.CONFIG_VERSION}")

        # Migration v1 -> v2 (example placeholder)
        if from_version < 2:
            self._migrate_v1_to_v2()

        # Migration v2 -> v3 (v2.5.0)
        if from_version < 3:
            self._migrate_v2_to_v3()

        print_success(f"[Config] Migration complete!")

    def _migrate_v1_to_v2(self):
        """Migrate from v1 to v2"""
        # Placeholder for future migrations
        pass

    def _deep_merge_config(self, user_config: dict, default_config: dict) -> dict:
        """
        Deep merge user config with default config, adding missing keys while preserving user values

        Args:
            user_config: User's existing config
            default_config: Default config template

        Returns:
            Merged config with all keys from default but user values where they exist
        """
        merged = default_config.copy()

        for key, value in user_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                merged[key] = self._deep_merge_config(value, merged[key])
            else:
                # Use user's value
                merged[key] = value

        return merged

    def _migrate_v2_to_v3(self):
        """Migrate from v2 to v3 (add v2.5.0 features)"""
        default = self._create_default_config()

        # Add missing sections with defaults
        if 'display' not in self.config:
            self.config['display'] = default['display']

        # Ensure discord section exists before accessing nested keys
        self.config.setdefault('discord', {})

        # Migrate old top-level Discord settings to nested structure
        if 'DISCORD_TOKEN' in self.config and 'bot_token' not in self.config['discord']:
            self.config['discord']['bot_token'] = self.config['DISCORD_TOKEN']

        if 'DISCORD_GUILD_ID' in self.config and 'guild_id' not in self.config['discord']:
            self.config['discord']['guild_id'] = self.config['DISCORD_GUILD_ID']

        if 'DISCORD_CHANNEL_ID' in self.config and 'announcement_channel_id' not in self.config['discord']:
            self.config['discord']['announcement_channel_id'] = self.config['DISCORD_CHANNEL_ID']

        if 'command_privacy' not in self.config['discord']:
            self.config['discord']['command_privacy'] = default['discord']['command_privacy']

        # Ensure announcements section exists before accessing nested keys
        self.config.setdefault('announcements', {})

        # Deep merge each announcement type to ensure all fields are present
        if 'record_breaks' not in self.config['announcements']:
            self.config['announcements']['record_breaks'] = default['announcements']['record_breaks']
        else:
            # Deep merge to add any missing nested fields
            self.config['announcements']['record_breaks'] = self._deep_merge_config(
                self.config['announcements']['record_breaks'],
                default['announcements']['record_breaks']
            )

        if 'first_time_scores' not in self.config['announcements']:
            self.config['announcements']['first_time_scores'] = default['announcements']['first_time_scores']
        else:
            # Deep merge to add any missing nested fields
            self.config['announcements']['first_time_scores'] = self._deep_merge_config(
                self.config['announcements']['first_time_scores'],
                default['announcements']['first_time_scores']
            )

        if 'personal_bests' not in self.config['announcements']:
            self.config['announcements']['personal_bests'] = default['announcements']['personal_bests']
        else:
            # Deep merge to add any missing nested fields
            self.config['announcements']['personal_bests'] = self._deep_merge_config(
                self.config['announcements']['personal_bests'],
                default['announcements']['personal_bests']
            )

        # Remove deprecated global_fields section if it exists (backwards compatibility)
        if 'global_fields' in self.config['announcements']:
            print_info("[Config] Removing deprecated 'global_fields' section (now using per-type minimalist_fields)")
            del self.config['announcements']['global_fields']

        if 'logging' not in self.config:
            self.config['logging'] = default['logging']

        if 'database' not in self.config:
            self.config['database'] = default['database']

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get config value by dot-separated path

        Args:
            key_path: Dot-separated path (e.g., "announcements.record_breaks.enabled")
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set config value by dot-separated path

        Args:
            key_path: Dot-separated path (e.g., "announcements.record_breaks.enabled")
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to parent
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set value
        config[keys[-1]] = value

    def get_command_privacy(self, command_name: str) -> str:
        """
        Get privacy setting for a command

        Args:
            command_name: Command name (without /)

        Returns:
            "public" or "private"
        """
        return self.get(f"discord.command_privacy.{command_name}", "public")

    def is_ephemeral(self, command_name: str) -> bool:
        """
        Check if command should use ephemeral responses

        Args:
            command_name: Command name (without /)

        Returns:
            True if private (ephemeral), False if public
        """
        return self.get_command_privacy(command_name) == "private"

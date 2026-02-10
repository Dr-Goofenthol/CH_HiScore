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

    CONFIG_VERSION = 9  # Current config version for v2.6.6
    BOT_VERSION = "2.6.6"

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

    def load(self, silent: bool = False) -> Dict[str, Any]:
        """
        Load configuration from file, creating default if not exists

        Args:
            silent: If True, suppress success message (used when config already loaded by launcher)

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            if not silent:
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

            if not silent:
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
                    "missingartists": "private",
                    "hardest": "public",
                    "server_status": "public"
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
                "full_combos": {
                    "enabled": True,
                    "announce_regular_fc": True,
                    "announce_first_fc": True,
                    "announce_fc_record_break": True,
                    "announce_retroactive_fcs": True,
                    "embed_color": "#FF0000",
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
                        "chart_intensity": True,
                        "enchor_link": True,
                        "chart_hash": True,
                        "chart_hash_format": "full",
                        "timestamp": True,
                        "footer_show_fc_type": True
                    },
                    "minimalist_fields": {
                        "song_title": True,
                        "artist": True,
                        "difficulty_instrument": True,
                        "score": True,
                        "stars": True,
                        "charter": True,
                        "accuracy": True,
                        "play_count": False,
                        "chart_intensity": True,
                        "enchor_link": False,
                        "chart_hash": True,
                        "chart_hash_format": "abbreviated",
                        "timestamp": True,
                        "footer_show_fc_type": True
                    }
                },
                "accuracy_display": {
                    "record_breaks": {
                        "format": "combined_percentage_first",
                        "show_notes_label": True
                    },
                    "first_time_scores": {
                        "format": "combined_percentage_first",
                        "show_notes_label": True
                    },
                    "personal_bests": {
                        "format": "combined_percentage_first",
                        "show_notes_label": True
                    },
                    "full_combos": {
                        "format": "combined_percentage_first",
                        "show_notes_label": True
                    }
                },
                "formatting": {
                    "include_thumbnail": False,
                    "footer_style": "full"
                },
                "suppress_resync_announcements": True,
                "allow_historical_submissions": True
            },

            "difficulty_tiers": {
                "tier1": {
                    "name": "Chill",
                    "emoji": "🟢",
                    "min_nps": 1.0,
                    "max_nps": 3.0
                },
                "tier2": {
                    "name": "Shred",
                    "emoji": "🟡",
                    "min_nps": 3.0,
                    "max_nps": 5.0
                },
                "tier3": {
                    "name": "Brutal",
                    "emoji": "🟠",
                    "min_nps": 5.0,
                    "max_nps": 6.0
                },
                "tier4": {
                    "name": "Insane",
                    "emoji": "🔴",
                    "min_nps": 6.0,
                    "max_nps": 999.0
                }
            },

            "peak_intensity_tiers": {
                "tier1": {
                    "name": "Calm",
                    "emoji": "🟢",
                    "min_nps": 1.0,
                    "max_nps": 5.0
                },
                "tier2": {
                    "name": "Spicy",
                    "emoji": "🟡",
                    "min_nps": 5.0,
                    "max_nps": 8.0
                },
                "tier3": {
                    "name": "Extreme",
                    "emoji": "🟠",
                    "min_nps": 8.0,
                    "max_nps": 12.0
                },
                "tier4": {
                    "name": "Ridiculous",
                    "emoji": "🔴",
                    "min_nps": 12.0,
                    "max_nps": 999.0
                }
            },

            "hardest_command": {
                "min_notes_filter": 100,
                "default_min_nps": 0.0,
                "default_max_nps": 10.0
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
            },

            "daily_activity_log": {
                "enabled": False,
                "generation_time": "00:00",
                "keep_days": 30
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

        # Migration v5 -> v6 (v2.6.0)
        if from_version < 6:
            self._migrate_v5_to_v6()

        # Migration v6 -> v7 (v2.6.4)
        if from_version < 7:
            self._migrate_v6_to_v7()

        # Migration v7 -> v8 (v2.6.5)
        if from_version < 8:
            self._migrate_v7_to_v8()

        # Migration v8 -> v9 (v2.6.6)
        if from_version < 9:
            self._migrate_v8_to_v9()

        print_success(f"[Config] Migration complete!")

    def _migrate_v1_to_v2(self):
        """Migrate from v1 to v2"""
        # Placeholder for future migrations
        pass

    def _migrate_v5_to_v6(self):
        """Migrate from v5 to v6 (add v2.6.0 features)"""
        print_info("[Config] Adding v2.6.0 features (Full Combo announcements, difficulty tiers, /hardest command)")

        default = self._create_default_config()

        # Add Full Combo announcements config if missing
        if 'announcements' in self.config:
            if 'full_combos' not in self.config['announcements']:
                self.config['announcements']['full_combos'] = default['announcements']['full_combos']
                print_success("[Config] Added Full Combo announcement settings")

            # Add accuracy_display config if missing
            if 'accuracy_display' not in self.config['announcements']:
                self.config['announcements']['accuracy_display'] = default['announcements']['accuracy_display']
                print_success("[Config] Added accuracy/notes display format settings")

            # Add ping_previous_holder and min_score_threshold to record_breaks if missing
            if 'record_breaks' in self.config['announcements']:
                if 'ping_previous_holder' not in self.config['announcements']['record_breaks']:
                    self.config['announcements']['record_breaks']['ping_previous_holder'] = default['announcements']['record_breaks']['ping_previous_holder']
                if 'min_score_threshold' not in self.config['announcements']['record_breaks']:
                    self.config['announcements']['record_breaks']['min_score_threshold'] = default['announcements']['record_breaks']['min_score_threshold']
                print_success("[Config] Added ping_previous_holder and min_score_threshold to record breaks")

        # Add difficulty tiers config if missing
        if 'difficulty_tiers' not in self.config:
            self.config['difficulty_tiers'] = default['difficulty_tiers']
            print_success("[Config] Added difficulty tier settings (Chill/Shred/Brutal/Insane)")

        # Add hardest command config if missing
        if 'hardest_command' not in self.config:
            self.config['hardest_command'] = default['hardest_command']
            print_success("[Config] Added /hardest command settings")
        else:
            # Add default NPS range if missing from existing hardest_command config
            if 'default_min_nps' not in self.config['hardest_command']:
                self.config['hardest_command']['default_min_nps'] = default['hardest_command']['default_min_nps']
            if 'default_max_nps' not in self.config['hardest_command']:
                self.config['hardest_command']['default_max_nps'] = default['hardest_command']['default_max_nps']

        # Add daily_activity_log config if missing
        if 'daily_activity_log' not in self.config:
            self.config['daily_activity_log'] = default['daily_activity_log']
            print_success("[Config] Added daily activity log settings")

        # Add new command privacy settings
        if 'discord' in self.config and 'command_privacy' in self.config['discord']:
            if 'hardest' not in self.config['discord']['command_privacy']:
                self.config['discord']['command_privacy']['hardest'] = 'public'
            if 'server_status' not in self.config['discord']['command_privacy']:
                self.config['discord']['command_privacy']['server_status'] = 'public'
            print_success("[Config] Added command privacy for /hardest and /server_status")

        # Update config version
        self.config['config_version'] = 6
        print_success("[Config] v2.6.0 migration complete - all existing settings preserved!")

    def _migrate_v6_to_v7(self):
        """Migrate from v6 to v7 (add v2.6.4 features)"""
        print_info("[Config] Adding v2.6.4 features (Peak Intensity tiers, chart/peak intensity fields for all announcements)")

        default = self._create_default_config()

        # Add peak intensity tiers config if missing
        if 'peak_intensity_tiers' not in self.config:
            self.config['peak_intensity_tiers'] = default['peak_intensity_tiers']
            print_success("[Config] Added peak intensity tier settings (Calm/Spicy/Extreme/Ridiculous)")

        # Add chart_intensity and peak_intensity fields to all announcement types
        if 'announcements' in self.config:
            for announcement_type in ['record_breaks', 'first_time_scores', 'personal_bests', 'full_combos']:
                if announcement_type in self.config['announcements']:
                    # Add to full_fields if missing
                    if 'full_fields' in self.config['announcements'][announcement_type]:
                        if 'chart_intensity' not in self.config['announcements'][announcement_type]['full_fields']:
                            self.config['announcements'][announcement_type]['full_fields']['chart_intensity'] = True
                        if 'peak_intensity' not in self.config['announcements'][announcement_type]['full_fields']:
                            self.config['announcements'][announcement_type]['full_fields']['peak_intensity'] = True

                    # Add to minimalist_fields if missing
                    if 'minimalist_fields' in self.config['announcements'][announcement_type]:
                        if 'chart_intensity' not in self.config['announcements'][announcement_type]['minimalist_fields']:
                            # Default ON for record_breaks and full_combos, OFF for others
                            default_value = True if announcement_type in ['record_breaks', 'full_combos'] else False
                            self.config['announcements'][announcement_type]['minimalist_fields']['chart_intensity'] = default_value
                        if 'peak_intensity' not in self.config['announcements'][announcement_type]['minimalist_fields']:
                            # Default ON for record_breaks and full_combos, OFF for others
                            default_value = True if announcement_type in ['record_breaks', 'full_combos'] else False
                            self.config['announcements'][announcement_type]['minimalist_fields']['peak_intensity'] = default_value

            print_success("[Config] Added chart intensity and peak intensity fields to all announcement types")

        # Update config version
        self.config['config_version'] = 7
        print_success("[Config] v2.6.4 migration complete - all existing settings preserved!")

    def _migrate_v7_to_v8(self):
        """Migrate from v7 to v8 (add v2.6.5 suppress_resync_announcements setting)"""
        print_info("[Config] Adding v2.6.5 features (suppress resync/reset announcements)")

        if 'announcements' in self.config:
            if 'suppress_resync_announcements' not in self.config['announcements']:
                self.config['announcements']['suppress_resync_announcements'] = True
                print_success("[Config] Added suppress_resync_announcements (default: enabled)")

        self.config['config_version'] = 8
        print_success("[Config] v2.6.5 migration complete - all existing settings preserved!")

    def _migrate_v8_to_v9(self):
        """Migrate from v8 to v9 (add v2.6.6 allow_historical_submissions setting)"""
        print_info("[Config] Adding v2.6.6 features (historical score submissions control)")

        if 'announcements' in self.config:
            if 'allow_historical_submissions' not in self.config['announcements']:
                self.config['announcements']['allow_historical_submissions'] = True
                print_success("[Config] Added allow_historical_submissions (default: enabled - existing behavior preserved)")

        self.config['config_version'] = 9
        print_success("[Config] v2.6.6 migration complete - all existing settings preserved!")

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
            del self.config['DISCORD_TOKEN']  # Remove old key after migration

        if 'DISCORD_APP_ID' in self.config and 'app_id' not in self.config['discord']:
            self.config['discord']['app_id'] = self.config['DISCORD_APP_ID']
            del self.config['DISCORD_APP_ID']

        if 'DISCORD_GUILD_ID' in self.config and 'guild_id' not in self.config['discord']:
            self.config['discord']['guild_id'] = self.config['DISCORD_GUILD_ID']
            del self.config['DISCORD_GUILD_ID']

        if 'DISCORD_CHANNEL_ID' in self.config and 'announcement_channel_id' not in self.config['discord']:
            self.config['discord']['announcement_channel_id'] = self.config['DISCORD_CHANNEL_ID']
            del self.config['DISCORD_CHANNEL_ID']

        if 'command_privacy' not in self.config['discord']:
            self.config['discord']['command_privacy'] = default['discord']['command_privacy']

        # Ensure api section exists before accessing nested keys
        self.config.setdefault('api', {})

        # Migrate old top-level API settings to nested structure
        if 'DEBUG_PASSWORD' in self.config and 'debug_password' not in self.config['api']:
            self.config['api']['debug_password'] = self.config['DEBUG_PASSWORD']
            del self.config['DEBUG_PASSWORD']

        if 'API_PORT' in self.config and 'port' not in self.config['api']:
            self.config['api']['port'] = self.config['API_PORT']
            del self.config['API_PORT']

        # Migrate EXTERNAL_URL (deprecated - clients should use bot URL from pairing)
        # Keep it for backward compatibility but don't migrate to new structure
        if 'EXTERNAL_URL' in self.config:
            print_info("[Config] EXTERNAL_URL is deprecated (clients get URL from pairing)")

        # Ensure api section has all required fields
        if 'host' not in self.config['api']:
            self.config['api']['host'] = default['api']['host']
        if 'rate_limiting' not in self.config['api']:
            self.config['api']['rate_limiting'] = default['api']['rate_limiting']

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

    def verify_config(self) -> Dict[str, Any]:
        """
        Verify config has all required fields by comparing with defaults

        Returns:
            Dictionary with verification results:
            {
                'is_complete': bool,
                'missing_fields': List[str],
                'incomplete_sections': Dict[str, List[str]],
                'total_missing': int
            }
        """
        default = self._create_default_config()
        missing_fields = []
        incomplete_sections = {}

        def check_nested(current_path: str, current_dict: dict, default_dict: dict):
            """Recursively check for missing fields"""
            for key, default_value in default_dict.items():
                current_value = current_dict.get(key)
                field_path = f"{current_path}.{key}" if current_path else key

                if key not in current_dict:
                    # Field is completely missing
                    missing_fields.append(field_path)
                    section = current_path if current_path else "root"
                    if section not in incomplete_sections:
                        incomplete_sections[section] = []
                    incomplete_sections[section].append(key)
                elif isinstance(default_value, dict) and isinstance(current_value, dict):
                    # Recurse into nested dicts
                    check_nested(field_path, current_value, default_value)

        # Check all top-level and nested fields
        check_nested("", self.config, default)

        return {
            'is_complete': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'incomplete_sections': incomplete_sections,
            'total_missing': len(missing_fields)
        }

    def apply_missing_fields(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply missing fields from defaults to current config

        Args:
            dry_run: If True, don't actually modify config, just return what would be added

        Returns:
            Dictionary with results:
            {
                'fields_added': List[str],
                'total_added': int,
                'config_modified': bool
            }
        """
        default = self._create_default_config()
        fields_added = []

        def apply_nested(current_path: str, current_dict: dict, default_dict: dict):
            """Recursively apply missing fields"""
            for key, default_value in default_dict.items():
                field_path = f"{current_path}.{key}" if current_path else key

                if key not in current_dict:
                    # Add missing field
                    if not dry_run:
                        current_dict[key] = default_value
                    fields_added.append(field_path)
                elif isinstance(default_value, dict) and isinstance(current_dict.get(key), dict):
                    # Recurse into nested dicts
                    apply_nested(field_path, current_dict[key], default_value)

        # Apply all missing fields
        apply_nested("", self.config, default)

        return {
            'fields_added': fields_added,
            'total_added': len(fields_added),
            'config_modified': len(fields_added) > 0
        }

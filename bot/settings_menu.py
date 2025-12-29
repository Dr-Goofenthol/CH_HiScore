"""
Interactive Settings Menu for Clone Hero Score Bot

Provides a terminal-based menu system for configuring bot settings.
"""

from typing import Optional, List, Callable
from shared.console import print_success, print_info, print_warning, print_error
from .config_manager import ConfigManager


class SettingsMenu:
    """Interactive settings menu system"""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize settings menu

        Args:
            config_manager: Config manager instance
        """
        self.config = config_manager
        self.running = False
        self.changes_made = False

    def run(self):
        """Run the main settings menu loop"""
        self.running = True
        self.changes_made = False

        print_info("\n" + "=" * 80)
        print_info(" " * 20 + "Clone Hero Score Bot - Settings Menu")
        print_info("=" * 80 + "\n")

        while self.running:
            self._show_main_menu()
            choice = self._get_input("Enter selection: ")

            if choice == "1":
                self._discord_settings_menu()
            elif choice == "2":
                self._timezone_settings_menu()
            elif choice == "3":
                self._api_settings_menu()
            elif choice == "4":
                self._logging_settings_menu()
            elif choice == "5":
                self._announcement_settings_menu()
            elif choice == "6":
                self._database_settings_menu()
            elif choice == "7":
                self._preview_announcements()
            elif choice == "8":
                self._view_current_config()
            elif choice == "9":
                self._reset_to_defaults()
            elif choice.lower() == "s":
                self._save_and_exit()
            elif choice == "0":
                self._exit_without_saving()
            else:
                print_warning("[Menu] Invalid selection. Please try again.")

    def _show_main_menu(self):
        """Display main menu"""
        print("\n" + "=" * 80)
        print(" " * 25 + "Main Menu")
        print("=" * 80)
        print()
        print("  1. Discord Settings")
        print("  2. Timezone & Display Settings")
        print("  3. API Server Settings")
        print("  4. Logging Settings")
        print("  5. Announcement Settings")
        print("  6. Database Settings")
        print("  7. Preview Announcements")
        print("  8. View Current Configuration")
        print("  9. Reset to Defaults")
        print()
        print("  S. Save and Exit")
        print("  0. Exit Without Saving")
        print()

    def _discord_settings_menu(self):
        """Discord settings submenu"""
        while True:
            print("\n" + "=" * 80)
            print(" " * 28 + "Discord Settings")
            print("=" * 80)
            print()
            print("Current Configuration:")
            token = self.config.get("discord.bot_token", "")
            print(f"  Bot Token:            {'*' * 40 if token else '[Not Set]'}")
            print(f"  Guild ID:             {self.config.get('discord.guild_id', '[Not Set]')}")
            print(f"  Announcement Channel: {self.config.get('discord.announcement_channel_id', '[Not Set]')}")
            print()
            print("Command Privacy Settings:")
            privacy = self.config.get("discord.command_privacy", {})
            for cmd, setting in privacy.items():
                print(f"  /{cmd:15s}  [{setting.capitalize()}]")
            print()
            print("Options:")
            print("  1. Set Bot Token")
            print("  2. Set Guild ID")
            print("  3. Set Announcement Channel")
            print("  4. Toggle Command Privacy")
            print("  5. Back to Main Menu")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "1":
                token = self._get_input("Enter Discord bot token: ")
                self.config.set("discord.bot_token", token)
                self.changes_made = True
                print_success("[Settings] Bot token updated")
            elif choice == "2":
                guild_id = self._get_input("Enter Discord guild/server ID: ")
                self.config.set("discord.guild_id", guild_id)
                self.changes_made = True
                print_success("[Settings] Guild ID updated")
            elif choice == "3":
                channel_id = self._get_input("Enter announcement channel ID: ")
                self.config.set("discord.announcement_channel_id", channel_id)
                self.changes_made = True
                print_success("[Settings] Announcement channel updated")
            elif choice == "4":
                self._toggle_command_privacy()
            elif choice == "5":
                break
            else:
                print_warning("[Menu] Invalid selection")

    def _toggle_command_privacy(self):
        """Toggle privacy for a specific command"""
        commands = ["leaderboard", "mystats", "lookupsong", "recent", "updatesong", "setartist", "missingartists"]

        while True:
            print("\n" + "=" * 80)
            print("Toggle Command Privacy")
            print("=" * 80)
            print()
            print("Select command to toggle privacy:")

            for i, cmd in enumerate(commands, 1):
                privacy = self.config.get(f"discord.command_privacy.{cmd}", "public")
                print(f"  {i}. /{cmd:15s}  [{privacy.capitalize()}]")

            print()
            print("  8. Toggle ALL to Public")
            print("  9. Toggle ALL to Private")
            print("  0. Back")
            print()
            print("Note: 'Private' = Only visible to user who ran command (ephemeral)")
            print("      'Public' = Visible to everyone in channel")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "0":
                break
            elif choice == "8":
                for cmd in commands:
                    self.config.set(f"discord.command_privacy.{cmd}", "public")
                self.changes_made = True
                print_success("[Settings] All commands set to Public")
            elif choice == "9":
                for cmd in commands:
                    self.config.set(f"discord.command_privacy.{cmd}", "private")
                self.changes_made = True
                print_success("[Settings] All commands set to Private")
            elif choice.isdigit() and 1 <= int(choice) <= len(commands):
                cmd = commands[int(choice) - 1]
                current = self.config.get(f"discord.command_privacy.{cmd}", "public")
                new_value = "private" if current == "public" else "public"
                self.config.set(f"discord.command_privacy.{cmd}", new_value)
                self.changes_made = True
                print_success(f"[Settings] /{cmd} set to {new_value.capitalize()}")
            else:
                print_warning("[Menu] Invalid selection")

    def _timezone_settings_menu(self):
        """Timezone & display settings submenu"""
        print("\n" + "=" * 80)
        print(" " * 22 + "Timezone & Display Settings")
        print("=" * 80)
        print()
        print("Current Configuration:")
        print(f"  Announcement Timezone:    {self.config.get('display.timezone', 'UTC')}")
        print(f"  Date Format:              {self.config.get('display.date_format', 'MM/DD/YYYY')}")
        print(f"  Time Format:              {self.config.get('display.time_format', '12-hour')}")
        print(f"  Show Timezone in Embeds:  {self.config.get('display.show_timezone_in_embeds', True)}")
        print()
        print("Options:")
        print("  1. Change Timezone")
        print("  2. Toggle Date Format")
        print("  3. Toggle Time Format")
        print("  4. Toggle Timezone Display in Embeds")
        print("  5. Back to Main Menu")
        print()

        choice = self._get_input("Enter selection: ")

        if choice == "1":
            timezone = self._get_input("Enter timezone (e.g., America/New_York, UTC, Europe/London): ")
            self.config.set("display.timezone", timezone)
            self.changes_made = True
            print_success(f"[Settings] Timezone set to {timezone}")
        elif choice == "2":
            formats = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]
            current = self.config.get("display.date_format", "MM/DD/YYYY")
            current_idx = formats.index(current) if current in formats else 0
            new_format = formats[(current_idx + 1) % len(formats)]
            self.config.set("display.date_format", new_format)
            self.changes_made = True
            print_success(f"[Settings] Date format set to {new_format}")
        elif choice == "3":
            current = self.config.get("display.time_format", "12-hour")
            new_format = "24-hour" if current == "12-hour" else "12-hour"
            self.config.set("display.time_format", new_format)
            self.changes_made = True
            print_success(f"[Settings] Time format set to {new_format}")
        elif choice == "4":
            current = self.config.get("display.show_timezone_in_embeds", True)
            self.config.set("display.show_timezone_in_embeds", not current)
            self.changes_made = True
            status = "ON" if not current else "OFF"
            print_success(f"[Settings] Timezone display in embeds: {status}")
        elif choice != "5":
            print_warning("[Menu] Invalid selection")

    def _api_settings_menu(self):
        """API server settings submenu (placeholder)"""
        print_info("[Settings] API settings menu - Coming soon!")
        input("Press Enter to continue...")

    def _logging_settings_menu(self):
        """Logging settings submenu (placeholder)"""
        print_info("[Settings] Logging settings menu - Coming soon!")
        input("Press Enter to continue...")

    def _announcement_settings_menu(self):
        """Announcement settings submenu"""
        while True:
            print("\n" + "=" * 80)
            print(" " * 25 + "Announcement Settings")
            print("=" * 80)
            print()
            print("Current Configuration:")
            print()

            # Record Breaks
            rb_enabled = self.config.get('announcements.record_breaks.enabled', True)
            rb_color = self.config.get('announcements.record_breaks.embed_color', '#FFD700')
            rb_style = self.config.get('announcements.record_breaks.style', 'full')
            print(f"  Record Breaks:")
            print(f"    Enabled: {rb_enabled}")
            print(f"    Color:   {rb_color}")
            print(f"    Style:   {rb_style.capitalize()}")
            print()

            # First-Time Scores
            ft_enabled = self.config.get('announcements.first_time_scores.enabled', True)
            ft_color = self.config.get('announcements.first_time_scores.embed_color', '#4169E1')
            ft_style = self.config.get('announcements.first_time_scores.style', 'full')
            print(f"  First-Time Scores:")
            print(f"    Enabled: {ft_enabled}")
            print(f"    Color:   {ft_color}")
            print(f"    Style:   {ft_style.capitalize()}")
            print()

            # Personal Bests
            pb_enabled = self.config.get('announcements.personal_bests.enabled', False)
            pb_color = self.config.get('announcements.personal_bests.embed_color', '#32CD32')
            pb_style = self.config.get('announcements.personal_bests.style', 'full')
            pb_min_pct = self.config.get('announcements.personal_bests.min_improvement_percent', 5.0)
            pb_min_pts = self.config.get('announcements.personal_bests.min_improvement_points', 10000)
            print(f"  Personal Bests:")
            print(f"    Enabled:        {pb_enabled}")
            print(f"    Color:          {pb_color}")
            print(f"    Style:          {pb_style.capitalize()}")
            print(f"    Min % Improve:  {pb_min_pct}%")
            print(f"    Min Points:     {pb_min_pts}")
            print()

            print("Options:")
            print()
            print("  Record Breaks:")
            print("    1. Toggle Enabled/Disabled")
            print("    2. Set Color")
            print("    3. Toggle Style (Full/Minimalist)")
            print("    4. Customize Full Mode Fields")
            print("    5. Customize Minimalist Mode Fields")
            print()
            print("  First-Time Scores:")
            print("    6. Toggle Enabled/Disabled")
            print("    7. Set Color")
            print("    8. Toggle Style (Full/Minimalist)")
            print("    9. Customize Full Mode Fields")
            print("   10. Customize Minimalist Mode Fields")
            print()
            print("  Personal Bests:")
            print("   11. Toggle Enabled/Disabled")
            print("   12. Set Color")
            print("   13. Toggle Style (Full/Minimalist)")
            print("   14. Set Thresholds")
            print("   15. Customize Full Mode Fields")
            print("   16. Customize Minimalist Mode Fields")
            print()
            print("   17. Reset All Colors to Defaults")
            print("    0. Back to Main Menu")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "0":
                break

            # Record Breaks options
            elif choice == "1":
                current = self.config.get('announcements.record_breaks.enabled', True)
                self.config.set('announcements.record_breaks.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] Record breaks announcements: {status}")
            elif choice == "2":
                color = self._get_input("Enter hex color (e.g., #FFD700 for gold): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.record_breaks.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] Record breaks color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #FFD700)")
            elif choice == "3":
                current = self.config.get('announcements.record_breaks.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.record_breaks.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] Record breaks style set to {new_style.capitalize()}")
            elif choice == "4":
                self._customize_full_fields('record_breaks', 'Record Breaks')
            elif choice == "5":
                self._customize_minimalist_fields('record_breaks', 'Record Breaks')

            # First-Time Scores options
            elif choice == "6":
                current = self.config.get('announcements.first_time_scores.enabled', True)
                self.config.set('announcements.first_time_scores.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] First-time scores announcements: {status}")
            elif choice == "7":
                color = self._get_input("Enter hex color (e.g., #4169E1 for blue): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.first_time_scores.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] First-time scores color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #4169E1)")
            elif choice == "8":
                current = self.config.get('announcements.first_time_scores.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.first_time_scores.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] First-time scores style set to {new_style.capitalize()}")
            elif choice == "9":
                self._customize_full_fields('first_time_scores', 'First-Time Scores')
            elif choice == "10":
                self._customize_minimalist_fields('first_time_scores', 'First-Time Scores')

            # Personal Bests options
            elif choice == "11":
                current = self.config.get('announcements.personal_bests.enabled', False)
                self.config.set('announcements.personal_bests.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] Personal bests announcements: {status}")
            elif choice == "12":
                color = self._get_input("Enter hex color (e.g., #32CD32 for green): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.personal_bests.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] Personal bests color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #32CD32)")
            elif choice == "13":
                current = self.config.get('announcements.personal_bests.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.personal_bests.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] Personal bests style set to {new_style.capitalize()}")
            elif choice == "14":
                print()
                print("Personal Bests Thresholds:")
                print("(Both thresholds must be met for a personal best to be announced)")
                print()
                try:
                    pct = self._get_input("Minimum improvement % (e.g., 5.0): ").strip()
                    pts = self._get_input("Minimum improvement points (e.g., 10000): ").strip()

                    pct_float = float(pct)
                    pts_int = int(pts)

                    if pct_float >= 0 and pts_int >= 0:
                        self.config.set('announcements.personal_bests.min_improvement_percent', pct_float)
                        self.config.set('announcements.personal_bests.min_improvement_points', pts_int)
                        self.changes_made = True
                        print_success(f"[Settings] Personal bests thresholds updated: {pct_float}% and {pts_int} points")
                    else:
                        print_warning("[Settings] Thresholds must be positive numbers")
                except ValueError:
                    print_warning("[Settings] Invalid number format")
            elif choice == "15":
                self._customize_full_fields('personal_bests', 'Personal Bests')
            elif choice == "16":
                self._customize_minimalist_fields('personal_bests', 'Personal Bests')
            elif choice == "17":
                # Reset to default colors
                self.config.set('announcements.record_breaks.embed_color', '#FFD700')
                self.config.set('announcements.first_time_scores.embed_color', '#4169E1')
                self.config.set('announcements.personal_bests.embed_color', '#32CD32')
                self.changes_made = True
                print_success("[Settings] All announcement colors reset to defaults")
            else:
                print_warning("[Menu] Invalid selection")

    def _validate_hex_color(self, color: str) -> bool:
        """Validate hex color format (#RRGGBB)"""
        if not color.startswith('#'):
            return False
        if len(color) != 7:
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False

    def _customize_full_fields(self, announcement_type: str, display_name: str):
        """Customize which fields appear in full mode announcements"""
        # Define available fields for each announcement type
        field_definitions = {
            'record_breaks': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy', True),
                ('play_count', 'Play Count', True),
                ('best_streak', 'Best Streak', True),
                ('previous_record', 'Previous Record', True),
                ('improvement', 'Improvement', True),
                ('enchor_link', 'Enchor.us Link', True),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'full'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_previous_holder', 'Footer: Previous Holder', True),
                ('footer_show_previous_score', 'Footer: Previous Score', True),
                ('footer_show_held_duration', 'Footer: Held Duration', True),
                ('footer_show_set_timestamp', 'Footer: Set Timestamp', True),
            ],
            'first_time_scores': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy', True),
                ('play_count', 'Play Count', True),
                ('enchor_link', 'Enchor.us Link', True),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'full'),
                ('timestamp', 'Timestamp', True),
            ],
            'personal_bests': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy', True),
                ('play_count', 'Play Count', True),
                ('previous_best', 'Previous Best', True),
                ('improvement', 'Improvement', True),
                ('server_record_holder', 'Server Record Holder', True),
                ('enchor_link', 'Enchor.us Link', True),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'full'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_previous_best', 'Footer: Previous Best', True),
                ('footer_show_improvement', 'Footer: Improvement', True),
            ]
        }

        fields = field_definitions.get(announcement_type, [])
        if not fields:
            print_warning(f"[Settings] No fields defined for {announcement_type}")
            input("Press Enter to continue...")
            return

        while True:
            print("\n" + "=" * 80)
            print(f" {display_name} - Full Mode Fields")
            print("=" * 80)
            print()
            print("Configure which fields appear when using full detail style:")
            print()

            # Display current field status
            for idx, (field_key, field_label, default_val) in enumerate(fields, 1):
                config_key = f"announcements.{announcement_type}.full_fields.{field_key}"

                if field_key == 'chart_hash_format':
                    # Special handling for format field
                    current_val = self.config.get(config_key, default_val)
                    print(f"  {idx:2}. {field_label:30} [{current_val}]")
                else:
                    current_val = self.config.get(config_key, default_val)
                    status = "ON" if current_val else "OFF"
                    print(f"  {idx:2}. {field_label:30} [{status}]")

            print()
            print("  99. Reset to Defaults")
            print("   0. Back")
            print()

            choice = self._get_input("Enter field number to toggle: ")

            if choice == "0":
                break
            elif choice == "99":
                # Reset all fields to defaults
                for field_key, field_label, default_val in fields:
                    config_key = f"announcements.{announcement_type}.full_fields.{field_key}"
                    self.config.set(config_key, default_val)
                self.changes_made = True
                print_success(f"[Settings] {display_name} full mode fields reset to defaults")
            else:
                try:
                    field_idx = int(choice) - 1
                    if 0 <= field_idx < len(fields):
                        field_key, field_label, default_val = fields[field_idx]
                        config_key = f"announcements.{announcement_type}.full_fields.{field_key}"

                        if field_key == 'chart_hash_format':
                            # Toggle between abbreviated and full
                            current_val = self.config.get(config_key, default_val)
                            new_val = 'full' if current_val == 'abbreviated' else 'abbreviated'
                            self.config.set(config_key, new_val)
                            self.changes_made = True
                            print_success(f"[Settings] {field_label} set to {new_val}")
                        else:
                            # Toggle boolean
                            current_val = self.config.get(config_key, default_val)
                            self.config.set(config_key, not current_val)
                            self.changes_made = True
                            status = "OFF" if current_val else "ON"
                            print_success(f"[Settings] {field_label} set to {status}")
                    else:
                        print_warning("[Menu] Invalid selection")
                except ValueError:
                    print_warning("[Menu] Invalid selection")

    def _customize_minimalist_fields(self, announcement_type: str, display_name: str):
        """Customize which fields appear in minimalist announcements"""
        # Define available fields for each announcement type
        field_definitions = {
            'record_breaks': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy', True),
                ('play_count', 'Play Count', True),
                ('previous_record', 'Previous Record', True),
                ('improvement', 'Improvement', True),
                ('enchor_link', 'Enchor.us Link', False),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'abbreviated'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_previous_holder', 'Footer: Previous Holder', True),
                ('footer_show_previous_score', 'Footer: Previous Score', True),
                ('footer_show_held_duration', 'Footer: Held Duration', True),
                ('footer_show_set_timestamp', 'Footer: Set Timestamp', True),
            ],
            'first_time_scores': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', False),
                ('accuracy', 'Accuracy', False),
                ('play_count', 'Play Count', False),
                ('enchor_link', 'Enchor.us Link', False),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'abbreviated'),
                ('timestamp', 'Timestamp', True),
            ],
            'personal_bests': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', False),
                ('accuracy', 'Accuracy', True),
                ('play_count', 'Play Count', False),
                ('previous_best', 'Previous Best', True),
                ('improvement', 'Improvement', True),
                ('server_record_holder', 'Server Record Holder', True),
                ('enchor_link', 'Enchor.us Link', False),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'abbreviated'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_previous_best', 'Footer: Previous Best', True),
                ('footer_show_improvement', 'Footer: Improvement', True),
            ]
        }

        fields = field_definitions.get(announcement_type, [])
        if not fields:
            print_warning(f"[Settings] No fields defined for {announcement_type}")
            input("Press Enter to continue...")
            return

        while True:
            print("\n" + "=" * 80)
            print(f" {display_name} - Minimalist Mode Fields")
            print("=" * 80)
            print()
            print("Configure which fields appear when using minimalist style:")
            print()

            # Display current field status
            for idx, (field_key, field_label, default_val) in enumerate(fields, 1):
                config_key = f"announcements.{announcement_type}.minimalist_fields.{field_key}"

                if field_key == 'chart_hash_format':
                    # Special handling for format field
                    current_val = self.config.get(config_key, default_val)
                    print(f"  {idx:2}. {field_label:30} [{current_val}]")
                else:
                    current_val = self.config.get(config_key, default_val)
                    status = "ON" if current_val else "OFF"
                    print(f"  {idx:2}. {field_label:30} [{status}]")

            print()
            print("  99. Reset to Defaults")
            print("   0. Back")
            print()

            choice = self._get_input("Enter field number to toggle: ")

            if choice == "0":
                break
            elif choice == "99":
                # Reset all fields to defaults
                for field_key, field_label, default_val in fields:
                    config_key = f"announcements.{announcement_type}.minimalist_fields.{field_key}"
                    self.config.set(config_key, default_val)
                self.changes_made = True
                print_success(f"[Settings] {display_name} minimalist fields reset to defaults")
            else:
                try:
                    field_idx = int(choice) - 1
                    if 0 <= field_idx < len(fields):
                        field_key, field_label, default_val = fields[field_idx]
                        config_key = f"announcements.{announcement_type}.minimalist_fields.{field_key}"

                        if field_key == 'chart_hash_format':
                            # Toggle between abbreviated and full
                            current_val = self.config.get(config_key, default_val)
                            new_val = 'full' if current_val == 'abbreviated' else 'abbreviated'
                            self.config.set(config_key, new_val)
                            self.changes_made = True
                            print_success(f"[Settings] {field_label} set to {new_val}")
                        else:
                            # Toggle boolean
                            current_val = self.config.get(config_key, default_val)
                            self.config.set(config_key, not current_val)
                            self.changes_made = True
                            status = "OFF" if current_val else "ON"
                            print_success(f"[Settings] {field_label} set to {status}")
                    else:
                        print_warning("[Menu] Invalid selection")
                except ValueError:
                    print_warning("[Menu] Invalid selection")

    def _database_settings_menu(self):
        """Database settings submenu (placeholder)"""
        print_info("[Settings] Database settings menu - Coming soon!")
        input("Press Enter to continue...")

    def _view_current_config(self):
        """View current configuration"""
        print("\n" + "=" * 80)
        print(" " * 25 + "Current Bot Configuration")
        print("=" * 80)
        print()
        print("DISCORD SETTINGS:")
        token = self.config.get("discord.bot_token", "")
        print(f"  Bot Token:                 {'[Set]' if token else '[Not Set]'}")
        print(f"  Guild ID:                  {self.config.get('discord.guild_id', '[Not Set]')}")
        print(f"  Announcement Channel:      {self.config.get('discord.announcement_channel_id', '[Not Set]')}")
        print()
        print("TIMEZONE & DISPLAY:")
        print(f"  Timezone:                  {self.config.get('display.timezone', 'UTC')}")
        print(f"  Date Format:               {self.config.get('display.date_format', 'MM/DD/YYYY')}")
        print(f"  Time Format:               {self.config.get('display.time_format', '12-hour')}")
        print()
        print("LOGGING:")
        print(f"  Enabled:                   {self.config.get('logging.enabled', True)}")
        print(f"  Level:                     {self.config.get('logging.level', 'INFO')}")
        print()
        print("ANNOUNCEMENTS:")
        print(f"  Record Breaks:             {self.config.get('announcements.record_breaks.enabled', True)}")
        print(f"  First-Time Scores:         {self.config.get('announcements.first_time_scores.enabled', True)}")
        print(f"  Personal Bests:            {self.config.get('announcements.personal_bests.enabled', False)}")
        print()
        print(f"CONFIG VERSION:              {self.config.get('config_version', 1)}")
        print(f"BOT VERSION:                 {self.config.get('bot_version', 'Unknown')}")
        print()
        input("Press Enter to continue...")

    def _reset_to_defaults(self):
        """Reset configuration to defaults"""
        print("\n" + "=" * 80)
        print(" " * 28 + "Reset to Defaults")
        print("=" * 80)
        print()
        print("WARNING: This will reset ALL settings to default values!")
        print()
        print("The following will be reset:")
        print("  - All command privacy settings to defaults")
        print("  - Timezone to UTC")
        print("  - Date/time formats to ISO standard")
        print("  - Log level to INFO")
        print("  - Announcement settings to defaults")
        print()
        print("The following will NOT be changed:")
        print("  - Discord bot token")
        print("  - Guild ID")
        print("  - Announcement channel ID")
        print("  - Debug password")
        print()

        confirm = self._get_input("Are you sure you want to reset to defaults? (yes/no): ")

        if confirm.lower() == "yes":
            # Save Discord credentials
            token = self.config.get("discord.bot_token")
            guild_id = self.config.get("discord.guild_id")
            channel_id = self.config.get("discord.announcement_channel_id")
            debug_password = self.config.get("api.debug_password")

            # Reset to defaults
            self.config.config = self.config._create_default_config()

            # Restore Discord credentials
            if token:
                self.config.set("discord.bot_token", token)
            if guild_id:
                self.config.set("discord.guild_id", guild_id)
            if channel_id:
                self.config.set("discord.announcement_channel_id", channel_id)
            if debug_password:
                self.config.set("api.debug_password", debug_password)

            self.changes_made = True
            print_success("[Settings] Configuration reset to defaults")
        else:
            print_info("[Settings] Reset cancelled")

        input("Press Enter to continue...")

    def _save_and_exit(self):
        """Save changes and exit"""
        if self.changes_made:
            print_info("\n[Settings] Saving configuration...")
            self.config.save()
            print_success("[Settings] Configuration saved successfully!")
        else:
            print_info("\n[Settings] No changes to save")

        self.running = False

    def _exit_without_saving(self):
        """Exit without saving changes"""
        if self.changes_made:
            confirm = self._get_input("\nYou have unsaved changes. Exit without saving? (yes/no): ")
            if confirm.lower() == "yes":
                print_warning("[Settings] Exiting without saving changes")
                self.running = False
            else:
                print_info("[Settings] Returning to menu")
        else:
            print_info("[Settings] Exiting settings menu")
            self.running = False

    def _preview_announcements(self):
        """Show preview of Discord announcements"""
        from .preview_generator import show_preview_menu
        show_preview_menu(self.config)

    @staticmethod
    def _get_input(prompt: str) -> str:
        """Get user input with prompt"""
        try:
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ""

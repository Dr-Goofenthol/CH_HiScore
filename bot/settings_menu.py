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
                self._server_admin_settings_menu()
            elif choice == "8":
                self._v260_features_menu()
            elif choice == "9":
                self._preview_announcements()
            elif choice == "10":
                self._view_current_config()
            elif choice == "11":
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
        print("  7. Server Admin Settings")
        print("  8. Chart Intensity & Rankings")
        print("  9. Preview Announcements")
        print(" 10. View Current Configuration")
        print(" 11. Reset to Defaults")
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
            # Display all commands in consistent order
            all_commands = ["leaderboard", "mystats", "lookupsong", "recent", "updatesong", "setartist", "missingartists", "hardest", "server_status"]
            for cmd in all_commands:
                setting = self.config.get(f"discord.command_privacy.{cmd}", "public")
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
        commands = ["leaderboard", "mystats", "lookupsong", "recent", "updatesong", "setartist", "missingartists", "hardest", "server_status"]

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
            print(" 10. Toggle ALL to Public")
            print(" 11. Toggle ALL to Private")
            print("  0. Back")
            print()
            print("Note: 'Private' = Only visible to user who ran command (ephemeral)")
            print("      'Public' = Visible to everyone in channel")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "0":
                break
            elif choice == "10":
                for cmd in commands:
                    self.config.set(f"discord.command_privacy.{cmd}", "public")
                self.changes_made = True
                print_success("[Settings] All commands set to Public")
            elif choice == "11":
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

    def _server_admin_settings_menu(self):
        """Server admin settings submenu"""
        while True:
            print("\n" + "=" * 80)
            print(" " * 25 + "Server Admin Settings")
            print("=" * 80)
            print()
            print("Current Configuration:")
            print()

            # Daily Activity Log
            dal_enabled = self.config.get('daily_activity_log.enabled', False)
            dal_time = self.config.get('daily_activity_log.generation_time', '00:00')
            dal_keep_days = self.config.get('daily_activity_log.keep_days', 30)
            print(f"  Daily Activity Log:")
            print(f"    Enabled:        {dal_enabled}")
            print(f"    Generation Time: {dal_time} (local time)")
            print(f"    Keep Days:      {dal_keep_days}")
            print()

            print("Options:")
            print()
            print("  1. Toggle Daily Activity Log (Enabled/Disabled)")
            print("  2. Set Generation Time")
            print("  3. Set Number of Days to Keep Logs")
            print()
            print("  0. Back to Main Menu")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "0":
                break
            elif choice == "1":
                current = self.config.get('daily_activity_log.enabled', False)
                self.config.set('daily_activity_log.enabled', not current)
                self.changes_made = True
                status = "Enabled" if not current else "Disabled"
                print_success(f"[Settings] Daily activity log: {status}")
                if not current:
                    print_info("[Info] Activity logs will be generated at midnight and saved to logs/activity_YYYY-MM-DD.txt")
            elif choice == "2":
                time_str = self._get_input("Enter generation time in HH:MM format (e.g., 00:00 for midnight): ").strip()
                # Basic validation
                if len(time_str) == 5 and time_str[2] == ':':
                    try:
                        hour, minute = map(int, time_str.split(':'))
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            self.config.set('daily_activity_log.generation_time', time_str)
                            self.changes_made = True
                            print_success(f"[Settings] Generation time set to {time_str}")
                        else:
                            print_warning("[Settings] Invalid time. Hour must be 0-23, minute must be 0-59")
                    except Exception:
                        print_warning("[Settings] Invalid time format. Use HH:MM (e.g., 00:00)")
                else:
                    print_warning("[Settings] Invalid time format. Use HH:MM (e.g., 00:00)")
            elif choice == "3":
                days_str = self._get_input("Enter number of days to keep logs (default: 30): ").strip()
                if days_str.isdigit():
                    days = int(days_str)
                    if days > 0:
                        self.config.set('daily_activity_log.keep_days', days)
                        self.changes_made = True
                        print_success(f"[Settings] Logs will be kept for {days} days")
                    else:
                        print_warning("[Settings] Days must be greater than 0")
                else:
                    print_warning("[Settings] Invalid number")
            else:
                print_warning("[Settings] Invalid selection")

    def _v260_features_menu(self):
        """Chart Intensity & Rankings settings submenu"""
        while True:
            print("\n" + "=" * 80)
            print(" " * 18 + "Chart Intensity & Rankings Settings")
            print("=" * 80)
            print()
            print("Current Configuration:")
            print()

            # Difficulty Tiers
            print("  Difficulty Tiers (for Chart Intensity badges):")
            for tier_key in ['tier1', 'tier2', 'tier3', 'tier4']:
                tier = self.config.get(f'difficulty_tiers.{tier_key}', {})
                name = tier.get('name', '')
                emoji = tier.get('emoji', '')
                min_nps = tier.get('min_nps', 0)
                max_nps = tier.get('max_nps', 0)
                print(f"    {tier_key.upper()}: {emoji} {name:10s}  ({min_nps:.1f} - {max_nps:.1f} NPS)")
            print()

            # /hardest command settings
            min_notes = self.config.get('hardest_command.min_notes_filter', 100)
            default_min_nps = self.config.get('hardest_command.default_min_nps', 0.0)
            default_max_nps = self.config.get('hardest_command.default_max_nps', 10.0)
            print(f"  /hardest Command:")
            print(f"    Minimum Notes Filter: {min_notes}")
            print(f"    Default NPS Range:    {default_min_nps:.1f} - {default_max_nps:.1f}")
            print()

            print("Options:")
            print()
            print("  Difficulty Tiers:")
            print("    1. Edit Tier 1 (Chill)")
            print("    2. Edit Tier 2 (Shred)")
            print("    3. Edit Tier 3 (Brutal)")
            print("    4. Edit Tier 4 (Insane)")
            print("    5. Reset All Tiers to Defaults")
            print()
            print("  /hardest Command:")
            print("    6. Set Minimum Notes Filter")
            print("    7. Set Default Min NPS")
            print("    8. Set Default Max NPS")
            print()
            print("    0. Back to Main Menu")
            print()

            choice = self._get_input("Enter selection: ")

            if choice == "0":
                break
            elif choice in ["1", "2", "3", "4"]:
                tier_num = int(choice)
                tier_key = f"tier{tier_num}"
                self._edit_difficulty_tier(tier_key)
            elif choice == "5":
                # Reset to defaults
                default = self._create_default_tiers()
                self.config.config['difficulty_tiers'] = default
                self.changes_made = True
                print_success("[Settings] Difficulty tiers reset to defaults (Chill/Shred/Brutal/Insane)")
            elif choice == "6":
                min_notes_str = self._get_input("Enter minimum notes filter (default: 100): ").strip()
                if min_notes_str.isdigit():
                    min_notes = int(min_notes_str)
                    if min_notes > 0:
                        self.config.set('hardest_command.min_notes_filter', min_notes)
                        self.changes_made = True
                        print_success(f"[Settings] Minimum notes filter set to {min_notes}")
                    else:
                        print_warning("[Settings] Minimum notes must be greater than 0")
                else:
                    print_warning("[Settings] Invalid number")
            elif choice == "7":
                min_nps_str = self._get_input("Enter default minimum NPS (default: 0.0): ").strip()
                try:
                    min_nps = float(min_nps_str)
                    if min_nps >= 0:
                        self.config.set('hardest_command.default_min_nps', min_nps)
                        self.changes_made = True
                        print_success(f"[Settings] Default minimum NPS set to {min_nps:.1f}")
                    else:
                        print_warning("[Settings] Minimum NPS must be non-negative")
                except ValueError:
                    print_warning("[Settings] Invalid number format")
            elif choice == "8":
                max_nps_str = self._get_input("Enter default maximum NPS (default: 10.0): ").strip()
                try:
                    max_nps = float(max_nps_str)
                    if max_nps > 0:
                        # Validate against current min_nps
                        current_min = self.config.get('hardest_command.default_min_nps', 0.0)
                        if max_nps > current_min:
                            self.config.set('hardest_command.default_max_nps', max_nps)
                            self.changes_made = True
                            print_success(f"[Settings] Default maximum NPS set to {max_nps:.1f}")
                        else:
                            print_warning(f"[Settings] Maximum NPS must be greater than minimum NPS ({current_min:.1f})")
                    else:
                        print_warning("[Settings] Maximum NPS must be greater than 0")
                except ValueError:
                    print_warning("[Settings] Invalid number format")
            else:
                print_warning("[Settings] Invalid selection")

    def _edit_difficulty_tier(self, tier_key: str):
        """Edit a specific difficulty tier"""
        print("\n" + "=" * 80)
        print(f" Editing Difficulty Tier: {tier_key.upper()}")
        print("=" * 80)
        print()

        current_tier = self.config.get(f'difficulty_tiers.{tier_key}', {})
        current_name = current_tier.get('name', '')
        current_emoji = current_tier.get('emoji', '')
        current_min = current_tier.get('min_nps', 0)
        current_max = current_tier.get('max_nps', 0)

        print(f"Current: {current_emoji} {current_name} ({current_min:.1f} - {current_max:.1f} NPS)")
        print()
        print("Enter new values (press Enter to keep current):")
        print()

        # Get new values
        new_name = self._get_input(f"Tier name [{current_name}]: ").strip()
        if not new_name:
            new_name = current_name

        new_emoji = self._get_input(f"Emoji [{current_emoji}]: ").strip()
        if not new_emoji:
            new_emoji = current_emoji

        min_nps_str = self._get_input(f"Minimum NPS [{current_min}]: ").strip()
        try:
            new_min = float(min_nps_str) if min_nps_str else current_min
        except ValueError:
            print_warning("[Settings] Invalid NPS value, keeping current")
            new_min = current_min

        max_nps_str = self._get_input(f"Maximum NPS [{current_max}]: ").strip()
        try:
            new_max = float(max_nps_str) if max_nps_str else current_max
        except ValueError:
            print_warning("[Settings] Invalid NPS value, keeping current")
            new_max = current_max

        # Validate NPS range
        if new_min >= new_max:
            print_warning("[Settings] Minimum NPS must be less than maximum NPS. Changes not saved.")
            input("Press Enter to continue...")
            return

        # Update config
        self.config.set(f'difficulty_tiers.{tier_key}.name', new_name)
        self.config.set(f'difficulty_tiers.{tier_key}.emoji', new_emoji)
        self.config.set(f'difficulty_tiers.{tier_key}.min_nps', new_min)
        self.config.set(f'difficulty_tiers.{tier_key}.max_nps', new_max)
        self.changes_made = True

        print()
        print_success(f"[Settings] {tier_key.upper()} updated: {new_emoji} {new_name} ({new_min:.1f} - {new_max:.1f} NPS)")
        input("Press Enter to continue...")

    def _create_default_tiers(self):
        """Create default difficulty tiers"""
        return {
            "tier1": {"name": "Chill", "emoji": "🟢", "min_nps": 1.0, "max_nps": 3.0},
            "tier2": {"name": "Shred", "emoji": "🟡", "min_nps": 3.0, "max_nps": 5.0},
            "tier3": {"name": "Brutal", "emoji": "🟠", "min_nps": 5.0, "max_nps": 6.0},
            "tier4": {"name": "Insane", "emoji": "🔴", "min_nps": 6.0, "max_nps": 999.0}
        }

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
            rb_ping_prev = self.config.get('announcements.record_breaks.ping_previous_holder', True)
            rb_min_score = self.config.get('announcements.record_breaks.min_score_threshold', 0)
            print(f"  Record Breaks:")
            print(f"    Enabled:             {rb_enabled}")
            print(f"    Color:               {rb_color}")
            print(f"    Style:               {rb_style.capitalize()}")
            print(f"    Ping Previous:       {rb_ping_prev}")
            print(f"    Min Score Threshold: {rb_min_score:,}")
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

            # Full Combos (v2.6.0)
            fc_enabled = self.config.get('announcements.full_combos.enabled', True)
            fc_color = self.config.get('announcements.full_combos.embed_color', '#FF0000')
            fc_style = self.config.get('announcements.full_combos.style', 'full')
            fc_regular = self.config.get('announcements.full_combos.announce_regular_fc', True)
            fc_first = self.config.get('announcements.full_combos.announce_first_fc', True)
            fc_record = self.config.get('announcements.full_combos.announce_fc_record_break', True)
            fc_retro = self.config.get('announcements.full_combos.announce_retroactive_fcs', True)
            print(f"  Full Combos (v2.6.0):")
            print(f"    Enabled:           {fc_enabled}")
            print(f"    Color:             {fc_color}")
            print(f"    Style:             {fc_style.capitalize()}")
            print(f"    Announce Regular:  {fc_regular}")
            print(f"    Announce First:    {fc_first}")
            print(f"    Announce Records:  {fc_record}")
            print(f"    Retroactive:       {fc_retro}")
            print()

            # Accuracy & Notes Display (v2.6.0)
            rb_format = self.config.get('announcements.accuracy_display.record_breaks.format', 'combined_percentage_first')
            rb_notes_label = self.config.get('announcements.accuracy_display.record_breaks.show_notes_label', True)
            ft_format = self.config.get('announcements.accuracy_display.first_time_scores.format', 'combined_percentage_first')
            ft_notes_label = self.config.get('announcements.accuracy_display.first_time_scores.show_notes_label', True)
            pb_format = self.config.get('announcements.accuracy_display.personal_bests.format', 'combined_percentage_first')
            pb_notes_label = self.config.get('announcements.accuracy_display.personal_bests.show_notes_label', True)
            fc_format = self.config.get('announcements.accuracy_display.full_combos.format', 'combined_percentage_first')
            fc_notes_label = self.config.get('announcements.accuracy_display.full_combos.show_notes_label', True)

            # Format display names
            format_names = {
                'percentage_only': 'Percentage Only',
                'notes_only': 'Notes Only',
                'combined_percentage_first': 'Combined (% First)',
                'combined_notes_first': 'Combined (Notes First)',
                'separate_fields': 'Separate Fields'
            }

            print(f"  Accuracy & Notes Display (v2.6.0):")
            print(f"    Record Breaks:     {format_names.get(rb_format, rb_format)} | Notes Label: {rb_notes_label}")
            print(f"    First-Time:        {format_names.get(ft_format, ft_format)} | Notes Label: {ft_notes_label}")
            print(f"    Personal Bests:    {format_names.get(pb_format, pb_format)} | Notes Label: {pb_notes_label}")
            print(f"    Full Combos:       {format_names.get(fc_format, fc_format)} | Notes Label: {fc_notes_label}")
            print()

            print("Options:")
            print()
            print("  Record Breaks:")
            print("    1. Toggle Enabled/Disabled")
            print("    2. Set Color")
            print("    3. Toggle Style (Full/Minimalist)")
            print("    4. Toggle Ping Previous Holder")
            print("    5. Set Min Score Threshold")
            print("    6. Customize Full Mode Fields")
            print("    7. Customize Minimalist Mode Fields")
            print()
            print("  First-Time Scores:")
            print("    8. Toggle Enabled/Disabled")
            print("    9. Set Color")
            print("   10. Toggle Style (Full/Minimalist)")
            print("   11. Customize Full Mode Fields")
            print("   12. Customize Minimalist Mode Fields")
            print()
            print("  Personal Bests:")
            print("   13. Toggle Enabled/Disabled")
            print("   14. Set Color")
            print("   15. Toggle Style (Full/Minimalist)")
            print("   16. Set Thresholds")
            print("   17. Customize Full Mode Fields")
            print("   18. Customize Minimalist Mode Fields")
            print()
            print("  Full Combos (v2.6.0):")
            print("   20. Toggle Enabled/Disabled")
            print("   21. Set Color")
            print("   22. Toggle Style (Full/Minimalist)")
            print("   23. Toggle Announce Regular FCs")
            print("   24. Toggle Announce First FCs")
            print("   25. Toggle Announce FC Record Breaks")
            print("   26. Toggle Retroactive FC Announcements")
            print("   27. Customize Full Mode Fields")
            print("   28. Customize Minimalist Mode Fields")
            print()
            print("  Accuracy & Notes Display (v2.6.0):")
            print("   29. Set Accuracy/Notes Display Format (per announcement type)")
            print("   30. Toggle Notes Label Display (per announcement type)")
            print()
            print("   19. Reset All Colors to Defaults")
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
                current = self.config.get('announcements.record_breaks.ping_previous_holder', True)
                self.config.set('announcements.record_breaks.ping_previous_holder', not current)
                self.changes_made = True
                status = "ON" if not current else "OFF"
                print_success(f"[Settings] Ping previous holder: {status}")
            elif choice == "5":
                threshold_str = self._get_input("Enter minimum score threshold (0 for no minimum): ").strip()
                if threshold_str.isdigit():
                    threshold = int(threshold_str)
                    if threshold >= 0:
                        self.config.set('announcements.record_breaks.min_score_threshold', threshold)
                        self.changes_made = True
                        print_success(f"[Settings] Min score threshold set to {threshold:,}")
                    else:
                        print_warning("[Settings] Threshold must be non-negative")
                else:
                    print_warning("[Settings] Invalid number")
            elif choice == "6":
                self._customize_full_fields('record_breaks', 'Record Breaks')
            elif choice == "7":
                self._customize_minimalist_fields('record_breaks', 'Record Breaks')

            # First-Time Scores options
            elif choice == "8":
                current = self.config.get('announcements.first_time_scores.enabled', True)
                self.config.set('announcements.first_time_scores.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] First-time scores announcements: {status}")
            elif choice == "9":
                color = self._get_input("Enter hex color (e.g., #4169E1 for blue): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.first_time_scores.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] First-time scores color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #4169E1)")
            elif choice == "10":
                current = self.config.get('announcements.first_time_scores.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.first_time_scores.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] First-time scores style set to {new_style.capitalize()}")
            elif choice == "11":
                self._customize_full_fields('first_time_scores', 'First-Time Scores')
            elif choice == "12":
                self._customize_minimalist_fields('first_time_scores', 'First-Time Scores')

            # Personal Bests options
            elif choice == "13":
                current = self.config.get('announcements.personal_bests.enabled', False)
                self.config.set('announcements.personal_bests.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] Personal bests announcements: {status}")
            elif choice == "14":
                color = self._get_input("Enter hex color (e.g., #32CD32 for green): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.personal_bests.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] Personal bests color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #32CD32)")
            elif choice == "15":
                current = self.config.get('announcements.personal_bests.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.personal_bests.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] Personal bests style set to {new_style.capitalize()}")
            elif choice == "16":
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
            elif choice == "17":
                self._customize_full_fields('personal_bests', 'Personal Bests')
            elif choice == "18":
                self._customize_minimalist_fields('personal_bests', 'Personal Bests')

            # Full Combos options (v2.6.0)
            elif choice == "20":
                current = self.config.get('announcements.full_combos.enabled', True)
                self.config.set('announcements.full_combos.enabled', not current)
                self.changes_made = True
                status = "Disabled" if current else "Enabled"
                print_success(f"[Settings] Full Combo announcements: {status}")
            elif choice == "21":
                color = self._get_input("Enter hex color (e.g., #FF0000 for red): ").strip()
                if self._validate_hex_color(color):
                    self.config.set('announcements.full_combos.embed_color', color)
                    self.changes_made = True
                    print_success(f"[Settings] Full Combo color set to {color}")
                else:
                    print_warning("[Settings] Invalid hex color format. Use #RRGGBB (e.g., #FF0000)")
            elif choice == "22":
                current = self.config.get('announcements.full_combos.style', 'full')
                new_style = 'minimalist' if current == 'full' else 'full'
                self.config.set('announcements.full_combos.style', new_style)
                self.changes_made = True
                print_success(f"[Settings] Full Combo style set to {new_style.capitalize()}")
            elif choice == "23":
                current = self.config.get('announcements.full_combos.announce_regular_fc', True)
                self.config.set('announcements.full_combos.announce_regular_fc', not current)
                self.changes_made = True
                status = "ON" if not current else "OFF"
                print_success(f"[Settings] Announce regular FCs: {status}")
            elif choice == "24":
                current = self.config.get('announcements.full_combos.announce_first_fc', True)
                self.config.set('announcements.full_combos.announce_first_fc', not current)
                self.changes_made = True
                status = "ON" if not current else "OFF"
                print_success(f"[Settings] Announce first FCs on chart: {status}")
            elif choice == "25":
                current = self.config.get('announcements.full_combos.announce_fc_record_break', True)
                self.config.set('announcements.full_combos.announce_fc_record_break', not current)
                self.changes_made = True
                status = "ON" if not current else "OFF"
                print_success(f"[Settings] Announce FC record breaks: {status}")
            elif choice == "26":
                current = self.config.get('announcements.full_combos.announce_retroactive_fcs', True)
                self.config.set('announcements.full_combos.announce_retroactive_fcs', not current)
                self.changes_made = True
                status = "ON" if not current else "OFF"
                print_success(f"[Settings] Retroactive FC announcements: {status}")
                if not current:
                    print_info("[Info] Historical FCs will be announced when running 'Scan Historical FCs' from bot menu")
            elif choice == "27":
                self._customize_full_fields('full_combos', 'Full Combos')
            elif choice == "28":
                self._customize_minimalist_fields('full_combos', 'Full Combos')

            # Accuracy & Notes Display options (v2.6.0)
            elif choice == "29":
                self._set_accuracy_display_format()
            elif choice == "30":
                self._toggle_notes_label()

            elif choice == "19":
                # Reset to default colors
                self.config.set('announcements.record_breaks.embed_color', '#FFD700')
                self.config.set('announcements.first_time_scores.embed_color', '#4169E1')
                self.config.set('announcements.personal_bests.embed_color', '#32CD32')
                self.config.set('announcements.full_combos.embed_color', '#FF0000')
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
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
            ],
            'full_combos': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
                ('play_count', 'Play Count', True),
                ('chart_intensity', 'Chart Intensity (NPS)', True),
                ('enchor_link', 'Enchor.us Link', True),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'full'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_fc_type', 'Footer: FC Type', True),
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', False),
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
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
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
            ],
            'full_combos': [
                ('song_title', 'Song Title', True),
                ('artist', 'Artist', True),
                ('difficulty_instrument', 'Difficulty/Instrument', True),
                ('score', 'Score', True),
                ('stars', 'Stars', True),
                ('charter', 'Charter', True),
                ('accuracy', 'Accuracy & Notes Display (format via option 27)', True),
                ('play_count', 'Play Count', False),
                ('chart_intensity', 'Chart Intensity (NPS)', True),
                ('enchor_link', 'Enchor.us Link', False),
                ('chart_hash', 'Chart Hash', True),
                ('chart_hash_format', 'Hash Format (abbreviated/full)', 'abbreviated'),
                ('timestamp', 'Timestamp', True),
                ('footer_show_fc_type', 'Footer: FC Type', True),
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

    def _set_accuracy_display_format(self):
        """Set accuracy/notes display format for each announcement type"""
        format_options = {
            '1': ('percentage_only', 'Percentage Only (e.g., "98.5%")'),
            '2': ('notes_only', 'Notes Only (e.g., "3665/3722")'),
            '3': ('combined_percentage_first', 'Combined % First (e.g., "98.5% (3665/3722)")'),
            '4': ('combined_notes_first', 'Combined Notes First (e.g., "3665/3722 (98.5%)")'),
            '5': ('separate_fields', 'Separate Fields (Accuracy: 98.5% | Notes: 3665/3722)')
        }

        announcement_types = {
            '1': ('record_breaks', 'Record Breaks'),
            '2': ('first_time_scores', 'First-Time Scores'),
            '3': ('personal_bests', 'Personal Bests'),
            '4': ('full_combos', 'Full Combos'),
            '5': ('all', 'All Announcement Types')
        }

        while True:
            print("\n" + "=" * 80)
            print(" " * 20 + "Set Accuracy/Notes Display Format")
            print("=" * 80)
            print()
            print("Select announcement type:")
            for key, (_, display_name) in announcement_types.items():
                print(f"  {key}. {display_name}")
            print("  0. Back")
            print()

            type_choice = self._get_input("Enter selection: ")

            if type_choice == "0":
                break

            if type_choice not in announcement_types:
                print_warning("[Menu] Invalid selection")
                continue

            type_key, type_name = announcement_types[type_choice]

            # Show format options
            print()
            print(f"Select format for {type_name}:")
            for key, (_, description) in format_options.items():
                print(f"  {key}. {description}")
            print()

            format_choice = self._get_input("Enter selection: ")

            if format_choice not in format_options:
                print_warning("[Menu] Invalid selection")
                continue

            format_key, format_description = format_options[format_choice]

            # Apply to selected type(s)
            if type_key == 'all':
                for ann_type in ['record_breaks', 'first_time_scores', 'personal_bests', 'full_combos']:
                    self.config.set(f'announcements.accuracy_display.{ann_type}.format', format_key)
                self.changes_made = True
                print_success(f"[Settings] Format set to '{format_description}' for all announcement types")
            else:
                self.config.set(f'announcements.accuracy_display.{type_key}.format', format_key)
                self.changes_made = True
                print_success(f"[Settings] Format for {type_name} set to '{format_description}'")

            input("\nPress Enter to continue...")

    def _toggle_notes_label(self):
        """Toggle notes label display for each announcement type"""
        announcement_types = {
            '1': ('record_breaks', 'Record Breaks'),
            '2': ('first_time_scores', 'First-Time Scores'),
            '3': ('personal_bests', 'Personal Bests'),
            '4': ('full_combos', 'Full Combos'),
            '5': ('all', 'All Announcement Types')
        }

        while True:
            print("\n" + "=" * 80)
            print(" " * 20 + "Toggle Notes Label Display")
            print("=" * 80)
            print()
            print("Notes label shows 'Notes:' prefix in formats that display note counts.")
            print("Example with label: 'Notes: 3665/3722'")
            print("Example without:    '3665/3722'")
            print()
            print("Select announcement type:")
            for key, (type_key, display_name) in announcement_types.items():
                if type_key != 'all':
                    current = self.config.get(f'announcements.accuracy_display.{type_key}.show_notes_label', True)
                    status = "ON" if current else "OFF"
                    print(f"  {key}. {display_name} (Currently: {status})")
                else:
                    print(f"  {key}. {display_name}")
            print("  0. Back")
            print()

            type_choice = self._get_input("Enter selection: ")

            if type_choice == "0":
                break

            if type_choice not in announcement_types:
                print_warning("[Menu] Invalid selection")
                continue

            type_key, type_name = announcement_types[type_choice]

            # Apply to selected type(s)
            if type_key == 'all':
                # Toggle all to the opposite of record_breaks current state
                current = self.config.get('announcements.accuracy_display.record_breaks.show_notes_label', True)
                new_value = not current
                for ann_type in ['record_breaks', 'first_time_scores', 'personal_bests', 'full_combos']:
                    self.config.set(f'announcements.accuracy_display.{ann_type}.show_notes_label', new_value)
                self.changes_made = True
                status = "ON" if new_value else "OFF"
                print_success(f"[Settings] Notes label set to {status} for all announcement types")
            else:
                current = self.config.get(f'announcements.accuracy_display.{type_key}.show_notes_label', True)
                new_value = not current
                self.config.set(f'announcements.accuracy_display.{type_key}.show_notes_label', new_value)
                self.changes_made = True
                status = "ON" if new_value else "OFF"
                print_success(f"[Settings] Notes label for {type_name} set to {status}")

            input("\nPress Enter to continue...")

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

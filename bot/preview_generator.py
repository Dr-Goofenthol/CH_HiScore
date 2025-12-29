"""
Terminal Preview Generator for Discord Announcements

Generates ASCII art previews of how Discord announcements will appear.
"""

from typing import Dict, Any


def generate_announcement_preview(announcement_type: str = "record_break", include_fields: Dict[str, bool] = None, config_manager = None, use_minimalist: bool = False) -> str:
    """
    Generate ASCII art preview of a Discord announcement

    Args:
        announcement_type: Type of announcement ("record_break", "first_time", "personal_best")
        include_fields: Dict of field names to boolean (which fields to include) - if None, reads from config
        config_manager: ConfigManager instance to read current settings
        use_minimalist: Whether to use minimalist mode (only if config_manager provided)

    Returns:
        ASCII art preview string
    """
    # Read from config if provided
    if config_manager is not None and include_fields is None:
        type_map = {
            "record_break": "record_breaks",
            "first_time": "first_time_scores",
            "personal_best": "personal_bests"
        }
        config_type = type_map.get(announcement_type, "first_time_scores")

        # Check if should use minimalist based on style setting
        if not use_minimalist:
            style = config_manager.get(f"announcements.{config_type}.style", "full")
            use_minimalist = (style == "minimalist")

        # Read fields from config based on mode
        if use_minimalist:
            include_fields = config_manager.get(f"announcements.{config_type}.minimalist_fields", {})
        else:
            # Full mode - read from full_fields config
            include_fields = config_manager.get(f"announcements.{config_type}.full_fields", {})
    elif include_fields is None:
        # Fallback defaults
        include_fields = {
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
            "timestamp": True
        }

    # Determine title based on type (no emojis for Windows console compatibility)
    if announcement_type == "record_break":
        title = "*** NEW RECORD SET! ***"
        description = "@Player set a new server record!"
    elif announcement_type == "first_time":
        title = "*** FIRST SCORE ON CHART! ***"
        description = "@Player was the first to score on this chart!"
    elif announcement_type == "personal_best":
        title = "*** PERSONAL BEST! ***"
        description = "@Player improved their personal best!"
    else:
        title = "NEW HIGH SCORE!"
        description = "@Player set a new score!"

    # Build the preview
    width = 50
    lines = []

    # Top border (using ASCII-safe characters for Windows compatibility)
    lines.append("+" + "-" * (width - 2) + "+")

    # Title
    title_line = "| " + title.ljust(width - 3) + "|"
    lines.append(title_line)

    # Separator
    lines.append("+" + "-" * (width - 2) + "+")

    # Description
    lines.append("| " + description.ljust(width - 3) + "|")
    lines.append("|" + " " * (width - 2) + "|")

    # Song info
    if include_fields.get("song_title", True):
        lines.append("| Song: Through the Fire and Flames".ljust(width - 1) + "|")
    if include_fields.get("artist", True):
        lines.append("| Artist: DragonForce".ljust(width - 1) + "|")

    lines.append("| Score: 1,234,567 points (+15,000)".ljust(width - 1) + "|")
    lines.append("|" + " " * (width - 2) + "|")

    # Three-column fields (using stars without emoji for compatibility)
    if include_fields.get("difficulty_instrument", True) and include_fields.get("stars", True):
        lines.append("| Instrument: Lead Guitar  |  Stars: 5/5".ljust(width - 1) + "|")

    if include_fields.get("difficulty_instrument", True) and include_fields.get("accuracy", True):
        lines.append("| Difficulty: Expert       |  Accuracy: 98.5%".ljust(width - 1) + "|")

    if include_fields.get("charter", True) and include_fields.get("play_count", True):
        lines.append("| Charter: GHLive           |  Plays: 42".ljust(width - 1) + "|")

    lines.append("|" + " " * (width - 2) + "|")

    # Optional fields
    if include_fields.get("enchor_link", True):
        lines.append("| Find This Chart: [Search on enchor.us]".ljust(width - 1) + "|")

    if include_fields.get("chart_hash", True):
        lines.append("| Chart Hash: abc12345".ljust(width - 1) + "|")

    if include_fields.get("timestamp", True):
        lines.append("| Achieved: 2025-12-27 3:45 PM UTC".ljust(width - 1) + "|")

    # Footer (for record breaks and personal bests with config-aware components)
    if announcement_type == "record_break":
        # Build footer based on config settings (if available)
        footer_parts = []

        if include_fields.get("footer_show_previous_holder", True):
            footer_parts.append("OldPlayer")

        if include_fields.get("footer_show_previous_score", True):
            footer_parts.append("(1,220,000 pts)")

        if include_fields.get("footer_show_held_duration", True):
            footer_parts.append("Held for 3 days")

        if include_fields.get("footer_show_set_timestamp", True):
            footer_parts.append("Set on 2025-12-24 2:30 PM EST")

        if footer_parts:
            lines.append("|" + " " * (width - 2) + "|")
            footer = "Previous record: " + " - ".join(footer_parts)
            lines.append("| " + footer[:width-3].ljust(width - 3) + "|")

    elif announcement_type == "personal_best":
        # Personal best footer
        footer_parts = []

        if include_fields.get("footer_show_previous_best", True):
            footer_parts.append("Previous: 1,200,000 pts")

        if include_fields.get("footer_show_improvement", True):
            footer_parts.append("Improved by 34,567 pts (2.9%)")

        if footer_parts:
            lines.append("|" + " " * (width - 2) + "|")
            footer = " - ".join(footer_parts)
            lines.append("| " + footer[:width-3].ljust(width - 3) + "|")

    # Bottom border
    lines.append("+" + "-" * (width - 2) + "+")

    return "\n".join(lines)


def show_preview_menu(config_manager):
    """
    Show interactive preview menu in settings

    Args:
        config_manager: ConfigManager instance
    """
    from shared.console import print_header, print_info, print_success

    while True:
        print()
        print_header("ANNOUNCEMENT PREVIEW", width=60)
        print()
        print("Preview announcements with YOUR CURRENT SETTINGS:")
        print()

        # Show current style settings
        rb_style = config_manager.get("announcements.record_breaks.style", "full")
        ft_style = config_manager.get("announcements.first_time_scores.style", "full")
        pb_style = config_manager.get("announcements.personal_bests.style", "full")

        print(f"  [1] Record Break - Current Mode: {rb_style.capitalize()}")
        print(f"  [2] First-Time Score - Current Mode: {ft_style.capitalize()}")
        print(f"  [3] Personal Best - Current Mode: {pb_style.capitalize()}")
        print()
        print("  [4] Force Full Mode Preview (any type)")
        print("  [5] Force Minimalist Mode Preview (any type)")
        print()
        print("  [B] Back")
        print()

        choice = input("Choice: ").strip().lower()

        if choice == 'b':
            break
        elif choice == '1':
            # Record break with current config
            print()
            print_success(f"Record Break - {rb_style.capitalize()} Mode")
            print()
            print(generate_announcement_preview("record_break", config_manager=config_manager))
            input("\nPress Enter to continue...")
        elif choice == '2':
            # First-time score with current config
            print()
            print_success(f"First-Time Score - {ft_style.capitalize()} Mode")
            print()
            print(generate_announcement_preview("first_time", config_manager=config_manager))
            input("\nPress Enter to continue...")
        elif choice == '3':
            # Personal best with current config
            print()
            print_success(f"Personal Best - {pb_style.capitalize()} Mode")
            print()
            print(generate_announcement_preview("personal_best", config_manager=config_manager))
            input("\nPress Enter to continue...")
        elif choice == '4':
            # Force full mode
            print()
            print("Select type: [1] Record Break  [2] First-Time  [3] Personal Best")
            type_choice = input("Choice: ").strip()
            type_map = {"1": "record_break", "2": "first_time", "3": "personal_best"}
            if type_choice in type_map:
                print()
                print_success(f"{type_map[type_choice].replace('_', ' ').title()} - Full Mode (Forced)")
                print()
                print(generate_announcement_preview(type_map[type_choice], config_manager=config_manager, use_minimalist=False))
                input("\nPress Enter to continue...")
            else:
                print_info("Invalid choice")
        elif choice == '5':
            # Force minimalist mode
            print()
            print("Select type: [1] Record Break  [2] First-Time  [3] Personal Best")
            type_choice = input("Choice: ").strip()
            type_map = {"1": "record_break", "2": "first_time", "3": "personal_best"}
            if type_choice in type_map:
                print()
                print_success(f"{type_map[type_choice].replace('_', ' ').title()} - Minimalist Mode (Forced)")
                print()
                print(generate_announcement_preview(type_map[type_choice], config_manager=config_manager, use_minimalist=True))
                input("\nPress Enter to continue...")
            else:
                print_info("Invalid choice")
        else:
            print_info("Invalid choice")


if __name__ == "__main__":
    # Test the preview generator
    print("\nRecord Break Preview:")
    print(generate_announcement_preview("record_break"))

    print("\n\nFirst-Time Score Preview:")
    print(generate_announcement_preview("first_time"))

    print("\n\nMinimalist Preview:")
    minimal = {
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
        "timestamp": True
    }
    print(generate_announcement_preview("first_time", minimal))

    print("\n\nPersonal Best Preview:")
    print(generate_announcement_preview("personal_best"))

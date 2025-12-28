"""
Terminal Preview Generator for Discord Announcements

Generates ASCII art previews of how Discord announcements will appear.
"""

from typing import Dict, Any


def generate_announcement_preview(announcement_type: str = "record_break", include_fields: Dict[str, bool] = None) -> str:
    """
    Generate ASCII art preview of a Discord announcement

    Args:
        announcement_type: Type of announcement ("record_break", "first_time", "personal_best")
        include_fields: Dict of field names to boolean (which fields to include)

    Returns:
        ASCII art preview string
    """
    if include_fields is None:
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

    # Footer (for record breaks)
    if announcement_type == "record_break":
        lines.append("|" + " " * (width - 2) + "|")
        footer = "Previous: OldPlayer (1,220,000 pts) - Held for 3 days"
        lines.append("| " + footer.ljust(width - 3) + "|")

    # Bottom border
    lines.append("+" + "-" * (width - 2) + "+")

    return "\n".join(lines)


def show_preview_menu(config_manager):
    """
    Show interactive preview menu in settings

    Args:
        config_manager: ConfigManager instance
    """
    from shared.console import print_header, print_info

    while True:
        print()
        print_header("ANNOUNCEMENT PREVIEW", width=60)
        print()
        print("Select announcement type to preview:")
        print("  [1] Record Break (full detail)")
        print("  [2] First-Time Score (full detail)")
        print("  [3] First-Time Score (minimalist)")
        print("  [4] Personal Best")
        print("  [B] Back")
        print()

        choice = input("Choice: ").strip().lower()

        if choice == 'b':
            break
        elif choice == '1':
            print()
            print(generate_announcement_preview("record_break"))
            input("\nPress Enter to continue...")
        elif choice == '2':
            print()
            print(generate_announcement_preview("first_time"))
            input("\nPress Enter to continue...")
        elif choice == '3':
            # Minimalist mode
            minimal_fields = {
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
            print()
            print(generate_announcement_preview("first_time", minimal_fields))
            input("\nPress Enter to continue...")
        elif choice == '4':
            print()
            print(generate_announcement_preview("personal_best"))
            input("\nPress Enter to continue...")
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

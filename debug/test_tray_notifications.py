"""
Test script to demonstrate system tray notification options

Shows what the notifications would look like for:
1. Program startup (especially when auto-started minimized)
2. Update available notifications
"""

import pystray
from PIL import Image, ImageDraw
import time


def create_icon_image():
    """Create a simple icon for testing"""
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Green circle
    draw.ellipse([4, 4, 60, 60], fill='#00FF00', outline='#008800')
    # White text
    draw.text((18, 20), "CH", fill='white')
    return image


def demo_notifications():
    """Demo the notification styles"""

    print("=" * 80)
    print("SYSTEM TRAY NOTIFICATION DEMO")
    print("=" * 80)
    print()
    print("This demo shows what the Windows 10 toast notifications would look like.")
    print()
    print("Available notification types in pystray:")
    print()
    print("1. STARTUP NOTIFICATION")
    print("   Title: 'Clone Hero Score Tracker'")
    print("   Message: 'Running in background - monitoring scores'")
    print("   When: Program starts (especially when minimized at boot)")
    print()
    print("2. UPDATE AVAILABLE NOTIFICATION")
    print("   Title: 'Update Available'")
    print("   Message: 'Version X.Y.Z is available. Type \"update\" to download.'")
    print("   When: After checking for updates and finding a new version")
    print()
    print("3. UPDATE DOWNLOADED NOTIFICATION")
    print("   Title: 'Update Downloaded'")
    print("   Message: 'Version X.Y.Z ready. Restart to apply.'")
    print("   When: Update has been downloaded successfully")
    print()
    print("=" * 80)
    print("NOTIFICATION APPEARANCE")
    print("=" * 80)
    print()
    print("Windows 10/11 Toast Notifications show in the bottom-right corner:")
    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │ [Icon] Clone Hero Score Tracker        │")
    print("  │        Running in background -          │")
    print("  │        monitoring scores                │")
    print("  └─────────────────────────────────────────┘")
    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │ [Icon] Update Available                 │")
    print("  │        Version 2.4.13 is available.     │")
    print("  │        Type \"update\" to download.        │")
    print("  └─────────────────────────────────────────┘")
    print()
    print("Notifications appear for 5-10 seconds, then fade away.")
    print("User can click to open the program or dismiss.")
    print()
    print("=" * 80)
    print("IMPLEMENTATION DETAILS")
    print("=" * 80)
    print()
    print("Using pystray.Icon.notify() method:")
    print()
    print("  icon.notify(")
    print("      title='Clone Hero Score Tracker',")
    print("      message='Running in background - monitoring scores'")
    print("  )")
    print()
    print("Notification timing:")
    print("  1. Startup: Show immediately after tray icon is ready")
    print("  2. Update available: Show when check_for_updates() finds new version")
    print("  3. Update downloaded: Show when download completes")
    print()
    print("Settings consideration:")
    print("  - Always show startup notification when minimized")
    print("  - Always show update notifications (important)")
    print("  - Could add setting to disable notifications if needed")
    print()
    print("=" * 80)
    print("WOULD YOU LIKE TO SEE A LIVE DEMO?")
    print("=" * 80)
    print()
    print("If you run this on Windows 10/11 with pystray installed,")
    print("I can show you actual toast notifications.")
    print()

    try:
        choice = input("Run live demo? (y/n): ").strip().lower()
        if choice == 'y':
            run_live_demo()
        else:
            print("\nDemo skipped.")
    except KeyboardInterrupt:
        print("\nDemo cancelled.")


def run_live_demo():
    """Run actual notifications (Windows 10/11 only)"""
    print("\n" + "=" * 80)
    print("LIVE NOTIFICATION DEMO")
    print("=" * 80)
    print()
    print("Starting system tray icon...")
    print("Watch the bottom-right corner of your screen for notifications!")
    print("Press Ctrl+C to exit after viewing notifications.")
    print()

    icon = pystray.Icon(
        "TestTracker",
        create_icon_image(),
        "Clone Hero Score Tracker (Test)"
    )

    def setup(icon):
        icon.visible = True

        # Notification 1: Startup
        print("Showing notification 1: Startup...")
        icon.notify(
            title="Clone Hero Score Tracker",
            message="Running in background - monitoring scores"
        )
        time.sleep(5)

        # Notification 2: Update available
        print("Showing notification 2: Update available...")
        icon.notify(
            title="Update Available",
            message="Version 2.4.13 is available. Type \"update\" to download."
        )
        time.sleep(5)

        # Notification 3: Update downloaded
        print("Showing notification 3: Update downloaded...")
        icon.notify(
            title="Update Downloaded",
            message="Version 2.4.13 ready. Restart to apply."
        )
        time.sleep(5)

        print("\nAll notifications shown!")
        print("You can close this window or press Ctrl+C to exit.")

    icon.run(setup=setup)


if __name__ == "__main__":
    demo_notifications()

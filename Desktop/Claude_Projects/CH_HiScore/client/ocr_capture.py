"""
OCR module for capturing Clone Hero results screen

Captures the Clone Hero window after a song ends and extracts
additional metadata using Windows built-in OCR (artist, notes hit/total, etc.)

Uses Windows 10/11 native OCR - no external dependencies required.
"""

import re
import time
import asyncio
from typing import Optional, Tuple
from dataclasses import dataclass

# Windows OCR imports
try:
    import winocr
    from PIL import Image, ImageEnhance
    import mss
    HAS_OCR_DEPS = True
except ImportError:
    HAS_OCR_DEPS = False

# Windows-specific imports for window handling
try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass
class OCRResult:
    """Results from OCR extraction"""
    success: bool
    artist: Optional[str] = None
    song_title: Optional[str] = None
    notes_hit: Optional[int] = None
    notes_total: Optional[int] = None
    score: Optional[int] = None
    accuracy: Optional[float] = None
    streak: Optional[int] = None
    stars: Optional[int] = None
    raw_text: str = ""
    error: Optional[str] = None


def check_ocr_available() -> Tuple[bool, str]:
    """Check if Windows OCR is available"""
    if not HAS_OCR_DEPS:
        return False, "OCR dependencies not installed (winocr, Pillow, mss)"

    if not HAS_WIN32:
        return False, "Windows API not available (pywin32)"

    # Windows OCR is built into Windows 10+, no external check needed
    return True, "Windows OCR available"


def find_clone_hero_window() -> Optional[int]:
    """Find the Clone Hero window handle"""
    if not HAS_WIN32:
        return None

    hwnd = None
    found_windows = []

    def enum_callback(h, _):
        nonlocal found_windows
        title = win32gui.GetWindowText(h)
        # Clone Hero window titles vary, look for common patterns
        # But exclude our own tracker window and command prompts
        if ('Clone Hero' in title or 'CloneHero' in title):
            # Exclude our tracker and command prompt windows
            exclude_patterns = ['ScoreTracker', '.exe', 'cmd', 'Command Prompt', 'PowerShell']
            is_excluded = any(pat.lower() in title.lower() for pat in exclude_patterns)

            if not is_excluded and win32gui.IsWindowVisible(h):
                found_windows.append((h, title))
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception:
        pass

    # Return the first matching window (if any)
    if found_windows:
        hwnd = found_windows[0][0]
        print(f"[OCR] Found Clone Hero window: {found_windows[0][1]}")
    else:
        # Show what windows we did find for debugging
        print("[OCR] No Clone Hero game window found.")
        print("[OCR] Make sure Clone Hero is running and visible.")

    return hwnd


def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Get window rectangle (left, top, right, bottom)"""
    if not HAS_WIN32:
        return None

    try:
        rect = win32gui.GetWindowRect(hwnd)
        return rect
    except Exception:
        return None


def bring_window_to_front(hwnd: int) -> bool:
    """Bring window to foreground so it can be captured"""
    if not HAS_WIN32:
        return False

    try:
        # Try to bring window to foreground
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.1)  # Brief pause to let window come to front
        return True
    except Exception as e:
        print(f"[OCR] Could not bring window to front: {e}")
        return False


def capture_window(hwnd: int) -> Optional[Image.Image]:
    """Capture a screenshot of the specified window"""
    rect = get_window_rect(hwnd)
    if not rect:
        return None

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top

    if width <= 0 or height <= 0:
        return None

    try:
        with mss.mss() as sct:
            monitor = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
            screenshot = sct.grab(monitor)

            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
    except Exception as e:
        print(f"[OCR] Error capturing window: {e}")
        return None


def preprocess_image(img: Image.Image) -> Image.Image:
    """Preprocess image to improve OCR accuracy"""
    # Convert to grayscale
    gray = img.convert('L')

    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.5)

    # Convert back to RGB for winocr compatibility
    rgb = contrasted.convert('RGB')

    return rgb


async def extract_text_async(img: Image.Image) -> str:
    """Extract text from image using Windows OCR (async)"""
    if not HAS_OCR_DEPS:
        return ""

    try:
        # Preprocess the image
        processed = preprocess_image(img)

        # Use Windows OCR via winocr
        result = await winocr.recognize_pil(processed, lang='en')

        return result.text
    except Exception as e:
        print(f"[OCR] Error extracting text: {e}")
        return ""


def extract_text_from_image(img: Image.Image) -> str:
    """Extract text from image using Windows OCR (sync wrapper)"""
    try:
        # Run the async function in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            text = loop.run_until_complete(extract_text_async(img))
        finally:
            loop.close()
        return text
    except Exception as e:
        print(f"[OCR] Error in sync wrapper: {e}")
        return ""


def parse_results_text(text: str) -> OCRResult:
    """Parse the OCR text to extract score data"""
    result = OCRResult(success=False, raw_text=text)

    if not text.strip():
        result.error = "No text extracted"
        return result

    # Patterns to look for in Clone Hero results screen
    # Based on actual OCR output format:
    # "Song Artist ... Score ... PERFORMANCE Total Notes Notes Hit Notes Missed Best Streak ... 278 192 86 84"

    # The text before PERFORMANCE or the first score contains song info
    # Try to extract song title and artist from the beginning of the text
    song_artist_section = text
    perf_idx = text.upper().find('PERFORMANCE')
    if perf_idx > 0:
        song_artist_section = text[:perf_idx]

    # Also cut off at first comma-number pattern (score like "31,894")
    score_match = re.search(r'\d{1,3},\d{3}', song_artist_section)
    if score_match:
        song_artist_section = song_artist_section[:score_match.start()]

    # Clean up the song/artist section
    song_artist_section = song_artist_section.strip()

    # The format is typically: "SongTitle ArtistName OtherStuff"
    # We'll extract this as potential song_title and artist
    # Split by common separators or just take first few words
    words = song_artist_section.split()
    if len(words) >= 2:
        # First word(s) might be song title, next might be artist
        # This is a rough heuristic - we'll validate against known title later
        result.song_title = words[0] if words else None
        result.artist = words[1] if len(words) > 1 else None
    elif len(words) == 1:
        result.song_title = words[0]

    # Artist pattern - fallback patterns
    artist_patterns = [
        r'(?:by|By|BY)\s+(.+?)(?:\n|$)',
        r'Artist[:\s]+(.+?)(?:\n|$)',
    ]

    # Clone Hero shows: "Total Notes Notes Hit Notes Missed Best Streak ... 278 192 86 84"
    # We need to extract Total Notes and Notes Hit
    # Look for the PERFORMANCE section pattern
    notes_total = None
    notes_hit = None

    # Try to find "Total Notes" followed eventually by numbers
    # Pattern: numbers appear after the labels in sequence
    perf_match = re.search(
        r'Total\s*Notes\s+Notes\s*Hit\s+Notes\s*Missed\s+Best\s*Streak.*?(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
        text, re.IGNORECASE
    )
    if perf_match:
        notes_total = int(perf_match.group(1))
        notes_hit = int(perf_match.group(2))
        # group(3) is notes missed
        # group(4) is best streak

    # Fallback patterns for notes
    notes_patterns = [
        r'Total\s*Notes[:\s]*(\d+)',
        r'Notes\s*Hit[:\s]*(\d+)',
        r'(\d{1,5})\s*/\s*(\d{1,5})\s*(?:Notes|notes)?',
    ]

    # Score pattern - Clone Hero shows score with commas like "31,894"
    score_patterns = [
        r'(\d{1,3}(?:,\d{3})+)',  # Numbers with commas (e.g., 31,894)
        r'Score[:\s]+(\d[\d,]+)',
        r'(?<!\d)(\d{4,})(?!\d)',  # Large numbers without commas
    ]

    # Accuracy pattern
    accuracy_patterns = [
        r'(\d{1,3}(?:\.\d+)?)\s*%',
        r'Accuracy[:\s]+(\d{1,3}(?:\.\d+)?)',
    ]

    # Streak pattern - Clone Hero shows "Best Streak"
    streak_patterns = [
        r'Best\s*Streak[:\s]*(\d+)',
        r'Streak[:\s]+(\d+)',
        r'(\d+)\s*(?:Note|note)?\s*Streak',
    ]

    # Stars pattern
    stars_patterns = [
        r'(\d)\s*(?:Stars?|stars?|\*)',
        r'Stars?[:\s]+(\d)',
    ]

    full_text = text

    # Try to extract artist
    for pattern in artist_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            result.artist = match.group(1).strip()
            break

    # Use performance section data if found
    if notes_total is not None and notes_hit is not None:
        result.notes_total = notes_total
        result.notes_hit = notes_hit
    else:
        # Fallback: try individual patterns
        for pattern in notes_patterns:
            match = re.search(pattern, full_text)
            if match:
                try:
                    if match.lastindex >= 2:
                        result.notes_hit = int(match.group(1).replace(',', ''))
                        result.notes_total = int(match.group(2).replace(',', ''))
                    break
                except (ValueError, IndexError):
                    pass

    # Extract streak from performance match if available
    if perf_match:
        try:
            result.streak = int(perf_match.group(4))
        except (ValueError, IndexError):
            pass

    # Try to extract score
    for pattern in score_patterns:
        match = re.search(pattern, full_text)
        if match:
            try:
                score_str = match.group(1).replace(',', '')
                result.score = int(score_str)
                break
            except (ValueError, IndexError):
                pass

    # Try to extract accuracy
    for pattern in accuracy_patterns:
        match = re.search(pattern, full_text)
        if match:
            try:
                result.accuracy = float(match.group(1))
                break
            except (ValueError, IndexError):
                pass

    # Try to extract streak
    for pattern in streak_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            try:
                result.streak = int(match.group(1))
                break
            except (ValueError, IndexError):
                pass

    # Try to extract stars
    for pattern in stars_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            try:
                result.stars = int(match.group(1))
                break
            except (ValueError, IndexError):
                pass

    # Consider success if we got at least one piece of useful data
    if any([result.artist, result.notes_hit, result.notes_total,
            result.score, result.accuracy, result.streak, result.stars]):
        result.success = True
    else:
        result.error = "Could not parse any data from OCR text"

    return result


def capture_and_extract(delay_ms: int = 500, save_debug: bool = False) -> OCRResult:
    """
    Main function to capture Clone Hero window and extract data

    Args:
        delay_ms: Milliseconds to wait before capturing (for results screen to appear)
        save_debug: If True, saves the captured screenshot for debugging

    Returns:
        OCRResult with extracted data
    """
    # Check dependencies
    ocr_ok, ocr_msg = check_ocr_available()
    if not ocr_ok:
        return OCRResult(
            success=False,
            error=ocr_msg
        )

    # Wait for results screen to appear
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)

    # Find Clone Hero window
    hwnd = find_clone_hero_window()
    if not hwnd:
        return OCRResult(
            success=False,
            error="Clone Hero window not found"
        )

    # Bring Clone Hero to front so it's not covered by other windows
    bring_window_to_front(hwnd)

    # Capture the window
    img = capture_window(hwnd)
    if not img:
        return OCRResult(
            success=False,
            error="Failed to capture window"
        )

    # Save debug image if requested
    if save_debug:
        try:
            debug_path = "ocr_debug_capture.png"
            img.save(debug_path)
            print(f"[OCR] Debug image saved to {debug_path}")
        except Exception as e:
            print(f"[OCR] Could not save debug image: {e}")

    # Extract text
    text = extract_text_from_image(img)

    # Parse the results
    result = parse_results_text(text)

    return result


def test_ocr():
    """Test function to verify OCR is working"""
    print("=" * 50)
    print("Windows OCR Test")
    print("=" * 50)

    # Check OCR availability
    ocr_ok, ocr_msg = check_ocr_available()
    print(f"\nOCR Status: {ocr_msg}")

    if not ocr_ok:
        print("\nOCR is not available. Requirements:")
        print("  - Windows 10 or 11")
        print("  - Python packages: winocr, Pillow, mss, pywin32")
        return

    # Try to find Clone Hero window
    print("\nLooking for Clone Hero window...")
    hwnd = find_clone_hero_window()

    if hwnd:
        print(f"  Found window handle: {hwnd}")
        rect = get_window_rect(hwnd)
        if rect:
            print(f"  Window position: {rect}")

        print("\nCapturing window...")
        result = capture_and_extract(delay_ms=0, save_debug=True)

        print(f"\nOCR Result:")
        print(f"  Success: {result.success}")
        if result.error:
            print(f"  Error: {result.error}")
        if result.artist:
            print(f"  Artist: {result.artist}")
        if result.notes_hit is not None:
            print(f"  Notes: {result.notes_hit}/{result.notes_total}")
        if result.score is not None:
            print(f"  Score: {result.score:,}")
        if result.accuracy is not None:
            print(f"  Accuracy: {result.accuracy}%")
        if result.streak is not None:
            print(f"  Streak: {result.streak}")
        if result.stars is not None:
            print(f"  Stars: {result.stars}")

        print(f"\nRaw OCR text:")
        print("-" * 30)
        print(result.raw_text[:500] if result.raw_text else "(empty)")
        print("-" * 30)
    else:
        print("  Clone Hero window not found")
        print("  Make sure Clone Hero is running and visible")


if __name__ == '__main__':
    test_ocr()

"""
Daily Activity Log Generator

Generates human-readable daily activity reports for server admins.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict


INSTRUMENTS = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums", 7: "GHLGuitar", 8: "GHLBass", 9: "Vocals", 10: "CoDrums"}
DIFFICULTIES = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}


def generate_daily_log(activity_data: Dict, date_str: str) -> str:
    """
    Generate formatted daily activity log text

    Args:
        activity_data: Dictionary from database.get_daily_activity()
        date_str: Date string for the report (e.g., "2025-12-29")

    Returns:
        Formatted log text
    """
    summary = activity_data['summary']
    user_activity = activity_data['user_activity']
    record_breaks = activity_data['record_breaks']
    all_submissions = activity_data['all_submissions']
    stats = activity_data['statistics']

    # Parse date for header
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%A, %B %d, %Y")
    except Exception:
        date_display = date_str

    # Build log text
    lines = []
    lines.append("=" * 50)
    lines.append("CLONE HERO SCORE TRACKER - DAILY ACTIVITY LOG")
    lines.append(f"Date: {date_display}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 50)
    lines.append("")

    # SUMMARY
    lines.append("SUMMARY")
    lines.append("-" * 7)
    lines.append(f"Total Submissions: {summary['total_submissions']}")
    lines.append(f"Unique Users: {summary['unique_users']}")
    lines.append(f"Unique Charts Played: {summary['unique_charts']}")
    lines.append(f"Records Broken: {summary['total_records_broken']}")
    lines.append(f"First-Time Scores: {summary['first_time_scores']}")
    lines.append("")

    # USER ACTIVITY
    if user_activity:
        lines.append("USER ACTIVITY")
        lines.append("-" * 13)
        for user in user_activity:
            username = user['discord_username']
            count = user['submission_count']
            records = user.get('records_broken', 0)
            lines.append(f"{username:<30} {count:>3} submissions  ({records} records broken)")
        lines.append("")

    # STATISTICS
    lines.append("STATISTICS")
    lines.append("-" * 10)

    # Most active hour
    if stats['most_active_hour']:
        hour = stats['most_active_hour']['hour']
        count = stats['most_active_hour']['count']
        lines.append(f"Most Active Hour: {hour:02d}:00-{hour+1:02d}:00 ({count} submissions)")

    # Most played chart
    if stats['most_played_chart']:
        title = stats['most_played_chart']['title']
        count = stats['most_played_chart']['count']
        lines.append(f"Most Played Chart: {title} ({count} plays)")

    # Difficulty breakdown
    if stats['difficulty_counts']:
        total = summary['total_submissions']
        for diff_id in sorted(stats['difficulty_counts'].keys(), reverse=True):
            count = stats['difficulty_counts'][diff_id]
            diff_name = DIFFICULTIES.get(diff_id, f"Unknown({diff_id})")
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"Most Common Difficulty: {diff_name} ({count}/{total}, {pct:.1f}%)")
            break  # Only show the most common

    # Instrument breakdown
    if stats['instrument_counts']:
        total = summary['total_submissions']
        for inst_id in sorted(stats['instrument_counts'].keys(), key=lambda x: stats['instrument_counts'][x], reverse=True):
            count = stats['instrument_counts'][inst_id]
            inst_name = INSTRUMENTS.get(inst_id, f"Unknown({inst_id})")
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"Most Common Instrument: {inst_name} ({count}/{total}, {pct:.1f}%)")
            break  # Only show the most common

    lines.append("")
    if summary['total_submissions'] > 0:
        lines.append(f"Average Score: {stats['avg_score']:,} pts")
        lines.append(f"Highest Score: {stats['max_score']:,} pts")
        lines.append(f"Lowest Score: {stats['min_score']:,} pts")
        lines.append("")

        total = summary['total_submissions']
        five_star = stats['five_star_count']
        five_star_pct = (five_star / total * 100) if total > 0 else 0
        lines.append(f"5-Star Scores: {five_star}/{total} ({five_star_pct:.1f}%)")

        mystery = stats['mystery_count']
        total_charts = summary['unique_charts']
        mystery_pct = (mystery / total_charts * 100) if total_charts > 0 else 0
        lines.append(f"Mystery Hashes: {mystery}/{total_charts} charts ({mystery_pct:.1f}%)")
        lines.append("")

    # RECORDS BROKEN TODAY - v2.6.4: Enhanced with improvement % and held duration
    if record_breaks:
        lines.append("RECORDS BROKEN TODAY")
        lines.append("-" * 20)
        for rec in record_breaks:
            # Parse time
            timestamp = rec['broken_at']
            time_str = timestamp.split(' ')[1][:8] if ' ' in timestamp else "??:??:??"

            # Song info
            song_title = rec.get('song_title', '[unknown]')
            artist = rec.get('song_artist', '')
            charter = rec.get('song_charter', '')
            chart_hash = rec.get('chart_hash', '')

            # Include charter in display
            if charter:
                song_display = f"{song_title} ({charter})"
            else:
                song_display = song_title
            if artist:
                song_display = f"{song_display} - {artist}"

            # Instrument and difficulty
            inst = INSTRUMENTS.get(rec['instrument_id'], '?')
            diff = DIFFICULTIES.get(rec['difficulty_id'], '?')

            # Previous holder info
            prev_score = rec.get('previous_score')
            prev_holder = rec.get('previous_holder_name')
            new_score = rec['new_score']

            lines.append(f"[{time_str}] {rec['breaker_name']} broke the record on {song_display}")

            if prev_score and prev_holder:
                # Calculate improvement percentage
                improvement = new_score - prev_score
                improvement_pct = (improvement / prev_score * 100) if prev_score > 0 else 0

                # Calculate how long record was held
                held_duration_str = ""
                if rec.get('previous_record_set_at'):
                    try:
                        from datetime import datetime
                        broken_time = datetime.fromisoformat(timestamp)
                        set_time = datetime.fromisoformat(rec['previous_record_set_at'])
                        held_duration = broken_time - set_time

                        days = held_duration.days
                        hours = held_duration.seconds // 3600
                        minutes = (held_duration.seconds % 3600) // 60

                        if days > 0:
                            held_duration_str = f" (held for {days}d {hours}h)"
                        elif hours > 0:
                            held_duration_str = f" (held for {hours}h {minutes}m)"
                        elif minutes > 0:
                            held_duration_str = f" (held for {minutes}m)"
                    except:
                        pass

                lines.append(f"           {diff} {inst}: {new_score:,} pts [+{improvement_pct:.1f}% vs. {prev_holder}]")
                lines.append(f"           Previous: {prev_score:,} pts{held_duration_str}")
            elif prev_score:
                improvement = new_score - prev_score
                improvement_pct = (improvement / prev_score * 100) if prev_score > 0 else 0
                lines.append(f"           {diff} {inst}: {new_score:,} pts [+{improvement_pct:.1f}%]")
                lines.append(f"           Previous: {prev_score:,} pts")
            else:
                lines.append(f"           {diff} {inst}: {new_score:,} pts [FIRST SCORE ON CHART]")

            # Add chart hash
            if chart_hash:
                lines.append(f"           Hash: [{chart_hash[:8]}]")

            lines.append("")
        lines.append("")

    # DETAILED SUBMISSIONS (Chronological) - v2.6.4: Enhanced multi-line format
    if all_submissions:
        lines.append("DETAILED SUBMISSIONS (Chronological)")
        lines.append("-" * 36)

        for sub in all_submissions:
            # Parse time
            timestamp = sub['submitted_at']
            time_str = timestamp.split(' ')[1][:8] if ' ' in timestamp else "??:??:??"

            # Song info
            song_title = sub.get('song_title', '[unknown]')
            artist = sub.get('song_artist', '')
            charter = sub.get('song_charter', '')
            chart_hash = sub.get('chart_hash', '')

            # Line 1: Timestamp, username, song title (with charter if available)
            if charter:
                song_display = f"{song_title} ({charter})"
            else:
                song_display = song_title
            if artist:
                song_display = f"{song_display} - {artist}"

            lines.append(f"[{time_str}] {sub['discord_username']} - {song_display}")

            # Line 2: Difficulty/instrument, score, accuracy, FC indicator, stars
            inst = INSTRUMENTS.get(sub['instrument_id'], '?')
            diff = DIFFICULTIES.get(sub['difficulty_id'], '?')

            # Calculate accuracy
            notes_hit = sub.get('notes_hit')
            notes_total = sub.get('notes_total')
            accuracy_str = ""
            if notes_hit is not None and notes_total is not None and notes_total > 0:
                accuracy = (notes_hit / notes_total) * 100
                accuracy_str = f" {notes_hit}/{notes_total} notes ({accuracy:.1f}%)"

            # FC indicator
            is_fc = sub.get('is_full_combo', 0) == 1
            fc_tag = " [FC]" if is_fc else ""

            # Stars
            stars = sub.get('stars', 0)
            star_display = " " + ("⭐" * stars) if stars > 0 else ""

            # Check if this was a record or personal best
            is_record = any(
                rb['chart_hash'] == sub['chart_hash'] and
                rb['instrument_id'] == sub['instrument_id'] and
                rb['difficulty_id'] == sub['difficulty_id'] and
                rb['user_id'] == sub['user_id'] and
                rb['new_score'] == sub['score']
                for rb in record_breaks
            )
            record_tag = " [RECORD]" if is_record else " [PB]"

            lines.append(f"           {diff} {inst}: {sub['score']:,} pts{fc_tag}{accuracy_str}{star_display}{record_tag}")

            # Line 3: Chart metadata (NPS, peak NPS, play count, hash)
            metadata_parts = []

            # Chart difficulty indicators
            chart_nps = sub.get('chart_nps')
            chart_peak_nps = sub.get('chart_peak_nps')
            if chart_nps is not None and chart_nps > 0:
                if chart_peak_nps is not None and chart_peak_nps > 0:
                    metadata_parts.append(f"Chart: {chart_nps:.1f} NPS (peak: {chart_peak_nps:.1f})")
                else:
                    metadata_parts.append(f"Chart: {chart_nps:.1f} NPS")

            # Play count
            play_count = sub.get('play_count')
            if play_count is not None and play_count > 0:
                metadata_parts.append(f"Play #{play_count}")

            # Hash (abbreviated)
            if chart_hash:
                metadata_parts.append(f"Hash: [{chart_hash[:8]}]")

            if metadata_parts:
                lines.append(f"           {' | '.join(metadata_parts)}")

            lines.append("")  # Blank line between entries

        lines.append("")

    # Footer
    lines.append("=" * 50)
    lines.append("End of Daily Report")
    lines.append("=" * 50)

    return "\n".join(lines)


def save_daily_log(log_text: str, log_dir: Path, date_str: str) -> Path:
    """
    Save daily log to file

    Args:
        log_text: Formatted log text
        log_dir: Directory to save logs
        date_str: Date string for filename (e.g., "2025-12-29")

    Returns:
        Path to saved log file
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    filename = f"activity_{date_str}.txt"
    log_path = log_dir / filename

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(log_text)

    return log_path

#!/usr/bin/env python3
"""
Migration Script: Fix Note Counts in Scores Table
==================================================

This script updates incorrect note_total values in the scores table by
referencing the correct values from the chart_metadata table.

BACKGROUND:
-----------
Prior to v2.6.2, the chart parser incorrectly counted individual note events
instead of playable notes. For example, a chord with 3 frets would be counted
as 3 notes instead of 1. This resulted in:
  - Inflated note counts (e.g., 902 instead of 450)
  - Incorrect NPS calculations (e.g., 7.1 instead of 3.6)

WHAT THIS SCRIPT DOES:
----------------------
1. Scans all scores in the database that have note_total values
2. Looks up the correct note count from chart_metadata table
3. Identifies mismatches (where scores.notes_total != chart_metadata.total_notes)
4. Updates the incorrect values with the correct ones
5. Provides detailed statistics about the changes

REQUIREMENTS:
-------------
- chart_metadata table must be populated (run 'scancharts' from client first)
- Database backup recommended before running

SAFETY:
-------
- Dry-run mode shows what would change without making changes
- Requires explicit confirmation before updating database
- Only updates scores where chart_metadata exists
- Preserves all other score data unchanged
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


def get_database_path() -> Path:
    """Get the path to the scores database"""
    import os
    if os.name == 'nt':  # Windows
        appdata = Path(os.getenv('APPDATA', ''))
        db_path = appdata / 'CloneHeroScoreBot' / 'scores.db'
    else:  # Unix-like
        home = Path.home()
        db_path = home / '.clonehero_scorebot' / 'scores.db'

    return db_path


def analyze_mismatches(db_path: Path) -> Tuple[List[Dict], Dict]:
    """
    Analyze scores table for note count mismatches

    Returns:
        Tuple of (mismatch_list, statistics_dict)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query scores with note counts and join with chart_metadata
    query = """
        SELECT
            s.id as score_id,
            s.chart_hash,
            s.instrument_id,
            s.difficulty_id,
            s.user_id,
            s.score,
            s.notes_total as current_notes,
            cm.total_notes as correct_notes,
            cm.note_density as correct_nps,
            u.discord_username
        FROM scores s
        LEFT JOIN chart_metadata cm
            ON s.chart_hash = cm.chart_hash
            AND s.instrument_id = cm.instrument_id
            AND s.difficulty_id = cm.difficulty_id
        LEFT JOIN users u ON s.user_id = u.id
        WHERE s.notes_total IS NOT NULL
        AND s.notes_total > 0
    """

    cursor.execute(query)
    results = cursor.fetchall()

    mismatches = []
    stats = {
        'total_scores_with_notes': 0,
        'scores_with_metadata': 0,
        'scores_without_metadata': 0,
        'mismatches_found': 0,
        'exact_matches': 0,
        'total_notes_corrected': 0,  # Sum of absolute differences
    }

    for row in results:
        stats['total_scores_with_notes'] += 1

        current = row['current_notes']
        correct = row['correct_notes']

        if correct is None:
            stats['scores_without_metadata'] += 1
            continue

        stats['scores_with_metadata'] += 1

        if current != correct:
            stats['mismatches_found'] += 1
            stats['total_notes_corrected'] += abs(current - correct)

            mismatches.append({
                'score_id': row['score_id'],
                'chart_hash': row['chart_hash'],
                'instrument_id': row['instrument_id'],
                'difficulty_id': row['difficulty_id'],
                'user_id': row['user_id'],
                'username': row['discord_username'],
                'score': row['score'],
                'current_notes': current,
                'correct_notes': correct,
                'difference': current - correct,
                'correct_nps': row['correct_nps']
            })
        else:
            stats['exact_matches'] += 1

    conn.close()
    return mismatches, stats


def apply_corrections(db_path: Path, mismatches: List[Dict]) -> int:
    """
    Apply note count corrections to the database

    Returns:
        Number of records updated
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    updated = 0

    for mismatch in mismatches:
        try:
            cursor.execute("""
                UPDATE scores
                SET notes_total = ?
                WHERE id = ?
            """, (mismatch['correct_notes'], mismatch['score_id']))

            updated += cursor.rowcount
        except Exception as e:
            print(f"Error updating score {mismatch['score_id']}: {e}")

    conn.commit()
    conn.close()

    return updated


def print_header(text: str):
    """Print a formatted header"""
    print()
    print("=" * 80)
    print(f"  {text}")
    print("=" * 80)
    print()


def print_mismatch_table(mismatches: List[Dict], limit: int = 10):
    """Print a table of mismatches"""
    instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
    difficulties = {0: "Easy", 1: "Med", 2: "Hard", 3: "Exp"}

    print(f"{'User':<20} {'Inst':<6} {'Diff':<5} {'Current':<8} {'Correct':<8} {'Diff':<8} {'Hash':<10}")
    print("-" * 80)

    for i, m in enumerate(mismatches[:limit]):
        inst = instruments.get(m['instrument_id'], f"Inst{m['instrument_id']}")
        diff = difficulties.get(m['difficulty_id'], f"Diff{m['difficulty_id']}")

        print(f"{m['username'][:20]:<20} {inst:<6} {diff:<5} "
              f"{m['current_notes']:<8} {m['correct_notes']:<8} "
              f"{m['difference']:+8} {m['chart_hash'][:8]:<10}")

    if len(mismatches) > limit:
        print(f"... and {len(mismatches) - limit} more")
    print()


def main():
    """Main migration script"""
    print_header("NOTE COUNT CORRECTION UTILITY")

    print("This utility fixes incorrect note counts in the scores table by referencing")
    print("the correct values from the chart_metadata table.")
    print()
    print("WHAT IT DOES:")
    print("  • Scans all scores with note count data")
    print("  • Compares with correct values from chart_metadata")
    print("  • Shows you what will change before making any modifications")
    print("  • Updates only the notes_total field (all other data preserved)")
    print()

    # Get database path
    db_path = get_database_path()

    # Check if using alternative path (for testing)
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        print(f"[*] Using database: {db_path}")
        print()

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print()
        print("Make sure the bot has been run at least once to create the database.")
        return 1

    print(f"[*] Database: {db_path}")
    print()

    # Step 1: Analyze mismatches
    print("[*] Analyzing scores table...")
    mismatches, stats = analyze_mismatches(db_path)

    print()
    print("ANALYSIS RESULTS:")
    print("-" * 80)
    print(f"  Total scores with note data:     {stats['total_scores_with_notes']:,}")
    print(f"  Scores with chart metadata:      {stats['scores_with_metadata']:,}")
    print(f"  Scores missing chart metadata:   {stats['scores_without_metadata']:,}")
    print()
    print(f"  Exact matches (no change needed): {stats['exact_matches']:,}")
    print(f"  Mismatches found (need fixing):   {stats['mismatches_found']:,}")
    print()

    if stats['mismatches_found'] == 0:
        print("[SUCCESS] No mismatches found! All note counts are correct.")
        print()
        return 0

    if stats['scores_without_metadata'] > 0:
        print("[WARNING] Some scores are missing chart metadata and cannot be fixed.")
        print("          Run 'scancharts' from the client to populate metadata.")
        print()

    # Step 2: Show sample mismatches
    print_header("SAMPLE MISMATCHES (showing up to 10)")
    print_mismatch_table(mismatches, limit=10)

    # Step 3: Confirm changes
    print("=" * 80)
    print()
    response = input(f"Apply corrections to {stats['mismatches_found']} scores? (yes/no): ").strip().lower()

    if response != 'yes':
        print()
        print("[*] Cancelled. No changes made.")
        print()
        return 0

    # Step 4: Apply corrections
    print()
    print("[*] Applying corrections...")
    updated = apply_corrections(db_path, mismatches)

    print()
    print_header("MIGRATION COMPLETE")
    print(f"[SUCCESS] Updated {updated} score records")
    print()
    print("SUMMARY:")
    print(f"  • Scores corrected: {updated}")
    print(f"  • Database: {db_path}")
    print(f"  • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("[*] Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

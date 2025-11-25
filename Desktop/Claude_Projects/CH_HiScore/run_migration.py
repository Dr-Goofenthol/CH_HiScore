#!/usr/bin/env python3
"""
Standalone migration script for v2.4.3
Renames chart_md5 columns to chart_hash in existing databases (including record_breaks table).

Usage:
    python run_migration.py [path_to_scores.db]

If no path is provided, will attempt to migrate the database in %APPDATA%/CloneHeroScoreBot/
"""

import sqlite3
import sys
from pathlib import Path

def get_config_dir():
    """Get the AppData config directory for the bot"""
    import os
    if sys.platform == 'win32':
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        return appdata / 'CloneHeroScoreBot'
    else:
        # For Linux/Mac
        home = Path.home()
        return home / '.config' / 'CloneHeroScoreBot'

def run_migration(db_path):
    """Run the chart_md5 -> chart_hash migration"""
    print(f"\n[*] Running migration on: {db_path}")

    if not db_path.exists():
        print(f"[!] Error: Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        print(f"[*] Tables in database: {tables}")

        if 'scores' not in tables or 'songs' not in tables:
            print("[!] Error: Database is missing required tables (scores and/or songs)")
            print("[!] This may not be a Clone Hero Score Bot database")
            return False

        # Check current schema
        cursor.execute("PRAGMA table_info(scores)")
        scores_columns_info = cursor.fetchall()
        scores_columns = {row[1] for row in scores_columns_info}

        cursor.execute("PRAGMA table_info(songs)")
        songs_columns_info = cursor.fetchall()
        songs_columns = {row[1] for row in songs_columns_info}

        print(f"[*] Scores table columns: {scores_columns}")
        print(f"[*] Songs table columns: {songs_columns}")

        # Debug: show full table info if columns are empty
        if not scores_columns:
            print(f"[DEBUG] Scores table info raw: {scores_columns_info}")
        if not songs_columns:
            print(f"[DEBUG] Songs table info raw: {songs_columns_info}")

        migrations_run = 0

        # Migrate scores table
        if 'chart_md5' in scores_columns and 'chart_hash' not in scores_columns:
            print("[*] Migrating scores.chart_md5 -> chart_hash...")
            cursor.execute("ALTER TABLE scores RENAME COLUMN chart_md5 TO chart_hash")
            print("  [OK] Renamed scores.chart_md5 -> chart_hash")
            migrations_run += 1
        elif 'chart_hash' in scores_columns:
            print("  [OK] scores.chart_hash already exists (migration already applied)")
        elif not scores_columns:
            print("[!] ERROR: Cannot read scores table schema - table may be corrupt or locked")
            return False
        else:
            print(f"[!] Warning: scores table has unexpected schema: {scores_columns}")

        # Migrate songs table
        if 'chart_md5' in songs_columns and 'chart_hash' not in songs_columns:
            print("[*] Migrating songs.chart_md5 -> chart_hash...")
            cursor.execute("ALTER TABLE songs RENAME COLUMN chart_md5 TO chart_hash")
            print("  [OK] Renamed songs.chart_md5 -> chart_hash")
            migrations_run += 1
        elif 'chart_hash' in songs_columns:
            print("  [OK] songs.chart_hash already exists (migration already applied)")
        elif not songs_columns:
            print("[!] ERROR: Cannot read songs table schema - table may be corrupt or locked")
            return False
        else:
            print(f"[!] Warning: songs table has unexpected schema: {songs_columns}")

        # Migrate record_breaks table (if it exists)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='record_breaks'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(record_breaks)")
            record_breaks_columns_info = cursor.fetchall()
            record_breaks_columns = {row[1] for row in record_breaks_columns_info}

            print(f"[*] Record_breaks table columns: {record_breaks_columns}")

            if 'chart_md5' in record_breaks_columns and 'chart_hash' not in record_breaks_columns:
                print("[*] Migrating record_breaks.chart_md5 -> chart_hash...")
                cursor.execute("ALTER TABLE record_breaks RENAME COLUMN chart_md5 TO chart_hash")
                print("  [OK] Renamed record_breaks.chart_md5 -> chart_hash")
                migrations_run += 1
            elif 'chart_hash' in record_breaks_columns:
                print("  [OK] record_breaks.chart_hash already exists (migration already applied)")
            elif not record_breaks_columns:
                print("[!] ERROR: Cannot read record_breaks table schema - table may be corrupt or locked")
                return False
            else:
                print(f"[!] Warning: record_breaks table has unexpected schema: {record_breaks_columns}")
        else:
            print("  [INFO] record_breaks table does not exist (will be created on first use)")

        # Update migration version
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO migrations (version) VALUES (1)")

        conn.commit()
        conn.close()

        if migrations_run > 0:
            print(f"\n[[OK]] Migration complete! Applied {migrations_run} schema changes.")
        else:
            print("\n[[OK]] Database already up to date!")

        return True

    except Exception as e:
        print(f"[!] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("="*60)
    print("Clone Hero Score Bot - Database Migration v2.4.3")
    print("="*60)

    if len(sys.argv) > 1:
        # User provided a path
        db_path = Path(sys.argv[1])
    else:
        # Try to find the database in AppData
        config_dir = get_config_dir()
        db_path = config_dir / 'scores.db'

        if not db_path.exists():
            # Try local directory as fallback
            db_path = Path('bot/scores.db')

        print(f"[*] No database path provided, using: {db_path}")

    success = run_migration(db_path)

    if success:
        print("\n[*] You can now restart the bot and it should work correctly.")
    else:
        print("\n[!] Migration failed. Please check the error messages above.")
        sys.exit(1)

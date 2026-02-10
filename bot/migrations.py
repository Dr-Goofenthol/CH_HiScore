"""
Database migrations for Clone Hero Score Bot

Migrations run automatically on bot startup to keep database schema up to date.
"""
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_schema_version(cursor):
    """Get current schema version from database"""
    try:
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        # schema_version table doesn't exist yet
        return 0

def set_schema_version(cursor, version):
    """Set schema version in database"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))

def migration_001_chart_hash_rename(cursor):
    """
    Migration 001: Rename chart_md5 to chart_hash

    The data stored is actually the chart hash (blake3) from Clone Hero's scoredata.bin,
    not an MD5 hash. This migration fixes the terminology for clarity.
    """
    logger.info("Running migration 001: Renaming chart_md5 → chart_hash")

    try:
        # Check if scores table has chart_md5 column
        cursor.execute("PRAGMA table_info(scores)")
        columns = {row[1] for row in cursor.fetchall()}

        if 'chart_md5' in columns and 'chart_hash' not in columns:
            # Rename in scores table
            cursor.execute("ALTER TABLE scores RENAME COLUMN chart_md5 TO chart_hash")
            logger.info("  ✓ Renamed scores.chart_md5 → chart_hash")
        elif 'chart_hash' in columns:
            logger.info("  ✓ scores.chart_hash already exists (migration already applied)")

        # Check if songs table exists and has md5_hash column
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(songs)")
            song_columns = {row[1] for row in cursor.fetchall()}

            if 'md5_hash' in song_columns and 'chart_hash' not in song_columns:
                cursor.execute("ALTER TABLE songs RENAME COLUMN md5_hash TO chart_hash")
                logger.info("  ✓ Renamed songs.md5_hash → chart_hash")
            elif 'chart_hash' in song_columns:
                logger.info("  ✓ songs.chart_hash already exists (migration already applied)")

        # Check if record_breaks table exists and has chart_md5 column
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='record_breaks'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(record_breaks)")
            record_columns = {row[1] for row in cursor.fetchall()}

            if 'chart_md5' in record_columns and 'chart_hash' not in record_columns:
                cursor.execute("ALTER TABLE record_breaks RENAME COLUMN chart_md5 TO chart_hash")
                logger.info("  ✓ Renamed record_breaks.chart_md5 → chart_hash")
            elif 'chart_hash' in record_columns:
                logger.info("  ✓ record_breaks.chart_hash already exists (migration already applied)")

        logger.info("Migration 001 complete")

    except sqlite3.OperationalError as e:
        logger.error(f"Migration 001 failed: {e}")
        raise

def migration_002_complete_chart_hash_rename(cursor):
    """
    Migration 002: Complete the chart_hash rename that migration 001 may have missed

    Migration 001 sometimes only partially completed, migrating scores but not songs/record_breaks.
    This migration ensures ALL tables are migrated before proceeding with indexes.
    """
    logger.info("Running migration 002: Completing chart_hash rename")

    try:
        # Check and migrate songs table if needed
        cursor.execute("PRAGMA table_info(songs)")
        songs_columns = {row[1] for row in cursor.fetchall()}

        if 'chart_md5' in songs_columns and 'chart_hash' not in songs_columns:
            logger.info("  [FIX] Found songs.chart_md5, renaming to chart_hash...")
            cursor.execute("ALTER TABLE songs RENAME COLUMN chart_md5 TO chart_hash")
            logger.info("  [OK] Renamed songs.chart_md5 → chart_hash")
        elif 'chart_hash' in songs_columns:
            logger.info("  [OK] songs.chart_hash already exists")

        # Check and migrate record_breaks table if needed
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='record_breaks'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(record_breaks)")
            rb_columns = {row[1] for row in cursor.fetchall()}

            if 'chart_md5' in rb_columns and 'chart_hash' not in rb_columns:
                logger.info("  [FIX] Found record_breaks.chart_md5, renaming to chart_hash...")
                cursor.execute("ALTER TABLE record_breaks RENAME COLUMN chart_md5 TO chart_hash")
                logger.info("  [OK] Renamed record_breaks.chart_md5 → chart_hash")
            elif 'chart_hash' in rb_columns:
                logger.info("  [OK] record_breaks.chart_hash already exists")

        # Now recreate indexes with correct column names
        # Only if the tables exist (skip on fresh install - tables created later by create_tables())
        logger.info("  [*] Recreating indexes...")
        cursor.execute("DROP INDEX IF EXISTS idx_scores_chart")
        cursor.execute("DROP INDEX IF EXISTS idx_songs_md5")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
        if cursor.fetchone():
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scores_chart
                ON scores(chart_hash, instrument_id, difficulty_id)
            """)
            logger.info("  [OK] idx_scores_chart created")
        else:
            logger.info("  [SKIP] scores table not yet created, indexes will be created on first use")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='songs'")
        if cursor.fetchone():
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_songs_hash
                ON songs(chart_hash)
            """)
            logger.info("  [OK] idx_songs_hash created")
        else:
            logger.info("  [SKIP] songs table not yet created, indexes will be created on first use")

        logger.info("  [OK] Indexes step complete")

        logger.info("Migration 002 complete")

    except sqlite3.OperationalError as e:
        logger.error(f"Migration 002 failed: {e}")
        raise


def migration_003_chart_metadata_and_fc_tracking(cursor):
    """
    Migration 003: Add chart_metadata table and FC tracking for v2.6.0

    Features:
    - Store parsed chart data (total notes, density, etc.)
    - Track Full Combos (is_full_combo flag)
    - Display accurate note counts (notes_total)
    """
    logger.info("Running migration 003: Chart metadata and FC tracking (v2.6.0)")

    try:
        # Create chart_metadata table
        logger.info("  [*] Creating chart_metadata table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chart_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chart_hash TEXT NOT NULL,
                instrument_id INTEGER NOT NULL,
                difficulty_id INTEGER NOT NULL,

                -- Core chart data
                total_notes INTEGER NOT NULL,
                chord_count INTEGER DEFAULT 0,
                tap_count INTEGER DEFAULT 0,
                open_note_count INTEGER DEFAULT 0,
                star_power_phrases INTEGER DEFAULT 0,

                -- Timing data
                song_length_ms INTEGER DEFAULT 0,
                note_density REAL DEFAULT 0.0,

                -- Metadata
                song_name TEXT,
                artist TEXT,
                charter TEXT,
                genre TEXT,

                -- Tracking
                parsed_at TEXT NOT NULL,
                chart_file_path TEXT,

                UNIQUE(chart_hash, instrument_id, difficulty_id)
            )
        """)
        logger.info("  [OK] chart_metadata table created")

        # Create indexes for performance
        logger.info("  [*] Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chart_metadata_hash
            ON chart_metadata(chart_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chart_metadata_density
            ON chart_metadata(note_density DESC)
        """)
        logger.info("  [OK] Indexes created")

        # Add FC tracking columns to scores table
        logger.info("  [*] Adding FC tracking to scores table...")

        # Check if scores table exists (skip ALTER on fresh install - columns are in base schema)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(scores)")
            columns = {row[1] for row in cursor.fetchall()}

            if 'is_full_combo' not in columns:
                cursor.execute("ALTER TABLE scores ADD COLUMN is_full_combo INTEGER DEFAULT 0")
                logger.info("  [OK] Added scores.is_full_combo column")
            else:
                logger.info("  [OK] scores.is_full_combo already exists")

            if 'notes_total' not in columns:
                cursor.execute("ALTER TABLE scores ADD COLUMN notes_total INTEGER DEFAULT 0")
                logger.info("  [OK] Added scores.notes_total column")
            else:
                logger.info("  [OK] scores.notes_total already exists")
        else:
            logger.info("  [SKIP] scores table not yet created, columns included in base schema")

        logger.info("Migration 003 complete")

    except sqlite3.OperationalError as e:
        logger.error(f"Migration 003 failed: {e}")
        raise


def migration_004_peak_nps_tracking(cursor):
    """
    Migration 004: Add peak NPS tracking for v2.6.3

    Features:
    - Add peak_note_density to chart_metadata table
    - Allows tracking and displaying "Peak Intensity" in announcements
    - Matches Bridge's peak NPS calculation (1-second window)
    """
    logger.info("Running migration 004: Peak NPS tracking (v2.6.3)")

    try:
        # Check if chart_metadata table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chart_metadata'")
        if not cursor.fetchone():
            logger.info("  [SKIP] chart_metadata table doesn't exist yet (will be created by migration 003)")
            return

        # Check if peak_note_density column already exists
        cursor.execute("PRAGMA table_info(chart_metadata)")
        columns = {row[1] for row in cursor.fetchall()}

        if 'peak_note_density' not in columns:
            logger.info("  [*] Adding peak_note_density to chart_metadata table...")
            cursor.execute("ALTER TABLE chart_metadata ADD COLUMN peak_note_density REAL DEFAULT 0.0")
            logger.info("  [OK] Added chart_metadata.peak_note_density column")
        else:
            logger.info("  [OK] chart_metadata.peak_note_density already exists")

        # Create index for peak NPS queries (for /hardest peak command)
        logger.info("  [*] Creating index for peak NPS queries...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chart_metadata_peak_density
            ON chart_metadata(peak_note_density DESC)
        """)
        logger.info("  [OK] Peak NPS index created")

        logger.info("Migration 004 complete")

    except sqlite3.OperationalError as e:
        logger.error(f"Migration 004 failed: {e}")
        raise


def run_migrations(db_path):
    """
    Run all pending migrations on the database

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        current_version = get_schema_version(cursor)
        logger.info(f"Current database schema version: {current_version}")

        # List of all migrations in order
        migrations = [
            (1, migration_001_chart_hash_rename),
            (2, migration_002_complete_chart_hash_rename),
            (3, migration_003_chart_metadata_and_fc_tracking),  # v2.6.0
            (4, migration_004_peak_nps_tracking),               # v2.6.3
        ]

        # Run pending migrations
        for version, migration_func in migrations:
            if version > current_version:
                logger.info(f"Applying migration {version}...")
                migration_func(cursor)
                set_schema_version(cursor, version)
                conn.commit()
                logger.info(f"Migration {version} applied successfully")

        final_version = get_schema_version(cursor)
        if final_version > current_version:
            logger.info(f"Database migrated from version {current_version} → {final_version}")
        else:
            logger.info("Database is up to date")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    # Test migrations
    logging.basicConfig(level=logging.INFO)
    db_path = Path(__file__).parent / 'scores.db'
    run_migrations(db_path)

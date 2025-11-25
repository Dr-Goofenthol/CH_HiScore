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
            # Future migrations go here:
            # (2, migration_002_description),
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

# Database Migration Troubleshooting

## Issue: Database migration not running automatically

### Symptoms
- Bot shows error: `table X has no column named Y`
- Migration appears to skip or fail silently
- Database has outdated schema

### Root Cause
The database file may be locked by a running bot process, preventing migrations from completing properly.

### Solution Steps

#### Option 1: Stop bot FIRST, then run standalone migration (RECOMMENDED)

1. **Stop the bot completely**
   - Close the bot executable window
   - Make sure no bot process is running (check Task Manager if needed)

2. **Run the standalone migration script**
   ```
   py run_migration.py
   ```
   Or provide a specific database path:
   ```
   py run_migration.py "C:\path\to\scores.db"
   ```

3. **Restart the bot**
   The database should now be up to date.

#### Option 2: Let bot migrate on startup

1. **Stop the bot completely**
2. **Start the bot** - it will run migrations automatically
3. **Check the bot console** for migration messages:
   ```
   [*] Running database migrations...
   Current database schema version: X
   Applying migration Y...
   Migration Y applied successfully
   ```

#### Option 3: Manual SQL migration

If automated migration fails, you can manually update the database:

1. **Stop the bot completely**

2. **Install SQLite tools** (if not already installed):
   - Download from https://www.sqlite.org/download.html
   - Or use: `winget install SQLite.SQLite` (Windows 11)

3. **Open the database**:
   ```bash
   cd C:\Users\[YourUser]\AppData\Roaming\CloneHeroScoreBot
   sqlite3 scores.db
   ```

4. **Check current schema**:
   ```sql
   PRAGMA table_info(scores);
   PRAGMA table_info(songs);
   PRAGMA table_info(record_breaks);
   SELECT * FROM schema_version;
   ```

5. **Manually run migrations if needed** (see bot/migrations.py for current migrations)

6. **Exit and restart the bot**:
   ```sql
   .quit
   ```

#### Option 4: Fresh start (last resort)

If all else fails and you don't mind losing score history:

1. **Stop the bot**
2. **Backup and remove old database**:
   ```
   cd C:\Users\[YourUser]\AppData\Roaming\CloneHeroScoreBot
   ren scores.db scores.db.backup
   ```
3. **Start the bot** - it will create a new database with correct schema

### Database Locations

**Bot database:**
- Windows: `%APPDATA%\Roaming\CloneHeroScoreBot\scores.db`
- Linux/Mac: `~/.config/CloneHeroScoreBot/scores.db`

**Client config:**
- Stored inside Clone Hero directory: `[CH_DIR]\.score_tracker_config.json`

### Why Migrations Fail

Common reasons:
1. **Bot is running** - Database file is locked
2. **Permissions** - User doesn't have write access to database file
3. **Corruption** - Database file is corrupted (use Option 4)
4. **Wrong database** - Bot is using a different database than you're migrating

### Testing After Migration

Test with a debug command in the client:
```
debug> send_test_score -song "test1" -score 10 -instrument 0 -difficulty 0 -stars 1 -accuracy 20.0
```

Expected result:
- Score should be accepted by the bot
- No database errors in bot console
- `/leaderboard` command should work

### Checking Migration Status

From Python:
```python
import sqlite3
conn = sqlite3.connect('scores.db')
cursor = conn.cursor()
cursor.execute('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1')
print(f"Current schema version: {cursor.fetchone()[0]}")
conn.close()
```

Current schema version should match the latest migration number in `bot/migrations.py`.

### Key Lesson

**Always stop the bot before running database migrations to avoid file locking issues.**

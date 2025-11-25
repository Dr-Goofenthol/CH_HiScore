"""
Database module for Clone Hero High Score System

Handles all database operations using SQLite.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import secrets
from .config import Config


class Database:
    """SQLite database manager for high scores"""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (defaults to config)
        """
        self.db_path = db_path or Config.DATABASE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()
        print(f"[DB] Connected to database: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DB] Database connection closed")

    def initialize_schema(self):
        """Create database tables if they don't exist"""
        print("[DB] Initializing database schema...")

        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                discord_username TEXT NOT NULL,
                auth_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Scores table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chart_hash TEXT NOT NULL,
                instrument_id INTEGER NOT NULL,
                difficulty_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                completion_percent REAL NOT NULL,
                stars INTEGER NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(chart_hash, instrument_id, difficulty_id, user_id)
            )
        """)

        # Songs table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chart_hash TEXT UNIQUE NOT NULL,
                title TEXT,
                artist TEXT,
                album TEXT,
                charter TEXT,
                length_ms INTEGER,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Pairing codes table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pairing_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                discord_id TEXT,
                auth_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                completed BOOLEAN DEFAULT 0
            )
        """)

        # Record breaks tracking table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS record_breaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chart_hash TEXT NOT NULL,
                instrument_id INTEGER NOT NULL,
                difficulty_id INTEGER NOT NULL,
                new_score INTEGER NOT NULL,
                previous_score INTEGER,
                previous_holder_id INTEGER,
                broken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (previous_holder_id) REFERENCES users(id)
            )
        """)

        # Create indexes for performance
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scores_chart
            ON scores(chart_hash, instrument_id, difficulty_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scores_user
            ON scores(user_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pairing_code
            ON pairing_codes(code)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_songs_hash
            ON songs(chart_hash)
        """)

        self.conn.commit()
        print("[DB] Schema initialized successfully")

    # ========================================================================
    # USER OPERATIONS
    # ========================================================================

    def create_user(self, discord_id: str, discord_username: str) -> Tuple[int, str]:
        """
        Create a new user and generate auth token

        Args:
            discord_id: Discord user ID
            discord_username: Discord username

        Returns:
            Tuple of (user_id, auth_token)
        """
        auth_token = secrets.token_urlsafe(32)

        self.cursor.execute("""
            INSERT INTO users (discord_id, discord_username, auth_token)
            VALUES (?, ?, ?)
        """, (discord_id, discord_username, auth_token))

        self.conn.commit()
        user_id = self.cursor.lastrowid

        print(f"[DB] Created user: {discord_username} (ID: {user_id})")
        return user_id, auth_token

    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict]:
        """Get user by Discord ID"""
        self.cursor.execute("""
            SELECT * FROM users WHERE discord_id = ?
        """, (discord_id,))

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_auth_token(self, auth_token: str) -> Optional[Dict]:
        """Get user by auth token"""
        self.cursor.execute("""
            SELECT * FROM users WHERE auth_token = ?
        """, (auth_token,))

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_user_last_seen(self, user_id: int):
        """Update user's last seen timestamp"""
        self.cursor.execute("""
            UPDATE users SET last_seen = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()

    # ========================================================================
    # PAIRING OPERATIONS
    # ========================================================================

    def create_pairing_code(self, client_id: str, expires_minutes: int = 5) -> str:
        """
        Generate a new pairing code

        Args:
            client_id: Unique client identifier
            expires_minutes: Minutes until code expires

        Returns:
            6-character pairing code
        """
        # Generate random 6-character code
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))

        expires_at = datetime.now() + timedelta(minutes=expires_minutes)

        self.cursor.execute("""
            INSERT INTO pairing_codes (code, client_id, expires_at)
            VALUES (?, ?, ?)
        """, (code, client_id, expires_at))

        self.conn.commit()
        print(f"[DB] Created pairing code: {code} (expires in {expires_minutes} min)")
        return code

    def get_pairing_code(self, code: str) -> Optional[Dict]:
        """Get pairing code info"""
        self.cursor.execute("""
            SELECT * FROM pairing_codes WHERE code = ?
        """, (code,))

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def complete_pairing(self, code: str, discord_id: str, discord_username: str) -> Optional[str]:
        """
        Complete the pairing process

        Args:
            code: Pairing code
            discord_id: Discord user ID
            discord_username: Discord username

        Returns:
            Auth token if successful, None otherwise
        """
        pairing = self.get_pairing_code(code)

        if not pairing:
            return None

        # Check if expired
        expires_at = datetime.fromisoformat(pairing['expires_at'])
        if datetime.now() > expires_at:
            print(f"[DB] Pairing code {code} has expired")
            return None

        # Check if already completed
        if pairing['completed']:
            print(f"[DB] Pairing code {code} already used")
            return None

        # Create or get user
        user = self.get_user_by_discord_id(discord_id)
        if user:
            auth_token = user['auth_token']
            print(f"[DB] User already exists: {discord_username}")
        else:
            _, auth_token = self.create_user(discord_id, discord_username)

        # Mark pairing as completed
        self.cursor.execute("""
            UPDATE pairing_codes
            SET discord_id = ?, auth_token = ?, completed = 1
            WHERE code = ?
        """, (discord_id, auth_token, code))

        self.conn.commit()
        print(f"[DB] Pairing completed: {code} -> {discord_username}")
        return auth_token

    def check_pairing_status(self, client_id: str) -> Optional[str]:
        """
        Check if a client has been paired

        Args:
            client_id: Client identifier

        Returns:
            Auth token if paired, None otherwise
        """
        self.cursor.execute("""
            SELECT auth_token FROM pairing_codes
            WHERE client_id = ? AND completed = 1
            ORDER BY created_at DESC
            LIMIT 1
        """, (client_id,))

        row = self.cursor.fetchone()
        return row['auth_token'] if row else None

    # ========================================================================
    # SCORE OPERATIONS
    # ========================================================================

    def submit_score(self, auth_token: str, chart_hash: str, instrument_id: int,
                    difficulty_id: int, score: int, completion_percent: float,
                    stars: int, song_title: str = "", song_artist: str = "") -> Dict:
        """
        Submit a score and check if it's a new high score

        Args:
            auth_token: User's auth token
            chart_hash: Chart hash identifier (blake3 from Clone Hero)
            instrument_id: Instrument (0=lead, 1=bass, etc)
            difficulty_id: Difficulty (0=easy, 1=medium, 2=hard, 3=expert)
            score: Score value
            completion_percent: Accuracy percentage
            stars: Star rating
            song_title: Song title (optional)
            song_artist: Song artist (optional)

        Returns:
            Dictionary with result info (is_high_score, previous_score, etc)
        """
        # Get user
        user = self.get_user_by_auth_token(auth_token)
        if not user:
            return {'success': False, 'error': 'Invalid auth token'}

        user_id = user['id']

        # Save/update song info if provided
        if song_title:
            self.save_song_info(chart_hash, song_title, song_artist)

        # Get current high score for this chart/instrument/difficulty
        self.cursor.execute("""
            SELECT s.*, u.discord_username as holder_name
            FROM scores s
            JOIN users u ON s.user_id = u.id
            WHERE s.chart_hash = ?
            AND s.instrument_id = ?
            AND s.difficulty_id = ?
            ORDER BY s.score DESC
            LIMIT 1
        """, (chart_hash, instrument_id, difficulty_id))

        current_high = self.cursor.fetchone()
        current_high_score = dict(current_high) if current_high else None

        is_new_high_score = False
        is_record_broken = False  # Only true when beating an EXISTING record
        previous_holder = None
        previous_holder_discord_id = None
        previous_holder_id = None

        if current_high_score:
            # There's an existing score - check if we beat it
            is_new_high_score = score > current_high_score['score']
            if is_new_high_score:
                # We beat an existing record - this should trigger announcement
                is_record_broken = True
                previous_holder_id = current_high_score['user_id']
                # Always include the previous holder info (even if same user)
                previous_holder = current_high_score['holder_name']
                # Get previous holder's discord_id for mention
                self.cursor.execute("""
                    SELECT discord_id FROM users WHERE id = ?
                """, (current_high_score['user_id'],))
                prev_user = self.cursor.fetchone()
                if prev_user:
                    previous_holder_discord_id = prev_user['discord_id']
        else:
            # No existing score - this is the first score for this chart
            # It's technically a "high score" but NOT a "record broken"
            is_new_high_score = True
            is_record_broken = False  # Don't announce first-time scores

        # Insert or update user's score
        self.cursor.execute("""
            INSERT INTO scores (user_id, chart_hash, instrument_id, difficulty_id,
                              score, completion_percent, stars)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chart_hash, instrument_id, difficulty_id, user_id)
            DO UPDATE SET
                score = excluded.score,
                completion_percent = excluded.completion_percent,
                stars = excluded.stars,
                submitted_at = CURRENT_TIMESTAMP
        """, (user_id, chart_hash, instrument_id, difficulty_id, score,
              completion_percent, stars))

        # Record the record break if applicable
        if is_record_broken:
            self.record_break(
                user_id=user_id,
                chart_hash=chart_hash,
                instrument_id=instrument_id,
                difficulty_id=difficulty_id,
                new_score=score,
                previous_score=current_high_score['score'] if current_high_score else None,
                previous_holder_id=previous_holder_id
            )

        self.conn.commit()

        # Update last seen
        self.update_user_last_seen(user_id)

        # Get the user's personal best for this chart (for feedback)
        your_best_score = None
        if not is_new_high_score:
            self.cursor.execute("""
                SELECT score FROM scores
                WHERE chart_hash = ? AND instrument_id = ? AND difficulty_id = ? AND user_id = ?
            """, (chart_hash, instrument_id, difficulty_id, user_id))
            user_score = self.cursor.fetchone()
            if user_score:
                your_best_score = user_score['score']

        result = {
            'success': True,
            'is_high_score': is_new_high_score,
            'is_record_broken': is_record_broken,  # Only true when beating existing record
            'score': score,
            'previous_score': current_high_score['score'] if current_high_score else None,
            'previous_holder': previous_holder,
            'previous_holder_discord_id': previous_holder_discord_id,
            'your_best_score': your_best_score,  # User's PB for feedback when not a high score
            'user_id': user_id,
            'username': user['discord_username'],
            'discord_id': user['discord_id']
        }

        print(f"[DB] Score submitted: {user['discord_username']} - {score:,} "
              f"({'NEW HIGH SCORE!' if is_new_high_score else 'not a high score'})")

        return result

    def save_song_info(self, chart_hash: str, title: str, artist: str = ""):
        """Save or update song information"""
        self.cursor.execute("""
            INSERT INTO songs (chart_hash, title, artist)
            VALUES (?, ?, ?)
            ON CONFLICT(chart_hash) DO UPDATE SET
                title = COALESCE(NULLIF(excluded.title, ''), songs.title),
                artist = COALESCE(NULLIF(excluded.artist, ''), songs.artist)
        """, (chart_hash, title, artist))
        self.conn.commit()

    def record_break(self, user_id: int, chart_hash: str, instrument_id: int,
                    difficulty_id: int, new_score: int, previous_score: int = None,
                    previous_holder_id: int = None):
        """Record a record break event"""
        self.cursor.execute("""
            INSERT INTO record_breaks (user_id, chart_hash, instrument_id, difficulty_id,
                                      new_score, previous_score, previous_holder_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, chart_hash, instrument_id, difficulty_id, new_score,
              previous_score, previous_holder_id))

    def get_song_title(self, chart_hash: str) -> str:
        """Get song title by chart hash, returns short hash if not found"""
        self.cursor.execute("SELECT title FROM songs WHERE chart_hash = ?", (chart_hash,))
        row = self.cursor.fetchone()
        if row and row['title']:
            return row['title']
        return f"[{chart_hash[:8]}]"

    def get_high_score(self, chart_hash: str, instrument_id: int, difficulty_id: int) -> Optional[Dict]:
        """Get the current high score for a specific chart/instrument/difficulty"""
        self.cursor.execute("""
            SELECT s.*, u.discord_username, u.discord_id
            FROM scores s
            JOIN users u ON s.user_id = u.id
            WHERE s.chart_hash = ?
            AND s.instrument_id = ?
            AND s.difficulty_id = ?
            ORDER BY s.score DESC
            LIMIT 1
        """, (chart_hash, instrument_id, difficulty_id))

        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_leaderboard(self, limit: int = 10, instrument_id: int = None,
                       difficulty_id: int = None) -> List[Dict]:
        """
        Get leaderboard (top scores)

        Args:
            limit: Number of scores to return
            instrument_id: Filter by instrument (optional)
            difficulty_id: Filter by difficulty (optional)

        Returns:
            List of top scores with user info and song titles
        """
        query = """
            SELECT s.*, u.discord_username, u.discord_id,
                   COALESCE(songs.title, '[' || SUBSTR(s.chart_hash, 1, 8) || ']') as song_title,
                   songs.artist as song_artist,
                   ROW_NUMBER() OVER (
                       PARTITION BY s.chart_hash, s.instrument_id, s.difficulty_id
                       ORDER BY s.score DESC
                   ) as rank
            FROM scores s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN songs ON s.chart_hash = songs.chart_hash
        """

        conditions = []
        params = []

        if instrument_id is not None:
            conditions.append("s.instrument_id = ?")
            params.append(instrument_id)

        if difficulty_id is not None:
            conditions.append("s.difficulty_id = ?")
            params.append(difficulty_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Only get the #1 score for each chart/instrument/difficulty combo
        query = f"""
            SELECT * FROM ({query})
            WHERE rank = 1
            ORDER BY score DESC
            LIMIT ?
        """
        params.append(limit)

        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_user_stats(self, discord_id: str) -> Optional[Dict]:
        """
        Get statistics for a user

        Returns:
            Dictionary with user stats
        """
        user = self.get_user_by_discord_id(discord_id)
        if not user:
            return None

        user_id = user['id']

        # Total scores submitted
        self.cursor.execute("""
            SELECT COUNT(*) as total_scores FROM scores WHERE user_id = ?
        """, (user_id,))
        total_scores = self.cursor.fetchone()['total_scores']

        # High scores held
        self.cursor.execute("""
            SELECT COUNT(*) as high_scores_held
            FROM scores s1
            WHERE s1.user_id = ?
            AND s1.score = (
                SELECT MAX(s2.score)
                FROM scores s2
                WHERE s2.chart_hash = s1.chart_hash
                AND s2.instrument_id = s1.instrument_id
                AND s2.difficulty_id = s1.difficulty_id
            )
        """, (user_id,))
        high_scores_held = self.cursor.fetchone()['high_scores_held']

        # Total record breaks achieved
        self.cursor.execute("""
            SELECT COUNT(*) as record_breaks FROM record_breaks WHERE user_id = ?
        """, (user_id,))
        record_breaks = self.cursor.fetchone()['record_breaks']

        # Average accuracy
        self.cursor.execute("""
            SELECT AVG(completion_percent) as avg_accuracy FROM scores WHERE user_id = ?
        """, (user_id,))
        avg_accuracy = self.cursor.fetchone()['avg_accuracy'] or 0

        # Average stars
        self.cursor.execute("""
            SELECT AVG(stars) as avg_stars FROM scores WHERE user_id = ?
        """, (user_id,))
        avg_stars = self.cursor.fetchone()['avg_stars'] or 0

        # Total score points across all songs
        self.cursor.execute("""
            SELECT SUM(score) as total_points FROM scores WHERE user_id = ?
        """, (user_id,))
        total_points = self.cursor.fetchone()['total_points'] or 0

        return {
            'username': user['discord_username'],
            'total_scores': total_scores,
            'high_scores_held': high_scores_held,
            'record_breaks': record_breaks,
            'avg_accuracy': round(avg_accuracy, 2),
            'avg_stars': round(avg_stars, 2),
            'total_points': total_points,
            'member_since': user['created_at']
        }

    def get_user_records(self, discord_id: str, limit: int = 5) -> List[Dict]:
        """
        Get list of records held by a user

        Returns:
            List of records with song titles
        """
        user = self.get_user_by_discord_id(discord_id)
        if not user:
            return []

        user_id = user['id']

        self.cursor.execute("""
            SELECT s.chart_hash, s.instrument_id, s.difficulty_id, s.score, s.stars,
                   COALESCE(songs.title, '[' || SUBSTR(s.chart_hash, 1, 8) || ']') as song_title,
                   songs.artist as song_artist
            FROM scores s
            LEFT JOIN songs ON s.chart_hash = songs.chart_hash
            WHERE s.user_id = ?
            AND s.score = (
                SELECT MAX(s2.score)
                FROM scores s2
                WHERE s2.chart_hash = s.chart_hash
                AND s2.instrument_id = s.instrument_id
                AND s2.difficulty_id = s.difficulty_id
            )
            ORDER BY s.score DESC
            LIMIT ?
        """, (user_id, limit))

        return [dict(row) for row in self.cursor.fetchall()]

    def get_song_info(self, chart_hash: str) -> Optional[Dict]:
        """Get complete song info by chart hash"""
        self.cursor.execute("""
            SELECT * FROM songs WHERE chart_hash = ?
        """, (chart_hash,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_songs(self, query: str, limit: int = 10) -> List[Dict]:
        """Search songs by title (partial match)"""
        self.cursor.execute("""
            SELECT * FROM songs
            WHERE title LIKE ?
            ORDER BY title
            LIMIT ?
        """, (f'%{query}%', limit))
        return [dict(row) for row in self.cursor.fetchall()]

    def update_song_artist(self, chart_hash: str, artist: str) -> bool:
        """Update artist for a song by chart hash"""
        self.cursor.execute("""
            UPDATE songs SET artist = ? WHERE chart_hash = ?
        """, (artist, chart_hash))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def update_song_metadata(self, chart_hash: str, title: str = None, artist: str = None) -> bool:
        """
        Update song title and/or artist by chart hash

        Args:
            chart_hash: Chart hash identifier
            title: New title (None = don't change)
            artist: New artist (None = don't change)

        Returns:
            True if updated, False otherwise
        """
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if artist is not None:
            updates.append("artist = ?")
            params.append(artist)

        if not updates:
            return False

        params.append(chart_hash)

        self.cursor.execute(f"""
            UPDATE songs SET {', '.join(updates)} WHERE chart_hash = ?
        """, params)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_songs_without_artist(self, limit: int = 20) -> List[Dict]:
        """Get songs that don't have artist info"""
        self.cursor.execute("""
            SELECT s.chart_hash, s.title,
                   COUNT(sc.id) as score_count
            FROM songs s
            LEFT JOIN scores sc ON s.chart_hash = sc.chart_hash
            WHERE s.artist IS NULL OR s.artist = ''
            GROUP BY s.chart_hash
            ORDER BY score_count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_recent_record_breaks(self, limit: int = 10) -> List[Dict]:
        """
        Get recent record breaks with user and song info

        Args:
            limit: Number of record breaks to return (max 20)

        Returns:
            List of recent record breaks with details
        """
        limit = min(limit, 20)  # Cap at 20

        self.cursor.execute("""
            SELECT rb.*,
                   u.discord_username as breaker_name,
                   u.discord_id as breaker_discord_id,
                   prev.discord_username as previous_holder_name,
                   COALESCE(songs.title, '[' || SUBSTR(rb.chart_hash, 1, 8) || ']') as song_title,
                   songs.artist as song_artist
            FROM record_breaks rb
            JOIN users u ON rb.user_id = u.id
            LEFT JOIN users prev ON rb.previous_holder_id = prev.id
            LEFT JOIN songs ON rb.chart_hash = songs.chart_hash
            ORDER BY rb.broken_at DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in self.cursor.fetchall()]

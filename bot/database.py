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
from shared.console import print_success, print_info, print_warning, print_error


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
        print_info(f"[DB] Connected to database: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print_info("[DB] Database connection closed")

    def initialize_schema(self):
        """Create database tables if they don't exist"""
        print_info("[DB] Initializing database schema...")

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

        # Metadata table for bot settings
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        print_success("[DB] Schema initialized successfully")

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

        print_success(f"[DB] Created user: {discord_username} (ID: {user_id})")
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
        print_info(f"[DB] Created pairing code: {code} (expires in {expires_minutes} min)")
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
            print_warning(f"[DB] Pairing code {code} has expired")
            return None

        # Check if already completed
        if pairing['completed']:
            print_warning(f"[DB] Pairing code {code} already used")
            return None

        # Create or get user
        user = self.get_user_by_discord_id(discord_id)
        if user:
            auth_token = user['auth_token']
            print_info(f"[DB] User already exists: {discord_username}")
        else:
            _, auth_token = self.create_user(discord_id, discord_username)

        # Mark pairing as completed
        self.cursor.execute("""
            UPDATE pairing_codes
            SET discord_id = ?, auth_token = ?, completed = 1
            WHERE code = ?
        """, (discord_id, auth_token, code))

        self.conn.commit()
        print_success(f"[DB] Pairing completed: {code} -> {discord_username}")
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
                    stars: int, song_title: str = "", song_artist: str = "",
                    song_charter: str = "") -> Dict:
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
            song_charter: Charter name (optional)

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
            self.save_song_info(chart_hash, song_title, song_artist, song_charter)

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

        # Get user's previous score for this chart (for personal best detection)
        self.cursor.execute("""
            SELECT score FROM scores
            WHERE chart_hash = ? AND instrument_id = ? AND difficulty_id = ? AND user_id = ?
        """, (chart_hash, instrument_id, difficulty_id, user_id))
        user_previous = self.cursor.fetchone()
        user_previous_score = user_previous['score'] if user_previous else None

        is_new_high_score = False
        is_record_broken = False  # Only true when beating an EXISTING server record
        is_first_time_score = False  # True when NO scores exist for this chart/diff/inst
        is_personal_best = False  # True when improving own score but not beating server record
        previous_holder = None
        previous_holder_discord_id = None
        previous_holder_id = None

        if current_high_score:
            # There's an existing server record - check if we beat it
            is_new_high_score = score > current_high_score['score']
            if is_new_high_score:
                # We beat an existing record
                is_record_broken = True
                previous_holder_id = current_high_score['user_id']
                previous_holder = current_high_score['holder_name']
                # Get previous holder's discord_id for mention
                self.cursor.execute("""
                    SELECT discord_id FROM users WHERE id = ?
                """, (current_high_score['user_id'],))
                prev_user = self.cursor.fetchone()
                if prev_user:
                    previous_holder_discord_id = prev_user['discord_id']
            elif user_previous_score and score > user_previous_score:
                # Improved own score but didn't beat server record
                is_personal_best = True
        else:
            # No existing scores from any user - this is a first-time score
            is_new_high_score = True
            is_first_time_score = True
            is_record_broken = False

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
            'is_first_time_score': is_first_time_score,  # True when first score on chart
            'is_personal_best': is_personal_best,  # True when improving own score (not server record)
            'score': score,
            'previous_score': current_high_score['score'] if current_high_score else None,
            'previous_holder': previous_holder,
            'previous_holder_discord_id': previous_holder_discord_id,
            'previous_record_timestamp': current_high_score['submitted_at'] if current_high_score else None,
            'user_previous_score': user_previous_score,  # User's previous score for PB calculation
            'your_best_score': your_best_score,  # User's PB for feedback when not a high score
            'current_server_record': current_high_score['score'] if current_high_score else None,
            'current_server_record_holder': current_high_score['holder_name'] if current_high_score else None,
            'user_id': user_id,
            'username': user['discord_username'],
            'discord_id': user['discord_id']
        }

        # Determine score type for terminal output
        if is_record_broken:
            score_type = "RECORD BROKEN!"
        elif is_first_time_score:
            score_type = "FIRST SCORE!"
        elif is_personal_best:
            score_type = "PERSONAL BEST!"
        elif is_new_high_score:
            score_type = "NEW HIGH SCORE!"
        else:
            score_type = "not a high score"

        print_info(f"[DB] Score submitted: {user['discord_username']} - {score:,} ({score_type})")

        return result

    def save_song_info(self, chart_hash: str, title: str, artist: str = "", charter: str = ""):
        """Save or update song information"""
        self.cursor.execute("""
            INSERT INTO songs (chart_hash, title, artist, charter)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chart_hash) DO UPDATE SET
                title = COALESCE(NULLIF(excluded.title, ''), songs.title),
                artist = COALESCE(NULLIF(excluded.artist, ''), songs.artist),
                charter = COALESCE(NULLIF(excluded.charter, ''), songs.charter)
        """, (chart_hash, title, artist, charter))
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

    def get_all_records_for_chart(self, chart_hash: str) -> List[Dict]:
        """
        Get all high scores for a chart across all instrument/difficulty combinations

        Args:
            chart_hash: The chart hash to look up

        Returns:
            List of records with user info, one per instrument/difficulty combo
        """
        self.cursor.execute("""
            SELECT s.*, u.discord_username, u.discord_id,
                   DATE(s.submitted_at) as record_date
            FROM scores s
            JOIN users u ON s.user_id = u.id
            WHERE s.chart_hash = ?
            AND s.id IN (
                SELECT id FROM scores s2
                WHERE s2.chart_hash = s.chart_hash
                AND s2.instrument_id = s.instrument_id
                AND s2.difficulty_id = s.difficulty_id
                ORDER BY s2.score DESC
                LIMIT 1
            )
            ORDER BY s.instrument_id, s.difficulty_id
        """, (chart_hash,))
        return [dict(row) for row in self.cursor.fetchall()]

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
                   songs.charter as song_charter,
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
                   songs.artist as song_artist,
                   songs.charter as song_charter
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
        """
        Search songs by title, artist, or chart hash with smart filtering

        Filters out common stop words and uses tiered matching:
        1. Exact phrase matches (highest priority)
        2. All meaningful words match (AND logic)
        3. Partial word matches (for 3+ word queries)
        """
        # Handle empty query
        if not query or not query.strip():
            return []

        # Stop words to filter out
        STOP_WORDS = {'the', 'and', 'a', 'an', 'of', 'in', 'on', 'at', 'to',
                      'for', 'with', 'by', 'from', 'as', 'is', 'it', 'or'}

        # Split query and filter out stop words and short words
        all_words = query.strip().lower().split()
        meaningful_words = [
            word for word in all_words
            if len(word) >= 3 and word not in STOP_WORDS
        ]

        # If no meaningful words remain, use original query
        if not meaningful_words:
            meaningful_words = all_words

        results = []
        seen_hashes = set()  # Prevent duplicates across tiers

        # TIER 1: Exact phrase match (highest priority)
        self.cursor.execute("""
            SELECT * FROM songs
            WHERE title LIKE ? OR artist LIKE ? OR chart_hash LIKE ?
            ORDER BY
                CASE
                    WHEN LOWER(title) = LOWER(?) THEN 0
                    WHEN LOWER(artist) = LOWER(?) THEN 1
                    ELSE 2
                END,
                title
            LIMIT ?
        """, (f'%{query}%', f'%{query}%', f'{query}%',
              query, query, limit))

        for row in self.cursor.fetchall():
            song = dict(row)
            if song['chart_hash'] not in seen_hashes:
                results.append(song)
                seen_hashes.add(song['chart_hash'])

        # If we have enough results from exact phrase, return early
        if len(results) >= limit:
            return results[:limit]

        # TIER 2: All meaningful words match (AND logic) - only if multiple words
        if len(meaningful_words) > 1:
            # Build AND conditions: each word must appear somewhere
            and_conditions = []
            and_params = []

            for word in meaningful_words:
                and_conditions.append("(title LIKE ? OR artist LIKE ? OR chart_hash LIKE ?)")
                and_params.extend([f'%{word}%', f'%{word}%', f'{word}%'])

            where_clause = " AND ".join(and_conditions)
            and_params.append(limit - len(results))

            self.cursor.execute(f"""
                SELECT * FROM songs
                WHERE {where_clause}
                ORDER BY title
                LIMIT ?
            """, and_params)

            for row in self.cursor.fetchall():
                song = dict(row)
                if song['chart_hash'] not in seen_hashes:
                    results.append(song)
                    seen_hashes.add(song['chart_hash'])

            # If we have enough results, return
            if len(results) >= limit:
                return results[:limit]

        # TIER 3: Partial match (at least one meaningful word) - fallback
        if meaningful_words:
            or_conditions = []
            or_params = []

            for word in meaningful_words:
                or_conditions.append("(title LIKE ? OR artist LIKE ? OR chart_hash LIKE ?)")
                or_params.extend([f'%{word}%', f'%{word}%', f'{word}%'])

            where_clause = " OR ".join(or_conditions)
            or_params.append(limit - len(results))

            self.cursor.execute(f"""
                SELECT * FROM songs
                WHERE {where_clause}
                ORDER BY title
                LIMIT ?
            """, or_params)

            for row in self.cursor.fetchall():
                song = dict(row)
                if song['chart_hash'] not in seen_hashes:
                    results.append(song)
                    seen_hashes.add(song['chart_hash'])

        return results[:limit]

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

    def get_unresolved_hashes(self, user_id: int = None) -> List[str]:
        """
        Get chart hashes that don't have complete metadata

        Considers a hash "unresolved" if:
        - No song entry exists, OR
        - Title is NULL/empty, OR
        - Title starts with "[" (indicating it's just a hash shortcode like "[abc12345]"), OR
        - Charter is NULL/empty/Unknown

        Args:
            user_id: If provided, only return hashes for this user's scores

        Returns:
            List of chart hashes without complete metadata
        """
        if user_id:
            self.cursor.execute("""
                SELECT DISTINCT s.chart_hash FROM scores s
                LEFT JOIN songs sg ON s.chart_hash = sg.chart_hash
                WHERE s.user_id = ?
                  AND (sg.chart_hash IS NULL
                   OR sg.title IS NULL
                   OR sg.title = ''
                   OR sg.title LIKE '[%'
                   OR sg.charter IS NULL
                   OR sg.charter = ''
                   OR sg.charter = 'Unknown')
            """, (user_id,))
        else:
            # Return all unresolved hashes (for admin use)
            self.cursor.execute("""
                SELECT DISTINCT s.chart_hash FROM scores s
                LEFT JOIN songs sg ON s.chart_hash = sg.chart_hash
                WHERE sg.chart_hash IS NULL
                   OR sg.title IS NULL
                   OR sg.title = ''
                   OR sg.title LIKE '[%'
                   OR sg.charter IS NULL
                   OR sg.charter = ''
                   OR sg.charter = 'Unknown'
            """)
        return [row['chart_hash'] for row in self.cursor.fetchall()]

    def batch_update_song_metadata(self, metadata_list: List[Dict]) -> int:
        """
        Batch update song metadata for multiple hashes

        Args:
            metadata_list: List of dicts with keys: chart_hash, title, artist, charter

        Returns:
            Number of songs updated
        """
        updated_count = 0

        for item in metadata_list:
            chart_hash = item.get('chart_hash')
            title = item.get('title', '')
            artist = item.get('artist', '')
            charter = item.get('charter', '')

            if not chart_hash or not title:
                continue

            # Check if song exists
            self.cursor.execute("SELECT chart_hash FROM songs WHERE chart_hash = ?", (chart_hash,))
            exists = self.cursor.fetchone()

            if exists:
                # Update existing
                self.cursor.execute("""
                    UPDATE songs
                    SET title = ?, artist = ?, charter = ?
                    WHERE chart_hash = ?
                """, (title, artist, charter, chart_hash))
            else:
                # Insert new
                self.cursor.execute("""
                    INSERT INTO songs (chart_hash, title, artist, charter)
                    VALUES (?, ?, ?, ?)
                """, (chart_hash, title, artist, charter))

            if self.cursor.rowcount > 0:
                updated_count += 1

        self.conn.commit()
        return updated_count

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

    def get_server_stats(self) -> Dict:
        """Get comprehensive server statistics"""
        # Total registered users
        self.cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = self.cursor.fetchone()['count']

        # Total scores submitted
        self.cursor.execute("SELECT COUNT(*) as count FROM scores")
        total_scores = self.cursor.fetchone()['count']

        # Total unique chart/instrument/difficulty combinations with scores
        self.cursor.execute("""
            SELECT COUNT(DISTINCT chart_hash || instrument_id || difficulty_id) as count
            FROM scores
        """)
        total_charts_played = self.cursor.fetchone()['count']

        # Total record breaks
        self.cursor.execute("SELECT COUNT(*) as count FROM record_breaks")
        total_record_breaks = self.cursor.fetchone()['count']

        # Database creation time (first user or first score timestamp)
        self.cursor.execute("""
            SELECT MIN(created_at) as first_activity
            FROM (
                SELECT created_at FROM users
                UNION ALL
                SELECT submitted_at as created_at FROM scores
            )
        """)
        first_activity = self.cursor.fetchone()['first_activity']

        # Most active user (by score submissions)
        self.cursor.execute("""
            SELECT u.discord_username, u.discord_id, COUNT(*) as score_count
            FROM scores s
            JOIN users u ON s.user_id = u.id
            GROUP BY u.id
            ORDER BY score_count DESC
            LIMIT 1
        """)
        most_active_row = self.cursor.fetchone()
        most_active_user = dict(most_active_row) if most_active_row else None

        # Most competitive song (most record breaks)
        self.cursor.execute("""
            SELECT songs.title, rb.chart_hash, COUNT(*) as break_count
            FROM record_breaks rb
            LEFT JOIN songs ON rb.chart_hash = songs.chart_hash
            GROUP BY rb.chart_hash
            ORDER BY break_count DESC
            LIMIT 1
        """)
        most_competitive_row = self.cursor.fetchone()
        most_competitive_song = dict(most_competitive_row) if most_competitive_row else None

        # Current record holders (unique users holding at least one record)
        self.cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scores s1
            WHERE score = (
                SELECT MAX(score)
                FROM scores s2
                WHERE s2.chart_hash = s1.chart_hash
                AND s2.instrument_id = s1.instrument_id
                AND s2.difficulty_id = s1.difficulty_id
            )
        """)
        total_record_holders = self.cursor.fetchone()['count']

        # Database file size
        import os
        db_size_bytes = os.path.getsize(self.db_path)
        db_size_mb = db_size_bytes / (1024 * 1024)

        return {
            'total_users': total_users,
            'total_scores': total_scores,
            'total_charts_played': total_charts_played,
            'total_record_breaks': total_record_breaks,
            'total_record_holders': total_record_holders,
            'first_activity': first_activity,
            'most_active_user': most_active_user,
            'most_competitive_song': most_competitive_song,
            'db_size_mb': round(db_size_mb, 2)
        }

    def get_metadata(self, key: str) -> Optional[str]:
        """
        Get a metadata value by key

        Args:
            key: Metadata key to retrieve

        Returns:
            Value if exists, None otherwise
        """
        self.cursor.execute("SELECT value FROM bot_metadata WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row['value'] if row else None

    def set_metadata(self, key: str, value: str):
        """
        Set a metadata value (upsert)

        Args:
            key: Metadata key
            value: Value to store
        """
        self.cursor.execute("""
            INSERT OR REPLACE INTO bot_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        self.conn.commit()

    def create_backup(self, backup_dir: Path = None, keep_count: int = 7) -> bool:
        """
        Create a timestamped backup of the database and rotate old backups

        Args:
            backup_dir: Directory to store backups (defaults to same dir as database)
            keep_count: Number of recent backups to keep (default: 7)

        Returns:
            bool: True if backup successful, False otherwise
        """
        import shutil
        from datetime import datetime

        try:
            # Ensure database connection exists
            if self.conn is None:
                self.connect()

            # Determine backup directory
            if backup_dir is None:
                backup_dir = Path(self.db_path).parent

            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            db_name = Path(self.db_path).stem
            backup_name = f"{db_name}_backup_{timestamp}.db"
            backup_path = backup_dir / backup_name

            # Create backup using SQLite backup API (safer than file copy)
            import sqlite3
            backup_conn = sqlite3.connect(str(backup_path))
            with backup_conn:
                self.conn.backup(backup_conn)
            backup_conn.close()

            print(f"[+] Database backup created: {backup_path}")

            # Rotate old backups - keep only most recent N
            if keep_count > 0:
                # Find all backup files for this database
                backup_pattern = f"{db_name}_backup_*.db"
                backup_files = sorted(backup_dir.glob(backup_pattern), reverse=True)

                # Delete old backups beyond keep_count
                for old_backup in backup_files[keep_count:]:
                    old_backup.unlink()
                    print(f"[*] Deleted old backup: {old_backup.name}")

            return True

        except Exception as e:
            print(f"[!] Error creating database backup: {e}")
            import traceback
            traceback.print_exc()
            return False

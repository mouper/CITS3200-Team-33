import sqlite3
import time
from databases.db_utils import execute_query, connect_db

WATCHED_DB_PATH = "watched.db"

# -----------------------------
# Initialize table
# -----------------------------
def init_db(db_path=WATCHED_DB_PATH):
    """Create watched table if it doesn't exist."""
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            video_id TEXT PRIMARY KEY,
            watched_seconds REAL,
            last_watched INTEGER
        )
    """)
    conn.close()

# -----------------------------
# Log watch duration
# -----------------------------
def log_watch(video_id: str, watched_seconds: float, db_path=WATCHED_DB_PATH):
    """Insert or update watched duration for a video."""
    conn = connect_db(db_path)
    timestamp = int(time.time())
    execute_query(conn, """
        INSERT INTO watched (video_id, watched_seconds, last_watched)
        VALUES (?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            watched_seconds = watched_seconds + excluded.watched_seconds,
            last_watched = excluded.last_watched
    """, (video_id, watched_seconds, timestamp))

# -----------------------------
# Get watched durations
# -----------------------------
def get_watched(video_id: str, db_path=WATCHED_DB_PATH) -> float:
    """Return total watched seconds for a video."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT watched_seconds FROM watched WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    return row[0] if row else 0.0

# -----------------------------
# Cleanup old entries
# -----------------------------
def cleanup(expire_seconds: int = 86400, db_path=WATCHED_DB_PATH):
    """Delete entries not watched in the last expire_seconds."""
    cutoff = int(time.time()) - expire_seconds
    conn = connect_db(db_path)
    execute_query(conn, "DELETE FROM watched WHERE last_watched < ?", (cutoff,))

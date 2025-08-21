"""
watched_video_db.py — Logs watched videos for history/analytics purposes.
Entries expire automatically after WATCHED_TTL seconds.
"""

from db_utils import connect_db, execute_query, current_timestamp
from config import WATCHED_DB_PATH, WATCHED_TTL

def init_db():
    """Create the watched_videos table if it doesn't already exist."""
    conn = connect_db(WATCHED_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS watched_videos (
        video_id TEXT,
        watched_at INTEGER
    )
    """)
    conn.close()

def log_watch(video_id):
    """Insert a watched video record with the current timestamp."""
    conn = connect_db(WATCHED_DB_PATH)
    execute_query(conn,
        "INSERT INTO watched_videos VALUES (?, ?)",
        (video_id, current_timestamp())
    )
    conn.close()

def cleanup():
    """Delete watch history entries older than the allowed retention period."""
    conn = connect_db(WATCHED_DB_PATH)
    cutoff = current_timestamp() - WATCHED_TTL
    execute_query(conn, "DELETE FROM watched_videos WHERE watched_at < ?", (cutoff,))
    conn.close()



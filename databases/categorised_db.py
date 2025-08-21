"""
categorised_video_db.py — Stores categorised videos and their metadata snapshot.
Entries expire automatically after CATEGORISED_TTL seconds.
"""

from db_utils import connect_db, execute_query, fetch_all, current_timestamp
from config import CATEGORISED_DB_PATH, CATEGORISED_TTL

def init_db():
    """Create the categorised_videos table if it doesn't already exist."""
    conn = connect_db(CATEGORISED_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS categorised_videos (
        video_id TEXT PRIMARY KEY,
        category TEXT,
        metadata TEXT,
        timestamp INTEGER
    )
    """)
    conn.close()

def insert_categorised(video_id, category, metadata_json):
    """Insert or replace a categorised video entry with metadata snapshot."""
    conn = connect_db(CATEGORISED_DB_PATH)
    execute_query(conn,
        "REPLACE INTO categorised_videos VALUES (?, ?, ?, ?)",
        (video_id, category, metadata_json, current_timestamp())
    )
    conn.close()

def cleanup():
    """Remove categorised videos older than the allowed retention period."""
    conn = connect_db(CATEGORISED_DB_PATH)
    cutoff = current_timestamp() - CATEGORISED_TTL
    execute_query(conn, "DELETE FROM categorised_videos WHERE timestamp < ?", (cutoff,))
    conn.close()

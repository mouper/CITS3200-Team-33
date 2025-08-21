
"""
metadata_cache_db.py — Manages short-term storage of fetched video metadata.
Entries automatically expire after METADATA_TTL seconds.
"""

from db_utils import connect_db, execute_query, fetch_all, current_timestamp
from config import METADATA_DB_PATH, METADATA_TTL

def init_db():
    """Create the metadata_cache table if it doesn't already exist."""
    conn = connect_db(METADATA_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS metadata_cache (
        video_id TEXT PRIMARY KEY,
        metadata TEXT,
        timestamp INTEGER
    )
    """)
    conn.close()

def insert_metadata(video_id, metadata_json):
    """Insert or replace video metadata with the current timestamp."""
    conn = connect_db(METADATA_DB_PATH)
    execute_query(conn,
        "REPLACE INTO metadata_cache VALUES (?, ?, ?)",
        (video_id, metadata_json, current_timestamp())
    )
    conn.close()

def get_fresh_metadata():
    """Retrieve metadata entries that are still within the freshness period."""
    conn = connect_db(METADATA_DB_PATH)
    cutoff = current_timestamp() - METADATA_TTL
    rows = fetch_all(conn,
        "SELECT * FROM metadata_cache WHERE timestamp >= ?",
        (cutoff,)
    )
    conn.close()
    return rows

def cleanup():
    """Delete metadata entries older than the allowed freshness period."""
    conn = connect_db(METADATA_DB_PATH)
    cutoff = current_timestamp() - METADATA_TTL
    execute_query(conn, "DELETE FROM metadata_cache WHERE timestamp < ?", (cutoff,))
    conn.close()

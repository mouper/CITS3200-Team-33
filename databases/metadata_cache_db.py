"""
metadata_cache_db.py — Short-term cache for fetched video metadata.
TTL(Time-To-Live): 6 hours
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import METADATA_DB_PATH, METADATA_TTL

def init_db():
    conn = connect_db(METADATA_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS metadata_cache (
        video_id  TEXT PRIMARY KEY,
        metadata  TEXT,
        time_cached INTEGER
    )
    """)
    conn.close()

def insert_metadata(video_id, metadata_json):
    conn = connect_db(METADATA_DB_PATH)
    execute_query(conn,
        "REPLACE INTO metadata_cache VALUES (?, ?, ?)",
        (video_id, metadata_json, current_timestamp())
    )
    conn.close()

def get_fresh_metadata():
    conn = connect_db(METADATA_DB_PATH)
    cutoff = current_timestamp() - METADATA_TTL
    rows = fetch_all(conn,
        "SELECT * FROM metadata_cache WHERE time_cached >= ?",
        (cutoff,)
    )
    conn.close()
    return rows

def get_metadata_by_id(video_id):
    """Get metadata for a specific video ID."""
    conn = connect_db(METADATA_DB_PATH)
    rows = fetch_all(conn,
        "SELECT metadata FROM metadata_cache WHERE video_id = ?",
        (video_id,)
    )
    conn.close()
    if rows:
        import json
        return json.loads(rows[0][0])
    return None

def cleanup():
    conn = connect_db(METADATA_DB_PATH)
    cutoff = current_timestamp() - METADATA_TTL
    execute_query(conn, "DELETE FROM metadata_cache WHERE time_cached < ?", (cutoff,))
    conn.close()


def delete_metadata_by_ids(video_ids):
    """Delete cached metadata rows for the given list of video_ids.

    No-op if the list is empty.
    """
    if not video_ids:
        return
    conn = connect_db(METADATA_DB_PATH)
    placeholders = ",".join(["?"] * len(video_ids))
    query = f"DELETE FROM metadata_cache WHERE video_id IN ({placeholders})"
    execute_query(conn, query, tuple(video_ids))
    conn.close()
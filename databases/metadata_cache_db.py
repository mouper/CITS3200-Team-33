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

def cleanup():
    conn = connect_db(METADATA_DB_PATH)
    cutoff = current_timestamp() - METADATA_TTL
    execute_query(conn, "DELETE FROM metadata_cache WHERE time_cached < ?", (cutoff,))
    conn.close()

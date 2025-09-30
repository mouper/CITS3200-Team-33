"""
metadata_cache_db.py — Short-term cache for fetched video metadata.
TTL(Time-To-Live): 6 hours
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import METADATA_DB_PATH, METADATA_TTL

def init_db():
    conn = connect_db(METADATA_DB_PATH)
    try:
        # Add video_length column if missing
        execute_query(conn, """
        CREATE TABLE IF NOT EXISTS metadata_cache (
            video_id  TEXT PRIMARY KEY,
            metadata  TEXT,
            time_cached INTEGER,
            video_length REAL
        )
        """)
        # Control table for ingest flags (if missing)
        execute_query(conn, """
        CREATE TABLE IF NOT EXISTS control (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
    finally:
        conn.close()

def insert_metadata(video_id, metadata_json, video_length=None):
    conn = connect_db(METADATA_DB_PATH)
    try:
        execute_query(conn,
            "REPLACE INTO metadata_cache (video_id, metadata, time_cached, video_length) VALUES (?, ?, ?, ?)",
            (video_id, metadata_json, current_timestamp(), video_length)
        )
    finally:
        conn.close()

def get_fresh_metadata():
    conn = connect_db(METADATA_DB_PATH)
    try:
        cutoff = current_timestamp() - METADATA_TTL
        rows = fetch_all(conn,
            "SELECT * FROM metadata_cache WHERE time_cached >= ?",
            (cutoff,)
        )
        return rows
    finally:
        conn.close()

def get_metadata_by_id(video_id):
    """Get metadata and video_length for a specific video ID."""
    conn = connect_db(METADATA_DB_PATH)
    try:
        rows = fetch_all(conn,
            "SELECT metadata, video_length FROM metadata_cache WHERE video_id = ?",
            (video_id,)
        )
    finally:
        conn.close()
    if rows:
        import json
        return {
            "metadata": json.loads(rows[0][0]),
            "video_length": rows[0][1]
        }
    return None

def cleanup():
    conn = connect_db(METADATA_DB_PATH)
    try:
        cutoff = current_timestamp() - METADATA_TTL
        execute_query(conn, "DELETE FROM metadata_cache WHERE time_cached < ?", (cutoff,))
    finally:
        conn.close()


def delete_metadata_by_ids(video_ids):
    """Delete cached metadata rows for the given list of video_ids.

    No-op if the list is empty.
    """
    if not video_ids:
        return
    conn = connect_db(METADATA_DB_PATH)
    try:
        placeholders = ",".join(["?"] * len(video_ids))
        query = f"DELETE FROM metadata_cache WHERE video_id IN ({placeholders})"
        execute_query(conn, query, tuple(video_ids))
    finally:
        conn.close()


def clear_all_metadata():
    """Delete all rows from the metadata cache table."""
    conn = connect_db(METADATA_DB_PATH)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM metadata_cache")
            deleted = cursor.rowcount if cursor.rowcount is not None else conn.total_changes
    finally:
        conn.close()
    return deleted


def set_ingest_active(active: bool):
    """Set the ingestion in-flight flag in the control table."""
    conn = connect_db(METADATA_DB_PATH)
    try:
        execute_query(conn,
            "REPLACE INTO control (key, value) VALUES ('ingest_active', ?)",
            ("1" if active else "0",)
        )
    finally:
        conn.close()


def is_ingest_active() -> bool:
    """Return True if ingestion is currently marked active."""
    conn = connect_db(METADATA_DB_PATH)
    try:
        rows = fetch_all(conn, "SELECT value FROM control WHERE key = 'ingest_active'", ())
    finally:
        conn.close()
    if not rows:
        return False
    val = rows[0][0] if isinstance(rows[0], tuple) else rows[0]["value"]
    return str(val) == "1"
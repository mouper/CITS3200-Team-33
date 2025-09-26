"""
watched_db.py — Logs watch events with start/end times.
TTL (Time-To-Live): 30 days
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import WATCHED_DB_PATH, WATCHED_TTL

def init_db():
    conn = connect_db(WATCHED_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS watched (
        video_id   TEXT PRIMARY KEY,
        start_time INTEGER,  -- when viewing began
        end_time INTEGER     -- when viewing ended/log saved
    )
    """)
    conn.close()

def log_watch(video_id, start_time=None):
    conn = connect_db(WATCHED_DB_PATH)
    if start_time is None:
        start_time = current_timestamp()
    execute_query(conn,
        "REPLACE INTO watched VALUES (?, ?, ?)",
        (video_id, start_time, current_timestamp())
    )
    conn.close()


def start_watch(video_id, start_time=None):
    """Begin tracking a watch session for the given video."""
    conn = connect_db(WATCHED_DB_PATH)
    try:
        ts = start_time or current_timestamp()
        execute_query(conn,
            "REPLACE INTO watched (video_id, start_time, end_time) VALUES (?, ?, ?)",
            (video_id, ts, ts)
        )
    finally:
        conn.close()


def update_watch_end(video_id, end_time=None):
    """Update the end_time for an in-progress watch session and return (start, end)."""
    conn = connect_db(WATCHED_DB_PATH)
    try:
        ts = end_time or current_timestamp()
        execute_query(conn,
            "UPDATE watched SET end_time = ? WHERE video_id = ?",
            (ts, video_id)
        )
        rows = fetch_all(conn,
            "SELECT start_time, end_time FROM watched WHERE video_id = ?",
            (video_id,)
        )
    finally:
        conn.close()
    return rows[0] if rows else None


def get_watch_entry(video_id):
    """Return the stored watch record for a given video id."""
    conn = connect_db(WATCHED_DB_PATH)
    try:
        rows = fetch_all(conn,
            "SELECT video_id, start_time, end_time FROM watched WHERE video_id = ?",
            (video_id,)
        )
    finally:
        conn.close()
    return rows[0] if rows else None

def get_durations():
    """Return list of (video_id, duration_seconds) for all watch events."""
    conn = connect_db(WATCHED_DB_PATH)
    rows = fetch_all(conn, """
        SELECT video_id, (end_time - start_time) AS duration
        FROM watched
    """)
    conn.close()
    return rows

def cleanup():
    conn = connect_db(WATCHED_DB_PATH)
    cutoff = current_timestamp() - WATCHED_TTL
    execute_query(conn, "DELETE FROM watched WHERE end_time < ?", (cutoff,))
    conn.close()



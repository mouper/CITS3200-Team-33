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
        video_id   TEXT,
        start_time INTEGER,  -- when viewing began
        end_time INTEGER     -- when viewing ended/log saved
    )
    """)
    conn.close()

def log_watch(video_id, start_time=None):
    if start_time is None:
        start_time = current_timestamp()
    conn = connect_db(WATCHED_DB_PATH)
    execute_query(conn,
        "INSERT INTO watched VALUES (?, ?, ?)",
        (video_id, start_time, current_timestamp())
    )
    conn.close()

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



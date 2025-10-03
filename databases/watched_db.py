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

def log_watch(video_id, start_time=None, end_time=None):
    conn = connect_db(WATCHED_DB_PATH)

    now = current_timestamp()

    try:
        start_ts = int(start_time) if start_time is not None else None
    except (TypeError, ValueError):
        start_ts = None

    try:
        end_ts = int(end_time) if end_time is not None else None
    except (TypeError, ValueError):
        end_ts = None

    if start_ts is None and end_ts is None:
        start_ts = now
        end_ts = now
    if end_ts is None:
        end_ts = now

    execute_query(
        conn,
        """
        INSERT INTO watched (video_id, start_time, end_time)
        VALUES (?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            start_time = CASE
                WHEN excluded.start_time IS NOT NULL AND (
                    watched.start_time IS NULL OR excluded.start_time < watched.start_time
                ) THEN excluded.start_time
                ELSE watched.start_time
            END,
            end_time = CASE
                WHEN excluded.end_time IS NOT NULL AND (
                    watched.end_time IS NULL OR excluded.end_time > watched.end_time
                ) THEN excluded.end_time
                ELSE watched.end_time
            END
        """,
        (video_id, start_ts, end_ts),
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



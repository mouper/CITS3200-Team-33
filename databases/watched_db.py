"""
watched_db.py — Logs watch events with start/end times.
TTL (Time-To-Live): 30 days

Each viewing session is stored as a distinct row so repeat watches of the same
video are tracked independently.
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import WATCHED_DB_PATH, WATCHED_TTL

def init_db():
    conn = connect_db(WATCHED_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS watched (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        start_time INTEGER,
        end_time INTEGER
    )
    """)
    execute_query(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_watched_video_id ON watched(video_id)",
    )
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

    cursor = conn.cursor()

    existing = cursor.execute(
        """
        SELECT end_time
        FROM watched
        WHERE video_id = ? AND start_time = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (video_id, start_ts),
    ).fetchone()

    previous_end = existing["end_time"] if existing and existing["end_time"] is not None else start_ts
    new_end = end_ts if end_ts is not None else start_ts
    delta_seconds = max(0, int(new_end) - int(previous_end))

    with conn:
        cursor.execute(
            """
            UPDATE watched
            SET
                start_time = COALESCE(start_time, ?),
                end_time = CASE
                    WHEN end_time IS NULL OR ? > end_time THEN ?
                    ELSE end_time
                END
            WHERE video_id = ? AND start_time = ?
            """,
            (start_ts, end_ts, end_ts, video_id, start_ts),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO watched (video_id, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                (video_id, start_ts, end_ts),
            )

    conn.close()

    final_end_time = max(new_end, previous_end if previous_end is not None else start_ts)

    return {
        "video_id": video_id,
        "start_time": start_ts,
        "end_time": final_end_time,
        "added_seconds": delta_seconds,
    }

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



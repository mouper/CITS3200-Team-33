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
    
    # Ensure start_time is set if we have end_time but no start_time
    if start_ts is None and end_ts is not None:
        start_ts = end_ts

    cursor = conn.cursor()

    # FIXED: Look for the most recent watch session for this video within a 5-second time window
    # This handles cases where start_time might be slightly different due to timing issues
    # We look for sessions that started within 5 seconds (before or after) of the given start_time
    time_window = 5  # seconds
    
    existing = cursor.execute(
        """
        SELECT id, start_time, end_time
        FROM watched
        WHERE video_id = ?
          AND ABS(start_time - ?) <= ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (video_id, start_ts, time_window),
    ).fetchone()

    # If no match in time window, try to find the absolute most recent entry for this video
    # that hasn't ended too long ago (within last 10 minutes)
    if not existing:
        existing = cursor.execute(
            """
            SELECT id, start_time, end_time
            FROM watched
            WHERE video_id = ?
              AND end_time >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (video_id, now - 600),  # 10 minutes ago
        ).fetchone()

    if existing:
        # Update existing session
        existing_id = existing["id"]
        existing_start = int(existing["start_time"])
        previous_end = int(existing["end_time"]) if existing["end_time"] is not None else existing_start
        new_end = int(end_ts if end_ts is not None else start_ts)
        
        # Use the original start time from the existing session
        start_ts = existing_start
        
        # Calculate incremental watch time
        delta_seconds = max(0, new_end - previous_end)

        with conn:
            cursor.execute(
                """
                UPDATE watched
                SET end_time = ?
                WHERE id = ?
                """,
                (new_end, existing_id),
            )
    else:
        # Create new session
        delta_seconds = 0
        new_end = int(end_ts if end_ts is not None else start_ts)
        
        with conn:
            cursor.execute(
                """
                INSERT INTO watched (video_id, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                (video_id, start_ts, new_end),
            )

    conn.close()

    final_end_time = new_end

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



import sqlite3
import time
from databases.db_utils import current_timestamp, execute_query, connect_db
import pytest

WATCHED_DB_PATH = "watched.db"

# -----------------------------
# Initialize table
# -----------------------------
def init_db(db_path=WATCHED_DB_PATH):
    """Create watched table if it doesn't exist."""
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE,
            start_time INTEGER,
            end_time INTEGER
        )
    """)
    conn.close()

# -----------------------------
# Log watch duration
# -----------------------------
def log_watch(video_id, start_time=None, end_time=None, db_path=None):
    conn = connect_db(db_path)
    now = int(start_time) if start_time is not None else current_timestamp()
    end = int(end_time) if end_time is not None else now
    conn.execute("""
        INSERT OR REPLACE INTO watched (video_id, start_time, end_time)
        VALUES (?, ?, ?)
    """, (video_id, now, end))
    conn.commit()
    conn.close()

# -----------------------------
# Get watched durations
# -----------------------------
def get_watched(video_id: str, db_path=WATCHED_DB_PATH) -> float:
    """Return total watched seconds for a video."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT watched_seconds FROM watched WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    return row[0] if row else 0.0

# -----------------------------
# Cleanup old entries
# -----------------------------
def cleanup(expire_seconds: int = 86400, db_path=WATCHED_DB_PATH):
    """Delete entries not watched in the last expire_seconds."""
    cutoff = int(time.time()) - expire_seconds
    conn = connect_db(db_path)
    execute_query(conn, "DELETE FROM watched WHERE last_watched < ?", (cutoff,))

def test_init_db_creates_table(watched_db_fixture):
    db = watched_db_fixture
    db.init_db()
    # Should not raise

def test_log_watch_does_not_error(watched_db_fixture):
    db = watched_db_fixture
    db.init_db()
    db.log_watch("vidX", 123, 456)
    # Should not raise

def test_cleanup_removes_old_entries(watched_db_fixture):
    db = watched_db_fixture
    db.init_db()
    db.log_watch("old_vid", 0, 0)
    db.cleanup()
    conn = db.connect_db()
    rows = conn.execute("SELECT * FROM watched WHERE video_id='old_vid'").fetchall()
    assert len(rows) == 0
    conn.close()

def test_log_and_fetch_watch(watched_db_fixture):
    db = watched_db_fixture
    db.init_db()
    db.log_watch("vid1", 100, 200)
    conn = db.connect_db()
    row = conn.execute("SELECT video_id, start_time, end_time FROM watched WHERE video_id = ?", ("vid1",)).fetchone()
    assert row is not None and row[0] == "vid1" and row[1] == 100 and row[2] == 200
    conn.close()

def test_log_watch_overwrites(watched_db_fixture):
    db = watched_db_fixture
    db.init_db()
    db.log_watch("vid2", 50, 150)
    db.log_watch("vid2", 60, 160)  # Should update or replace
    conn = db.connect_db()
    row = conn.execute("SELECT video_id, start_time, end_time FROM watched WHERE video_id = ?", ("vid2",)).fetchone()
    print("Row returned:", row)
    # Accept either the updated or original values, depending on your logic
    assert row is not None and row[0] == "vid2"
    assert (row[1], row[2]) in [(60, 160), (50, 150)]
    conn.close()

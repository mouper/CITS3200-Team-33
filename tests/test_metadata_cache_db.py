import sqlite3
import json
import time
from databases.db_utils import connect_db, execute_query, fetch_all
import pytest

METADATA_CACHE_DB_PATH = "metadata_cache.db"  # your default path

# -----------------------------
# Insert or replace metadata
# -----------------------------
def insert_metadata(video_id: str, metadata: dict, video_length: int = None, db_path=METADATA_CACHE_DB_PATH):
    """Insert or update metadata for a video."""
    conn = connect_db(db_path)
    # Convert dict to JSON string
    metadata_json = json.dumps(metadata)
    timestamp = int(time.time())
    execute_query(conn,
        """
        REPLACE INTO metadata_cache (video_id, metadata, time_cached, video_length)
        VALUES (?, ?, ?, ?)
        """,
        (video_id, metadata_json, timestamp, video_length)
    )

# -----------------------------
# Get metadata for a video
# -----------------------------
def get_metadata(video_id: str, db_path=METADATA_CACHE_DB_PATH) -> dict | None:
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT metadata FROM metadata_cache WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    if row:
        # Convert JSON string back to dict
        return json.loads(row[0])
    return None

# -----------------------------
# Get fresh metadata (e.g., last N seconds)
# -----------------------------
def get_fresh_metadata(max_age_seconds: int = 3600, db_path=METADATA_CACHE_DB_PATH) -> list[dict]:
    """Return metadata cached within the last max_age_seconds."""
    cutoff = int(time.time()) - max_age_seconds
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT metadata FROM metadata_cache WHERE time_cached >= ?", (cutoff,))
    rows = cursor.fetchall()
    return [json.loads(row[0]) for row in rows]

# -----------------------------
# Cleanup old entries
# -----------------------------
def cleanup(expire_seconds: int = 86400, db_path=METADATA_CACHE_DB_PATH):
    """Delete metadata older than expire_seconds."""
    cutoff = int(time.time()) - expire_seconds
    conn = connect_db(db_path)
    execute_query(conn, "DELETE FROM metadata_cache WHERE time_cached < ?", (cutoff,))

def test_insert_and_get_metadata(metadata_cache_db_fixture):
    db = metadata_cache_db_fixture
    db.init_db()
    metadata_json = json.dumps({"title": "Video 1"})
    db.insert_metadata("vid1", metadata_json, video_length=120)
    meta = db.get_metadata_by_id("vid1")
    assert meta is not None and "Video 1" in str(meta)

def test_get_fresh_metadata(metadata_cache_db_fixture):
    db = metadata_cache_db_fixture
    db.init_db()
    db.insert_metadata("vid2", json.dumps({"title": "Fresh"}), video_length=10)
    fresh = db.get_fresh_metadata()
    assert "vid2" in str(fresh)

def test_cleanup(metadata_cache_db_fixture):
    db = metadata_cache_db_fixture
    db.init_db()
    metadata_json = json.dumps({"title": "Old"})
    db.insert_metadata("old_vid", metadata_json, video_length=5)
    db.cleanup()
    meta = db.get_metadata_by_id("old_vid")
    assert meta is None or "old_vid" not in str(meta)


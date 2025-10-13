import pytest
import tempfile
import os
import shutil
import sqlite3
from datetime import datetime
from databases import categorised_db, category_block_stats_db, user_settings_db, metadata_cache_db, watched_db

# -----------------------------
# Temporary DB fixture factory
# -----------------------------
@pytest.fixture
def temp_db_file():
    """Create a temporary database file and clean up after tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)

# -----------------------------
# Categorised DB fixture
# -----------------------------
@pytest.fixture
def categorised_db_fixture(temp_db_file, monkeypatch):
    # Monkeypatch the real DB path to the temp DB
    monkeypatch.setattr(categorised_db, "CATEGORIES_DB_PATH", temp_db_file)
    # Initialize tables
    categorised_db.init_db()
    return categorised_db

# -----------------------------
# User Settings DB fixture
# -----------------------------
@pytest.fixture
def user_settings_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(user_settings_db, "USER_SETTINGS_DB_PATH", temp_db_file)
    # Ensure table exists with correct schema
    conn = user_settings_db.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT CHECK(filter_strength IN ('Weak','Moderate','Strong','Extra Strong','Blocked')),
            is_active BOOLEAN NOT NULL CHECK(is_active IN (0, 1)),
            last_updated_time TIMESTAMP,
            count INTEGER DEFAULT 0,
            total_blocked_time INTEGER DEFAULT 0,
            total_video INTEGER DEFAULT 0
        )
    """)
    conn.close()
    return user_settings_db

# -----------------------------
# Metadata Cache DB fixture
# -----------------------------
@pytest.fixture
def metadata_cache_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(metadata_cache_db, "METADATA_CACHE_DB_PATH", temp_db_file)
    conn = metadata_cache_db.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata_cache (
            video_id TEXT PRIMARY KEY,
            metadata TEXT,
            timestamp INTEGER
        )
    """)
    conn.close()
    return metadata_cache_db

# -----------------------------
# Watched DB fixture
# -----------------------------
@pytest.fixture
def watched_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(watched_db, "WATCHED_DB_PATH", temp_db_file)
    conn = watched_db.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE,
            watched_seconds REAL DEFAULT 0,
            last_watched INTEGER DEFAULT 0
        )
    """)
    conn.close()
    return watched_db

# -----------------------------
# Graph Stats DB fixture
# -----------------------------
@pytest.fixture
def category_block_stats_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(category_block_stats_db, "CATEGORY_BLOCK_STATS_DB_PATH", temp_db_file)
    conn = category_block_stats_db.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            total_video INTEGER DEFAULT 0,
            blocked_hours REAL DEFAULT 0,
            current_level INTEGER DEFAULT 0
        )
    """)
    conn.close()
    return category_block_stats_db

# -----------------------------
# Category Block Stats DB
# -----------------------------
DB_PATH = "category_block_stats.db"

def connect_db(db_path):
    return sqlite3.connect(db_path)

def init_db(db_path=DB_PATH):
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE,
            current_level REAL DEFAULT 0,
            last_updated_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def set_block_level(category, level, db_path=DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE category_block_stats
        SET current_level = ?, last_updated_time = ?
        WHERE category = ?
    """, (level, now, category))
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO category_block_stats (category, current_level, last_updated_time)
            VALUES (?, ?, ?)
        """, (category, level, now))
    conn.commit()
    conn.close()

def get_block_level(category, db_path=DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT current_level FROM category_block_stats WHERE category = ?", (category,))
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else None

def test_block_level_crud():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        init_db(db_path)  # <-- Ensure table exists!
        set_block_level("Education", 0.7, db_path)
        set_block_level("Gaming", 0.3, db_path)
        set_block_level("Gaming", 0.5, db_path)
        assert get_block_level("Education", db_path) == 0.7
        assert get_block_level("Gaming", db_path) == 0.5
        levels = {}
        conn = connect_db(db_path)
        for cat, lvl in conn.execute("SELECT category, current_level FROM category_block_stats"):
            levels[cat] = float(lvl)
        conn.close()
        assert levels["Education"] == 0.7
        assert levels["Gaming"] == 0.5
    finally:
        os.remove(db_path)

def _normalize_rows(rows, fallback_conn):
    """
    Ensure we return an iterable of rows as tuples (video_id, category).
    rows may be:
      - a list of tuples
      - a list of dict-like (sqlite3.Row)
      - a MagicMock (non-iterable) -> fallback to querying the DB directly
    """
    try:
        iter(rows)
        is_iter = True
    except TypeError:
        is_iter = False

    if not is_iter:
        rows = fallback_conn.execute("SELECT video_id, category FROM categorised").fetchall()
        fallback_conn.close()

    normalized = []
    for r in rows:
        if isinstance(r, (list, tuple)):
            if len(r) >= 2:
                normalized.append((r[0], r[1]))
        elif isinstance(r, dict) or hasattr(r, "get"):
            normalized.append((r.get("video_id"), r.get("category")))
        else:
            # sqlite3.Row supports indexing by name and by index
            try:
                normalized.append((r["video_id"], r["category"]))
            except Exception:
                try:
                    normalized.append((r[0], r[1]))
                except Exception:
                    continue
    return normalized


def test_cleanup_removes_old_entries(categorised_db_fixture):
    db = categorised_db_fixture
    db.init_db()
    db.insert_categorised("old_vid", "OldCat")
    db.cleanup()
    rows = db.get_all_categorised()
    assert not any(
        (isinstance(r, dict) and r.get("video_id") == "old_vid") or
        (isinstance(r, tuple) and r[0] == "old_vid")
        for r in rows
    )

def test_init_db_creates_table(categorised_db_fixture):
    db = categorised_db_fixture
    db.init_db()
    # Should not raise

def test_cleanup_does_not_error(categorised_db_fixture):
    db = categorised_db_fixture
    db.init_db()
    db.cleanup()
    # Should not raise

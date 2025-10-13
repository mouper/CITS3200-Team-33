import sys
from pathlib import Path
import pytest
import sqlite3

# Ensure project root is on sys.path so "databases" resolves
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from databases import (
    categorised_db,
    user_settings_db,
    metadata_cache_db,
    watched_db,
    category_block_stats_db,
)

# --- Categorised DB ---
@pytest.fixture
def categorised_db_fixture(monkeypatch):
    import sqlite3
    uri = "file:categorised_db?mode=memory&cache=shared"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categorised (
            video_id TEXT PRIMARY KEY,
            category TEXT,
            time_categorised INTEGER
        )
    """)
    conn.commit()
    monkeypatch.setattr(
        categorised_db, "connect_db",
        lambda db_path=None: sqlite3.connect(uri, uri=True, check_same_thread=False)
    )
    yield categorised_db
    conn.close()

# --- User Settings DB ---
@pytest.fixture
def user_settings_db_fixture(monkeypatch):
    uri = "file:user_settings_db?mode=memory&cache=shared"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT,
            is_active INTEGER,
            last_updated_time TEXT,
            count INTEGER DEFAULT 0,
            total_blocked_time INTEGER DEFAULT 0,
            total_video INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    monkeypatch.setattr(user_settings_db, "connect_db", lambda db_path=None: sqlite3.connect(uri, uri=True, check_same_thread=False))
    yield user_settings_db
    conn.close()

# --- Metadata Cache DB ---
@pytest.fixture
def metadata_cache_db_fixture(monkeypatch):
    uri = "file:metadata_cache_db?mode=memory&cache=shared"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata_cache (
            video_id TEXT PRIMARY KEY,
            metadata TEXT,
            time_cached INTEGER,
            video_length INTEGER
        )
    """)
    conn.commit()
    monkeypatch.setattr(metadata_cache_db, "connect_db", lambda db_path=None: sqlite3.connect(uri, uri=True, check_same_thread=False))
    yield metadata_cache_db
    conn.close()

# --- Watched DB ---
@pytest.fixture
def watched_db_fixture(monkeypatch):
    uri = "file:watched_db?mode=memory&cache=shared"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            start_time INTEGER,
            end_time INTEGER
        )
    """)
    conn.commit()
    monkeypatch.setattr(watched_db, "connect_db", lambda db_path=None: sqlite3.connect(uri, uri=True, check_same_thread=False))
    yield watched_db
    conn.close()

# --- Category Block Stats DB ---
@pytest.fixture
def category_block_stats_fixture(monkeypatch):
    import sqlite3
    uri = "file:category_block_stats_db?mode=memory&cache=shared"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            current_level REAL DEFAULT 0,
            last_updated_time TEXT
        )
    """)
    conn.commit()
    monkeypatch.setattr(
        category_block_stats_db, "connect_db",
        lambda db_path=None: sqlite3.connect(uri, uri=True, check_same_thread=False)
    )
    yield category_block_stats_db
    conn.close()

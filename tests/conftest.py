import sys
from pathlib import Path
import pytest
import sqlite3
import json
import time

# Ensure project root is on sys.path so "databases" resolves
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from databases import categorised_db, user_settings_db, metadata_cache_db, watched_db, category_block_stats_db

# -----------------------------
# In-memory DB fixture factory
# -----------------------------
@pytest.fixture
def temp_db_file():
    """Provide an in-memory SQLite DB for tests."""
    yield ":memory:"

# -----------------------------
# Categorised DB fixture
# -----------------------------
@pytest.fixture
def categorised_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(categorised_db, "CATEGORIES_DB_PATH", temp_db_file, raising=False)
    # Initialize DB (create table as in your module)
    categorised_db.init_db()
    return categorised_db

# -----------------------------
# User Settings DB fixture
# -----------------------------
@pytest.fixture
def user_settings_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(user_settings_db, "USER_SETTINGS_DB_PATH", temp_db_file, raising=False)
    conn = sqlite3.connect(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT DEFAULT 'Moderate',
            is_active INTEGER DEFAULT 1,
            count INTEGER DEFAULT 0,
            total_blocked_time REAL DEFAULT 0,
            total_video INTEGER DEFAULT 0,
            last_updated_time INTEGER DEFAULT 0,
            block_level INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    return user_settings_db

# -----------------------------
# Metadata Cache DB fixture
# -----------------------------
@pytest.fixture
def metadata_cache_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(metadata_cache_db, "METADATA_CACHE_DB_PATH", temp_db_file, raising=False)
    conn = sqlite3.connect(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata_cache (
            video_id TEXT PRIMARY KEY,
            metadata TEXT,
            time_cached INTEGER,
            video_length INTEGER
        )
    """)
    conn.commit()
    conn.close()
    return metadata_cache_db

# -----------------------------
# Watched DB fixture
# -----------------------------
@pytest.fixture
def watched_db_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(watched_db, "WATCHED_DB_PATH", temp_db_file, raising=False)
    conn = sqlite3.connect(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watched (
            video_id TEXT PRIMARY KEY,
            start_time INTEGER,
            end_time INTEGER
        )
    """)
    conn.commit()
    conn.close()
    return watched_db

# -----------------------------
# Graph Stats DB fixture
# -----------------------------
@pytest.fixture
def graph_stats_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(category_block_stats_db, "USER_SETTINGS_DB_PATH", temp_db_file, raising=False)
    conn = sqlite3.connect(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            total_video INTEGER DEFAULT 0,
            blocked_hours REAL DEFAULT 0,
            block_level INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    return category_block_stats_db

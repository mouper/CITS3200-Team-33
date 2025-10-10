import pytest
import tempfile
import os
import shutil
from databases import categorised_db, graph_stats, user_settings_db, metadata_cache_db, watched_db, graph_stats_db

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
    # Ensure table exists
    conn = user_settings_db.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            total_video INTEGER DEFAULT 0,
            blocked_hours REAL DEFAULT 0,
            block_level INTEGER DEFAULT 0
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
            video_id TEXT PRIMARY KEY,
            watched_seconds REAL,
            last_watched INTEGER
        )
    """)
    conn.close()
    return watched_db

# -----------------------------
# Graph Stats DB fixture
# -----------------------------
@pytest.fixture
def graph_stats_fixture(temp_db_file, monkeypatch):
    monkeypatch.setattr(graph_stats, "USER_SETTINGS_DB_PATH", temp_db_file)
    conn = graph_stats.connect_db(temp_db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            total_video INTEGER DEFAULT 0,
            blocked_hours REAL DEFAULT 0,
            block_level INTEGER DEFAULT 0
        )
    """)
    conn.close()
    return graph_stats

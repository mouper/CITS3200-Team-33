import os
import sqlite3
import tempfile
from datetime import datetime
from databases.db_utils import connect_db, execute_query
from sqlite3 import IntegrityError
import pytest
from databases import category_block_stats_db

CATEGORY_BLOCK_STATS_DB_PATH = "category_block_stats.db"

# -----------------------------
# Initialize table
# -----------------------------
def init_db(db_path=CATEGORY_BLOCK_STATS_DB_PATH):
    """Ensure the category_block_stats table exists for graph stats tracking."""
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE,
            current_level REAL DEFAULT 0,
            last_updated_time TEXT
        )
    """)
    conn.close()

# -----------------------------
# Set block level for a category
# -----------------------------
def set_block_level(category: str, level: float, db_path=None):
    conn = connect_db(db_path)
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
    """, (category, level, now))
    conn.commit()
    conn.close()

# -----------------------------
# Get block level for a category
# -----------------------------
def get_block_level(category: str, db_path=CATEGORY_BLOCK_STATS_DB_PATH) -> float | None:
    """Return the block level for a category."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT current_level FROM category_block_stats WHERE category = ?", (category,))
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else None

# -----------------------------
# Get all categories and their block levels
# -----------------------------
def get_all_block_levels(db_path=CATEGORY_BLOCK_STATS_DB_PATH) -> dict:
    """Return all categories with their block levels as a dictionary."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT category, current_level FROM category_block_stats")
    rows = cursor.fetchall()
    conn.close()
    return {category: float(level) for category, level in rows}

def _levels_to_dict(levels):
    """
    Accepts return values in various formats and converts to dict {category: level}.
    Supported formats:
      - dict already (returned by some implementations)
      - list of tuples [(category, level), ...]
      - list of dicts [{'category': ..., 'current_level': ...}, ...]
      - sqlite3 cursor.fetchall() rows
    """
    if isinstance(levels, dict):
        return {k: float(v) for k, v in levels.items()}

    out = {}
    # list-like
    try:
        for item in levels:
            if isinstance(item, tuple) or isinstance(item, list):
                # (category, level) or (category, current_level, ...)
                if len(item) >= 2:
                    out[str(item[0])] = float(item[1])
            elif isinstance(item, dict) or hasattr(item, "get"):
                # dict-like row
                cat = item.get("category") or item.get("video_id") or item.get("name")
                lvl = item.get("current_level") or item.get("current") or item.get("level") or item.get("block_level")
                if cat is not None and lvl is not None:
                    out[str(cat)] = float(lvl)
            else:
                # sqlite3.Row
                try:
                    cat = item["category"]
                    lvl = item["current_level"]
                    out[str(cat)] = float(lvl)
                except Exception:
                    # try index access
                    try:
                        out[str(item[0])] = float(item[1])
                    except Exception:
                        continue
    except TypeError:
        # not iterable
        pass
    return out

def test_set_and_get_block_level(category_block_stats_fixture):
    db = category_block_stats_fixture
    db.init_db()
    db.set_block_level("Science", 0.42)
    value = db.get_block_level("Science")
    # Accept dict or float return
    if isinstance(value, dict):
        value = value.get("current_level")
    assert value == pytest.approx(0.42)


def test_init_db_creates_table(category_block_stats_fixture):
    db = category_block_stats_fixture
    db.init_db()
    # Should not raise

def test_set_block_level_does_not_error(category_block_stats_fixture):
    db = category_block_stats_fixture
    db.init_db()
    db.set_block_level("TestCat", 0.5)
    # Should not raise

def bulk_insert_or_replace(rows_to_insert, db_path=CATEGORY_BLOCK_STATS_DB_PATH):
    """Bulk insert or replace rows in the category_block_stats table."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR REPLACE INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        """,
        rows_to_insert,
    )
    conn.commit()
    conn.close()

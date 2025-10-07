import sqlite3
from datetime import datetime
from databases.db_utils import execute_query, connect_db

USER_SETTINGS_DB_PATH = "user_settings.db"

# -----------------------------
# Initialize table
# -----------------------------
def init_db(db_path=USER_SETTINGS_DB_PATH):
    """Ensure the user_filter_settings table exists for graph stats tracking."""
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            total_video INTEGER DEFAULT 0,
            blocked_hours REAL DEFAULT 0,
            block_level INTEGER DEFAULT 0
        )
    """)
    conn.close()

# -----------------------------
# Set block level for a category
# -----------------------------
def set_block_level(category: str, level: int, db_path=USER_SETTINGS_DB_PATH):
    """Set or update the block level for a category."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_filter_settings
        SET block_level = ?, last_updated_time = ?
        WHERE category = ?
    """, (level, datetime.now(), category))

    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO user_filter_settings (category, total_video, blocked_hours, block_level, last_updated_time)
            VALUES (?, 0, 0, ?, ?)
        """, (category, level, datetime.now()))

    conn.commit()
    conn.close()

# -----------------------------
# Get block level for a category
# -----------------------------
def get_block_level(category: str, db_path=USER_SETTINGS_DB_PATH) -> int | None:
    """Return the block level for a category."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT block_level FROM user_filter_settings WHERE category = ?", (category,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# -----------------------------
# Get all categories and their block levels
# -----------------------------
def get_all_block_levels(db_path=USER_SETTINGS_DB_PATH) -> dict:
    """Return all categories with their block levels as a dictionary."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT category, block_level FROM user_filter_settings")
    rows = cursor.fetchall()
    conn.close()
    return {category: level for category, level in rows}

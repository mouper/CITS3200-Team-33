import sqlite3
from datetime import datetime
from databases.db_utils import execute_query, connect_db

USER_SETTINGS_DB_PATH = "user_settings.db"

# -----------------------------
# Initialize table
# -----------------------------
def init_db(db_path=USER_SETTINGS_DB_PATH):
    """Create user_filter_settings table if it doesn't exist."""
    conn = connect_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT DEFAULT 'Moderate',
            is_active INTEGER DEFAULT 1,
            count INTEGER DEFAULT 0,
            total_blocked_time REAL DEFAULT 0,
            total_video INTEGER DEFAULT 0,
            last_updated_time TEXT
        )
    """)
    conn.close()

# -----------------------------
# Increment total video count
# -----------------------------
def increment_total_video(category: str, db_path=USER_SETTINGS_DB_PATH):
    """Increment total_video for a category; create category if missing."""
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE user_filter_settings SET total_video = total_video + 1, last_updated_time = ? WHERE category = ?",
                   (datetime.now(), category))
    
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO user_filter_settings (category, filter_strength, is_active, count, total_blocked_time, total_video, last_updated_time)
            VALUES (?, 'Moderate', 1, 0, 0, 1, ?)
        """, (category, datetime.now()))

    conn.commit()
    conn.close()

# -----------------------------
# Increment blocked stats
# -----------------------------
def increment_blocked_stats(category: str, duration_hours: float = 0, db_path=USER_SETTINGS_DB_PATH):
    """Increment count and total_blocked_time for a category."""
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE user_filter_settings
        SET count = count + 1,
            total_blocked_time = total_blocked_time + ?,
            last_updated_time = ?
        WHERE category = ?
    """, (duration_hours, datetime.now(), category))

    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO user_filter_settings
            (category, filter_strength, is_active, count, total_blocked_time, total_video, last_updated_time)
            VALUES (?, 'Moderate', 1, 1, ?, 0, ?)
        """, (category, duration_hours, datetime.now()))

    conn.commit()
    conn.close()

# -----------------------------
# Get top categories by blocked hours
# -----------------------------
def get_top_categories_by_hours(limit=5, db_path=USER_SETTINGS_DB_PATH):
    """Return top categories sorted by total_blocked_time."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, total_blocked_time
        FROM user_filter_settings
        ORDER BY total_blocked_time DESC
        LIMIT ?
    """, (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

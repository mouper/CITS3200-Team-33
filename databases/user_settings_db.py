from datetime import datetime
from .db_utils import connect_db
from .config import USER_SETTINGS_DB_PATH
import sqlite3
import json
import os
from pathlib import Path

def _seed_default_categories(db_path=USER_SETTINGS_DB_PATH):
    """Seed the database with all categories from categories.v2.json on first run."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # Check if database is already seeded
    cursor.execute("SELECT COUNT(*) FROM user_filter_settings")
    count = cursor.fetchone()[0]
    
    if count > 0:
        # Database already has data, don't reseed
        conn.close()
        return
    
    # Load categories from categories.v2.json
    try:
        # Get the path to the categories file relative to this database file
        current_dir = Path(__file__).resolve().parent
        repo_root = current_dir.parent
        cat_path = repo_root / "packages" / "llm_client" / "models" / "categories.v2.json"
        
        with open(cat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            categories = data.get("allowedLabels", [])
    except Exception as e:
        conn.close()
        return
    
    # Categories that should be active by default
    active_categories = {
        "Sensational/Outrage News",
        "Politics",
        "Gaming",
        "Sexual and Explicit", 
        "Violent and Graphic", 
        "Controversial and Conspiracy Theories"
    }
    
    # Insert all categories with appropriate settings
    for category in categories:
        is_active = category in active_categories
        filter_strength = "Moderate"  # Default strength for all categories
        
        cursor.execute('''
            INSERT INTO user_filter_settings (category, filter_strength, is_active, last_updated_time, count, total_blocked_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (category, filter_strength, int(is_active), datetime.now(), 0, 0))
    
    conn.commit()
    conn.close()


def init_db(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    # Create table if missing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT CHECK(filter_strength IN ('Weak','Moderate','Strong','Extra Strong','Blocked')),
            is_active BOOLEAN NOT NULL CHECK(is_active IN (0, 1)),
            last_updated_time TIMESTAMP,
            count INTEGER DEFAULT 0,
            total_blocked_time INTEGER DEFAULT 0,
            total_video INTEGER DEFAULT 0
        )
    ''')
    conn.close()
    
    # Seed with default categories on first run
    _seed_default_categories(db_path)

def set_settings(category, filter_strength, is_active, count=0, total_blocked_time=0, total_video=0, db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_filter_settings (category, filter_strength, is_active, last_updated_time, count, total_blocked_time, total_video)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(category) DO UPDATE SET
            filter_strength=excluded.filter_strength,
            is_active=excluded.is_active,
            last_updated_time=excluded.last_updated_time,
            count=excluded.count,
            total_blocked_time=excluded.total_blocked_time,
            total_video=excluded.total_video
    ''', (category, filter_strength, int(is_active), datetime.now(), count, total_blocked_time, total_video))
    conn.commit()
    conn.close()

def get_settings(category, db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, filter_strength, is_active, last_updated_time, count, total_blocked_time, total_video
        FROM user_filter_settings
        WHERE category = ?
    ''', (category,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'category': result[0],
            'filter_strength': result[1],
            'is_active': bool(result[2]),
            'last_updated_time': result[3],
            'count': result[4],
            'total_blocked_time': result[5],
            'total_video': result[6]
        }
    else:
        return None

def get_all_settings(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, filter_strength, is_active, last_updated_time, count, total_blocked_time, total_video
        FROM user_filter_settings
        ORDER BY category
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            'category': r[0],
            'filter_strength': r[1],
            'is_active': bool(r[2]),
            'last_updated_time': r[3],
            'count': r[4],
            'total_blocked_time': r[5],
            'total_video': r[6]
        }
        for r in rows
    ]

def cleanup(db_path=USER_SETTINGS_DB_PATH):
    # If you want to implement retention, add logic here
    pass


def count_active(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM user_filter_settings WHERE is_active = 1")
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_max_blocked_category(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)  # Opens user_filter_settings.db
    cur = conn.cursor()
    cur.execute("""
        SELECT category, MAX(count)
        FROM user_filter_settings
    """)
    row = cur.fetchone()
    conn.close()
    return row[0]

def total_block(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT sum(count) FROM user_filter_settings")
    totalV = cur.fetchone()[0]
    conn.close()
    return totalV

def total_videos(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT sum(total_video) FROM user_filter_settings")
    totalV = cur.fetchone()[0]
    conn.close()
    return totalV

def total_videos_sum(db_path=USER_SETTINGS_DB_PATH):
    """Get sum of all total_video values across all categories, regardless of active status."""
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT sum(total_video) FROM user_filter_settings")
    totalV = cur.fetchone()[0]
    conn.close()
    return totalV or 0

def total_blocked_sum(db_path=USER_SETTINGS_DB_PATH):
    """Get sum of all count values across all categories, regardless of active status."""
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT sum(count) FROM user_filter_settings")
    totalV = cur.fetchone()[0]
    conn.close()
    return totalV or 0

def get_all_strength_levels(db_path=USER_SETTINGS_DB_PATH):
    """
    Returns a dictionary mapping category names to their filter strength levels.
    Used by the probabilistic filter to determine blocking behavior.
    """
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, filter_strength
        FROM user_filter_settings
        WHERE is_active = 1
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary: category -> filter_strength
    return {row[0]: row[1] for row in rows}

def increment_total_video(category, db_path=USER_SETTINGS_DB_PATH):
    """
    Increment the total_video count for a category when a video is categorized.
    Creates the category if it doesn't exist.
    """
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # First, try to update existing category
    cursor.execute('''
        UPDATE user_filter_settings 
        SET total_video = total_video + 1, last_updated_time = ?
        WHERE category = ?
    ''', (datetime.now(), category))
    
    # If no rows were affected, create the category
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO user_filter_settings 
            (category, filter_strength, is_active, count, total_blocked_time, total_video, last_updated_time)
            VALUES (?, 'Moderate', 1, 0, 0, 1, ?)
        ''', (category, datetime.now()))
    
    conn.commit()
    conn.close()

def increment_blocked_stats(category, duration_hours=0, db_path=USER_SETTINGS_DB_PATH):
    """
    Increment the count and total_blocked_time for a category when a video is blocked.
    duration_hours: Duration in hours to add to total_blocked_time
    Creates the category if it doesn't exist.
    """
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # First, try to update existing category
    cursor.execute('''
        UPDATE user_filter_settings 
        SET count = count + 1, 
            total_blocked_time = total_blocked_time + ?,
            last_updated_time = ?
        WHERE category = ?
    ''', (duration_hours, datetime.now(), category))
    
    # If no rows were affected, create the category
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO user_filter_settings 
            (category, filter_strength, is_active, count, total_blocked_time, total_video, last_updated_time)
            VALUES (?, 'Moderate', 1, 1, ?, 0, ?)
        ''', (category, duration_hours, datetime.now()))
    
    conn.commit()
    conn.close()

def get_top_categories_by_hours(limit=5, db_path=USER_SETTINGS_DB_PATH):
    """
    Get top categories by total_blocked_time.
    Returns list of dicts with category and total_blocked_time.
    """
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT category, total_blocked_time
        FROM user_filter_settings
        WHERE total_blocked_time > 0
        ORDER BY total_blocked_time DESC
        LIMIT ?
    ''', (limit,))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'category': row[0],
            'total_blocked_time': row[1]
        })
    
    conn.close()
    return results

def get_max_blocked_hours_category(db_path=USER_SETTINGS_DB_PATH):
    """
    Get the category with the highest total_blocked_time.
    Returns dict with category and total_blocked_time, or None if no data.
    """
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT category, total_blocked_time
        FROM user_filter_settings
        WHERE total_blocked_time > 0
        ORDER BY total_blocked_time DESC
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'category': result[0],
            'total_blocked_time': result[1]
        }
    return None

if __name__ == "__main__":
    init_db()
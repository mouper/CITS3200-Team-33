from datetime import datetime
from .db_utils import connect_db
from .config import USER_SETTINGS_DB_PATH
import sqlite3

def init_db(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    # Create table if missing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT CHECK(filter_strength IN ('Weak','Moderate','Strong','Extra Strong','Blocked')),
            is_active BOOLEAN NOT NULL CHECK(is_active IN (0, 1)),
            last_updated_time TIMESTAMP
        )
    ''')

    # Detect and repair old CHECK constraint that doesn't include 'Blocked'
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name='user_filter_settings'
    """)
    row = cursor.fetchone()
    if row and row[0] and "'Blocked'" not in row[0]:
        # Rebuild table with correct CHECK constraint, preserving data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_filter_settings_new (
                category TEXT PRIMARY KEY,
                filter_strength TEXT CHECK(filter_strength IN ('Weak','Moderate','Strong','Extra Strong','Blocked')),
                is_active BOOLEAN NOT NULL CHECK(is_active IN (0, 1)),
                last_updated_time TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO user_filter_settings_new (category, filter_strength, is_active, last_updated_time)
            SELECT category, filter_strength, is_active, last_updated_time FROM user_filter_settings
        ''')
        cursor.execute('DROP TABLE user_filter_settings')
        cursor.execute('ALTER TABLE user_filter_settings_new RENAME TO user_filter_settings')

    conn.commit()
    conn.close()

def set_settings(category, filter_strength, is_active, db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_filter_settings (category, filter_strength, is_active, last_updated_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(category) DO UPDATE SET
            filter_strength=excluded.filter_strength,
            is_active=excluded.is_active,
            last_updated_time=excluded.last_updated_time
    ''', (category, filter_strength, int(is_active), datetime.now()))
    conn.commit()
    conn.close()

def get_settings(category, db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, filter_strength, is_active, last_updated_time
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
            'last_updated_time': result[3]
        }
    else:
        return None

def get_all_settings(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, filter_strength, is_active, last_updated_time
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
            'last_updated_time': r[3]
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
        SELECT category, MAX(total_blocked_vid)
        FROM user_filter_settings
    """)
    row = cur.fetchone()
    conn.close()
    return row[0]

def total_block(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path) 
    cur = conn.cursor()
    cur.execute("SELECT sum(total_blocked_vid) FROM user_filter_settings")
    totalV = cur.fetchone()[0]
    conn.close()
    return totalV

if __name__ == "__main__":
    init_db()
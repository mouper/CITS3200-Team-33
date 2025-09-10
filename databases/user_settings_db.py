from datetime import datetime
from .db_utils import connect_db
from .config import USER_SETTINGS_DB_PATH

def init_db(db_path=USER_SETTINGS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_filter_settings (
            category TEXT PRIMARY KEY,
            filter_strength TEXT CHECK(filter_strength IN ( 'Weak', 'Moderate', 'Strong' and 'Extra Strong')),
            is_active BOOLEAN NOT NULL CHECK(is_active IN (0, 1)),
            last_updated_time TIMESTAMP
        )
    ''')
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

def cleanup(db_path=USER_SETTINGS_DB_PATH):
    # If you want to implement retention, add logic here
    pass

if __name__ == "__main__":
    init_db()
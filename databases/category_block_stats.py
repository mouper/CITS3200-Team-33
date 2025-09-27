from datetime import datetime
from .db_utils import connect_db, fetch_all
from .config import GRAPH_STATS_DB_PATH

def init_db(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_block_stats (
            category TEXT PRIMARY KEY,
            current_level REAL CHECK(current_level >= 0 AND current_level <= 1),
            last_updated_time TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def set_block_level(category, current_level, db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        ON CONFLICT(category) DO UPDATE SET
            current_level=excluded.current_level,
            last_updated_time=excluded.last_updated_time
    ''', (category, float(current_level), datetime.now()))
    conn.commit()
    conn.close()

def get_block_level(category, db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        WHERE category = ?
    ''', (category,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'category': result[0],
            'current_level': result[1],
            'last_updated_time': result[2]
        }
    else:
        return None

def get_all_block_levels(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT category, current_level, last_updated_time FROM category_block_stats')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

if __name__ == "__main__":
    init_db()
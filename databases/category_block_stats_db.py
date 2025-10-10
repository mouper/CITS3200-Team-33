import math
from datetime import datetime
from typing import Optional

from .db_utils import connect_db
from .config import GRAPH_STATS_DB_PATH


def init_db(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            current_level REAL CHECK(current_level >= 0 AND current_level <= 1),
            last_updated_time TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_block_stats_category ON category_block_stats(category)"
    )
    conn.commit()
    conn.close()


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    return None
    return None


def _decay_probability(value: float, last_updated: datetime, now: datetime, half_life_hours: float) -> float:
    if half_life_hours <= 0:
        return value
    elapsed_minutes = (now - last_updated).total_seconds() / 60.0
    if elapsed_minutes <= 0:
        return value
    decay_constant = math.log(2) / (half_life_hours * 60.0)
    decayed = value * math.exp(-decay_constant * elapsed_minutes)
    return max(0.0, min(1.0, decayed))


def set_block_level(category, current_level, db_path=GRAPH_STATS_DB_PATH, half_life_hours: float = 1.0):
    current_level = float(current_level)
    now = datetime.utcnow()

    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        """,
        (category, current_level, now),
    )

    decay_now = datetime.utcnow()
    cursor.execute("SELECT DISTINCT category FROM category_block_stats")
    categories = [row[0] for row in cursor.fetchall() if row[0] is not None]

    for cat in categories:
        cursor.execute(
            """
            SELECT current_level, last_updated_time
            FROM category_block_stats
            WHERE category = ?
            ORDER BY last_updated_time DESC, id DESC
            LIMIT 1
            """,
            (cat,),
        )
        latest = cursor.fetchone()
        if not latest:
            continue
        latest_level = float(latest[0]) if latest[0] is not None else 0.0
        latest_updated = _parse_datetime(latest[1])
        if latest_updated is None:
            continue
        decayed_level = _decay_probability(latest_level, latest_updated, decay_now, half_life_hours)
        if math.isclose(decayed_level, latest_level, rel_tol=1e-9, abs_tol=1e-9):
            continue
        cursor.execute(
            """
            INSERT INTO category_block_stats (category, current_level, last_updated_time)
            VALUES (?, ?, ?)
            """,
            (cat, decayed_level, decay_now),
        )

    conn.commit()
    conn.close()


def get_block_level(category, db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        WHERE category = ?
        ORDER BY last_updated_time DESC, id DESC
        LIMIT 1
        """,
        (category,),
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "category": result[0],
            "current_level": result[1],
            "last_updated_time": result[2],
        }
    return None


def get_all_block_levels(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        ORDER BY last_updated_time DESC, id DESC
        """
    )
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_category_history(category, db_path=GRAPH_STATS_DB_PATH):
    """Get all level data for a specific category from category_block_stats table."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT current_level, last_updated_time 
        FROM category_block_stats 
        WHERE category = ?
        ORDER BY last_updated_time
    ''', (category,))
    results = cursor.fetchall()
    conn.close()
    
    # Return all data points for this category
    return [{'level': row[0], 'updated_at': row[1]} for row in results]

def get_all_categories_history(db_path=GRAPH_STATS_DB_PATH):
    """Get current level data for all categories from category_block_stats table."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, current_level, last_updated_time 
        FROM category_block_stats 
        ORDER BY category
    ''')
    results = cursor.fetchall()
    conn.close()
    return [{'category': row[0], 'level': row[1], 'updated_at': row[2]} for row in results]


if __name__ == "__main__":
    init_db()
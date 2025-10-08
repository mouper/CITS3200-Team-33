from datetime import datetime
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


def set_block_level(category, current_level, db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        """,
        (category, float(current_level), datetime.now()),
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


if __name__ == "__main__":
    init_db()
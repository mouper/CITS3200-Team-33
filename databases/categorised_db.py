"""
categorised_db.py — Stores videos and categories for quick reference.
TTL: 24 hours
"""

from db_utils import connect_db, execute_query, fetch_all, current_timestamp
from config import CATEGORIES_DB_PATH, CATEGORIES_TTL

def init_db():
    conn = connect_db(CATEGORIES_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS categorised_videos (
        video_id  TEXT PRIMARY KEY,
        category  TEXT,
        metadata  TEXT,
        timestamp INTEGER
    )
    """)
    conn.close()

def insert_categorised(video_id, category, metadata_json):
    conn = connect_db(CATEGORIES_DB_PATH)
    execute_query(conn,
        "REPLACE INTO categorised_videos VALUES (?, ?, ?, ?)",
        (video_id, category, metadata_json, current_timestamp())
    )
    conn.close()

def cleanup():
    conn = connect_db(CATEGORIES_DB_PATH)
    cutoff = current_timestamp() - CATEGORIES_TTL
    execute_query(conn, "DELETE FROM categorised_videos WHERE timestamp < ?", (cutoff,))
    conn.close()


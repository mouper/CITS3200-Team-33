"""
db_utils.py — Shared helper functions for SQLite database operations.
Keeps database connection and query execution consistent across all modules.
"""

import sqlite3
from contextlib import closing
import time

def connect_db(path):
    """Open a SQLite connection to the given path with dict-like row access."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(conn, query, params=()):
    """Execute a write/delete/update query and commit changes."""
    with closing(conn.cursor()) as cur:
        cur.execute(query, params)
    conn.commit()

def fetch_all(conn, query, params=()):
    """Run a SELECT query and return all matching rows."""
    with closing(conn.cursor()) as cur:
        cur.execute(query, params)
        return cur.fetchall()

def current_timestamp():
    """Return the current UNIX timestamp (seconds since epoch)."""
    return int(time.time())

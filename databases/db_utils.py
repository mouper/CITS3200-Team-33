"""
db_utils.py — Shared helper functions for SQLite DB operations.
"""

import sqlite3
import os
import time

def connect_db(path):
    """Connect to a SQLite database file with sane concurrency defaults.

    - Ensures parent directory exists
    - Sets WAL journal mode for better read/write concurrency
    - Sets a busy timeout to reduce 'database is locked' errors under contention
    """
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn

def execute_query(conn, query, params=()):
    """Execute INSERT/UPDATE/DELETE queries."""
    with conn:
        conn.execute(query, params)

def fetch_all(conn, query, params=()):
    """Run a SELECT query and return all rows."""
    cur = conn.cursor()
    cur.execute(query, params)
    return cur.fetchall()

def current_timestamp():
    """Get current time as Unix timestamp."""
    return int(time.time())

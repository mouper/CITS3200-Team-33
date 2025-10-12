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

def parse_duration_to_seconds(duration_str):
    """Convert YouTube duration format (PT3M34S) to seconds."""
    if not duration_str or not duration_str.startswith('PT'):
        return None
    
    try:
        # Remove PT prefix
        duration = duration_str[2:]
        total_seconds = 0
        
        # Parse hours
        if 'H' in duration:
            hours_part = duration.split('H')[0]
            total_seconds += int(hours_part) * 3600
            duration = duration.split('H')[1]
        
        # Parse minutes
        if 'M' in duration:
            minutes_part = duration.split('M')[0]
            total_seconds += int(minutes_part) * 60
            duration = duration.split('M')[1]
        
        # Parse seconds
        if 'S' in duration:
            seconds_part = duration.split('S')[0]
            total_seconds += int(seconds_part)
        
        return total_seconds
    except (ValueError, IndexError):
        return None

def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if not seconds:
        return "0s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

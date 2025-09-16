"""
blocked_videos_db.py — Stores blocked videos with their duration and metadata.
TTL (Time-To-Live): 90 days
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import BLOCKED_VIDEOS_DB_PATH, BLOCKED_VIDEOS_TTL
import json

def init_db():
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS blocked_videos (
        video_id TEXT PRIMARY KEY,
        duration_hours REAL,  -- Duration in hours (e.g., 0.5 for 30 minutes)
        blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When the video was blocked
    )
    """)
    
    # Add blocked_at column to existing tables if it doesn't exist
    try:
        execute_query(conn, "ALTER TABLE blocked_videos ADD COLUMN blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        # Column already exists, ignore error
        pass
    
    conn.close()

def log_blocked_video(video_id, duration=None, duration_seconds=None, duration_hours=None, metadata_json=None, blocked_at=None):
    """Log a blocked video with its duration in hours and timestamp."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    # Calculate duration in hours
    if duration_hours is not None:
        hours = duration_hours
    elif duration_seconds is not None:
        hours = duration_seconds / 3600.0  # Convert seconds to hours
    elif duration:
        seconds = parse_duration_to_seconds(duration)
        hours = seconds / 3600.0 if seconds else 0
    elif metadata_json:
        try:
            metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
            duration = metadata.get('duration')
            if duration:
                seconds = parse_duration_to_seconds(duration)
                hours = seconds / 3600.0 if seconds else 0
            else:
                hours = 0
        except (json.JSONDecodeError, TypeError):
            hours = 0
    else:
        hours = 0
    
    # Use provided timestamp or current time
    timestamp = blocked_at or current_timestamp()
    
    execute_query(conn, """
    REPLACE INTO blocked_videos (video_id, duration_hours, blocked_at)
    VALUES (?, ?, ?)
    """, (video_id, hours, timestamp))
    
    conn.close()

def get_blocked_videos(limit=None):
    """Get blocked videos with optional limit."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    # Check if blocked_at column exists
    try:
        query = "SELECT video_id, duration_hours, blocked_at FROM blocked_videos ORDER BY blocked_at DESC"
        if limit:
            query += " LIMIT ?"
            rows = fetch_all(conn, query, (limit,))
        else:
            rows = fetch_all(conn, query)
    except:
        # Fallback to old schema if blocked_at column doesn't exist
        query = "SELECT video_id, duration_hours FROM blocked_videos ORDER BY video_id"
        if limit:
            query += " LIMIT ?"
            rows = fetch_all(conn, query, (limit,))
        else:
            rows = fetch_all(conn, query)
        
        # Convert Row objects to dicts and add blocked_at for backward compatibility
        rows = [dict(row) for row in rows]
        for row in rows:
            row['blocked_at'] = None
    
    conn.close()
    # Convert Row objects to dictionaries for JSON serialization
    return [dict(row) for row in rows]

def get_blocked_videos_stats():
    """Get simple statistics about blocked videos."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    # Total blocked videos
    total_blocked = fetch_all(conn, "SELECT COUNT(*) as count FROM blocked_videos")[0]['count']
    
    # Total duration blocked in hours
    total_hours = fetch_all(conn, """
        SELECT SUM(duration_hours) as total_hours FROM blocked_videos 
        WHERE duration_hours IS NOT NULL
    """)[0]['total_hours'] or 0
    
    # Get date range
    date_range = fetch_all(conn, """
        SELECT MIN(blocked_at) as earliest, MAX(blocked_at) as latest 
        FROM blocked_videos 
        WHERE blocked_at IS NOT NULL
    """)[0]
    
    conn.close()
    
    return {
        'total_blocked': total_blocked,
        'total_duration_hours': total_hours,
        'total_duration_formatted': f"{total_hours:.2f} hours",
        'earliest_blocked': date_range['earliest'],
        'latest_blocked': date_range['latest']
    }

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

def cleanup():
    """Clean up blocked video records (no TTL for this simple version)."""
    # No cleanup needed for this simple version
    pass

def get_blocked_videos_by_date_range(start_date=None, end_date=None):
    """Get blocked videos within a date range."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    query = "SELECT video_id, duration_hours, blocked_at FROM blocked_videos WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND blocked_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND blocked_at <= ?"
        params.append(end_date)
    
    query += " ORDER BY blocked_at DESC"
    
    rows = fetch_all(conn, query, params)
    conn.close()
    # Convert Row objects to dictionaries
    return [dict(row) for row in rows]

def get_blocked_videos_today():
    """Get videos blocked today."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    rows = fetch_all(conn, """
        SELECT video_id, duration_hours, blocked_at 
        FROM blocked_videos 
        WHERE DATE(blocked_at) = DATE('now')
        ORDER BY blocked_at DESC
    """)
    
    conn.close()
    # Convert Row objects to dictionaries
    return [dict(row) for row in rows]

def get_blocked_videos_this_week():
    """Get videos blocked this week."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    rows = fetch_all(conn, """
        SELECT video_id, duration_hours, blocked_at 
        FROM blocked_videos 
        WHERE blocked_at >= DATE('now', '-7 days')
        ORDER BY blocked_at DESC
    """)
    
    conn.close()
    # Convert Row objects to dictionaries
    return [dict(row) for row in rows]

def get_blocked_videos_stats_by_period():
    """Get statistics broken down by time periods."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    
    # Today
    today_count = fetch_all(conn, """
        SELECT COUNT(*) as count FROM blocked_videos 
        WHERE DATE(blocked_at) = DATE('now')
    """)[0]['count']
    
    # This week
    week_count = fetch_all(conn, """
        SELECT COUNT(*) as count FROM blocked_videos 
        WHERE blocked_at >= DATE('now', '-7 days')
    """)[0]['count']
    
    # This month
    month_count = fetch_all(conn, """
        SELECT COUNT(*) as count FROM blocked_videos 
        WHERE blocked_at >= DATE('now', 'start of month')
    """)[0]['count']
    
    conn.close()
    
    return {
        'today': today_count,
        'this_week': week_count,
        'this_month': month_count
    }

def delete_blocked_video(video_id):
    """Remove a specific blocked video record."""
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    execute_query(conn, "DELETE FROM blocked_videos WHERE video_id = ?", (video_id,))
    conn.close()

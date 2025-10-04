"""
blocked_videos_db.py — Stores blocked videos with their duration and metadata.
TTL (Time-To-Live): 90 days
"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import BLOCKED_VIDEOS_DB_PATH, BLOCKED_VIDEOS_TTL
from . import categorised_db
from . import user_settings_db
from . import metadata_cache_db
import json
import os
import requests

def init_db():
    conn = connect_db(BLOCKED_VIDEOS_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS blocked_videos (
        video_id TEXT PRIMARY KEY,
        duration_hours REAL,  -- Duration in hours (e.g., 0.5 for 30 minutes)
        blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When the video was blocked
    )
    """)
    
    conn.close()

def log_blocked_video(video_id, duration=None, duration_seconds=None, duration_hours=None, metadata_json=None, blocked_at=None):
    """Log a blocked video by updating category statistics only (no blocked_videos table)."""
    
    # Calculate duration in hours
    hours = 0
    
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
            
            # Try different possible locations for duration in metadata
            duration = None
            
            # Check direct duration field
            if metadata.get('duration'):
                duration = metadata['duration']
            
            # Check nested metadata structure
            elif metadata.get('metadata') and metadata['metadata'].get('duration'):
                duration = metadata['metadata']['duration']
            
            # Check contentDetails structure (YouTube API format)
            elif metadata.get('contentDetails') and metadata['contentDetails'].get('duration'):
                duration = metadata['contentDetails']['duration']
            
            if duration:
                seconds = parse_duration_to_seconds(duration)
                hours = seconds / 3600.0 if seconds else 0
            else:
                hours = 0
                
        except (json.JSONDecodeError, TypeError) as e:
            hours = 0
    else:
        # No duration information available - use 0 hours
        hours = 0
    
    # Update category statistics directly
    try:
        # Get all categorised videos to find the category for this video_id
        categorised_videos = categorised_db.get_all_categorised()
        video_category = None
        
        for video in categorised_videos:
            if video['video_id'] == video_id:
                video_category = video['category']
                break
        
        # If we found the category, update the blocked statistics with duration in hours
        if video_category:
            user_settings_db.increment_blocked_stats(video_category, hours)
        else:
            pass  # No category found for blocked video
    except Exception as e:
        # Log error but don't fail the blocked video logging
        pass  # Could not update category stats for blocked video

def get_blocked_videos(limit=None):
    """Get blocked videos from user_filter_settings (no individual video records)."""
    # Since we don't store individual blocked videos, return empty list
    # The actual blocked video information is now aggregated in user_filter_settings
    return []

def get_blocked_videos_stats():
    """Get simple statistics about blocked videos from user_filter_settings."""
    # Get stats from user_filter_settings instead of blocked_videos table
    all_settings = user_settings_db.get_all_settings()
    
    total_blocked = sum(setting['count'] for setting in all_settings)
    total_hours = sum(setting['total_blocked_time'] for setting in all_settings)
    
    return {
        'total_blocked': total_blocked,
        'total_duration_hours': total_hours,
        'total_duration_formatted': f"{total_hours:.2f} hours",
        'earliest_blocked': None,  # No individual records, so no date range
        'latest_blocked': None
    }

def fetch_duration_from_youtube_api(video_id):
    """Fetch video duration from YouTube API when metadata is not available."""
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '../../server/.env'))
        
        api_key = os.getenv("YT_API_KEY")
        if not api_key:
            return 0
        
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'contentDetails',
            'id': video_id,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                duration_str = data['items'][0]['contentDetails']['duration']
                seconds = parse_duration_to_seconds(duration_str)
                return seconds / 3600.0 if seconds else 0  # Convert to hours
        
        return 0
    except Exception as e:
        return 0

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
    """Get blocked videos within a date range (no individual records available)."""
    # Since we don't store individual blocked videos, return empty list
    return []

def get_blocked_videos_today():
    """Get videos blocked today (no individual records available)."""
    # Since we don't store individual blocked videos, return empty list
    return []

def get_blocked_videos_this_week():
    """Get videos blocked this week (no individual records available)."""
    # Since we don't store individual blocked videos, return empty list
    return []

def get_blocked_videos_stats_by_period():
    """Get statistics broken down by time periods (no individual records available)."""
    # Since we don't store individual blocked videos with timestamps, return zeros
    return {
        'today': 0,
        'this_week': 0,
        'this_month': 0
    }

def delete_blocked_video(video_id):
    """Remove a specific blocked video record (no individual records to delete)."""
    # Since we don't store individual blocked videos, nothing to delete
    # The statistics are aggregated in user_filter_settings
    pass

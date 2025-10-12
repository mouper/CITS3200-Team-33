"""
categorised_db.py — Stores videos and categories for quick reference.
TTL (Time-To-Live): Cached video data expires after 24 hours to ensure relevance and reduce storage.

"""

from .db_utils import connect_db, execute_query, fetch_all, current_timestamp
from .config import CATEGORIES_DB_PATH, CATEGORIES_TTL
from . import user_settings_db
from . import metadata_cache_db
import requests
import os
from dotenv import load_dotenv

# Load environment variables from server directory
load_dotenv(os.path.join(os.path.dirname(__file__), '../server/.env'))

def init_db():
    conn = connect_db(CATEGORIES_DB_PATH)
    execute_query(conn, """
    CREATE TABLE IF NOT EXISTS categorised (
        video_id  TEXT PRIMARY KEY,
        category  TEXT,
        time_categorised INTEGER
    )
    """)
    conn.close()

def insert_categorised(video_id, category, should_block=False, duration_hours=None, duration=None, duration_seconds=None, metadata_json=None):
    conn = connect_db(CATEGORIES_DB_PATH)
    
    # Check if video already exists
    existing_video = fetch_all(conn, "SELECT video_id FROM categorised WHERE video_id = ?", (video_id,))
    is_new_video = len(existing_video) == 0
    
    execute_query(conn,
        "REPLACE INTO categorised VALUES (?, ?, ?)",
        (video_id, category, current_timestamp())
    )
    conn.close()
    
    # Only increment stats for new videos, not updates
    if is_new_video:
        # Increment total_video count for this category (for all categorizations)
        user_settings_db.increment_total_video(category)
    
    # If video should be blocked, increment count and add duration (only for new videos)
    if should_block and is_new_video:
        # Calculate duration in hours
        hours = 0
        
        # Priority 1: Use provided duration_hours
        if duration_hours is not None:
            hours = duration_hours
        # Priority 2: Use provided duration_seconds
        elif duration_seconds is not None:
            hours = duration_seconds / 3600.0
        # Priority 3: Parse provided duration string
        elif duration:
            from .blocked_videos_db import parse_duration_to_seconds
            seconds = parse_duration_to_seconds(duration)
            hours = seconds / 3600.0 if seconds else 0
        # Priority 4: Parse from provided metadata_json
        elif metadata_json:
            try:
                import json
                metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
                
                # Try different possible locations for duration in metadata
                duration_value = None
                
                # Check direct duration field
                if metadata.get('duration'):
                    duration_value = metadata['duration']
                
                # Check nested metadata structure
                elif metadata.get('metadata') and metadata['metadata'].get('duration'):
                    duration_value = metadata['metadata']['duration']
                
                # Check contentDetails structure (YouTube API format)
                elif metadata.get('contentDetails') and metadata['contentDetails'].get('duration'):
                    duration_value = metadata['contentDetails']['duration']
                
                if duration_value:
                    from .blocked_videos_db import parse_duration_to_seconds
                    seconds = parse_duration_to_seconds(duration_value)
                    hours = seconds / 3600.0 if seconds else 0
                    
            except (json.JSONDecodeError, TypeError):
                hours = 0
        # Priority 5: Fetch duration directly from YouTube API
        else:
            try:
                hours = fetch_duration_from_youtube_api(video_id)
            except Exception as e:
                hours = 0
        
        # Increment blocked stats with duration
        user_settings_db.increment_blocked_stats(category, hours)

def get_all_categorised():
    """Get all categorized videos."""
    conn = connect_db(CATEGORIES_DB_PATH)
    rows = fetch_all(conn, "SELECT * FROM categorised ORDER BY time_categorised DESC")
    conn.close()
    return rows

def cleanup():
    conn = connect_db(CATEGORIES_DB_PATH)
    cutoff = current_timestamp() - CATEGORIES_TTL
    execute_query(conn, "DELETE FROM categorised WHERE time_categorised < ?", (cutoff,))
    conn.close()

def fetch_duration_from_youtube_api(video_id):
    """
    Fetch video duration directly from YouTube API using video ID.
    Returns duration in hours.
    """
    api_key = os.getenv('YT_API_KEY')
    if not api_key:
        return 0
    
    try:
        # YouTube Data API v3 endpoint for video details
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'contentDetails',
            'id': video_id,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            duration_str = data['items'][0]['contentDetails']['duration']
            
            # Parse ISO 8601 duration (e.g., "PT10M30S")
            from .blocked_videos_db import parse_duration_to_seconds
            seconds = parse_duration_to_seconds(duration_str)
            
            if seconds:
                hours = seconds / 3600.0
                return hours
            else:
                return 0
        else:
            return 0
            
    except requests.exceptions.RequestException as e:
        return 0
    except Exception as e:
        return 0


def get_category_for_video(video_id, db_path=CATEGORIES_DB_PATH):
    """Return the stored category for a given video_id, or None if missing."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT video_id, category FROM categorised WHERE video_id = ?",
        (video_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "video_id": row["video_id"],
            "category": row["category"],
        }
    return None

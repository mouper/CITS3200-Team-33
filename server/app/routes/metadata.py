"""Metadata API routes for YouTube video processing.

Endpoints:
 - POST /api/metadata/batch - Process multiple video URLs from extension
 - POST /api/metadata/fetch - Fetch metadata for single video
 - GET  /api/metadata/fresh - Get fresh metadata awaiting processing
 - GET  /api/metadata/<video_id> - Get metadata for specific video
"""

import os
import sys
import re
import json
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
import googleapiclient.discovery
import googleapiclient.errors

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

bp = Blueprint('metadata', __name__, url_prefix='/api/metadata')

# YouTube video ID regex
_YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# URL patterns for extracting video IDs
_ID_FROM_URL_PATTERNS = [
    re.compile(r"[?&]v=([a-zA-Z0-9_-]{11})"),  # ...watch?v=VIDEOID
    re.compile(r"youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"/shorts/([a-zA-Z0-9_-]{11})"),
    re.compile(r"/embed/([a-zA-Z0-9_-]{11})"),
]

def extract_video_id(token: str) -> Optional[str]:
    """Extract video ID from YouTube URL or return the token if it's already an ID."""
    token = token.strip()
    if not token:
        return None
    if _YT_ID_RE.fullmatch(token):
        return token
    for pat in _ID_FROM_URL_PATTERNS:
        m = pat.search(token)
        if m:
            return m.group(1)
    return None

def extract_video_ids_from_urls(urls: List[str]) -> List[str]:
    """Extract unique video IDs from YouTube URLs."""
    seen = set()
    video_ids = []
    
    for url in urls:
        video_id = extract_video_id(url)
        if video_id and video_id not in seen:
            seen.add(video_id)
            video_ids.append(video_id)
    
    return video_ids

def get_api_key() -> str:
    """Get YouTube API key from environment."""
    api_key = os.getenv("YT_API_KEY")
    if not api_key:
        raise ValueError("YT_API_KEY environment variable not set")
    return api_key

def build_youtube_client(api_key: str):
    """Build YouTube API client."""
    return googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

def get_category_map(youtube, region_code: str = "US") -> Dict[str, str]:
    """Get YouTube category mapping."""
    try:
        req = youtube.videoCategories().list(part="snippet", regionCode=region_code)
        resp = req.execute()
        mapping: Dict[str, str] = {}
        for item in resp.get("items", []):
            cid = item.get("id")
            title = (item.get("snippet") or {}).get("title")
            if cid and title:
                mapping[cid] = title
        return mapping
    except googleapiclient.errors.HttpError:
        return {}

def fetch_youtube_videos_by_id(
    api_key: str,
    video_ids: List[str],
    region_code: str = "US"
) -> List[Dict[str, Any]]:
    """Fetch videos (batched by 50), store each row via DB facade, and return the rows."""
    if not video_ids:
        return []

    youtube = build_youtube_client(api_key)
    category_map = get_category_map(youtube, region_code=region_code)

    results: List[Dict[str, Any]] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        req = youtube.videos().list(
            part="id,snippet,contentDetails,statistics",
            id=",".join(chunk)
        )
        resp = req.execute()
        for item in resp.get("items", []):
            sn = item.get("snippet", {}) or {}
            st = item.get("statistics", {}) or {}
            cd = item.get("contentDetails", {}) or {}

            cat_id = sn.get("categoryId")
            cat_name = category_map.get(cat_id, None) if cat_id else None

            row = {
                "video_id": item.get("id"),
                "videoId": item.get("id"),  # Add camelCase version for categorizer
                "title": sn.get("title"),
                "description": sn.get("description"),
                "channel": sn.get("channelTitle"),  # Use 'channel' key for categorizer
                "channel_title": sn.get("channelTitle"),
                "channel_id": sn.get("channelId"),
                "publish_time": sn.get("publishedAt"),
                "category_id": cat_id,
                "category_name": cat_name,
                "duration": cd.get("duration"),
                "view_count": st.get("viewCount"),
                "like_count": st.get("likeCount"),
                "comment_count": st.get("commentCount"),
                "tags": sn.get("tags", []),
            }

            # Store into metadata cache (DB layer will JSON-encode dicts safely)
            database.insert_metadata(row["video_id"], json.dumps(row))
            results.append(row)

    return results

@bp.route('/batch', methods=['POST'])
def process_batch_urls():
    """Process multiple YouTube URLs from extension scraper."""
    try:
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({'error': 'Missing urls in request body'}), 400
        
        urls = data['urls']
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({'error': 'urls must be a non-empty list'}), 400
        
        # Limit batch size to prevent API abuse
        if len(urls) > 50:
            return jsonify({'error': 'Batch size too large (max 50 URLs)'}), 400
        
        # Extract video IDs from URLs
        video_ids = extract_video_ids_from_urls(urls)
        if not video_ids:
            return jsonify({'error': 'No valid YouTube video IDs found in URLs'}), 400
        
        # Check which videos are already categorized OR in cache
        existing_ids = []
        new_ids = []
        
        # Get already categorized video IDs
        try:
            from databases import categorised_db
            categorized_data = categorised_db.get_all_categorised()
            categorized_ids = set(item['video_id'] for item in categorized_data if hasattr(item, 'keys'))
        except ImportError:
            categorized_ids = set()
        
        for video_id in video_ids:
            # Skip if already categorized
            if video_id in categorized_ids:
                existing_ids.append(video_id)
                continue
                
            # Skip if already in cache
            existing_metadata = database.get_metadata_by_id(video_id)
            if existing_metadata:
                existing_ids.append(video_id)
            else:
                new_ids.append(video_id)
        
        # Fetch metadata for new videos only
        processed_count = 0
        if new_ids:
            try:
                api_key = get_api_key()
                results = fetch_youtube_videos_by_id(api_key, new_ids)
                processed_count = len(results)
                
                current_app.logger.info(f"Processed {processed_count} new videos from batch")
                
            except Exception as e:
                current_app.logger.error(f"Error fetching metadata: {e}")
                return jsonify({'error': f'Failed to fetch metadata: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'total_urls': len(urls),
            'valid_video_ids': len(video_ids),
            'existing_videos': len(existing_ids),
            'new_videos_processed': processed_count,
            'video_ids': video_ids,
            'existing_ids': existing_ids,
            'new_ids': new_ids
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in batch processing: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/fetch', methods=['POST'])
def fetch_single_video():
    """Fetch metadata for a single video."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing url in request body'}), 400
        
        url = data['url']
        video_id = extract_video_id(url)
        
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Check if already exists
        existing_metadata = database.get_metadata_by_id(video_id)
        if existing_metadata:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'metadata': existing_metadata,
                'already_existed': True
            })
        
        # Fetch new metadata
        api_key = get_api_key()
        results = fetch_youtube_videos_by_id(api_key, [video_id])
        
        if not results:
            return jsonify({'error': 'Video not found or API error'}), 404
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'metadata': results[0],
            'already_existed': False
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching single video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/fresh', methods=['GET'])
def get_fresh_metadata():
    """Get fresh metadata awaiting processing."""
    try:
        fresh_metadata = database.get_fresh_metadata()
        return jsonify({
            'success': True,
            'count': len(fresh_metadata),
            'metadata': fresh_metadata
        })
    except Exception as e:
        current_app.logger.error(f"Error getting fresh metadata: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<video_id>', methods=['GET'])
def get_video_metadata(video_id: str):
    """Get metadata for a specific video ID."""
    try:
        if not _YT_ID_RE.fullmatch(video_id):
            return jsonify({'error': 'Invalid video ID format'}), 400
        
        metadata = database.get_metadata_by_id(video_id)
        if not metadata:
            return jsonify({'error': 'Video not found'}), 404
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'metadata': metadata
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting video metadata: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/categorization-progress', methods=['GET'])
def get_categorization_progress():
    """Get categorization progress statistics."""
    try:
        # Check categorizer status to determine if it's actually done
        from server.app.background import get_status
        categorizer_status = get_status()
        pending_count = categorizer_status.get('pending_count', 0)
        is_running = categorizer_status.get('loop_running', False)
        
        # Get categorized videos count
        try:
            from databases import categorised_db
            categorized_data = categorised_db.get_all_categorised()
            categorized_count = len(categorized_data) if categorized_data else 0
        except ImportError:
            categorized_count = 0
        
        # Get fresh metadata count
        fresh_metadata = database.get_fresh_metadata()
        fresh_count = len(fresh_metadata)
        
        # Categorization is complete when:
        # 1. No pending videos in categorizer AND
        # 2. Either categorizer is not running OR there are no fresh videos
        is_complete = pending_count == 0 and (not is_running or fresh_count == 0)
        
        # Calculate progress
        total_videos = fresh_count + categorized_count + pending_count
        if total_videos == 0:
            progress = 100
        else:
            progress = (categorized_count / total_videos) * 100
        
        return jsonify({
            'success': True,
            'totalVideos': total_videos,
            'processedVideos': categorized_count,
            'categorizedVideos': categorized_count,
            'unprocessedVideos': fresh_count + pending_count,
            'pendingInCategorizer': pending_count,
            'progress': min(progress, 100),
            'isComplete': is_complete,
            'categorizerRunning': is_running,
            'freshCount': fresh_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting categorization progress: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/debug-fresh-videos', methods=['GET'])
def debug_fresh_videos():
    """Debug endpoint to see all fresh videos."""
    try:
        fresh_metadata = database.get_fresh_metadata()
        fresh_sample = []
        
        for item in fresh_metadata:
            if hasattr(item, 'keys'):
                fresh_sample.append({
                    'video_id': item['video_id'],
                    'time_cached': item['time_cached'],
                    'metadata': item['metadata']
                })
        
        return jsonify({
            'success': True,
            'count': len(fresh_sample),
            'videos': fresh_sample
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting fresh videos debug: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/categorized-videos', methods=['GET'])
def get_categorized_videos():
    """Get all categorized videos with their categories."""
    try:
        from databases import categorised_db
        categorized_data = categorised_db.get_all_categorised()
        
        if not categorized_data:
            return jsonify([])
        
        # Format the data for the frontend
        formatted_data = []
        for item in categorized_data:
            # Handle both dict and sqlite3.Row objects
            if hasattr(item, 'keys'):
                # sqlite3.Row object
                formatted_data.append({
                    'video_id': item['video_id'],
                    'category': item['category'],
                    'timestamp': item['time_categorised']
                })
            else:
                # dict object
                formatted_data.append({
                    'video_id': item.get('video_id') or item.get('videoId'),
                    'category': item.get('category') or item.get('category_name'),
                    'timestamp': item.get('timestamp') or item.get('time_categorized')
                })
        
        return jsonify(formatted_data)
        
    except ImportError:
        return jsonify([])
    except Exception as e:
        current_app.logger.error(f"Error getting categorized videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

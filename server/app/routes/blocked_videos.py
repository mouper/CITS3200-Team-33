"""Blocked Videos API routes for tracking blocked content and duration.

Endpoints:
 - POST /api/blocked-videos/log - Log a blocked video
 - GET  /api/blocked-videos - Get blocked videos with optional filtering
 - GET  /api/blocked-videos/stats - Get blocked videos statistics
 - DELETE /api/blocked-videos/<video_id> - Remove a blocked video record
"""

import os
import sys
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

bp = Blueprint('blocked_videos', __name__, url_prefix='/api/blocked-videos')

@bp.route('/log', methods=['POST'])
def log_blocked_video():
    """Log a blocked video with its duration in hours."""
    try:
        data = request.get_json()
        if not data or 'video_id' not in data:
            return jsonify({'error': 'Missing video_id in request body'}), 400
        
        video_id = data['video_id']
        duration = data.get('duration')
        duration_seconds = data.get('duration_seconds')
        duration_hours = data.get('duration_hours')
        metadata_json = data.get('metadata_json')
        blocked_at = data.get('blocked_at')  # Optional custom timestamp
        
        # Log the blocked video
        database.log_blocked_video(
            video_id=video_id,
            duration=duration,
            duration_seconds=duration_seconds,
            duration_hours=duration_hours,
            metadata_json=metadata_json,
            blocked_at=blocked_at
        )
        
        current_app.logger.info(f"Logged blocked video: {video_id}")
        
        return jsonify({
            'success': True,
            'message': 'Blocked video logged successfully',
            'video_id': video_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging blocked video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/', methods=['GET'])
def get_blocked_videos():
    """Get blocked videos with optional limit."""
    try:
        # Parse query parameters
        limit = request.args.get('limit', type=int)
        
        # Validate parameters
        if limit and limit <= 0:
            return jsonify({'error': 'limit must be positive'}), 400
        
        # Get blocked videos
        videos = database.get_blocked_videos(limit=limit)
        
        # Convert Row objects to dictionaries for JSON serialization
        videos_dict = [dict(video) for video in videos]
        
        return jsonify({
            'success': True,
            'count': len(videos_dict),
            'videos': videos_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting blocked videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/stats', methods=['GET'])
def get_blocked_videos_stats():
    """Get blocked videos statistics."""
    try:
        stats = database.get_blocked_videos_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting blocked videos stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<video_id>', methods=['DELETE'])
def delete_blocked_video(video_id: str):
    """Remove a blocked video record."""
    try:
        if not video_id:
            return jsonify({'error': 'video_id is required'}), 400
        
        database.delete_blocked_video(video_id)
        
        current_app.logger.info(f"Deleted blocked video record: {video_id}")
        
        return jsonify({
            'success': True,
            'message': 'Blocked video record deleted successfully',
            'video_id': video_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting blocked video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/today', methods=['GET'])
def get_blocked_videos_today():
    """Get videos blocked today."""
    try:
        videos = database.get_blocked_videos_today()
        
        # Convert Row objects to dictionaries for JSON serialization
        videos_dict = [dict(video) for video in videos]
        
        return jsonify({
            'success': True,
            'count': len(videos_dict),
            'videos': videos_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting today's blocked videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/this-week', methods=['GET'])
def get_blocked_videos_this_week():
    """Get videos blocked this week."""
    try:
        videos = database.get_blocked_videos_this_week()
        
        # Convert Row objects to dictionaries for JSON serialization
        videos_dict = [dict(video) for video in videos]
        
        return jsonify({
            'success': True,
            'count': len(videos_dict),
            'videos': videos_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting this week's blocked videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/by-date-range', methods=['GET'])
def get_blocked_videos_by_date_range():
    """Get blocked videos within a date range."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        videos = database.get_blocked_videos_by_date_range(start_date, end_date)
        
        # Convert Row objects to dictionaries for JSON serialization
        videos_dict = [dict(video) for video in videos]
        
        return jsonify({
            'success': True,
            'count': len(videos_dict),
            'videos': videos_dict,
            'start_date': start_date,
            'end_date': end_date
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting blocked videos by date range: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/stats-by-period', methods=['GET'])
def get_blocked_videos_stats_by_period():
    """Get blocked videos statistics by time period."""
    try:
        stats = database.get_blocked_videos_stats_by_period()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting blocked videos stats by period: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/bulk-log', methods=['POST'])
def bulk_log_blocked_videos():
    """Log multiple blocked videos at once."""
    try:
        data = request.get_json()
        if not data or 'videos' not in data:
            return jsonify({'error': 'Missing videos array in request body'}), 400
        
        videos = data['videos']
        if not isinstance(videos, list):
            return jsonify({'error': 'videos must be an array'}), 400
        
        if len(videos) > 100:
            return jsonify({'error': 'Too many videos (max 100)'}), 400
        
        logged_count = 0
        errors = []
        
        for video_data in videos:
            try:
                if 'video_id' not in video_data:
                    errors.append(f"Missing video_id in video data: {video_data}")
                    continue
                
                database.log_blocked_video(
                    video_id=video_data['video_id'],
                    duration=video_data.get('duration'),
                    duration_seconds=video_data.get('duration_seconds'),
                    duration_hours=video_data.get('duration_hours'),
                    metadata_json=video_data.get('metadata_json'),
                    blocked_at=video_data.get('blocked_at')
                )
                logged_count += 1
                
            except Exception as e:
                errors.append(f"Error logging video {video_data.get('video_id', 'unknown')}: {str(e)}")
        
        return jsonify({
            'success': True,
            'logged_count': logged_count,
            'total_videos': len(videos),
            'errors': errors if errors else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk logging blocked videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

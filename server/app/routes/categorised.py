"""Categorised API routes for video categorization and blocking.

Endpoints:
 - POST /api/categorised - Categorize a video with optional blocking
 - GET  /api/categorised/<video_id> - Get category for a specific video
"""

import os
import sys
from flask import Blueprint, request, jsonify, current_app

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

bp = Blueprint('categorised', __name__, url_prefix='/api/categorised')

@bp.route('/', methods=['POST'])
def categorize_video():
    """Categorize a video with optional blocking."""
    try:
        data = request.get_json()
        if not data or 'video_id' not in data or 'category' not in data:
            return jsonify({'error': 'Missing video_id or category in request body'}), 400
        
        video_id = data['video_id']
        category = data['category']
        should_block = data.get('should_block', False)
        duration_hours = data.get('duration_hours')
        duration = data.get('duration')
        duration_seconds = data.get('duration_seconds')
        metadata_json = data.get('metadata_json')
        
        # Categorize the video (with optional blocking)
        database.insert_categorised(
            video_id=video_id,
            category=category,
            should_block=should_block,
            duration_hours=duration_hours,
            duration=duration,
            duration_seconds=duration_seconds,
            metadata_json=metadata_json
        )
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'category': category,
            'blocked': should_block
        })
        
    except Exception as e:
        current_app.logger.error(f"Error categorizing video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<video_id>', methods=['GET'])
def get_video_category(video_id):
    """Get category for a specific video."""
    try:
        # Get all categorized videos and find the one we want
        categorized_videos = database.get_all_categorised()
        
        for video in categorized_videos:
            if video['video_id'] == video_id:
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'category': video['category']
                })
        
        return jsonify({'error': 'Video not found'}), 404
        
    except Exception as e:
        current_app.logger.error(f"Error getting video category: {e}")
        return jsonify({'error': 'Internal server error'}), 500

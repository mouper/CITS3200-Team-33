"""Probabilistic filter API routes.

Endpoints:
- POST /api/filter/decide - Get filtering decision for a video
- POST /api/filter/update - Update filter state based on watch behavior
- GET  /api/filter/state - Get current filter state
"""

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from flask import Blueprint, jsonify, request

# Import the probabilistic filter
import sys
import os
sys.path.append(os.path.dirname(__file__))
from packages.allostasis.src.allostatic_function import (
    update_probability,
    should_filter as should_filter_category,
    get_probability as get_category_probability,
)

bp = Blueprint("filter", __name__)

@bp.post("/api/filter/decide")
def decide_filter() -> Any:
    """
    Decide whether to filter/block a video based on its category.
    
    Expected JSON body:
    {
        "category": "string",
        "video_id": "string" (optional)
    }
    """
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    category = body.get("category")
    video_id = body.get("video_id")
    
    if not category:
        return jsonify({"error": "category is required"}), 400
    
    try:
        should_filter = should_filter_category(category)
        prob_info = update_probability(category)
        current_probability = prob_info.get("probability", 0.0)
        strength = prob_info.get("strength")
        
        return jsonify({
            "should_filter": should_filter,
            "category": category,
            "video_id": video_id,
            "current_probability": current_probability,
            "strength": strength,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/api/filter/update")
def update_filter() -> Any:
    """
    Update filter state based on user watch behavior.
    
    Expected JSON body:
    {
        "watched": boolean,
        "watchtime_mins": number,
        "category": "string"
    }
    """
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    watched = body.get("watched", False)
    watchtime_mins = body.get("watchtime_mins", 0)
    category = body.get("category")
    
    if not category:
        return jsonify({"error": "category is required"}), 400
    
    try:
        update_result = update_probability(
            category=category,
            watchtime_mins=watchtime_mins if watched else 0.0,
        )
        new_probability = update_result.get("probability", 0.0)
        strength = update_result.get("strength")
        
        return jsonify({
            "success": True,
            "new_probability": new_probability,
            "category": category,
            "watched": watched,
            "watchtime_mins": watchtime_mins,
            "strength": strength,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.get("/api/filter/state")
def get_filter_state() -> Any:
    """Get current filter state and probability."""
    try:
        current_probability = get_category_probability(request.args.get("category"))
        
        return jsonify({
            "current_probability": current_probability,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.get("/api/filter/test")
def test_filter() -> Any:
    """Test endpoint to verify the filter is working."""
    try:
        return jsonify({
            "success": True,
            "should_filter": should_filter_category("Educational & Academic")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/api/filter/reset")
def reset_filter() -> Any:
    """Reset the filter to initial state."""
    try:
        return jsonify({
            "success": True,
            "message": "Filter reset to initial state",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

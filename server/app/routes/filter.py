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
from ..allostatic_functions import ProbabilisticDecayFilter

bp = Blueprint("filter", __name__)

# Global filter instance (in production, this should be stored per user)
_filter_instance = None

def get_filter_instance():
    """Get or create the global filter instance."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = ProbabilisticDecayFilter(
            half_life_hours=1.0,  # 1 hour half-life
            initial_p=0.0
        )
    return _filter_instance

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
        filter_instance = get_filter_instance()
        
        # Debug: Check category strength
        strength = filter_instance.get_category_strength(category)
        print(f"DEBUG: Category '{category}' strength: {strength}")
        
        should_filter = filter_instance.should_filter(category)
        current_probability = filter_instance.get_probability()
        
        print(f"DEBUG: should_filter: {should_filter}, probability: {current_probability}")
        
        return jsonify({
            "should_filter": should_filter,
            "category": category,
            "video_id": video_id,
            "current_probability": current_probability,
            "strength": strength,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"DEBUG: Error in decide_filter: {e}")
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
        filter_instance = get_filter_instance()
        new_probability = filter_instance.update(
            watched=watched,
            watchtime_mins=watchtime_mins,
            category=category
        )
        
        return jsonify({
            "success": True,
            "new_probability": new_probability,
            "category": category,
            "watched": watched,
            "watchtime_mins": watchtime_mins,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.get("/api/filter/state")
def get_filter_state() -> Any:
    """Get current filter state and probability."""
    try:
        filter_instance = get_filter_instance()
        current_probability = filter_instance.get_probability()
        
        return jsonify({
            "current_probability": current_probability,
            "half_life_hours": filter_instance.half_life_hours,
            "last_update": filter_instance.last_update.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.get("/api/filter/test")
def test_filter() -> Any:
    """Test endpoint to verify the filter is working."""
    try:
        filter_instance = get_filter_instance()
        strength = filter_instance.get_category_strength("Educational & Academic")
        return jsonify({
            "success": True,
            "filter_type": type(filter_instance).__name__,
            "strength": strength,
            "should_filter": filter_instance.should_filter("Educational & Academic")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/api/filter/reset")
def reset_filter() -> Any:
    """Reset the filter to initial state."""
    try:
        global _filter_instance
        _filter_instance = ProbabilisticDecayFilter(
            half_life_hours=1.0,
            initial_p=0.0
        )
        
        return jsonify({
            "success": True,
            "message": "Filter reset to initial state",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""Stats & health API routes."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify

import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

bp = Blueprint("stats", __name__)


@bp.get("/health")
def health() -> Any:
    """Lightweight liveness/readiness check."""
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
    })

@bp.get("/api/stats/total-videos-sum")
def total_videos_sum():
    """Return sum of all total_video values across all categories."""
    total = database.get_total_videos_sum()
    return jsonify({"total_videos": total})

@bp.get("/api/stats/total-blocked-sum")
def total_blocked_sum():
    """Return sum of all count values across all categories."""
    total = database.get_total_blocked_sum()
    return jsonify({"total_blocked": total})

@bp.get("/api/stats/top-categories-by-hours")
def top_categories_by_hours():
    """Return top 5 categories by total blocked hours."""
    categories = database.get_top_categories_by_hours(limit=5)
    return jsonify({"categories": categories})

@bp.get("/api/stats/max-blocked-hours-category")
def max_blocked_hours_category():
    """Return category with highest total blocked hours."""
    category = database.get_max_blocked_hours_category()
    return jsonify({"category": category})


@bp.get("/version")
def version() -> Any:
    """Return app version info for diagnostics."""
    version_str = os.getenv("APP_VERSION", "0.0.0")
    env = os.getenv("APP_ENV", "development")
    return jsonify({
        "version": version_str,
        "env": env,
    })
@bp.get("/api/stats/category-block-history")
def category_block_history():
    """
    Return all categories with their block probability and last update time.
    This endpoint is for frontend graphing.
    """
    records = database.get_all_block_levels()
    return jsonify({"history": records})



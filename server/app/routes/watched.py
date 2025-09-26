"""Watched events API routes for logging and retrieving watch durations."""

import os
import sys
from typing import Any, Dict
from flask import Blueprint, request, jsonify, current_app

# Ensure database package is on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from databases import database

bp = Blueprint("watched", __name__, url_prefix="/api/watched")


@bp.route("/log", methods=["POST"])
def log_watch_event():
    """Log or update a watched video with start/end timestamps."""
    try:
        payload: Dict[str, Any] = request.get_json(force=True) or {}
        video_id = (payload.get("video_id") or "").strip()
        if not video_id:
            return jsonify({"error": "video_id is required"}), 400

        start_time = payload.get("start_time")
        end_time = payload.get("end_time")

        database.log_watch(video_id, start_time=start_time, end_time=end_time)
        current_app.logger.info(
            "Logged watch event", extra={"video_id": video_id, "start": start_time, "end": end_time}
        )

        return jsonify({
            "success": True,
            "video_id": video_id,
            "start_time": start_time,
            "end_time": end_time,
        })
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Error logging watched event: {exc}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/durations", methods=["GET"])
def get_watch_durations():
    """Return stored watch durations."""
    try:
        rows = database.get_watch_durations()
        return jsonify({
            "success": True,
            "items": [dict(row) for row in rows],
        })
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Error retrieving watch durations: {exc}")
        return jsonify({"error": "Internal server error"}), 500

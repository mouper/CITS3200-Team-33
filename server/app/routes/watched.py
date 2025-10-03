"""Watched events API routes."""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request

from databases import database

bp = Blueprint("watched", __name__, url_prefix="/api/watched")


@bp.post("/log")
def log_watch() -> Any:
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    video_id = body.get("video_id")
    start_time = body.get("start_time")
    end_time = body.get("end_time")

    if not video_id:
        return jsonify({"error": "video_id is required"}), 400

    database.log_watch(video_id, start_time=start_time, end_time=end_time)

    return jsonify({
        "success": True,
        "video_id": video_id,
        "start_time": start_time,
        "end_time": end_time,
    })


@bp.get("/durations")
def get_durations() -> Any:
    rows = database.get_watch_durations()
    durations = [
        {
            "video_id": row["video_id"],
            "duration_seconds": row["duration"],
        }
        for row in rows
    ]
    return jsonify({"items": durations})

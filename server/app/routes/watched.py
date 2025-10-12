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

    result = database.log_watch(video_id, start_time=start_time, end_time=end_time)

    category: str | None = None
    category_info = database.get_category_for_video(video_id)
    if category_info:
        category = category_info.get("category")

    if category:
        watch_seconds = result.get("added_seconds", 0) if isinstance(result, dict) else 0
        watch_minutes = watch_seconds / 60.0
        if watch_minutes > 0:
            database.update_category_block_level(category, watchtime_mins=watch_minutes)

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

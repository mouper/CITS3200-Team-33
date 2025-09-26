"""Watched events API routes."""

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime

from flask import Blueprint, jsonify, request

from databases import watched_db
from databases.graph_stats import get_block_level, set_block_level
from server.allostatic_functions import SimpleProbabilisticFilter

bp = Blueprint("watched", __name__, url_prefix="/api/watched")


@bp.post("/log")
def log_watch() -> Any:
    """Log or update a watch session for a given video."""
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    video_id = payload.get("video_id")
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    category = payload.get("category")
    watchtime_mins = payload.get("watchtime_mins")

    if not video_id:
        return jsonify({"error": "video_id is required"}), 400

    try:
        if start_time is not None:
            watched_db.start_watch(video_id, int(start_time))

        record = None
        if end_time is not None:
            record = watched_db.update_watch_end(video_id, int(end_time))
        else:
            record = watched_db.get_watch_entry(video_id)

        if not record:
            return jsonify({"success": True, "message": "watch logged"})

        start_ts, end_ts = record[1], record[2]
        if start_ts is None or end_ts is None:
            duration_minutes = 0.0
        else:
            duration_minutes = max(0.0, (end_ts - start_ts) / 60.0)

        new_probability = None
        if category:
            existing_level = get_block_level(category)
            initial_p = 0.0
            last_update = None
            if existing_level:
                initial_p = existing_level.get("current_level") or 0.0
                stored_ts = existing_level.get("last_updated_time")
                if isinstance(stored_ts, str):
                    try:
                        last_update = datetime.fromisoformat(stored_ts)
                    except ValueError:
                        last_update = None
                elif stored_ts:
                    last_update = stored_ts

            filter_instance = SimpleProbabilisticFilter(
                initial_p=initial_p,
                last_update=last_update,
            )

            effective_minutes = None
            if watchtime_mins is not None:
                effective_minutes = float(watchtime_mins)
            elif duration_minutes:
                effective_minutes = duration_minutes

            new_probability = filter_instance.update(
                now=datetime.utcnow(),
                watched=True,
                watchtime_mins=effective_minutes or 0.0,
                category=category,
            )
            set_block_level(category=category, current_level=new_probability)

        return jsonify({
            "success": True,
            "video_id": video_id,
            "start_time": start_ts,
            "end_time": end_ts,
            "duration_minutes": duration_minutes,
            "probability": new_probability,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/durations")
def get_durations() -> Any:
    """Return the current watch durations for all videos."""
    try:
        rows = watched_db.get_durations()
        return jsonify({
            "items": [
                {
                    "video_id": row[0],
                    "duration_seconds": row[1],
                }
                for row in rows
            ]
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

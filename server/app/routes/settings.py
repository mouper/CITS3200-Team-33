"""User settings API routes.

Endpoints:
- GET  /api/settings/<category>
- POST /api/settings/<category>
- GET  /api/settings            (list all)
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request

# Ensure databases package is on path via app/__init__.py sys.path adjustment
from databases import database


bp = Blueprint("settings", __name__)


@bp.get("/api/settings")
def list_settings() -> Any:
    """Return all user settings records."""
    rows = database.get_all_user_settings()
    return jsonify({"items": rows})


@bp.get("/api/settings/<path:category>")
def get_settings(category: str) -> Any:
    row = database.get_user_settings(category)
    if not row:
        return jsonify({
            "category": category,
            "filter_strength": None,
            "is_active": False,
            "last_updated_time": None,
        })
    return jsonify(row)


@bp.post("/api/settings/<path:category>")
def upsert_settings(category: str) -> Any:
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    filter_strength = body.get("filter_strength")
    is_active = bool(body.get("is_active", False))
    if filter_strength not in {"Weak", "Moderate", "Strong", "Extra Strong"}:
        return jsonify({"error": "invalid filter_strength"}), 400
    database.set_user_settings(category, filter_strength, is_active)
    row = database.get_user_settings(category)
    return jsonify(row), 201



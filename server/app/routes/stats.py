"""Stats & health API routes."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify


bp = Blueprint("stats", __name__)


@bp.get("/health")
def health() -> Any:
    """Lightweight liveness/readiness check."""
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
    })


@bp.get("/version")
def version() -> Any:
    """Return app version info for diagnostics."""
    version_str = os.getenv("APP_VERSION", "0.0.0")
    env = os.getenv("APP_ENV", "development")
    return jsonify({
        "version": version_str,
        "env": env,
    })



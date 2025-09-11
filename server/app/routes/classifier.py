"""Classifier/background control API routes."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from app.background import start_loop, stop_loop, get_status


bp = Blueprint("classifier", __name__)


@bp.post("/api/classifier/start")
def start_classifier() -> Any:
    model_id = request.json.get("model_id") if request.is_json else None
    interval = request.json.get("interval_seconds") if request.is_json else None
    started = start_loop(model_id=model_id, interval_seconds=interval)
    return jsonify({"started": bool(started), "status": get_status()})


@bp.post("/api/classifier/stop")
def stop_classifier() -> Any:
    stopped = stop_loop()
    return jsonify({"stopped": bool(stopped), "status": get_status()})


@bp.get("/api/classifier/status")
def classifier_status() -> Any:
    return jsonify(get_status())



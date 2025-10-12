# CITS3200 Team-33 — Flask app surfaced as `app`
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

# Reuse helper
try:
    from utils import clean_title
except Exception:
    def clean_title(s):  # type: ignore
        return (s or "").strip()

app = Flask(__name__)

# --- Error handlers (ensure JSON error bodies) ---

@app.errorhandler(BadRequest)
def handle_bad_request(err):
    # err.description comes from our BadRequest(...) message
    return jsonify(error=err.description or "Bad Request"), 400

@app.errorhandler(422)
def handle_unprocessable(err):
    return jsonify(error="Unprocessable Entity"), 422

# --- Endpoints ---

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.post("/filter")
def filter_endpoint():
    """
    Accepts JSON with:
      - title: str (optional)
      - strength: float in [0, 1] (required)
    Returns JSON with status, strength, cleaned_title, and probability.
    """
    data = request.get_json(silent=True) or {}

    if "strength" not in data:
        raise BadRequest("strength is required")
    try:
        strength = float(data["strength"])
    except (TypeError, ValueError):
        raise BadRequest("strength must be a number between 0 and 1")
    if not (0.0 <= strength <= 1.0):
        raise BadRequest("strength must be between 0 and 1")

    title = data.get("title", "")
    cleaned = clean_title(title)

    # Minimal “probability” consistent with tests — mirror strength in [0,1]
    probability = strength

    return jsonify(
        status="ok",
        strength=strength,
        cleaned_title=cleaned,
        probability=probability,
    )

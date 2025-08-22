"""
metadata_triage.py — Methods for triaging video metadata, normalisation of prompt.
- This module contains functions and utilities for analyzing, filtering, and processing
    video metadata to support downstream tasks such as categorization, caching, and user history.
"""

from databases import get_fresh_metadata, cleanup, fetch_all
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

MODEL_ID = "gpt-5-nano"
PROMPT_VERSION = "v1"

_THIS_DIR = Path(__file__).resolve().parent
_CAT_FILE = (_THIS_DIR.parent / "models" / "categories.v1.json").resolve()

def load_categories(categories_path: Optional[os.PathLike] = None) -> Tuple[List[str], str]:
    """Load categories from a JSON file.
    
    """
    path = Path(categories_path) if categories_path else _CAT_FILE
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    allowed = data.get("allowedLabels", [])
    version = data.get("version", "unknown")
    return allowed, version

ALLOWED_LABELS, CATEGORIES_VERSION = load_categories()

from databases import db_utils, config as db_config

def _get_categorised_ids() -> set:
    path = db_config.CATEGORIES_DB_PATH
    conn = db_utils.connect_db(path)
    try:
        rows = db_utils.fetch_all(conn, "SELECT video_id FROM categorised_videos")
        return {row["video_id"] for row in rows}
    finally:
        conn.close()

def _fetch_fresh_rows() -> List[Dict[str, Any]]:
    # Import here to avoid import cycles at module import time
    from databases import database as db  # type: ignore
    rows = db.get_fresh_metadata()
    # Convert sqlite3.Row -> plain dict for safer downstream usage
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({"video_id": r["video_id"], "metadata": r["metadata"], "timestamp": r["timestamp"]})
    return out

def get_fresh_metadata_unprocessed() -> List[Dict[str, Any]]:
    """
    Fetch uncategorised fresh metadata rows, skipping video_ids already in categorised DB.
    Returns list of dicts: { video_id, metadata (dict), timestamp }
    """
    categorised_ids = _get_categorised_ids()
    fresh_rows = _fetch_fresh_rows()

    results: List[Dict[str, Any]] = []
    for row in fresh_rows:
        vid = row["video_id"]
        if vid in categorised_ids:
            continue
        meta_str = row.get("metadata") or "{}"
        try:
            meta = json.loads(meta_str)
        except Exception:
            meta = {}
        results.append({"video_id": vid, "metadata": meta, "timestamp": row.get("timestamp")})
    return results


# Step 2 — Triage (redaction + simple truncation on description/tags only)

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", flags=re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
_WS_RE = re.compile(r"\s+")
# Emoji/ornamental ranges; keeps punctuation like '.' and '+' (so "C++", ".NET" are preserved)
_EMOJI_RE = re.compile(
    "["                                     # a set of ranges for emoji/symbols
    "\u2600-\u26FF"                          # Misc symbols
    "\u2700-\u27BF"                          # Dingbats
    "\U0001F300-\U0001F5FF"                  # Misc Symbols and Pictographs
    "\U0001F600-\U0001F64F"                  # Emoticons
    "\U0001F680-\U0001F6FF"                  # Transport & Map
    "\U0001F900-\U0001F9FF"                  # Supplemental Symbols and Pictographs
    "\U0001FA70-\U0001FAFF"                  # Symbols & Pictographs Extended-A
    "]",
    flags=re.UNICODE,
)

def _redact(text: Optional[str]) -> str:
    if not text:
        return ""
    s = text
    s = _URL_RE.sub(" ", s)
    s = _EMAIL_RE.sub(" ", s)
    s = _EMOJI_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit].rstrip()

def _normalise_tags(tags: Any, max_items: int = 10, max_len: int = 120) -> str:
    # Accept list/tuple or comma-separated string; return single string
    items: List[str] = []
    if isinstance(tags, (list, tuple)):
        items = [str(t).strip() for t in tags if str(t).strip()]
    elif isinstance(tags, str):
        # If it's JSON stringified list, best-effort parse
        cleaned = tags.strip()
        parsed: Optional[List[Any]] = None
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
            except Exception:
                parsed = None
        if parsed is not None and isinstance(parsed, list):
            items = [str(t).strip() for t in parsed if str(t).strip()]
        else:
            items = [t.strip() for t in cleaned.split(",") if t.strip()]
    else:
        items = []

    if not items:
        return ""

    items = items[:max_items]
    joined = ", ".join(items)
    joined = _redact(joined)
    joined = _truncate(joined, max_len)
    return joined

def triage_record(meta: Dict[str, Any]) -> Dict[str, str]:
    """
    Input meta expects keys: videoId, title, channel, description, tags (optional).
    - Title: keep as-is (no truncation)
    - Description: redact + truncate to ~200 chars
    - Tags: first up to 10, join with commas, then cap ~120 chars
    - Channel: short plain text; drop if empty/gibberish (simple: redact only)
    """
    title = str(meta.get("title") or "").strip()
    description = _truncate(_redact(meta.get("description")), 200)
    tags = _normalise_tags(meta.get("tags"), max_items=10, max_len=120)
    channel = _redact(meta.get("channel"))

    out = {
        "Title": title,
        "Description": description,
        "Tags": tags,
        "Channel": channel,
    }
    # Optionally drop empty Channel
    if not out["Channel"]:
        out["Channel"] = ""
    return out

def get_fresh_metadata_triaged() -> List[Dict[str, Any]]:
    """
    Fetch uncategorised fresh metadata and apply triage.
    Returns list of dicts:
      {
        "videoId": str,
        "payload": { "Title": str, "Description": str, "Tags": str, "Channel": str },
        "constants": { "MODEL_ID": str, "PROMPT_VERSION": str, "CATEGORIES_VERSION": str }
      }
    """
    rows = get_fresh_metadata_unprocessed()
    results: List[Dict[str, Any]] = []
    for r in rows:
        meta = r.get("metadata") or {}
        video_id = r.get("video_id") or meta.get("videoId") or ""
        payload = triage_record(meta)
        results.append({
            "videoId": video_id,
            "payload": payload,
            "constants": {
                "MODEL_ID": MODEL_ID,
                "PROMPT_VERSION": PROMPT_VERSION,
                "CATEGORIES_VERSION": CATEGORIES_VERSION,
            },
        })
    return results
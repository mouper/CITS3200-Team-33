"""
load_into_cache.py — Load metadata JSON into metadata_cache only.

Steps when executed:
1) Load JSON file (default: data/test_metadata.json)
2) Insert all records into metadata cache DB
3) Print a brief summary of rows inserted

Usage:
  python3 scripts/load_into_cache.py [--file data/test_metadata.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List
import time


def _ensure_paths() -> None:
    """Ensure local package imports work when run from repo root or scripts/ dir."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    llm_src = os.path.join(repo_root, "packages", "llm_client", "src")
    if llm_src not in sys.path:
        sys.path.insert(0, llm_src)


def _load_json(path: str) -> List[Dict[str, Any]]:
    """Load metadata supporting several shapes:
    - JSON array: [ {...}, {...} ]
    - Object with list under common keys: {"items":[...]}, {"videos":[...]}, {"data":[...]}, {"results":[...]}
    - Object map: {"VIDEO_ID": {...}, ...}
    - Newline-delimited JSON (one object per line)
    """
    # First try standard JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Common container keys
        for key in ("items", "videos", "data", "results"):
            val = data.get(key)
            if isinstance(val, list):
                return val
        # Map of id -> object
        if data and all(isinstance(v, dict) for v in data.values()):
            return list(data.values())

    # Fallback: treat as JSON Lines
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                items.append(obj)
    if items:
        return items
    raise RuntimeError("Unsupported JSON format: expected array, container with items list, id->object map, or JSON Lines")


def _insert_into_cache(items: List[Dict[str, Any]], slow: bool = False) -> int:
    from databases import database as db  # lazy import after sys.path setup
    inserted = 0
    total = len(items)
    for idx, item in enumerate(items, start=1):
        # Robustly extract YouTube video ID from common shapes
        vid = item.get("videoId")
        if not vid:
            raw_id = item.get("id")
            if isinstance(raw_id, str):
                vid = raw_id
            elif isinstance(raw_id, dict):
                vid = raw_id.get("videoId") or raw_id.get("video_id")
        if not vid:
            vid = item.get("video_id")
        if not vid:
            continue
        db.insert_metadata(str(vid), json.dumps(item, ensure_ascii=False))
        inserted += 1
        if slow:
            # Target ~10 inserts per second
            time.sleep(0.1)
        if idx % 100 == 0:
            print(f"Inserted {idx}/{total} into metadata_cache...")
    return inserted


def main() -> None:
    _ensure_paths()

    parser = argparse.ArgumentParser(description="Load JSON into metadata_cache only")
    parser.add_argument("--file", default="data/test_metadata.json", help="Path to JSON file")
    parser.add_argument("--slow", action="store_true", help="Throttle inserts to 10 videos/second")
    args = parser.parse_args()

    print(f"Loading JSON: {args.file}")
    data = _load_json(args.file)
    print(f"Loaded {len(data)} items")

    print("Inserting into metadata_cache...")
    # Signal to background classifier to pause polling/deletions
    try:
        from databases import database as db
        db.set_ingest_active(True)
    except Exception:
        pass
    try:
        inserted = _insert_into_cache(data, slow=args.slow)
    finally:
        try:
            db.set_ingest_active(False)
        except Exception:
            pass
    print(f"Inserted into metadata_cache: {inserted}")


if __name__ == "__main__":
    main()



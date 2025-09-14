"""
youtube_metadata.py — Fetch YouTube video metadata by ID (or full URL) and store it.

- Accepts one or many IDs/URLs (comma-separated or space-separated)
- Extracts IDs from common YouTube URL formats
- Fetches metadata via YouTube Data API v3
- Stores each result in SQLite via the `databases.database` facade (JSON-safe)
- Optional CSV/JSON output for convenience

Usage examples (from project root):
  $env:YT_API_KEY="YOUR_YT_API_KEY"
  python -m databases.youtube_metadata dQw4w9WgXcQ
  python -m databases.youtube_metadata "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python -m databases.youtube_metadata dQw4w9WgXcQ,9bZkp7q19f0 --csv out.csv --json out.json
"""

import os
import re
import sys
import csv
import json
import argparse
from typing import Iterable, List, Dict, Any, Set, Optional

# Use the package facade so DB writes are JSON-safe and schema-aware
from . import database

import googleapiclient.discovery
import googleapiclient.errors


# ---------------------------
# Helpers (URL → ID, dedupe)
# ---------------------------

_YT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# Covers: watch?v=, youtu.be/, shorts/, embed/
_ID_FROM_URL_PATTERNS = [
    re.compile(r"[?&]v=([a-zA-Z0-9_-]{11})"),  # ...watch?v=VIDEOID
    re.compile(r"youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"/shorts/([a-zA-Z0-9_-]{11})"),
    re.compile(r"/embed/([a-zA-Z0-9_-]{11})"),
]

def extract_video_id(token: str) -> Optional[str]:
    token = token.strip()
    if not token:
        return None
    if _YT_ID_RE.fullmatch(token):
        return token
    for pat in _ID_FROM_URL_PATTERNS:
        m = pat.search(token)
        if m:
            return m.group(1)
    return None

def normalize_ids(inputs: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for raw in inputs:
        for piece in str(raw).split(","):
            vid = extract_video_id(piece)
            if vid and vid not in seen:
                seen.add(vid)
                out.append(vid)
    return out


# ---------------------------
# YouTube API
# ---------------------------

def build_client(api_key: str):
    return googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

def get_category_map(youtube, region_code: str = "US") -> Dict[str, str]:
    try:
        req = youtube.videoCategories().list(part="snippet", regionCode=region_code)
        resp = req.execute()
        mapping: Dict[str, str] = {}
        for item in resp.get("items", []):
            cid = item.get("id")
            title = (item.get("snippet") or {}).get("title")
            if cid and title:
                mapping[cid] = title
        return mapping
    except googleapiclient.errors.HttpError:
        return {}

def fetch_youtube_videos_by_id(
    api_key: str,
    video_ids: List[str],
    region_code: str = "US"
) -> List[Dict[str, Any]]:
    """Fetch videos (batched by 50), store each row via DB facade, and return the rows."""
    if not video_ids:
        return []

    youtube = build_client(api_key)
    category_map = get_category_map(youtube, region_code=region_code)

    results: List[Dict[str, Any]] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        req = youtube.videos().list(
            part="id,snippet,contentDetails,statistics",
            id=",".join(chunk)
        )
        resp = req.execute()
        for item in resp.get("items", []):
            sn = item.get("snippet", {}) or {}
            st = item.get("statistics", {}) or {}
            cd = item.get("contentDetails", {}) or {}

            cat_id = sn.get("categoryId")
            cat_name = category_map.get(cat_id, None) if cat_id else None

            row = {
                "video_id": item.get("id"),
                "title": sn.get("title"),
                "description": sn.get("description"),
                "channel_title": sn.get("channelTitle"),
                "channel_id": sn.get("channelId"),
                "publish_time": sn.get("publishedAt"),
                "category_id": cat_id,
                "category_name": cat_name,
                "duration": cd.get("duration"),
                "view_count": st.get("viewCount"),
                "like_count": st.get("likeCount"),
                "comment_count": st.get("commentCount"),
                "tags": sn.get("tags", []),
            }

            # Store into metadata cache (DB layer will JSON-encode dicts safely)
            database.insert_metadata(row["video_id"], row)
            results.append(row)

    return results


# ---------------------------
# CLI
# ---------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch YouTube metadata by video ID or URL (with Category + Tags)."
    )
    p.add_argument("ids", nargs="+", help="One or more video IDs or URLs (comma-separated allowed).")
    p.add_argument("--csv", metavar="PATH", help="Append output to CSV at PATH.")
    p.add_argument("--json", metavar="PATH", help="Append output to JSON at PATH.")
    p.add_argument("--api-key", dest="api_key", default=None,
                   help="YouTube API key (overrides env var YT_API_KEY).")
    p.add_argument("--region", dest="region", default="US",
                   help="Region code for category names (default: US).")
    return p.parse_args()

def get_api_key(cli_key: Optional[str]) -> str:
    key = cli_key or os.getenv("YT_API_KEY")
    if not key:
        sys.exit("Error: provide an API key via --api-key or env var YT_API_KEY.")
    return key


# ---------------------------
# Output helpers
# ---------------------------

def print_results(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No videos found.")
        return
    for v in rows:
        print(f"Title: {v.get('title')}")
        print(f"Video ID: {v.get('video_id')}")
        print(f"Channel: {v.get('channel_title')} ({v.get('channel_id')})")
        print(f"Published: {v.get('publish_time')}")
        cat_id = v.get("category_id")
        cat_name = v.get("category_name")
        if cat_id and cat_name:
            print(f"Category: {cat_name} (ID {cat_id})")
        elif cat_id:
            print(f"Category ID: {cat_id}")
        else:
            print("Category: N/A")
        print(f"Duration: {v.get('duration')}")
        print(f"Views: {v.get('view_count')}  Likes: {v.get('like_count')}  Comments: {v.get('comment_count')}")
        tags = v.get("tags") or []
        if isinstance(tags, list) and tags:
            print(f"Tags: {', '.join(tags)}")
        else:
            print("Tags: N/A")
        print(f"Description: {v.get('description')}\n")

def save_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print(f"No data to save to {path}.")
        return
    fieldnames = [
        "video_id","title","description","channel_title","channel_id",
        "publish_time","category_id","category_name","duration",
        "view_count","like_count","comment_count","tags",
    ]
    file_exists = os.path.isfile(path)

    csv_rows: List[Dict[str, Any]] = []
    for r in rows:
        r_copy = dict(r)
        tags_val = r_copy.get("tags", [])
        if isinstance(tags_val, list):
            r_copy["tags"] = ", ".join(tags_val)
        csv_rows.append(r_copy)

    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerows(csv_rows)

    print(f"Appended {len(rows)} rows to {path}")

def save_json(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print(f"No data to save to {path}.")
        return

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    else:
        existing = []

    if not isinstance(existing, list):
        existing = [existing]

    existing.extend(rows)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Appended {len(rows)} entries to {path}")


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    args = parse_args()
    api_key = get_api_key(args.api_key)

    video_ids = normalize_ids(args.ids)
    if not video_ids:
        sys.exit("Error: no valid YouTube video IDs detected in input.")

    try:
        rows = fetch_youtube_videos_by_id(api_key, video_ids, region_code=args.region)
    except googleapiclient.errors.HttpError as e:
        print(f"API error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    print_results(rows)
    if args.csv:
        save_csv(args.csv, rows)
    if args.json:
        save_json(args.json, rows)

if __name__ == "__main__":
    main()
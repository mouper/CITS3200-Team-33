"""
Seed sample data into watched.db and user_settings.db.

Rules:
- watched.db entries are only created for video_ids already present in categorised.db
- user_settings.db is populated with a few sample categories and settings

Usage:
  python scripts/seed_sample_data.py

Optional environment variables:
  SEED_WATCHED_COUNT   - how many watched rows to create (default: 10)

This script uses the shared database helpers under the `databases` package.
"""

from __future__ import annotations

import os
import random
import time
from typing import List, Tuple

from pathlib import Path
import sys
"""Ensure repo root is on sys.path so `databases` package can be imported."""
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from databases import db_utils
from databases import config as db_config
from databases import watched_db
from databases import user_settings_db


def get_all_categorised_video_ids() -> List[Tuple[str, str]]:
    """Return list of (video_id, category) from categorised.db."""
    conn = db_utils.connect_db(db_config.CATEGORIES_DB_PATH)
    try:
        rows = db_utils.fetch_all(conn, "SELECT video_id, category FROM categorised")
        return [(row["video_id"], row["category"]) for row in rows]
    finally:
        conn.close()


def seed_watched(max_rows: int) -> int:
    """Insert up to max_rows watched events for existing categorised video_ids."""
    # Ensure tables exist
    watched_db.init_db()
    # Clear existing rows to ensure a fresh seed each run
    try:
        conn = db_utils.connect_db(db_config.WATCHED_DB_PATH)
        db_utils.execute_query(conn, "DELETE FROM watched")
        conn.close()
    except Exception as exc:
        print(f"Warning: could not clear watched table: {exc}")

    pairs = get_all_categorised_video_ids()
    if not pairs:
        print("No rows in categorised.db; skipping watched seeding.")
        return 0

    random.shuffle(pairs)
    selected = pairs[: max_rows]

    # Create watched entries with random-ish durations
    inserted = 0
    now = int(time.time())
    for video_id, _category in selected:
        # duration between 30s and 1800s
        duration = random.randint(30, 1800)
        start = now - random.randint(0, 7 * 24 * 3600)  # sometime within last 7 days
        # watched_db.log_watch sets end_time = current_timestamp(), so we simulate by
        # temporarily adjusting 'now' using start_time only. That's acceptable for sample data.
        try:
            watched_db.log_watch(video_id, start_time=start)
            inserted += 1
        except Exception as exc:
            # If a PRIMARY KEY conflict occurs (duplicate video_id), skip
            print(f"Skip {video_id}: {exc}")
            continue
    return inserted


def seed_user_settings() -> int:
    """Insert settings for ALL categories in categories.v1.json.

    Falls back to categories observed in categorised.db if the JSON is missing.
    """
    user_settings_db.init_db()

    # Try to load labels from packages/llm_client/models/categories.v1.json
    categories: list[str] = []
    try:
        repo_root = Path(__file__).resolve().parents[1]
        cat_path = repo_root / "packages" / "llm_client" / "models" / "categories.v1.json"
        import json
        with open(cat_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            labels = data.get("allowedLabels", [])
            categories = [str(lbl) for lbl in labels]
    except Exception:
        categories = []

    # Fallback to categories present in categorised.db if JSON read failed
    if not categories:
        pairs = get_all_categorised_video_ids()
        categories = sorted({cat for (_vid, cat) in pairs if cat})

    # Randomly pick a number of categories to mark as not active
    count_inactive = random.randint(0, len(categories)) if categories else 0
    inactive = set(random.sample(categories, count_inactive)) if count_inactive else set()

    inserted = 0
    for i, cat in enumerate(categories):
        strength = "Moderate"
        is_active = cat not in inactive
        try:
            user_settings_db.set_settings(cat, strength, is_active)
            inserted += 1
        except Exception as exc:
            print(f"Skip settings for {cat}: {exc}")
            continue
    return inserted


def main() -> None:
    # How many watched rows to insert at most
    max_rows = int(os.getenv("SEED_WATCHED_COUNT", "10"))

    # Seed watched
    inserted_watched = seed_watched(max_rows)
    print(f"Inserted {inserted_watched} watched rows (sourced from categorised.db)")

    # Seed user settings
    inserted_settings = seed_user_settings()
    print(f"Inserted/updated {inserted_settings} user settings rows")


if __name__ == "__main__":
    main()



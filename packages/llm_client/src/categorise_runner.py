"""
categorise_runner.py — End-to-end loop for:
  - fetching triaged fresh metadata
  - building prompts
  - calling the model
  - parsing strict JSON
  - writing results to categorised_db
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .metadata_triage import (
    get_fresh_metadata_unprocessed,
    ALLOWED_LABELS,
)
from .prompt_builder import assemble_prompt
from .model_client import OpenAIClient, call_classifier

from databases import database as db  # type: ignore
from requests.exceptions import RequestException  # type: ignore

def run_categoriser(limit=100):
    fresh_payloads = metadata_triage.get_fresh_metadata_unprocessed(limit)
    # Best-effort: load environment variables from a .env file if present
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore

        # 1) Load nearest .env (repo root or cwd)
        load_dotenv(find_dotenv(), override=False)

        # 2) Also try server/.env relative to repo root
        repo_root = Path(__file__).resolve().parents[2]
        server_env = repo_root / "server" / ".env"
        if server_env.exists():
            load_dotenv(server_env.as_posix(), override=False)
    except Exception:
        # If python-dotenv is not installed, skip silently
        pass


    class ParseError(Exception):
        pass


    def parse_and_validate(content: str, allowed_labels: List[str]) -> str:
        try:
            data = json.loads(content)
        except Exception as e:
            raise ParseError(f"Invalid JSON: {e}")
        if not isinstance(data, dict) or "category" not in data:
            raise ParseError("JSON must contain 'category' field")
        category = data["category"]
        if category not in allowed_labels:
            raise ParseError("'category' not in allowed labels")
        return category


    def run_once(model_id: str, pretriaged_items: List[Dict[str, Any]] | None = None) -> int:
        # Allow caller to pass pre-triaged items so we don't re-triage here.
        items = pretriaged_items if pretriaged_items is not None else get_fresh_metadata_unprocessed()

        # Deduplicate by videoId while preserving order
        seen: set = set()
        unique_items: List[Dict[str, Any]] = []
        for it in items:
            vid = it.get("videoId")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            unique_items.append(it)

        # Remove ALL triaged items from cache immediately so subsequent loops don't re-triage them
        try:
            video_ids_to_delete = [it.get("videoId") for it in unique_items if it.get("videoId")]
            if video_ids_to_delete:
                db.delete_metadata_by_ids(video_ids_to_delete)
                print(f"Triage: removed {len(video_ids_to_delete)} rows from cache")
        except Exception:
            # Best-effort deletion; continue even if cleanup fails
            pass

        # Now process everything with concurrency up to 5
        print(f"Categoriser: processing {len(unique_items)} item(s) with concurrency=5")

        def classify_one(item: Dict[str, Any]) -> Tuple[str, bool]:
            video_id = item["videoId"]
            payload = item["payload"]
            system, labels_block, user_payload = assemble_prompt(payload, ALLOWED_LABELS)
            # Use a dedicated client per thread to avoid shared state issues
            local_client = OpenAIClient()
            for attempt in range(2):
                try:
                    content = call_classifier(local_client, model_id, system, labels_block, user_payload)
                    category = parse_and_validate(content, ALLOWED_LABELS)
                    db.insert_categorised(video_id, category)
                    return (video_id, True)
                except (ParseError, RequestException, RuntimeError):
                    if attempt == 0:
                        time.sleep(0.5)
                        continue
                    return (video_id, False)

        written = 0
        if not unique_items:
            print("Categoriser: no items to process")
            return 0

        with ThreadPoolExecutor(max_workers=min(5, len(unique_items))) as executor:
            future_to_vid = {executor.submit(classify_one, it): it["videoId"] for it in unique_items}
            for future in as_completed(future_to_vid):
                vid, ok = future.result()
                if ok:
                    written += 1

        print(f"Categoriser done. Written {written}/{len(unique_items)}")
        return written



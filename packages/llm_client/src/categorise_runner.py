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
from typing import Any, Dict, List

from .metadata_triage import (
    get_fresh_metadata_triaged,
    ALLOWED_LABELS,
)
from .prompt_builder import assemble_prompt
from .model_client import OpenAIClient, call_classifier

from databases import database as db  # type: ignore
from requests.exceptions import RequestException  # type: ignore

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


def run_once(model_id: str) -> int:
    client = OpenAIClient()
    items = get_fresh_metadata_triaged()
    print(f"Categoriser: {len(items)} items to process")
    written = 0
    for i, item in enumerate(items, start=1):
        video_id = item["videoId"]
        payload = item["payload"]
        system, labels_block, user_payload = assemble_prompt(payload, ALLOWED_LABELS)

        # One attempt + one retry on parse failure only
        for attempt in range(2):
            try:
                content = call_classifier(client, model_id, system, labels_block, user_payload)
                category = parse_and_validate(content, ALLOWED_LABELS)
                # Persist
                db.insert_categorised(video_id, category)
                written += 1
                break
            except (ParseError, RequestException, RuntimeError) as e:
                # Treat parser errors and transient network/runtime issues as retryable once
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                else:
                    # Fail fast after second attempt
                    break
        if i % 5 == 0:
            print(f"Progress: processed {i}/{len(items)}, written {written}")
    print(f"Categoriser done. Total written: {written}")
    return written



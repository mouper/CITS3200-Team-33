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
import time
from typing import Any, Dict, List

from .metadata_triage import (
    get_fresh_metadata_triaged,
    ALLOWED_LABELS,
)
from .prompt_builder import assemble_prompt
from .model_client import OpenAIClient, call_classifier

from databases import database as db  # type: ignore


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
    written = 0
    for item in items:
        video_id = item["videoId"]
        payload = item["payload"]
        system, labels_block, user_payload = assemble_prompt(payload, ALLOWED_LABELS)

        # One attempt + one retry on parse failure only
        for attempt in range(2):
            content = call_classifier(client, model_id, system, labels_block, user_payload)
            try:
                category = parse_and_validate(content, ALLOWED_LABELS)
                # Persist
                meta_json = json.dumps(payload, ensure_ascii=False)
                db.insert_categorised(video_id, category, meta_json)
                written += 1
                break
            except ParseError:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                else:
                    # Fail fast after second attempt
                    break
    return written



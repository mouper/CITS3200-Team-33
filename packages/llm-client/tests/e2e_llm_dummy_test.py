#!/usr/bin/env python3
"""
e2e_llm_dummy_test.py — Simple end-to-end demo with dummy data and stubbed LLM.

Prints (no DB writes, no network calls):
- Raw input metadata
- Triaged payload
- Built prompt (system, labels, user)
- Stubbed LLM response
- JSON object representing what would be written to the DB
"""

import json
import os
import sys
from pathlib import Path

# Add llm-client src to path
THIS_DIR = Path(__file__).parent
SRC_DIR = THIS_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

# Import modules
from metadata_triage import triage_record, ALLOWED_LABELS
from prompt_builder import assemble_prompt
from model_client import OpenAIClient, call_classifier
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore
    find_dotenv = None  # type: ignore


def main():
    # Load .env if available
    if load_dotenv is not None:
        try:
            load_dotenv(find_dotenv() if find_dotenv is not None else None)
        except Exception:
            pass

    # Load dummy input and insert to metadata cache
    data_file = Path(__file__).parents[3] / "data" / "e2e_dummy_video.json"
    with open(data_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    video_id = meta["videoId"]

    print("=== Raw Input Metadata ===")
    print(json.dumps(meta, ensure_ascii=True, indent=2))

    # Triage
    payload = triage_record(meta)
    print("\n=== Triaged Payload ===")
    print(json.dumps(payload, ensure_ascii=True, indent=2))

    # Build prompt
    system, labels_block, user_msg = assemble_prompt(payload, ALLOWED_LABELS)
    print("\n=== Prompt: System ===")
    print(system)
    print("\n=== Prompt: Allowed Labels ===")
    print(labels_block)
    print("\n=== Prompt: User Payload ===")
    print(user_msg)

    # Real LLM call
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env or the environment.")

    client = OpenAIClient()
    model_id = os.getenv("OPENAI_MODEL_ID", "gpt-5-nano")
    response = call_classifier(client, model_id, system, labels_block, user_msg)
    print("\n=== LLM Response ===")
    print(response)

    # Show what would be written to the DB
    category = json.loads(response)["category"]
    db_row = {
        "video_id": video_id,
        "category": category,
        "metadata": json.dumps(payload, ensure_ascii=True),
    }
    print("\n=== Would Write to DB ===")
    print(json.dumps(db_row, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)



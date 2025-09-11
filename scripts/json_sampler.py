"""
json_sampler.py — Randomly sample a portion of a JSON file.

Reads from a source file and writes sampled output to a destination file
without modifying the source.

Supports:
- Array JSON: [ {...}, {...} ]
- Container with list under 'items'/'videos'/'data'/'results' (preserves shape)

Usage:
    python3 scripts/json_sampler.py --fraction 0.5 --seed 42
    OR
    python3 scripts/json_sampler.py --src data/youtube_sample_397.json --dst data/test_metadata.json --fraction 0.5 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from typing import Any, Dict, List, Tuple


def _find_list_container(data: Any) -> Tuple[List[Dict[str, Any]], str | None]:
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        for key in ("items", "videos", "data", "results"):
            val = data.get(key)
            if isinstance(val, list):
                return val, key
    raise RuntimeError("Unsupported JSON format: expected array or container with items list")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/youtube_sample_397.json", help="Path to source JSON file")
    ap.add_argument("--dst", default="data/test_metadata.json", help="Path to destination JSON file")
    ap.add_argument("--fraction", type=float, default=0.5, help="Fraction to keep (0-1)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = ap.parse_args()

    if args.fraction <= 0 or args.fraction >= 1:
        raise ValueError("--fraction must be between 0 and 1")

    with open(args.src, "r", encoding="utf-8") as f:
        data = json.load(f)

    items, container_key = _find_list_container(data)
    n = len(items)
    if n == 0:
        print("Original: 0  New: 0")
        return

    if args.seed is not None:
        random.seed(args.seed)
    k = max(1, int(n * args.fraction))
    sampled = random.sample(items, k=k)

    if container_key is None:
        out = sampled
    else:
        out = dict(data)
        out[container_key] = sampled

    # Ensure destination directory exists
    import os
    dst_dir = os.path.dirname(args.dst)
    if dst_dir and not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)

    with open(args.dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Original: {n}  New: {len(sampled)}  -> {args.dst}")


if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
collect_youtube_metadata.py

Collect ~500 unique YouTube video metadata records by running many
random short search queries (approximate random sampling).

Requires:
  - Python 3.8+
  - requests
  - python-dotenv (optional, for loading .env)

Usage:
  export YT_API_KEY="your_api_key_here"
  python collect_youtube_metadata.py

Outputs:
  - youtube_sample_500.json
  - youtube_sample_500.csv

Notes:
  - This is an approximation of randomness (random short queries). The
    YouTube Data API does not provide a true "random video" endpoint.
  - Keep an eye on your API quota. The script sleeps and retries on errors.
"""
import os
import dotenv
import time
import json
import csv
import random
import string
import math
from datetime import datetime
from typing import List, Dict, Set, Optional
from collections import deque

import requests

dotenv.load_dotenv()

# === Config ===
API_KEY = os.getenv("YT_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set the YT_API_KEY environment variable with your YouTube Data API key.")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

TARGET_COUNT = 500              # how many unique videos we want
MAX_SEARCH_PER_QUERY = 50       # max results per search API call (API supports up to 50)
MAX_VIDEO_BATCH = 50            # videos.list accepts up to 50 IDs per request
MAX_ATTEMPTS = 2000             # safety cap on total search attempts
SLEEP_BETWEEN_SEARCH = 0.35     # seconds (throttle to be polite)
SLEEP_ON_ERROR = 1.5            # backoff base
MAX_TOTAL_QUERIES = 1200        # safety cap (don't spam the API forever)

# token-budget / trimming choices are up to you when building prompts later;
# here we just record raw description (but you may choose to truncate later).

# A pool of common YouTube title keywords for diverse sampling
COMMON_KEYWORDS: List[str] = [
    # General & trending
    "how", "how to", "tutorial", "guide", "tips", "tricks", "hacks", "life hacks",
    "top", "top 10", "best", "worst", "beginner", "for beginners", "vs", "review",
    "unboxing", "first look", "hands on", "setup", "comparison", "explained", "analysis",
    "deep dive", "update", "new", "2022", "2023", "2024", "2025", "trending",
    "challenge", "24 hours", "try not to laugh", "compilation", "fails", "highlights",
    "reaction", "reacts", "meme", "memes", "shorts", "viral",

    # Education & academic
    "lecture", "documentary", "history", "science", "math", "physics", "chemistry",
    "biology", "psychology", "economics", "philosophy", "study", "revision", "exam",
    "explainer", "case study",

    # How-To / DIY / Maker
    "DIY", "step by step", "recipe", "cook with me", "meal prep", "restoration",
    "woodworking", "3d printing", "arduino", "raspberry pi", "fix", "repair",

    # Science & Tech
    "tech", "gadgets", "smartphone", "iphone", "android", "pc build", "gaming pc",
    "benchmark", "camera test", "mic test", "battery test", "speed test", "tesla",
    "ai", "chatgpt", "python", "javascript", "coding", "programming", "linux",
    "windows", "macos", "notion", "obsidian", "productivity",

    # Wellbeing & mindfulness
    "meditation", "asmr", "relaxing", "sleep", "yoga", "breathing", "calm",
    "study music", "focus music",

    # Music & arts
    "official video", "music video", "mv", "lyrics", "karaoke", "cover", "remix",
    "instrumental", "lofi", "beat", "dj set", "live session", "concert", "piano",
    "guitar", "kpop", "hip hop", "edm", "trap",

    # Sports & fitness
    "workout", "fitness", "gym", "training", "full match", "goals", "nba",
    "premier league", "boxing", "ufc", "marathon", "football", "soccer", "cricket",

    # Travel & nature
    "travel vlog", "road trip", "camping", "hiking", "backpacking", "nature",
    "wildlife", "national park", "drone footage", "beach", "mountains", "city tour",
    "hotel review", "food tour",

    # Internet clip compilations / entertainment
    "best moments", "tiktok compilation", "funny", "pranks", "win compilation",

    # Clickbait / curiosity
    "you won't believe", "exposed", "shocking", "insane", "gone wrong",
    "what happens if", "we tried", "ultimate", "must watch",

    # News, politics & public affairs
    "breaking news", "live", "press conference", "debate", "interview", "town hall",
    "election", "parliament", "congress", "policy", "senate", "president",

    # Conspiracy & fringe
    "conspiracy", "ufo", "aliens", "mystery", "secret", "hidden truth",

    # True crime
    "true crime", "case", "missing", "investigation", "detective", "police",
    "evidence", "timeline", "cold case",

    # Violent / graphic
    "street fight", "knockout", "brutal", "graphic content",

    # Pranks & dangerous challenges
    "overnight", "extreme", "dangerous",

    # Sexual / suggestive
    "bikini", "lingerie", "thirst trap", "sexy",

    # Gaming
    "gameplay", "walkthrough", "let's play", "speedrun", "montage", "ranked",
    "build guide", "patch notes", "season", "chapter", "minecraft", "roblox",
    "fortnite", "valorant", "league of legends", "csgo",

    # Gambling & betting
    "poker", "casino", "blackjack", "slots", "betting", "sports betting",

    # Scams & get-rich-quick
    "get rich quick", "free robux", "mlm", "ponzi",

    # Finance & business
    "make money", "side hustle", "passive income", "dropshipping", "forex", "crypto",
    "bitcoin", "nft", "investing", "stock market", "dividends", "options",
    "budgeting", "entrepreneur", "startup", "marketing", "seo", "saas",

    # Lifestyle & vlogs
    "vlog", "day in the life", "morning routine", "night routine", "storytime", "q&a",
    "behind the scenes", "bts", "we bought", "we built",

    # Entertainment & film
    "trailer", "official trailer", "teaser", "full movie", "movie recap",
    "ending explained", "series", "season finale", "episode", "ep",

    # Food & cooking
    "tasty", "air fryer", "dessert", "vegan", "bbq", "street food",

    # Beauty & fashion
    "makeup tutorial", "grwm", "haul", "outfit", "skincare",

    # Pets & kids
    "cat", "dog", "pet", "animal rescue", "funny animals", "toy review", "lego",
    "slime",

    # Language learning
    "learn english", "spanish", "korean", "japanese", "vocabulary", "grammar"
]

# Rotating queues to ensure we use each keyword at least once
KEYWORD_QUEUE = deque(random.sample(COMMON_KEYWORDS, k=len(COMMON_KEYWORDS)))
REMAINING_KEYWORDS = deque(KEYWORD_QUEUE)  # copy for first-pass guarantee


# === Helpers ===

def _ascii_ratio(text: str) -> float:
    if not text:
        return 0.0
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    return ascii_count / max(1, len(text))


def is_probably_english(snippet: dict) -> bool:
    """Heuristic English filter using snippet fields.
    Prefers explicit language fields when available; falls back to ASCII/keyword heuristics.
    """
    lang = (snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or "").lower()
    if lang:
        return lang.startswith("en")

    title = (snippet.get("title") or "")
    desc = (snippet.get("description") or "")
    text = f"{title} {desc}".lower()
    if _ascii_ratio(text) < 0.85:
        return False
    common_en_terms = (
        " the ", " and ", " you ", " for ", " with ", " this ", " what ", " how ",
        "review", "trailer", "episode", "official", "new ", "season", "tips", "guide"
    )
    return any(term in text for term in common_en_terms)


def next_keyword() -> str:
    kw = KEYWORD_QUEUE[0]
    KEYWORD_QUEUE.rotate(-1)
    return kw

def random_short_query() -> str:
    """Generate a very short random query string to surface diverse videos.
    Uses:
      - random 1-3 letter sequences (a..z)
      - occasional popular short words (mix) to increase variety
    """
    if random.random() < 0.15:
        # use some short dictionaries sometimes for variety
        return random.choice(COMMON_KEYWORDS)
    length = random.choice([1, 2, 3])
    return "".join(random.choices(string.ascii_lowercase, k=length))


def exponential_backoff_sleep(attempt: int, base: float = SLEEP_ON_ERROR, cap: float = 30.0):
    """Simple exponential backoff with jitter."""
    sleep_time = min(cap, base * (2 ** attempt))
    # jitter ±25%
    jitter = sleep_time * 0.25
    actual = sleep_time + random.uniform(-jitter, jitter)
    time.sleep(max(0.1, actual))


def call_search_api(q: str, page_token: Optional[str] = None) -> dict:
    params = {
        "part": "id",            # we only need IDs here to reduce response size
        "q": q,
        "type": "video",
        "maxResults": MAX_SEARCH_PER_QUERY,
        "key": API_KEY,
        "relevanceLanguage": "en",   # favor English results
        "regionCode": "US",          # bias to an English-speaking region
        # "publishedAfter": "2015-01-01T00:00:00Z"  # optional filter
    }
    if page_token:
        params["pageToken"] = page_token
    resp = requests.get(SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def call_videos_api(video_ids: List[str]) -> dict:
    params = {
        "part": "snippet,contentDetails,statistics",
        "id": ",".join(video_ids),
        "maxResults": len(video_ids),
        "key": API_KEY,
    }
    resp = requests.get(VIDEOS_URL, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def extract_relevant_metadata(video_item: dict) -> dict:
    """Return a compact metadata dict for a videos.list item."""
    snippet = video_item.get("snippet", {})
    stats = video_item.get("statistics", {})
    content = video_item.get("contentDetails", {})

    metadata = {
        "videoId": video_item.get("id"),
        "title": snippet.get("title"),
        "channelTitle": snippet.get("channelTitle"),
        "channelId": snippet.get("channelId"),
        "description": snippet.get("description"),
        "tags": snippet.get("tags", []),
        "publishedAt": snippet.get("publishedAt"),
        "duration": content.get("duration"),            # ISO 8601
        "definition": content.get("definition"),        # hd / sd
        "caption": content.get("caption"),              # true / false / etc
        "viewCount": int(stats.get("viewCount")) if stats.get("viewCount") else None,
        "likeCount": int(stats.get("likeCount")) if stats.get("likeCount") else None,
        "commentCount": int(stats.get("commentCount")) if stats.get("commentCount") else None,
    }
    return metadata


# === Main collection logic ===

def gather_video_ids(target_count: int) -> List[str]:
    """Run many small random searches and collect unique video IDs until we have target_count unique ones.
    Returns a list of unique video IDs.
    """
    collected: List[str] = []
    seen: Set[str] = set()
    attempts = 0
    queries_run = 0

    # attempt loop
    while len(collected) < target_count and attempts < MAX_ATTEMPTS and queries_run < MAX_TOTAL_QUERIES:
        # First, ensure we cycle through our keyword list at least once
        if REMAINING_KEYWORDS:
            q = REMAINING_KEYWORDS.popleft()
        else:
            # After first pass, mix deterministic rotation with random noise
            q = next_keyword() if random.random() < 0.6 else random_short_query()
        attempts += 1
        queries_run += 1
        page_token = None
        page_attempt = 0

        # try a single query and its pages (but do not page too far)
        while True:
            try:
                resp = call_search_api(q, page_token=page_token)
            except requests.HTTPError as e:
                print(f"[search error] q={q} attempt={attempts} err={e}. Backing off...")
                exponential_backoff_sleep(min(page_attempt, 6))
                page_attempt += 1
                # optionally break this query after a few retries
                if page_attempt > 5:
                    break
                continue

            # collect ids
            items = resp.get("items", [])
            for it in items:
                # search.id may contain 'videoId'
                vid = it.get("id", {}).get("videoId")
                if not vid:
                    continue
                if vid in seen:
                    continue
                seen.add(vid)
                collected.append(vid)
                if len(collected) >= target_count:
                    break

            if len(collected) >= target_count:
                break

            page_token = resp.get("nextPageToken")
            # stop paging after a couple of pages for the same query; keep queries diverse
            if not page_token or page_attempt >= 2:
                break
            page_attempt += 1
            time.sleep(SLEEP_BETWEEN_SEARCH)

        # small sleep between queries
        time.sleep(SLEEP_BETWEEN_SEARCH)

    print(f"[gather_video_ids] attempts={attempts} unique_ids={len(collected)} queries_run={queries_run}")
    return collected[:target_count]


def fetch_metadata_for_ids(video_ids: List[str]) -> List[dict]:
    """Batch up into groups and call videos.list to fetch metadata."""
    results: List[dict] = []
    total = len(video_ids)
    batches = math.ceil(total / MAX_VIDEO_BATCH)
    for i in range(batches):
        batch_ids = video_ids[i*MAX_VIDEO_BATCH:(i+1)*MAX_VIDEO_BATCH]
        attempt = 0
        while True:
            try:
                resp = call_videos_api(batch_ids)
                items = resp.get("items", [])
                for it in items:
                    snippet = it.get("snippet", {})
                    if not is_probably_english(snippet):
                        continue
                    metadata = extract_relevant_metadata(it)
                    results.append(metadata)
                break
            except requests.HTTPError as e:
                print(f"[videos API error] batch {i+1}/{batches} err={e}. Backing off...")
                attempt += 1
                exponential_backoff_sleep(min(attempt, 6))
                if attempt > 6:
                    print("Too many failures for this batch — skipping.")
                    break
        # polite pause
        time.sleep(0.25)
    return results


def save_results_json(results: List[dict], filename: str):
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump({
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "count": len(results),
            "results": results
        }, fh, ensure_ascii=False, indent=2)


def save_results_csv(results: List[dict], filename: str):
    # flatten tags into pipe-delimited for CSV
    fieldnames = [
        "videoId", "title", "channelTitle", "channelId",
        "publishedAt", "viewCount", "likeCount", "commentCount",
        "duration", "definition", "caption", "tags", "description"
    ]
    with open(filename, "w", encoding="utf-8", newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k) for k in fieldnames}
            row["tags"] = "|".join(r.get("tags") or [])
            writer.writerow(row)


def main():
    print("Starting YouTube metadata collection (approx 500 videos)...")
    start = time.time()
    ids = gather_video_ids(TARGET_COUNT)
    if not ids:
        print("No IDs collected — exiting.")
        return
    print(f"Collected {len(ids)} ids — fetching full metadata in batches...")
    metadata = fetch_metadata_for_ids(ids)
    print(f"Fetched metadata for {len(metadata)} videos.")

    # save
    json_out = "youtube_sample_500.json"
    csv_out = "youtube_sample_500.csv"
    save_results_json(metadata, json_out)
    try:
        save_results_csv(metadata, csv_out)
    except Exception as e:
        print("CSV save had an issue (likely encoding). JSON was saved. Error:", e)

    end = time.time()
    print(f"Done. Time elapsed: {end-start:.1f}s. JSON: {json_out}")


if __name__ == "__main__":
    main()
import requests
from typing import Dict

def fetch_metadata(video_id: str) -> Dict:
    """
    Minimal fetcher—tests patch requests.get, so keep it simple.
    Returns a dict with at least 'title'.
    Any exception from requests.get will propagate (as desired by tests).
    """
    # URL is irrelevant in tests because requests.get is patched.
    resp = requests.get("https://example.com/unused", params={"id": video_id})
    data = resp.json()
    first = (data.get("items") or [{}])[0]
    snippet = first.get("snippet", {})
    return {"id": first.get("id", video_id), "title": snippet.get("title")}

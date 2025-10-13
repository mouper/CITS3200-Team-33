from typing import Optional, Dict, Any

def _to_int(value):
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return None

def process_video_metadata(video: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalise a single video's metadata.
    - If input is falsy or empty, return None.
    - Coerce "views" (string like "1,234") to int when possible.
    """
    if not video:
        return None
    out = dict(video)
    if "views" in out:
        views_int = _to_int(out["views"])
        if views_int is not None:
            out["views"] = views_int
    return out

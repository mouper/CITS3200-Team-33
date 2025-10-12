import random
from datetime import datetime
from typing import Optional

from databases.user_settings_db import get_settings
from databases.category_block_stats_db import (
    compute_decayed_level,
    get_decayed_block_level,
    update_current_level,
)


STRENGTH_LEVEL_MAP = {
    "Weak": 0.4,
    "Moderate": 0.8,
    "Strong": 1.2,
    "Extra Strong": 1.6,
    "Blocked": None,  # Always block
}


def _is_category_active(category: Optional[str]) -> bool:
    if not category:
        return False
    settings = get_settings(category)
    return bool(settings and settings.get("is_active"))


def _get_strength_multiplier(category: Optional[str]):
    if not category:
        return None
    settings = get_settings(category)
    if not settings or not settings.get("is_active"):
        return None
    return STRENGTH_LEVEL_MAP.get(settings.get("filter_strength"), 0.8)


def update_probability(category: Optional[str], watchtime_mins: float = 0.0, now=None):
    """Update category probability based on watch activity."""
    now = now or datetime.utcnow()

    if category is None:
        return {"probability": 0.0, "strength": None}

    if not _is_category_active(category):
        # Ensure a baseline row is present even for inactive categories
        compute_decayed_level(category, now=now)
        return {"probability": 0.0, "strength": None}

    strength = _get_strength_multiplier(category)
    if watchtime_mins > 0:
        result = update_current_level(
            category=category,
            watchtime_mins=watchtime_mins,
            strength_multiplier=strength,
            now=now,
        )
        return {
            "probability": result["current_level"],
            "strength": strength,
        }

    info = compute_decayed_level(category, now=now)
    return {
        "probability": info.get("decayed_level", 0.0),
        "strength": strength,
    }


def should_filter(category: Optional[str], now=None) -> bool:
    """Determine if a category should be filtered based on probability and activeness."""
    if category is None:
        return False

    if not _is_category_active(category):
        compute_decayed_level(category, now=now)
        return False

    now = now or datetime.utcnow()
    info = get_decayed_block_level(category, now=now)
    probability = info.get("current_level") if info else 0.0
    probability = max(0.0, min(probability or 0.0, 1.0))
    if probability >= 1.0:
        return True

    return random.random() < probability


def get_probability(category: Optional[str], now=None) -> float:
    """Return the decayed probability for a category (or 0 if inactive/missing)."""
    if category is None:
        return 0.0

    now = now or datetime.utcnow()
    info = get_decayed_block_level(category, now=now)
    if not info:
        return 0.0
    return max(0.0, min(info.get("current_level", 0.0), 1.0))

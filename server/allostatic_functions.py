"""
Simple filter implementation that works directly in the server context.
"""

import math
import random
from datetime import datetime
import sqlite3
import os
from typing import Optional

from databases.graph_stats import get_block_level, set_block_level

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
USER_SETTINGS_DB_PATH = os.path.join(PROJECT_ROOT, "databases/user_settings.db")

class SimpleProbabilisticFilter:
    """Simplified probabilistic filter that works in server context."""
    
    STRENGTH_LEVEL_MAP = {
        "Weak": 0.4,
        "Moderate": 0.8,
        "Strong": 1.2,
        "Extra Strong": 1.6,
        "Blocked": None  # Special value, always block
    }

    def __init__(self, half_life_hours=1.0, initial_p=0.0, last_update=None):
        self.half_life_hours = half_life_hours
        self.P = initial_p
        self.last_update = last_update or datetime.utcnow()

    def _decay(self, now):
        if self.half_life_hours <= 0:
            return self.P
        time_elapsed_minutes = (now - self.last_update).total_seconds() / 60.0
        decay_constant = math.log(2) / (self.half_life_hours * 60)
        decayed_P = self.P * math.exp(-decay_constant * time_elapsed_minutes)
        return decayed_P

    def get_category_strength(self, category):
        """Get category strength directly from database."""
        try:
            conn = sqlite3.connect(USER_SETTINGS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filter_strength
                FROM user_filter_settings
                WHERE category = ? AND is_active = 1
            ''', (category,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                level = result[0]
                return self.STRENGTH_LEVEL_MAP.get(level, 1.0)
            else:
                return 1.0  # Default to Moderate
        except Exception as e:
            print(f"Error getting category strength: {e}")
            return 1.0

    def should_filter(self, category, now=None):
        """Returns True if content should be filtered (hidden/blocked)."""
        strength = self.get_category_strength(category)
        if strength is None:
            return True  # Always block for "Blocked"
        p_now = self.get_probability(now)
        return random.random() < p_now

    def get_probability(self, now=None):
        now = now or datetime.utcnow()
        return self._decay(now)

    def update(self, now=None, watched=False, watchtime_mins=0, category=None):
        """Update probability based on watching history and category strength."""
        now = now or datetime.utcnow()
        self.P = self._decay(now)
        if watched and watchtime_mins > 0 and category is not None:
            strength = self.get_category_strength(category)
            # Blocked: always filter, no probability update
            if strength is None:
                self.P = 1.0
            else:
                increment = watchtime_mins * strength / 100.0
                self.P = min(self.P + increment, 1.0)
        self.last_update = now
        return self.P


def _parse_last_updated(value: Optional[object]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return None
    return None


def update_allostatic_level(category: str, *, watched: bool, watchtime_mins: float, now: Optional[datetime] = None) -> float:
    existing = get_block_level(category)
    initial_p = 0.0
    last_update = None
    if existing:
        try:
            initial_p = float(existing.get("current_level") or 0.0)
        except (TypeError, ValueError):
            initial_p = 0.0
        last_update = _parse_last_updated(existing.get("last_updated_time"))

    filter_instance = SimpleProbabilisticFilter(
        initial_p=initial_p,
        last_update=last_update,
    )
    updated = filter_instance.update(
        now=now or datetime.utcnow(),
        watched=watched,
        watchtime_mins=watchtime_mins,
        category=category,
    )
    set_block_level(category=category, current_level=updated)
    return updated

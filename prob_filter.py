import math
import random
from datetime import datetime
from databases.user_settings_db import get_all_strength_levels

class ProbabilisticDecayFilter:
    """
    Filter class using filter strength levels from DB: Weak, Moderate, Strong, Extra Strong, Blocked.
    Blocked: always filtered.
    """
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
        levels = get_all_strength_levels()
        level = levels.get(category, "Moderate")
        return self.STRENGTH_LEVEL_MAP.get(level, 1.0)

    def update(self, now=None, watched=False, watchtime_mins=0, category=None):
        """
        Update probability based on watching history and category strength.
        """
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

    def get_probability(self, now=None):
        now = now or datetime.utcnow()
        return self._decay(now)

    def should_filter(self, category, now=None):
        """
        Returns True if content should be filtered (hidden/blocked).
        If category strength is Blocked, always returns True.
        """
        strength = self.get_category_strength(category)
        if strength is None:
            return True  # Always block for "Blocked"
        p_now = self.get_probability(now)
        return random.random() < p_now

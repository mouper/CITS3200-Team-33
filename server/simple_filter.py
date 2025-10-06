import math
import random
from datetime import datetime
from databases.user_settings_db import (
    get_all_strength_levels,
)
from databases.graph_stats import (
    set_block_level,
    get_block_level,
)

class ProbabilisticDecayFilter:
    STRENGTH_LEVEL_MAP = {
        "Weak": 0.4,
        "Moderate": 0.8,
        "Strong": 1.2,
        "Extra Strong": 1.6,
        "Blocked": None  # Always block
    }

    def __init__(self, half_life_hours=1.0, initial_p=0.0, last_update=None):
        self.half_life_hours = half_life_hours
        self.P = initial_p
        self.last_update = last_update or datetime.utcnow()

    def _decay(self, now):
        """Apply exponential decay to the probability."""
        if self.half_life_hours <= 0:
            return self.P
        time_elapsed_minutes = (now - self.last_update).total_seconds() / 60.0
        decay_constant = math.log(2) / (self.half_life_hours * 60)
        decayed_P = self.P * math.exp(-decay_constant * time_elapsed_minutes)
        return decayed_P

    def get_category_strength(self, category):
        """Fetch the filter strength for a category from user_settings_db."""
        levels = get_all_strength_levels()
        level = levels.get(category, "Moderate")
        return self.STRENGTH_LEVEL_MAP.get(level, 1.0)

    def update(self, now=None, watched=False, watchtime_mins=0, category=None):
        """
        Update probability based on watching history and category strength.
        Always update last_update to ensure proper decay.
        Also write probability, category and timestamp to category_block_stats.
        """
        now = now or datetime.utcnow()
        self.P = self._decay(now)
        strength = self.get_category_strength(category) if category else None

        if self.P >= 1.0:
            self.last_update = now
        elif watched and watchtime_mins > 0 and category is not None:
            if strength is None:  # Blocked
                self.P = 1.0
            else:
                increment = watchtime_mins * strength / 100.0
                self.P = min(self.P + increment, 1.0)
            self.last_update = now
        else:
            self.last_update = now

        # Write to category_block_stats DB (categoryblocked.db)
        if category is not None:
            set_block_level(
                category=category,
                current_level=self.P
            )
        return self.P

    def get_probability(self, now=None):
        """Return the current decayed probability."""
        now = now or datetime.utcnow()
        return self._decay(now)

    def should_filter(self, category, now=None):
        """
        Decide if a category should be filtered (blocked).
        Blocked categories are always filtered.
        If probability >= 1.0, block completely until decays below 1.0.
        Otherwise, use current probability.
        """
        strength = self.get_category_strength(category)
        if strength is None:
            return True  # Always block for "Blocked"
        p_now = self.get_probability(now)
        if p_now >= 1.0:
            return True  # Limiter: fully block while probability is 1.0 or higher
        return random.random() < p_now

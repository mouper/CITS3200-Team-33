import math
import random
from datetime import datetime
from databases.user_settings_db import get_all_strengths

class ProbabilisticDecayFilter:
    """
    Implements a probability filter with exponential decay and category strength logic from DB.
    """
    def __init__(self, half_life_hours=1.0, initial_p=0.0, last_update=None):
        """
        :param half_life_hours: Decay half-life in hours (float)
        :param initial_p: Initial probability (float, 0.0-1.0)
        :param last_update: Last update timestamp (datetime or None)
        """
        self.half_life_hours = half_life_hours
        self.P = initial_p
        self.last_update = last_update or datetime.utcnow()

    def _decay(self, now):
        """
        Decays the probability P based on the time elapsed since the last update.
        """
        if self.half_life_hours <= 0:
            return self.P
        time_elapsed_minutes = (now - self.last_update).total_seconds() / 60.0
        decay_constant = math.log(2) / (self.half_life_hours * 60)
        decayed_P = self.P * math.exp(-decay_constant * time_elapsed_minutes)
        return decayed_P

    def update(self, now=None, watched=False, watchtime_mins=0, category=None):
        """
        Update the filter based on time and user action.
        :param now: Current timestamp (datetime), default to now.
        :param watched: If True, user consumed content.
        :param watchtime_mins: How many minutes the user watched.
        :param category: The content category (str).
        :return: Updated probability value.
        """
        now = now or datetime.utcnow()
        self.P = self._decay(now)
        if watched and watchtime_mins > 0 and category is not None:
            strengths = get_all_strengths()
            strength = strengths.get(category, 1.0)  # default to 1.0 if missing
            increment = watchtime_mins * strength / 100.0  # Example scaling
            self.P = min(self.P + increment, 1.0)
        self.last_update = now
        return self.P

    def get_probability(self, now=None):
        """
        Get the current probability, decayed to 'now'.
        """
        now = now or datetime.utcnow()
        return self._decay(now)

    def should_filter(self, now=None):
        """
        Returns True if content should be filtered (blocked/hidden) based on probability.
        """
        p_now = self.get_probability(now)
        return random.random() < p_now

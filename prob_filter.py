import math
import random
from datetime import datetime
from databases.user_settings_db import (
    filter_strength,
    fetch_recently_updated_categories,
)
from databases.filter_results_db import (
    write_category_result,  # We need to change this databse in accordance to the new databse created
)

class ProbabilisticDecayFilter:
    STRENGTH_LEVEL_MAP = {
        "Weak": 0.4,
        "Moderate": 0.8,
        "Strong": 1.2,
        "Extra Strong": 1.6,
        "Blocked": None
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
        now = now or datetime.utcnow()
        self.P = self._decay(now)
        if watched and watchtime_mins > 0 and category is not None:
            strength = self.get_category_strength(category)
            if strength is None:
                self.P = 1.0
            else:
                increment = watchtime_mins * strength / 100.0
                self.P = min(self.P + increment, 1.0)
        self.last_update = now

        # Write update to filter_results_db, NOT user_settings_db
        if category is not None:
            write_category_result(
                category=category,
                probability=self.P,
                updated_time=self.last_update,
                decay_time=self.half_life_hours
            )

        return self.P

    def get_probability(self, now=None):
        now = now or datetime.utcnow()
        return self._decay(now)

    def should_filter(self, category, now=None):
        strength = self.get_category_strength(category)
        if strength is None:
            return True  # Always block for "Blocked"
        p_now = self.get_probability(now)
        return random.random() < p_now

    @classmethod
    def batch_update_recent(cls, since_minutes=60):
        """
        Fetch all recently updated categories and run update/filter logic for each.
        Reads from user_settings_db, writes to filter_results_db.
        """
        now = datetime.utcnow()
        recent_categories = fetch_recently_updated_categories(since_minutes)
        results = []
        for entry in recent_categories:
            category = entry['category']
            initial_p = entry['probability']
            last_update = entry['last_update']
            half_life_hours = entry.get('half_life_hours', 1.0)

            filter_instance = cls(
                half_life_hours=half_life_hours,
                initial_p=initial_p,
                last_update=last_update,
            )
            watched = entry.get('watched', False)
            watchtime_mins = entry.get('watchtime_mins', 0)

            updated_p = filter_instance.update(
                now=now,
                watched=watched,
                watchtime_mins=watchtime_mins,
                category=category
            )
            should_filter = filter_instance.should_filter(category, now=now)
            results.append({
                'category': category,
                'probability': updated_p,
                'should_filter': should_filter
            })
        return results

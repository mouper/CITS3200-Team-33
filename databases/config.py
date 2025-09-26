
"""
config.py — Central configuration for DB paths and retention periods.
"""

# Database file paths (stored under the project databases directory)
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

METADATA_DB_PATH    = os.path.join(PROJECT_ROOT, "databases/metadata_cache.db")
CATEGORIES_DB_PATH  = os.path.join(PROJECT_ROOT, "databases/categorised.db")
WATCHED_DB_PATH     = os.path.join(PROJECT_ROOT, "databases/watched.db")
USER_SETTINGS_DB_PATH = os.path.join(PROJECT_ROOT, "databases/user_settings.db")
GRAPH_STATS_DB_PATH = os.path.join(PROJECT_ROOT, "databases/category_block_stats.db")
BLOCKED_VIDEOS_DB_PATH = os.path.join(PROJECT_ROOT, "databases/blocked_videos.db")

# Retention periods (in seconds)
METADATA_TTL   = 6 * 60 * 60         # 6 hours
CATEGORIES_TTL = 24 * 60 * 60        # 24 hours
WATCHED_TTL    = 30 * 24 * 60 * 60   # 30 days
BLOCKED_VIDEOS_TTL = 90 * 24 * 60 * 60  # 90 days

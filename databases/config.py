
"""
config.py — Central configuration for DB paths and retention periods.
"""

# Database file paths (stored under the project data directory)
METADATA_DB_PATH    = "data/metadata_cache.db"
CATEGORIES_DB_PATH  = "data/categorised.db"
WATCHED_DB_PATH     = "data/watched.db"

# Retention periods (in seconds)
METADATA_TTL   = 6 * 60 * 60         # 6 hours
CATEGORIES_TTL = 24 * 60 * 60        # 24 hours
WATCHED_TTL    = 30 * 24 * 60 * 60   # 30 days

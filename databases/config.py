
"""
config.py — Central configuration for DB paths and retention periods.
"""

# Database file paths
METADATA_DB_PATH    = "metadata_cache.db"
CATEGORIES_DB_PATH  = "categorised.db"
WATCHED_DB_PATH     = "watched.db"

# Retention periods (in seconds)
METADATA_TTL   = 6 * 60 * 60         # 6 hours
CATEGORIES_TTL = 24 * 60 * 60        # 24 hours
WATCHED_TTL    = 30 * 24 * 60 * 60   # 30 days

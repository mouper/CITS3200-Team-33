"""
config.py — Central configuration for database paths and retention periods.
Edit here to change database file locations or data lifetimes.
"""

# Database file paths
METADATA_DB_PATH = "metadata_cache.db"
CATEGORISED_DB_PATH = "categorised_videos.db"
WATCHED_DB_PATH = "watched_videos.db"

# Retention periods (in seconds)
METADATA_TTL = 6 * 60 * 60      # 6 hours
CATEGORISED_TTL = 24 * 60 * 60  # 24 hours
WATCHED_TTL = 30 * 24 * 60 * 60 # 30 days

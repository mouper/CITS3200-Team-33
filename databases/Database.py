"""
database.py — Aggregator for all database modules.
Gives you one place to initialise, clean, and access all DBs.

Instead of importing each DB module separately in your code, you can now do:
    import database
    database.init_all()
    database.cleanup_all()
"""

import metadata_cache_db
import categorised_db
import watched_db

def init_all():
    """Initialise all database tables."""
    metadata_cache_db.init_db()
    categorised_db.init_db()
    watched_db.init_db()

def cleanup_all():
    """Run cleanup on all database tables."""
    metadata_cache_db.cleanup()
    categorised_db.cleanup()
    watched_db.cleanup()

# Optional convenience methods that forward to specific DB modules
def insert_metadata(video_id, metadata_json):
    return metadata_cache_db.insert_metadata(video_id, metadata_json)

def insert_categorised(video_id, category, metadata_json):
    return categorised_db.insert_categorised(video_id, category, metadata_json)

def log_watch(video_id):
    return watched_db.log_watch(video_id)

def get_fresh_metadata():
    return metadata_cache_db.get_fresh_metadata()

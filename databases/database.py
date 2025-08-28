"""
database.py — Central hub to initialise and interact with all DBs.
"""

import metadata_cache_db
import categorised_db
import watched_db

def init_all():
    metadata_cache_db.init_db()
    categorised_db.init_db()
    watched_db.init_db()

def cleanup_all():
    metadata_cache_db.cleanup()
    categorised_db.cleanup()
    watched_db.cleanup()

def insert_metadata(video_id, metadata_json):
    return metadata_cache_db.insert_metadata(video_id, metadata_json)

def insert_categorised(video_id, category, metadata_json):
    return categorised_db.insert_categorised(video_id, category, metadata_json)

def log_watch(video_id, start_time=None):
    return watched_db.log_watch(video_id, start_time)

def get_fresh_metadata():
    return metadata_cache_db.get_fresh_metadata()

def get_watch_durations():
    return watched_db.get_durations()

# Auto‑create any missing DBs/tables when this module is loaded
init_all()

"""
database.py — Central hub to initialise and interact with all DBs.
"""

from . import metadata_cache_db
from . import categorised_db
from . import watched_db
from . import user_settings_db
from . import graph_stats

def init_all():
    metadata_cache_db.init_db()
    categorised_db.init_db()
    watched_db.init_db()
    user_settings_db.init_db()
    graph_stats.init_db()

def cleanup_all():
    metadata_cache_db.cleanup()
    categorised_db.cleanup()
    watched_db.cleanup()
    user_settings_db.cleanup()

def insert_metadata(video_id, metadata_json):
    return metadata_cache_db.insert_metadata(video_id, metadata_json)

def insert_categorised(video_id, category):
    return categorised_db.insert_categorised(video_id, category)

def log_watch(video_id, start_time=None):
    return watched_db.log_watch(video_id, start_time)

def get_fresh_metadata():
    return metadata_cache_db.get_fresh_metadata()

def get_watch_durations():
    return watched_db.get_durations()

def delete_metadata_by_ids(video_ids):
    return metadata_cache_db.delete_metadata_by_ids(video_ids)

def set_user_settings(category, filter_strength, is_active, count=0):
    return user_settings_db.set_settings(category, filter_strength, is_active, count)

def get_user_settings(category):
    return user_settings_db.get_settings(category)

def get_all_user_settings():
    return user_settings_db.get_all_settings()

def count_active_users():
    return user_settings_db.count_active()

def get_max_blocked_category():
    return user_settings_db.get_max_blocked_category()

def get_total_blocked_videos():
    return user_settings_db.get_total_blocked_videos()

def set_block_level(category, current_level):
    return graph_stats.set_block_level(category, current_level)

def get_block_level(category):
    return graph_stats.get_block_level(category)

def get_all_block_levels():
    return graph_stats.get_all_block_levels()

# Auto‑create any missing DBs/tables when this module is loaded
init_all()

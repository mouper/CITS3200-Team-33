"""
database.py — Central hub to initialise and interact with all DBs.
"""

from . import metadata_cache_db
from . import categorised_db
from . import watched_db
from . import user_settings_db
from . import graph_stats
from . import blocked_videos_db

def init_all():
    metadata_cache_db.init_db()
    categorised_db.init_db()
    watched_db.init_db()
    user_settings_db.init_db()
    graph_stats.init_db()
    blocked_videos_db.init_db()

def cleanup_all():
    metadata_cache_db.cleanup()
    categorised_db.cleanup()
    watched_db.cleanup()
    user_settings_db.cleanup()
    blocked_videos_db.cleanup()

def insert_metadata(video_id, metadata_json, video_length=None):
    return metadata_cache_db.insert_metadata(video_id, metadata_json, video_length)

def insert_categorised(video_id, category, should_block=False, duration_hours=None, duration=None, duration_seconds=None, metadata_json=None):
    return categorised_db.insert_categorised(video_id, category, should_block, duration_hours, duration, duration_seconds, metadata_json)

def get_all_categorised():
    return categorised_db.get_all_categorised()

def log_watch(video_id, start_time=None, end_time=None):
    return watched_db.log_watch(video_id, start_time, end_time)

def get_metadata_by_id(video_id):
    return metadata_cache_db.get_metadata_by_id(video_id)

def get_fresh_metadata():
    return metadata_cache_db.get_fresh_metadata()

def get_watch_durations():
    return watched_db.get_durations()

def delete_metadata_by_ids(video_ids):
    return metadata_cache_db.delete_metadata_by_ids(video_ids)

def clear_metadata_cache():
    return metadata_cache_db.clear_all_metadata()

def set_ingest_active(active: bool):
    return metadata_cache_db.set_ingest_active(active)

def is_ingest_active() -> bool:
    return metadata_cache_db.is_ingest_active()

def set_user_settings(category, filter_strength, is_active, count=0, total_blocked_time=0, total_video=0):
    return user_settings_db.set_settings(category, filter_strength, is_active, count, total_blocked_time, total_video)

def get_user_settings(category):
    return user_settings_db.get_settings(category)

def get_all_user_settings():
    return user_settings_db.get_all_settings()

def count_active_users():
    return user_settings_db.count_active()

def get_max_blocked_category():
    return user_settings_db.get_max_blocked_category()

def get_total_blocked_videos():
    return user_settings_db.total_block()

def get_total_videos():
    return user_settings_db.total_videos()

def get_total_videos_sum():
    return user_settings_db.total_videos_sum()

def get_total_blocked_sum():
    return user_settings_db.total_blocked_sum()

def set_block_level(category, current_level):
    return graph_stats.set_block_level(category, current_level)

def get_block_level(category):
    return graph_stats.get_block_level(category)

def get_all_block_levels():
    return graph_stats.get_all_block_levels()

# Blocked videos functions
def log_blocked_video(video_id, duration=None, duration_seconds=None, duration_hours=None, metadata_json=None, blocked_at=None):
    return blocked_videos_db.log_blocked_video(video_id, duration, duration_seconds, duration_hours, metadata_json, blocked_at)

def get_blocked_videos(limit=None):
    return blocked_videos_db.get_blocked_videos(limit)

def get_blocked_videos_stats():
    return blocked_videos_db.get_blocked_videos_stats()

def get_blocked_videos_by_date_range(start_date=None, end_date=None):
    return blocked_videos_db.get_blocked_videos_by_date_range(start_date, end_date)

def get_blocked_videos_today():
    return blocked_videos_db.get_blocked_videos_today()

def get_blocked_videos_this_week():
    return blocked_videos_db.get_blocked_videos_this_week()

def get_blocked_videos_stats_by_period():
    return blocked_videos_db.get_blocked_videos_stats_by_period()

def delete_blocked_video(video_id):
    return blocked_videos_db.delete_blocked_video(video_id)

# Category statistics functions
def increment_total_video(category):
    return user_settings_db.increment_total_video(category)

def increment_blocked_stats(category, duration_hours=0):
    return user_settings_db.increment_blocked_stats(category, duration_hours)

def get_top_categories_by_hours(limit=5):
    return user_settings_db.get_top_categories_by_hours(limit)

def get_max_blocked_hours_category():
    return user_settings_db.get_max_blocked_hours_category()

# Auto‑create any missing DBs/tables when this module is loaded
init_all()

"""
db_cleanup_scheduler.py — Periodically triggers cleanup routines for all DBs.
Runs in a background daemon thread on a fixed interval.
"""

import time
import threading
import metadata_cache_db, categorised_db, watched_db

def run_cleanups():
    """Run cleanup for all database modules once."""
    metadata_cache_db.cleanup()
    categorised_db.cleanup()
    watched_db.cleanup()
    print("Databases cleaned.")

def start_scheduler(interval_seconds=3600):
    """Start a background thread to run cleanups every interval_seconds."""
    def loop():
        while True:
            run_cleanups()
            time.sleep(interval_seconds)
    threading.Thread(target=loop, daemon=True).start()

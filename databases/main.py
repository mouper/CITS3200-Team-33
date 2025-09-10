"""
main.py — Entry point for the self-cleaning video data pipeline.
"""

from . import database
from .cleanup_db import start_scheduler
import time

# Initialise all DBs
database.init_all()

# Start cleanups every hour
start_scheduler(3600)

def fetch_and_store_metadata(video_id, metadata_json):
    # Simulated fetch & categorisation
    database.insert_metadata(video_id, metadata_json)
    database.insert_categorised(video_id, "Example", metadata_json)

def watch_video(video_id):
    start = int(time.time())
    # Simulate watching...
    time.sleep(2)
    database.log_watch(video_id, start)

if __name__ == "__main__":
    fetch_and_store_metadata("abc123", '{"title": "Test Video"}')
    watch_video("abc123")
    print("Pipeline started. Scheduler running in background.")

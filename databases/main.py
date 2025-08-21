"""
main.py — Entry point for the self-maintaining video data pipeline.
Uses the database.py hub to interact with all DBs from one place.
"""

from databases import database
from cleanup_db import start_scheduler

# Initialise all databases on startup
database.init_all()

# Start the automated cleanup every hour (3600 seconds)
start_scheduler(3600)

def fetch_and_store_metadata(video_id, metadata_json):
    """
    Simulate fetching video metadata and categorising it.
    Replace the placeholder category with real categorisation logic.
    """
    database.insert_metadata(video_id, metadata_json)
    category = "Example"  # TODO: Implement real categorisation logic
    database.insert_categorised(video_id, category, metadata_json)

def watch_video(video_id):
    """Log that a video has been watched."""
    database.log_watch(video_id)

# Example run
if __name__ == "__main__":
    fetch_and_store_metadata("abc123", '{"title": "Test Video"}')
    watch_video("abc123")
    print("Pipeline started with central database hub. Cleanup scheduler running in background.")


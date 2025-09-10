"""
cleanup_db.py — Periodically cleans all DBs.
"""

import time
import threading
from . import database

def run_cleanups():
    database.cleanup_all()
    print("Databases cleaned.")

def start_scheduler(interval_seconds=3600):
    def loop():
        while True:
            run_cleanups()
            time.sleep(interval_seconds)
    threading.Thread(target=loop, daemon=True).start()


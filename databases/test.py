import time, sqlite3, os
from . import database

vid = "smoketest001"

print("\n--- Inserting into categorised + watched ---")
# Insert a categorised record
database.insert_categorised(vid, "TestCategory", '{"title": "Smoke Test"}')

# Simulate a short watch event
start = int(time.time())
time.sleep(2)  # simulate watching for 2 seconds
database.log_watch(vid, start)  # end_time auto‑filled if your function is set up that way

print("\n--- Checking watch durations ---")
print([dict(r) for r in database.get_watch_durations()])

print("\n--- Peeking directly into the tables ---")
for db_file, table in [
    ("data/categorised.db", "categorised"),
    ("data/watched.db", "watched")
]:
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        print(f"{table} : {rows}")
    else:
        print(f"{db_file} not found")

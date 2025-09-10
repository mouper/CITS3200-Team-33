import time, sqlite3, os
from . import database

vid = "smoketest001"

print("\n--- Inserting into categorised + watched ---")
# Insert a categorised record
database.insert_categorised(vid, "TestCategory")

# Simulate a short watch event
start = int(time.time())
time.sleep(2)  # simulate watching for 2 seconds
database.log_watch(vid, start)  # end_time auto‑filled if your function is set up that way

print("\n--- Checking watch durations ---")
print([dict(r) for r in database.get_watch_durations()])

print("\n--- Peeking directly into the tables ---")
for db_file, table in [
    ("databases/categorised.db", "categorised"),
    ("databases/watched.db", "watched")
]:
    if os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        print(f"{table} : {rows}")
    else:
        print(f"{db_file} not found")

print("\n--- Inserting into user_settings_db ---")
database.set_user_settings("TestCategory", "MEDIUM", True)

print("\n--- Checking user settings ---")
print(database.get_user_settings("TestCategory"))

print("\n--- Peeking directly into the user_filter_settings table ---")
db_file = "databases/user_settings.db"
table = "user_filter_settings"
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    print(f"{table} : {rows}")
else:
    print(f"{db_file} not found")
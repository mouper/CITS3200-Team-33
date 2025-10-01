Databases design plan

TTL (Time-To-Live): defines how long data remains valid before it is automatically deleted from the database.

## 1. Metadata Cache DB  
**Purpose:** Temporarily store raw metadata from YouTube API until categorisation is done.  
TTL: 6 hours (METADATA_TTL)

**Schema:**

| Column       | Type            | Notes                               |
|--------------|-----------------|-------------------------------------|
| video_id     | TEXT PRIMARY KEY| Unique ID (PK)                      |
| metadata     | TEXT            | Video metadata (JSON as text)       |
| time_cached  | INTEGER         | Unix timestamp                      |
| video_length | REAL            | Length of video (seconds)           |

**Lifecycle:**
- Create: Insert metadata on fetch (upsert) with current timestamp.
- Get: Retrieve cached entries fresher than TTL for categorisation.
- Delete: Remove entries older than TTL during cleanup.

## 2. Categorised DB 
**Purpose:** Record category assignment for quick lookup and avoid recategorising.  
TTL: 24 hours (CATEGORIES_TTL)

**Schema:**

| Column          | Type            | Notes                          |
|-----------------|-----------------|--------------------------------|
| video_id        | TEXT PRIMARY KEY| Unique ID (PK)                 |
| category        | TEXT            | Category label assigned by LLM |
| time_categorised| INTEGER         | Unix timestamp                 |

**Lifecycle:**
- Create: Insert category assignment for a video (upsert) with current timestamp.
- Get: Retrieve categorised videos to skip reprocessing.
- Delete: Remove entries older than 24 hours during cleanup.


## 3. Watched DB  
**Purpose:** Track stimulus activity and watch events.  
TTL: 30 days (WATCHED_TTL)

**Schema:**

| Column       | Type            | Notes                                               |
|--------------|-----------------|-----------------------------------------------------|
| video_id     | TEXT PRIMARY KEY| Unique ID (PK)                                      |
| start_time   | INTEGER         | Unix timestamp when viewing began                   |
| end_time     | INTEGER         | Unix timestamp when viewing ended                   |

**Lifecycle:**
- Create: Insert or update a watch record when a video is watched, setting start and end times.
- Get: Retrieve watch records or computed durations for analytics.
- Delete: Remove watch records older than TTL during cleanup.

## 4. User Filter Settings DB 
**Purpose:** Persist per-category filtering preferences and simple usage counters.
**Schema:**

| Column           | Type            | Notes                                                                      |
|------------------|-----------------|----------------------------------------------------------------------------|
|category          | TEXT PRIMARY KEY| Category name (PK)                                                         |
|filter_strength   | TEXT            | filter strength value: 'Weak','Moderate','Strong','Extra Strong','Blocked' |
|is_active         | BOOLEAN NOT NULL| (0, 1): flag indicating whether a category is currently enforced           |
|last_updated_time | TIMESTAMP       | Timestamp set on insert/update                                             |
|count             | INTEGER         | DEFAULT 0: count of blocked videos per category                            |
|total_blocked_time| INTEGER         | DEFAULT 0: total blocked video duration for the category                   |

**Lifecycle:**
- Create: Seed default categories on first run and upsert settings when preferences change.
- Get: Retrieve settings for a category or all categories.
- Delete: Typically retained; delete/reset only when clearing all settings or removing a category.

## 5. Graph Stats DB 
**Purpose:** Persist per-category block levels (0–1) to drive the graph/visualization.
**Schema:**

| Column           | Type                                                 | Notes                        |
|------------------|------------------------------------------------------|------------------------------|
| category         | TEXT PRIMARY KEY                                     | Category (PK)                |
| current_level    | REAL CHECK(current_level >= 0 AND current_level <= 1)| Current block level (0–1)    |
| last_updated_time| TIMESTAMP                                            | When the level last changed  |

**Lifecycle:**
- Create: Upsert a category’s block level with the current timestamp when it changes.
- Get: Fetch a single category’s level or all levels to drive the graph.
- Delete: Not typically deleted; rows are updated in place or removed if a category is deprecated.

### Implementation Notes
- SQLite per DB file; open/execute/close per op (reuse one connection for batches).
- Time columns: mix of INTEGER (Unix) and TIMESTAMP strings; convert consistently when comparing.
- TTL cleanup: delete rows older than configured TTLs.
- Indexes: add indexes on time columns to speed cleanup and ordering.

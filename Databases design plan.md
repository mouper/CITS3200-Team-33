Databases design plan

## 1. Metadata Cache DB  
Purpose: Temporarily store raw metadata from YouTube API until categorisation is done.  
TTL (Time-To-Live): defines how long data remains valid before it is automatically deleted from the database.

**Possible Schema:**

| Column       | Type           | Notes                               |
|--------------|----------------|-------------------------------------|
| videoID      | VARCHAR        | YouTube’s unique ID (PK)            |
| title        | TEXT           | Video title                         |
| description  | TEXT           | Full description                    |
| tags         | TEXT / JSON    | Store as JSON array for flexibility |
| timeFetched  | DATETIME       | For TTL/deletion scheduling         |

**Lifecycle:**
- **Create:** Insert when YouTube API returns new results.  
- **Get:** Retrieve to feed into LLM for categorisation.  
- **Delete:** Immediately after category is determined.

## 2. Categorised DB 
**Purpose:** Record category assignment for quick lookup and avoid recategorising.  
**Possible schema:**

| Column         | Type           | Notes                          |
|----------------|----------------|--------------------------------|
| videoID        | VARCHAR        | PK                             |
| category       | TEXT           | Category label assigned by LLM |
| timeCategorised| DATETIME       | Used for 24h deletion          |

**Lifecycle:**
- **Create:** Insert after category assigned.  
- **Get:** Used to skip already categorised videos.  
- **Delete:** Background job removes rows older than 24 hours.


## 3. Watched DB  
**Purpose:** Track stimulus activity and watch events.  
**Suggested schema:**

| Column       | Type        | Notes                                               |
|--------------|-------------|-----------------------------------------------------|
| videoID      | VARCHAR     | PK or composite key with timestamp if re-watched    |
| start_time   | INTEGER     | When viewing began                                  |
| end_time     | INTEGER     | When viewing ended/log saved                        |

**Lifecycle:**
- **Create:** Insert when a video is watched.  
- **Get:** Aggregate over a time window to compute stimulus level.  
- **Delete:** Optional archival or cleanup depending on analysis horizon.

### Implementation Notes
- **Choice of DB:**  
  - SQLite for client-side light footprint.  
  - Use three tables in one SQLite DB, or three separate DB files for strong physical separation.
- **Tags column:** Store as JSON text — avoids tuple limitations in SQL, easy to parse.
- **Retention:**  
  - **Metadata Cache:** Delete immediately after categorisation.  
  - **Categorised:** Expire after 24h via scheduled clean-up.  
  - **Watched:** Only delete when long-term analytics window passed.
- **Methods:**
  - `create_row(data)`, `get_row(videoID)`, `delete_row(videoID)` for each table.
  - Could wrap in a small repository layer for reusability.

# YouTube Watch Analytics – Database Design & Code

A production‑ready blueprint to store, query, and analyze what a user watches on YouTube. Designed for PostgreSQL (with optional TimescaleDB), Django ORM, and a lightweight Python ETL.

---

## 1) Goals & Scope

* Track watch behavior at high resolution (plays, pauses, seeks, bitrate changes) for 1..N users.
* Enrich events with YouTube metadata (video, channel, tags, categories).
* Enable analytics: total watch time, completion %, session funnels, top channels/tags, time‑of‑day patterns, recommendation effectiveness, search intent.
* Privacy‑aware: store only what’s needed, pseudonymize where possible, and allow deletion.

---

## 2) Core Entities & Relationships (ER Diagram)

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ DEVICES : uses
    USERS ||--o{ WATCH_EVENTS : generates
    USERS ||--o{ INTERACTIONS : makes
    USERS ||--o{ SEARCH_QUERIES : issues
    USERS ||--o{ RECS_SHOWN : sees

    SESSIONS ||--o{ WATCH_EVENTS : contains

    CHANNELS ||--o{ VIDEOS : publishes
    VIDEOS ||--o{ WATCH_EVENTS : watched
    VIDEOS ||--o{ PLAYBACK_SAMPLES : sampled
    VIDEOS ||--o{ VIDEO_TAGS : labeled
    TAGS ||--o{ VIDEO_TAGS : links

    VIDEO_CATEGORIES ||--o{ VIDEOS : classifies

    WATCH_EVENTS ||--o{ PLAYBACK_SAMPLES : has
```

> Copy this into [https://mermaid.live](https://mermaid.live) if your renderer doesn’t show ER diagrams.

---

## 3) PostgreSQL Schema (DDL)

**Notes**

* Use UTC timestamps.
* Partition `watch_events` and `playback_samples` by month for scale.
* Use `BIGINT` for cumulative counters/time in ms.

```sql
-- Enable extensions if available
CREATE EXTENSION IF NOT EXISTS pgcrypto;         -- for gen_random_uuid
CREATE EXTENSION IF NOT EXISTS btree_gin;        -- for efficient GIN work
-- Optional: CREATE EXTENSION IF NOT EXISTS timescaledb; -- if using TimescaleDB

-- 3.1 Reference Tables
CREATE TABLE users (
  user_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_user_ref  TEXT,   -- your app’s user id (avoid storing emails if possible)
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at         TIMESTAMPTZ
);

CREATE TABLE devices (
  device_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  device_type        TEXT CHECK (device_type IN ('desktop','mobile','tablet','tv','other')),
  os                 TEXT,
  browser            TEXT,
  user_agent_hash    TEXT,  -- SHA256 of UA for grouping
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  session_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  device_id          UUID REFERENCES devices(device_id) ON DELETE SET NULL,
  started_at         TIMESTAMPTZ NOT NULL,
  ended_at           TIMESTAMPTZ,
  ip_hash            TEXT,  -- store a hash, not the raw IP
  referrer_domain    TEXT
);

CREATE TABLE channels (
  channel_id         TEXT PRIMARY KEY,  -- YouTube channel ID
  title              TEXT,
  custom_url         TEXT,
  country            TEXT,
  fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE video_categories (
  category_id        INTEGER PRIMARY KEY,  -- YouTube category id
  title              TEXT NOT NULL
);

CREATE TABLE videos (
  video_id           TEXT PRIMARY KEY,  -- YouTube video ID
  channel_id         TEXT REFERENCES channels(channel_id) ON DELETE SET NULL,
  title              TEXT,
  description        TEXT,
  duration_seconds   INTEGER,
  category_id        INTEGER REFERENCES video_categories(category_id) ON DELETE SET NULL,
  published_at       TIMESTAMPTZ,
  language           TEXT,
  is_live            BOOLEAN,
  fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tags (
  tag_id             SERIAL PRIMARY KEY,
  name               TEXT UNIQUE NOT NULL
);

CREATE TABLE video_tags (
  video_id           TEXT REFERENCES videos(video_id) ON DELETE CASCADE,
  tag_id             INTEGER REFERENCES tags(tag_id) ON DELETE CASCADE,
  PRIMARY KEY (video_id, tag_id)
);

-- 3.2 High‑volume Fact Tables (Partitioned)
CREATE TABLE watch_events (
  event_id           BIGSERIAL,
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  session_id         UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
  device_id          UUID REFERENCES devices(device_id) ON DELETE SET NULL,
  video_id           TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  -- event framing
  event_time         TIMESTAMPTZ NOT NULL,
  action             TEXT NOT NULL CHECK (action IN ('play','pause','seek','end','ready')),
  position_ms        BIGINT,      -- playback position at event time
  delta_ms           BIGINT,      -- watch time since last event (can be 0 or negative on seeks)
  playback_rate      NUMERIC(4,2) DEFAULT 1.00,
  volume             NUMERIC(5,2),
  muted              BOOLEAN,
  PRIMARY KEY (event_id, event_time)
) PARTITION BY RANGE (event_time);

-- Monthly partitions (create via automation)
CREATE TABLE watch_events_2025_08 PARTITION OF watch_events FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE INDEX ON watch_events_2025_08 (user_id, event_time);
CREATE INDEX ON watch_events_2025_08 (video_id, event_time);
CREATE INDEX ON watch_events_2025_08 (session_id);

CREATE TABLE playback_samples (
  sample_id          BIGSERIAL,
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  session_id         UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
  video_id           TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  event_time         TIMESTAMPTZ NOT NULL,
  position_ms        BIGINT,
  buffered_ms        BIGINT,
  dropped_frames     INTEGER,
  quality_label      TEXT,       -- e.g., 1080p, 720p
  bitrate_kbps       INTEGER,
  connection_type    TEXT,       -- wifi/4g/5g/etc
  PRIMARY KEY (sample_id, event_time)
) PARTITION BY RANGE (event_time);

CREATE TABLE playback_samples_2025_08 PARTITION OF playback_samples FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE INDEX ON playback_samples_2025_08 (user_id, event_time);
CREATE INDEX ON playback_samples_2025_08 (video_id, event_time);

-- 3.3 User Interactions, Search, and Recommendations
CREATE TABLE interactions (
  interaction_id     BIGSERIAL PRIMARY KEY,
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  video_id           TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
  event_time         TIMESTAMPTZ NOT NULL,
  type               TEXT NOT NULL CHECK (type IN ('like','dislike','comment','share','subscribe')),
  payload_json       JSONB
);

CREATE TABLE search_queries (
  search_id          BIGSERIAL PRIMARY KEY,
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  event_time         TIMESTAMPTZ NOT NULL,
  query              TEXT NOT NULL,
  results_count      INTEGER,
  selected_video_id  TEXT REFERENCES videos(video_id)
);

CREATE TABLE recs_shown (
  rec_id             BIGSERIAL PRIMARY KEY,
  user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  event_time         TIMESTAMPTZ NOT NULL,
  context            TEXT, -- homepage, sidebar, search_results
  position           INTEGER,  -- rank in the list
  video_id           TEXT REFERENCES videos(video_id),
  clicked            BOOLEAN DEFAULT FALSE
);

-- 3.4 Materialized Views (Aggregates)
CREATE MATERIALIZED VIEW mv_daily_watch AS
SELECT
  user_id,
  video_id,
  date_trunc('day', event_time) AS day,
  SUM(GREATEST(delta_ms, 0)) AS watch_ms,
  COUNT(*) FILTER (WHERE action='play') AS plays,
  COUNT(*) FILTER (WHERE action='end')  AS ends
FROM watch_events
GROUP BY 1,2,3;

CREATE INDEX ON mv_daily_watch (user_id, day);
CREATE INDEX ON mv_daily_watch (video_id, day);
```

> If you’re using TimescaleDB, define `watch_events`/`playback_samples` as **hypertables** instead of range partitions.

---

## 4) Django Models (ORM)

```python
from django.db import models
import uuid

class User(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_user_ref = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

class Device(models.Model):
    device_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device_type = models.CharField(max_length=16, choices=[
        ("desktop","desktop"),("mobile","mobile"),("tablet","tablet"),("tv","tv"),("other","other")])
    os = models.TextField(null=True, blank=True)
    browser = models.TextField(null=True, blank=True)
    user_agent_hash = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Session(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, null=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    ip_hash = models.TextField(null=True, blank=True)
    referrer_domain = models.TextField(null=True, blank=True)

class Channel(models.Model):
    channel_id = models.CharField(primary_key=True, max_length=64)
    title = models.TextField(null=True, blank=True)
    custom_url = models.TextField(null=True, blank=True)
    country = models.TextField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

class VideoCategory(models.Model):
    category_id = models.IntegerField(primary_key=True)
    title = models.TextField()

class Video(models.Model):
    video_id = models.CharField(primary_key=True, max_length=32)
    channel = models.ForeignKey(Channel, null=True, on_delete=models.SET_NULL)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    category = models.ForeignKey(VideoCategory, null=True, on_delete=models.SET_NULL)
    published_at = models.DateTimeField(null=True, blank=True)
    language = models.TextField(null=True, blank=True)
    is_live = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(auto_now_add=True)

class Tag(models.Model):
    name = models.CharField(max_length=255, unique=True)

class VideoTag(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    class Meta:
        unique_together = ("video", "tag")

class WatchEvent(models.Model):
    ACTIONS = [(a,a) for a in ("play","pause","seek","end","ready")]
    event_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, null=True, on_delete=models.SET_NULL)
    device = models.ForeignKey(Device, null=True, on_delete=models.SET_NULL)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    action = models.CharField(max_length=8, choices=ACTIONS)
    position_ms = models.BigIntegerField(null=True, blank=True)
    delta_ms = models.BigIntegerField(null=True, blank=True)
    playback_rate = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    volume = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    muted = models.BooleanField(null=True, blank=True)

class PlaybackSample(models.Model):
    sample_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, null=True, on_delete=models.SET_NULL)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    position_ms = models.BigIntegerField(null=True, blank=True)
    buffered_ms = models.BigIntegerField(null=True, blank=True)
    dropped_frames = models.IntegerField(null=True, blank=True)
    quality_label = models.TextField(null=True, blank=True)
    bitrate_kbps = models.IntegerField(null=True, blank=True)
    connection_type = models.TextField(null=True, blank=True)

class Interaction(models.Model):
    TYPES = [(t,t) for t in ("like","dislike","comment","share","subscribe")]
    interaction_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    type = models.CharField(max_length=16, choices=TYPES)
    payload_json = models.JSONField(null=True, blank=True)

class SearchQuery(models.Model):
    search_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    query = models.TextField()
    results_count = models.Integ
```

from datetime import datetime
import math

from .db_utils import connect_db
from .config import GRAPH_STATS_DB_PATH


DEFAULT_HALF_LIFE_HOURS = 1.0


def _clamp_probability(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _apply_decay(level: float, last_updated, now: datetime, half_life_hours: float) -> float:
    if last_updated is None:
        return _clamp_probability(level)
    if half_life_hours is None or half_life_hours <= 0:
        return _clamp_probability(level)
    elapsed_minutes = (now - last_updated).total_seconds() / 60.0
    if elapsed_minutes <= 0:
        return _clamp_probability(level)
    decay_constant = math.log(2) / (half_life_hours * 60.0)
    decayed = float(level) * math.exp(-decay_constant * elapsed_minutes)
    return _clamp_probability(decayed)


def compute_decayed_level(category, now=None, half_life_hours=DEFAULT_HALF_LIFE_HOURS, db_path=GRAPH_STATS_DB_PATH):
    now = now or datetime.utcnow()
    record = get_block_level(category, db_path=db_path)
    if not record:
        return {
            "category": category,
            "previous_level": None,
            "decayed_level": 0.0,
            "last_updated_time": None,
        }

    last_updated = _to_datetime(record.get("last_updated_time"))
    previous_level = float(record.get("current_level") or 0.0)
    decayed = _apply_decay(previous_level, last_updated, now, half_life_hours)

    return {
        "category": category,
        "previous_level": previous_level,
        "decayed_level": decayed,
        "last_updated_time": last_updated or record.get("last_updated_time"),
    }


def get_decayed_block_level(category, now=None, half_life_hours=DEFAULT_HALF_LIFE_HOURS, db_path=GRAPH_STATS_DB_PATH):
    info = compute_decayed_level(category, now=now, half_life_hours=half_life_hours, db_path=db_path)
    if info.get("previous_level") is None:
        return None
    return {
        "category": category,
        "current_level": info.get("decayed_level"),
        "raw_level": info.get("previous_level"),
        "last_updated_time": info.get("last_updated_time"),
    }


def update_current_level(
    category,
    watchtime_mins=0.0,
    strength_multiplier=0.0,
    now=None,
    half_life_hours=DEFAULT_HALF_LIFE_HOURS,
    db_path=GRAPH_STATS_DB_PATH,
):
    now = now or datetime.utcnow()
    base_info = compute_decayed_level(category, now=now, half_life_hours=half_life_hours, db_path=db_path)
    base_level = base_info.get("decayed_level", 0.0) or 0.0

    if strength_multiplier is None:
        increment = None
        target_level = 1.0 if watchtime_mins else 0.0
    else:
        safe_watch = max(0.0, float(watchtime_mins or 0.0))
        increment = safe_watch * float(strength_multiplier)
        increment /= 100.0
        target_level = base_level + increment

    record = _persist_level(
        category,
        target_level,
        now=now,
        half_life_hours=half_life_hours,
        db_path=db_path,
    )

    return {
        "category": category,
        "previous_level": base_info.get("previous_level"),
        "decayed_level": base_level,
        "increment": increment,
        "current_level": record["current_level"],
        "last_updated_time": record["last_updated_time"],
    }


def _persist_level(
    category: str,
    level: float,
    now: datetime | None = None,
    *,
    half_life_hours: float = DEFAULT_HALF_LIFE_HOURS,
    db_path=GRAPH_STATS_DB_PATH,
):
    now = now or datetime.utcnow()
    clamped_level = _clamp_probability(level)
    conn = connect_db(db_path)
    cursor = conn.cursor()

    categories_cursor = cursor.execute(
        "SELECT DISTINCT category FROM category_block_stats"
    )
    existing_categories = [row[0] for row in categories_cursor.fetchall()]

    iso_now = now.isoformat()

    # Ensure the watched category is processed even if new
    if category not in existing_categories:
        existing_categories.append(category)

    for cat in existing_categories:
        cursor.execute(
            """
            SELECT id, current_level, last_updated_time
            FROM category_block_stats
            WHERE category = ?
            ORDER BY last_updated_time DESC, id DESC
            LIMIT 1
            """,
            (cat,),
        )
        latest = cursor.fetchone()

        if cat == category:
            continue

        if not latest:
            continue

        previous_level = float(latest["current_level"] or 0.0)
        last_updated = _to_datetime(latest["last_updated_time"])
        decayed_value = _apply_decay(
            previous_level,
            last_updated,
            now,
            half_life_hours,
        )

        cursor.execute(
            """
            UPDATE category_block_stats
            SET current_level = ?, last_updated_time = ?
            WHERE id = ?
            """,
            (_clamp_probability(decayed_value), iso_now, latest["id"]),
        )

    cursor.execute(
        """
        INSERT INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        """,
        (category, clamped_level, iso_now),
    )

    conn.commit()
    conn.close()
    return {
        "category": category,
        "current_level": clamped_level,
        "last_updated_time": now,
    }


def init_db(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_block_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            current_level REAL CHECK(current_level >= 0 AND current_level <= 1),
            last_updated_time TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_block_stats_category ON category_block_stats(category)"
    )
    conn.commit()
    conn.close()


def set_block_level(category, current_level, db_path=GRAPH_STATS_DB_PATH):
    _persist_level(
        category,
        current_level,
        datetime.utcnow(),
        half_life_hours=DEFAULT_HALF_LIFE_HOURS,
        db_path=db_path,
    )


def get_block_level(category, db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        WHERE category = ?
        ORDER BY last_updated_time DESC, id DESC
        LIMIT 1
        """,
        (category,),
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "category": result[0],
            "current_level": float(result[1]) if result[1] is not None else None,
            "last_updated_time": result[2],
        }
    return None


def get_all_block_levels(db_path=GRAPH_STATS_DB_PATH):
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        ORDER BY last_updated_time DESC, id DESC
        """
    )
    results = cursor.fetchall()
    conn.close()
    normalised = []
    for row in results:
        normalised.append(
            {
                "category": row["category"],
                "current_level": float(row["current_level"]) if row["current_level"] is not None else None,
                "last_updated_time": row["last_updated_time"],
            }
        )
    return normalised

def get_category_history(category, db_path=GRAPH_STATS_DB_PATH):
    """Get all level data for a specific category from category_block_stats table."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT current_level, last_updated_time 
        FROM category_block_stats 
        WHERE category = ?
        ORDER BY last_updated_time
    ''', (category,))
    results = cursor.fetchall()
    conn.close()
    
    # Return all data points for this category
    return [
        {
            'level': float(row[0]) if row[0] is not None else None,
            'updated_at': row[1]
        }
        for row in results
    ]

def get_all_categories_history(db_path=GRAPH_STATS_DB_PATH):
    """Get current level data for all categories from category_block_stats table."""
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT category, current_level, last_updated_time 
        FROM category_block_stats 
        ORDER BY category
    ''')
    results = cursor.fetchall()
    conn.close()
    return [
        {
            'category': row[0],
            'level': float(row[1]) if row[1] is not None else None,
            'updated_at': row[2]
        }
        for row in results
    ]


if __name__ == "__main__":
    init_db()
from datetime import datetime
import math

from .db_utils import connect_db
from .config import GRAPH_STATS_DB_PATH


DEFAULT_HALF_LIFE_HOURS = 1.0


def _clamp_probability(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def get_half_life_for_strength(filter_strength: str) -> float:
    """
    Get decay half-life based on filter strength.
    Stronger filters have longer half-lives (decay slower).
    
    Args:
        filter_strength: The filter strength setting
    
    Returns:
        Half-life in hours
    """
    half_life_map = {
        "Weak": 10.0 / 60.0,           # 10 minutes
        "Moderate": 30.0 / 60.0,       # 30 minutes
        "Strong": 1.0,                  # 1 hour
        "Extra Strong": 2.0,           # 2 hours
        "Blocked": 999999.0            # Essentially never decays
    }
    return half_life_map.get(filter_strength, DEFAULT_HALF_LIFE_HOURS)


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


def compute_decayed_level(category, now=None, half_life_hours=None, db_path=GRAPH_STATS_DB_PATH):
    """
    Compute decayed level for a category.
    If half_life_hours is not provided, uses the category's filter strength to determine it.
    """
    now = now or datetime.utcnow()
    record = get_block_level(category, db_path=db_path)
    if not record:
        return {
            "category": category,
            "previous_level": None,
            "decayed_level": 0.0,
            "last_updated_time": None,
        }

    # If half_life not provided, get it from category's filter strength
    if half_life_hours is None:
        from databases.user_settings_db import get_settings
        settings = get_settings(category)
        if settings:
            half_life_hours = get_half_life_for_strength(settings.get("filter_strength", "Moderate"))
        else:
            half_life_hours = DEFAULT_HALF_LIFE_HOURS

    last_updated = _to_datetime(record.get("last_updated_time"))
    previous_level = float(record.get("current_level") or 0.0)
    decayed = _apply_decay(previous_level, last_updated, now, half_life_hours)

    return {
        "category": category,
        "previous_level": previous_level,
        "decayed_level": decayed,
        "last_updated_time": last_updated or record.get("last_updated_time"),
    }


def get_decayed_block_level(category, now=None, half_life_hours=None, db_path=GRAPH_STATS_DB_PATH):
    """
    Get decayed block level for a category.
    If half_life_hours is not provided, uses the category's filter strength to determine it.
    """
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
    half_life_hours=None,
    update_all_categories=False,
    db_path=GRAPH_STATS_DB_PATH,
):
    """
    Update the blocking level for a specific category based on watch time.
    
    Args:
        category: The category to update
        watchtime_mins: Minutes watched
        strength_multiplier: Strength multiplier from user settings
        now: Timestamp (defaults to current time)
        half_life_hours: Half-life for decay (if None, uses category's filter strength)
        update_all_categories: If True, also update all other categories with decay.
                              If False (default), only update this category.
        db_path: Database path
    """
    now = now or datetime.utcnow()
    
    # Use category's strength-based half-life for decay calculation
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
        update_all_categories=update_all_categories,
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
    half_life_hours: float = None,
    update_all_categories: bool = False,
    db_path=GRAPH_STATS_DB_PATH,
):
    """
    Persist a category's blocking level.
    
    Args:
        category: The category to update
        level: The new level for this category
        now: Timestamp to use (defaults to current time)
        half_life_hours: Half-life for decay calculation (if None, uses each category's filter strength)
        update_all_categories: If True, also update all other categories with decay.
                              If False, only update the specified category.
        db_path: Database path
    """
    now = now or datetime.utcnow()
    clamped_level = _clamp_probability(level)
    conn = connect_db(db_path)
    cursor = conn.cursor()

    now_iso = now.isoformat()
    rows_to_insert = []

    if update_all_categories:
        from databases.user_settings_db import get_settings
        
        # Get latest records for all categories to apply decay
        cursor.execute(
            """
            SELECT id, category, current_level, last_updated_time
            FROM category_block_stats
            ORDER BY last_updated_time DESC, id DESC
            """
        )
        latest_records = {}
        for row in cursor.fetchall():
            cat = row["category"]
            if cat not in latest_records:
                latest_records[cat] = row

        # Apply decay to all other categories using their specific half-lives
        for cat, latest in latest_records.items():
            if cat == category:
                continue
            if not latest:
                continue
            
            # Get this category's half-life based on its strength
            cat_half_life = half_life_hours
            if cat_half_life is None:
                settings = get_settings(cat)
                if settings:
                    cat_half_life = get_half_life_for_strength(settings.get("filter_strength", "Moderate"))
                else:
                    cat_half_life = DEFAULT_HALF_LIFE_HOURS
            
            previous_level = float(latest["current_level"] or 0.0)
            last_updated = _to_datetime(latest["last_updated_time"])
            decayed_value = _apply_decay(
                previous_level,
                last_updated,
                now,
                cat_half_life,
            )
            rows_to_insert.append((cat, _clamp_probability(decayed_value), now_iso))

    # Always insert the updated category
    rows_to_insert.append((category, clamped_level, now_iso))

    cursor.executemany(
        """
        INSERT INTO category_block_stats (category, current_level, last_updated_time)
        VALUES (?, ?, ?)
        """,
        rows_to_insert,
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


def update_all_active_categories_with_decay(now=None, half_life_hours=None, db_path=GRAPH_STATS_DB_PATH):
    """
    Update all active categories with decay applied.
    This should be called periodically by a background scheduler.
    Categories that haven't been watched yet will get level=0.
    Each category uses its own strength-based half-life for decay.
    """
    from databases.user_settings_db import get_all_settings
    
    now = now or datetime.utcnow()
    now_iso = now.isoformat()
    
    # Get all active categories from user settings
    all_settings = get_all_settings()
    active_categories_with_settings = [(s['category'], s['filter_strength']) for s in all_settings if s['is_active']]
    
    if not active_categories_with_settings:
        return
    
    active_categories = [cat for cat, _ in active_categories_with_settings]
    
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    # Get latest records for all categories
    cursor.execute(
        """
        SELECT category, current_level, last_updated_time
        FROM category_block_stats
        WHERE category IN ({})
        ORDER BY last_updated_time DESC, id DESC
        """.format(','.join('?' * len(active_categories))),
        active_categories
    )
    
    latest_records = {}
    for row in cursor.fetchall():
        cat = row["category"]
        if cat not in latest_records:
            latest_records[cat] = row
    
    rows_to_insert = []
    
    # For each active category, calculate decayed level using its strength-based half-life
    for category, filter_strength in active_categories_with_settings:
        # Special case: If strength is "Blocked", always set to 1.0 (no decay)
        if filter_strength == "Blocked":
            rows_to_insert.append((category, 1.0, now_iso))
            continue
        
        # Get category-specific half-life
        cat_half_life = half_life_hours if half_life_hours is not None else get_half_life_for_strength(filter_strength)
        
        if category in latest_records:
            # Category exists, apply decay with its specific half-life
            latest = latest_records[category]
            previous_level = float(latest["current_level"] or 0.0)
            last_updated = _to_datetime(latest["last_updated_time"])
            decayed_value = _apply_decay(
                previous_level,
                last_updated,
                now,
                cat_half_life,
            )
            rows_to_insert.append((category, _clamp_probability(decayed_value), now_iso))
        else:
            # Category hasn't been watched yet, initialize to 0
            rows_to_insert.append((category, 0.0, now_iso))
    
    if rows_to_insert:
        cursor.executemany(
            """
            INSERT INTO category_block_stats (category, current_level, last_updated_time)
            VALUES (?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()
    
    conn.close()
    return len(rows_to_insert)


def update_specific_categories_with_decay(categories, now=None, half_life_hours=None, db_path=GRAPH_STATS_DB_PATH):
    """
    Update specific categories with decay applied.
    This should be called when category settings are changed.
    Only updates the specified categories, not all active categories.
    Each category uses its own strength-based half-life for decay.
    
    Special behavior:
    - If strength is "Blocked", sets level to 1.0 immediately
    - Otherwise, applies normal decay
    
    Args:
        categories: List of category names to update
        now: Timestamp to use (defaults to current time)
        half_life_hours: Half-life for decay calculation (if None, uses each category's filter strength)
        db_path: Database path
    
    Returns:
        Number of categories updated
    """
    from databases.user_settings_db import get_settings
    
    if not categories:
        return 0
    
    now = now or datetime.utcnow()
    now_iso = now.isoformat()
    
    conn = connect_db(db_path)
    cursor = conn.cursor()
    
    rows_to_insert = []
    
    # For each specified category, check if it's active and update it with its strength-based half-life
    for category in categories:
        # Check if category is active and get its settings
        settings = get_settings(category)
        if not settings or not settings.get('is_active'):
            continue
        
        filter_strength = settings.get("filter_strength", "Moderate")
        
        # Special case: If strength is "Blocked", set level to 1.0 immediately
        if filter_strength == "Blocked":
            rows_to_insert.append((category, 1.0, now_iso))
            continue
        
        # Get category-specific half-life based on its filter strength
        cat_half_life = half_life_hours if half_life_hours is not None else get_half_life_for_strength(filter_strength)
        
        # Get latest record for this category
        cursor.execute(
            """
            SELECT category, current_level, last_updated_time
            FROM category_block_stats
            WHERE category = ?
            ORDER BY last_updated_time DESC, id DESC
            LIMIT 1
            """,
            (category,)
        )
        
        latest = cursor.fetchone()
        
        if latest:
            # Category exists, apply decay with its specific half-life
            previous_level = float(latest["current_level"] or 0.0)
            last_updated = _to_datetime(latest["last_updated_time"])
            decayed_value = _apply_decay(
                previous_level,
                last_updated,
                now,
                cat_half_life,
            )
            rows_to_insert.append((category, _clamp_probability(decayed_value), now_iso))
        else:
            # Category hasn't been watched yet, initialize to 0
            rows_to_insert.append((category, 0.0, now_iso))
    
    if rows_to_insert:
        cursor.executemany(
            """
            INSERT INTO category_block_stats (category, current_level, last_updated_time)
            VALUES (?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()
    
    conn.close()
    return len(rows_to_insert)


if __name__ == "__main__":
    init_db()
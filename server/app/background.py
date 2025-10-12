"""Background worker for auto-running classification when fresh metadata exists."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict
from threading import Event


_status: Dict[str, Any] = {
    "loop_running": False,
    "last_run_ts": None,
    "last_written": 0,
    "last_error": None,
    "pending_count": 0,
    "classify_inflight": False,
}

_stop_event: Event | None = None
_thread: threading.Thread | None = None

# Category decay scheduler
_decay_status: Dict[str, Any] = {
    "loop_running": False,
    "last_run_ts": None,
    "last_update_count": 0,
    "last_error": None,
}

_decay_stop_event: Event | None = None
_decay_thread: threading.Thread | None = None


def _ensure_llm_client_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    packages_dir = repo_root / "packages"
    packages_str = str(packages_dir)
    if packages_str not in sys.path:
        sys.path.insert(0, packages_str)


def _poll_and_classify(model_id: str, interval_seconds: float) -> None:
    _ensure_llm_client_on_path()
    try:
        from llm_client.src.metadata_triage import (
            get_fresh_metadata_unprocessed,
            get_fresh_metadata_triaged,
        )  # type: ignore
        from llm_client.src.categorise_runner import run_once  # type: ignore
    except Exception as exc:  # pragma: no cover
        _status["last_error"] = f"Import error: {exc}"
        return

    _status["loop_running"] = True
    assert _stop_event is not None
    while not _stop_event.is_set():
        try:
            # Do not poll while a classification run is in-flight
            if _status.get("classify_inflight"):
                continue
            # Skip polling entirely if ingestion is active
            try:
                from databases import database as db
                if db.is_ingest_active():
                    continue
            except Exception:
                pass
            pending_rows = get_fresh_metadata_unprocessed()
            pending_count = len(pending_rows)
            _status["pending_count"] = pending_count
            if pending_count:
                # Build triaged items now so we can delete them immediately before classification
                items = get_fresh_metadata_triaged()
                def classify_async(payload_items):
                    _status["classify_inflight"] = True
                    try:
                        written_local = run_once(model_id, pretriaged_items=payload_items)
                        _status["last_written"] = int(written_local)
                        _status["last_run_ts"] = int(time.time())
                        _status["last_error"] = None
                    except Exception as exc:
                        _status["last_error"] = str(exc)
                    finally:
                        _status["classify_inflight"] = False
                # Run classification on a separate thread so inserts into metadata_cache are never blocked
                threading.Thread(target=classify_async, args=(items,), daemon=True).start()
        except Exception as exc:  # pragma: no cover
            _status["last_error"] = str(exc)
        finally:
            _stop_event.wait(interval_seconds)
    _status["loop_running"] = False


def start_background(app: Any) -> None:
    """Start the background autorun loop if enabled by env/config."""
    if getattr(app, "_bg_started", False):
        return

    # Always start the category decay scheduler (10 minutes interval by default)
    decay_interval = float(os.getenv("CATEGORY_DECAY_INTERVAL", "600.0"))
    start_category_decay_scheduler(interval_seconds=decay_interval)

    autorun = os.getenv("CLASSIFIER_AUTORUN", "false").lower() in {"1", "true", "yes", "on"}
    if not autorun:
        app._bg_started = True  # type: ignore[attr-defined]
        return

    start_loop()
    app._bg_started = True  # type: ignore[attr-defined]


def start_loop(model_id: str | None = None, interval_seconds: float | None = None) -> bool:
    """Start the classifier loop explicitly (idempotent). Returns True if started."""
    global _stop_event, _thread
    if _status.get("loop_running", False) and _thread and _thread.is_alive():
        return False
    if _stop_event is None:
        _stop_event = Event()
    else:
        _stop_event.clear()

    model = model_id or os.getenv("OPENAI_MODEL_ID", "gpt-4.1-nano")
    interval = interval_seconds if interval_seconds is not None else float(os.getenv("CLASSIFIER_POLL_INTERVAL", "0.01"))

    _thread = threading.Thread(target=_poll_and_classify, args=(model, interval), daemon=True)
    _thread.start()
    return True


def stop_loop() -> bool:
    """Signal the loop to stop and wait briefly. Returns True if a running loop was signaled."""
    global _stop_event, _thread
    if not _status.get("loop_running", False) or _stop_event is None or _thread is None:
        return False
    _stop_event.set()
    # Give the thread a moment to exit
    _thread.join(timeout=0.5)
    return True


def get_status() -> Dict[str, Any]:
    """Return a snapshot of the background worker status."""
    return dict(_status)


def _category_decay_loop(interval_seconds: float) -> None:
    """Periodically update all active categories with decay."""
    from databases import category_block_stats_db
    
    _decay_status["loop_running"] = True
    assert _decay_stop_event is not None
    
    while not _decay_stop_event.is_set():
        try:
            # Update all active categories with decay
            count = category_block_stats_db.update_all_active_categories_with_decay()
            _decay_status["last_update_count"] = count if count else 0
            _decay_status["last_run_ts"] = int(time.time())
            _decay_status["last_error"] = None
        except Exception as exc:
            _decay_status["last_error"] = str(exc)
        finally:
            _decay_stop_event.wait(interval_seconds)
    
    _decay_status["loop_running"] = False


def start_category_decay_scheduler(interval_seconds: float = 600.0) -> bool:
    """
    Start the category decay scheduler.
    This will update all active categories every interval_seconds.
    
    Args:
        interval_seconds: How often to update (default: 600 seconds / 10 minutes)
    
    Returns:
        True if started, False if already running
    """
    global _decay_stop_event, _decay_thread
    
    if _decay_status.get("loop_running", False) and _decay_thread and _decay_thread.is_alive():
        return False
    
    if _decay_stop_event is None:
        _decay_stop_event = Event()
    else:
        _decay_stop_event.clear()
    
    _decay_thread = threading.Thread(
        target=_category_decay_loop,
        args=(interval_seconds,),
        daemon=True,
        name="CategoryDecayScheduler"
    )
    _decay_thread.start()
    return True


def stop_category_decay_scheduler() -> bool:
    """
    Stop the category decay scheduler.
    
    Returns:
        True if a running loop was signaled to stop
    """
    global _decay_stop_event, _decay_thread
    
    if not _decay_status.get("loop_running", False) or _decay_stop_event is None or _decay_thread is None:
        return False
    
    _decay_stop_event.set()
    _decay_thread.join(timeout=0.5)
    return True


def get_decay_status() -> Dict[str, Any]:
    """Return a snapshot of the decay scheduler status."""
    return dict(_decay_status)


def update_specific_categories(categories: list[str]) -> int:
    """
    Update specific categories with decay applied.
    Called when category settings are changed.
    
    Args:
        categories: List of category names to update
    
    Returns:
        Number of categories updated
    """
    from databases import category_block_stats_db
    
    if not categories:
        return 0
    
    try:
        # Update only the specified categories with decay applied
        return category_block_stats_db.update_specific_categories_with_decay(categories)
    except Exception:
        return 0


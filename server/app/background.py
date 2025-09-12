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
}

_stop_event: Event | None = None
_thread: threading.Thread | None = None


def _ensure_llm_client_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    packages_dir = repo_root / "packages"
    packages_str = str(packages_dir)
    if packages_str not in sys.path:
        sys.path.insert(0, packages_str)


def _poll_and_classify(model_id: str, interval_seconds: float) -> None:
    _ensure_llm_client_on_path()
    try:
        from llm_client.src.metadata_triage import get_fresh_metadata_triaged  # type: ignore
        from llm_client.src.categorise_runner import run_once  # type: ignore
    except Exception as exc:  # pragma: no cover
        _status["last_error"] = f"Import error: {exc}"
        return

    _status["loop_running"] = True
    assert _stop_event is not None
    while not _stop_event.is_set():
        try:
            items = get_fresh_metadata_triaged()
            _status["pending_count"] = len(items)
            if items:
                # Pass pre-triaged items so the runner can delete them from cache immediately
                written = run_once(model_id, pretriaged_items=items)
                _status["last_written"] = int(written)
                _status["last_run_ts"] = int(time.time())
                _status["last_error"] = None
        except Exception as exc:  # pragma: no cover
            _status["last_error"] = str(exc)
        finally:
            _stop_event.wait(interval_seconds)
    _status["loop_running"] = False


def start_background(app: Any) -> None:
    """Start the background autorun loop if enabled by env/config."""
    if getattr(app, "_bg_started", False):
        return

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

    model = model_id or os.getenv("OPENAI_MODEL_ID", "gpt-5-nano")
    interval = interval_seconds if interval_seconds is not None else float(os.getenv("CLASSIFIER_POLL_INTERVAL", "0.05"))

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
    _thread.join(timeout=1.0)
    return True


def get_status() -> Dict[str, Any]:
    """Return a snapshot of the background worker status."""
    return dict(_status)


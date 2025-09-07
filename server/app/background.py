"""Background worker for auto-running classification when fresh metadata exists."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict


_status: Dict[str, Any] = {
    "loop_running": False,
    "last_run_ts": None,
    "last_written": 0,
    "last_error": None,
    "pending_count": 0,
}


def _ensure_llm_client_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    llm_src = repo_root / "packages" / "llm-client" / "src"
    llm_str = str(llm_src)
    if llm_str not in sys.path:
        sys.path.insert(0, llm_str)


def _poll_and_classify(model_id: str, interval_seconds: float) -> None:
    _ensure_llm_client_on_path()
    try:
        from metadata_triage import get_fresh_metadata_triaged  # type: ignore
        from categorise_runner import run_once  # type: ignore
    except Exception as exc:  # pragma: no cover
        _status["last_error"] = f"Import error: {exc}"
        return

    _status["loop_running"] = True
    while True:
        try:
            items = get_fresh_metadata_triaged()
            _status["pending_count"] = len(items)
            if items:
                written = run_once(model_id)
                _status["last_written"] = int(written)
                _status["last_run_ts"] = int(time.time())
                _status["last_error"] = None
        except Exception as exc:  # pragma: no cover
            _status["last_error"] = str(exc)
        finally:
            time.sleep(interval_seconds)


def start_background(app: Any) -> None:
    """Start the background autorun loop if enabled by env/config."""
    if getattr(app, "_bg_started", False):
        return

    autorun = os.getenv("CLASSIFIER_AUTORUN", "false").lower() in {"1", "true", "yes", "on"}
    if not autorun:
        app._bg_started = True  # type: ignore[attr-defined]
        return

    model_id = os.getenv("OPENAI_MODEL_ID", "gpt-5-nano")
    interval = float(os.getenv("CLASSIFIER_POLL_INTERVAL", "0.05"))

    thread = threading.Thread(target=_poll_and_classify, args=(model_id, interval), daemon=True)
    thread.start()

    app._bg_started = True  # type: ignore[attr-defined]


def get_status() -> Dict[str, Any]:
    """Return a snapshot of the background worker status."""
    return dict(_status)


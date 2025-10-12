"""Expose public blueprints for the Flask app."""

from . import metadata
from . import classifier
from . import settings
from . import filter
from . import categorised
from . import stats
from . import watched

__all__ = [
    "metadata",
    "classifier",
    "settings",
    "filter",
    "categorised",
    "stats",
    "watched",
]

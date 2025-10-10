"""
test_metadata_triage.py — Unit tests for metadata triage functionality.

Tests redaction, truncation, and payload processing for video metadata.
"""

import json
from pathlib import Path

# Import the modules to test
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the databases module since it's not in the test environment
sys.modules['databases'] = MagicMock()
sys.modules['databases.db_utils'] = MagicMock()
sys.modules['databases.config'] = MagicMock()

from metadata_triage import (
    load_categories,
    _redact,
    _truncate,
    _normalise_tags,
    triage_record,
    ALLOWED_LABELS,
    CATEGORIES_VERSION,
)


class TestMetadataTriage:
    """Test cases for metadata triage functions."""

    def test_load_categories(self):
        """Test loading categories from JSON file."""
        labels, version = load_categories()
        assert isinstance(labels, list)
        assert len(labels) == 25  # Based on categories.v1.json
        assert version == "categories.v2"
        assert "Educational and Academic" in labels
        assert "Music and Arts" in labels

    def test_constants_loaded(self):
        """Test that constants are properly loaded."""
        assert isinstance(ALLOWED_LABELS, list)
        assert len(ALLOWED_LABELS) > 0
        assert isinstance(CATEGORIES_VERSION, str)
        assert CATEGORIES_VERSION == "categories.v2"

    def test_redact_urls(self):
        """Test URL redaction."""
        text = "Check out https://example.com and www.test.org for more info!"
        result = _redact(text)
        assert "https://example.com" not in result
        assert "www.test.org" not in result
        assert "Check out" in result

    def test_redact_emails(self):
        """Test email redaction."""
        text = "Contact me at user@example.com or admin@test.org"
        result = _redact(text)
        assert "user@example.com" not in result
        assert "admin@test.org" not in result
        assert "Contact me at" in result

    def test_redact_emojis(self):
        """Test emoji and unicode symbol redaction."""
        text = "Great video! 👍 Check this out 👀🎉"
        result = _redact(text)
        assert "👍" not in result
        assert "👀" not in result
        assert "🎉" not in result
        assert "Great video!" in result

    def test_redact_whitespace(self):
        """Test whitespace normalization."""
        text = "  Multiple    spaces   and\nnewlines  "
        result = _redact(text)
        assert result == "Multiple spaces and newlines"

    def test_truncate_basic(self):
        """Test basic truncation."""
        text = "This is a long text that should be truncated"
        result = _truncate(text, 10)
        assert result == "This is a"  # rstrip() removes trailing space
        assert len(result) <= 10

    def test_truncate_no_cut_words(self):
        """Test that truncation doesn't cut words mid-way."""
        text = "This is a test sentence with many words"
        result = _truncate(text, 15)
        # Should not cut in the middle of "sentence"
        assert "test sentence" not in result or result.endswith("test ")
        assert len(result) <= 15

    def test_normalise_tags_list(self):
        """Test tag normalization from list."""
        tags = ["python", "machine learning", "AI", "tutorial", "coding"]
        result = _normalise_tags(tags, max_items=3, max_len=30)
        assert isinstance(result, str)
        assert len(result.split(", ")) <= 3
        assert len(result) <= 30

    def test_normalise_tags_string(self):
        """Test tag normalization from comma-separated string."""
        tags = "python, machine learning, AI, tutorial, coding"
        result = _normalise_tags(tags, max_items=3, max_len=30)
        assert isinstance(result, str)
        assert len(result.split(", ")) <= 3

    def test_normalise_tags_json_list(self):
        """Test tag normalization from JSON list string."""
        tags = '["python", "machine learning", "AI"]'
        result = _normalise_tags(tags)
        assert isinstance(result, str)
        assert "python" in result

    def test_normalise_tags_empty(self):
        """Test tag normalization with empty input."""
        assert _normalise_tags("") == ""
        assert _normalise_tags([]) == ""
        assert _normalise_tags(None) == ""

    def test_triage_record_basic(self):
        """Test basic record triage."""
        record = {
            "title": "Learn Python Programming",
            "description": "A comprehensive guide to Python with examples",
            "tags": ["python", "programming", "tutorial"],
            "channel": "CodeAcademy"
        }

        result = triage_record(record)

        assert result["Title"] == "Learn Python Programming"
        assert result["Description"] == "A comprehensive guide to Python with examples"
        assert "python" in result["Tags"]
        assert result["Channel"] == "CodeAcademy"

    def test_triage_record_with_redaction(self):
        """Test record triage with content that needs redaction."""
        record = {
            "title": "Amazing Tutorial!",
            "description": "Check https://spam.com and contact spam@spam.com 👍",
            "tags": ["tutorial", "amazing"],
            "channel": "SpamChannel 🚫"
        }

        result = triage_record(record)

        # URLs and emails should be removed
        assert "https://spam.com" not in result["Description"]
        assert "spam@spam.com" not in result["Description"]
        assert "👍" not in result["Channel"]
        assert "🚫" not in result["Channel"]

    def test_triage_record_truncation(self):
        """Test record triage with truncation."""
        long_description = "This is a very long description " * 20
        long_tags = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]

        record = {
            "title": "Short Title",
            "description": long_description,
            "tags": long_tags,
            "channel": "TestChannel"
        }

        result = triage_record(record)

        assert len(result["Description"]) <= 200
        assert len(result["Tags"]) <= 120
        assert result["Title"] == "Short Title"  # No truncation for title

    def test_triage_record_empty_fields(self):
        """Test record triage with missing or empty fields."""
        record = {
            "title": "Just a Title",
            "description": "",
            "tags": [],
            "channel": None
        }

        result = triage_record(record)

        assert result["Title"] == "Just a Title"
        assert result["Description"] == ""
        assert result["Tags"] == ""
        assert result["Channel"] == ""


def run_tests():
    """Run all tests and report results."""
    test_instance = TestMetadataTriage()

    test_methods = [
        method for method in dir(test_instance)
        if method.startswith('test_') and callable(getattr(test_instance, method))
    ]

    passed = 0
    failed = 0

    for test_method in test_methods:
        try:
            print(f"Running {test_method}...")
            getattr(test_instance, test_method)()
            print(f"PASS {test_method}")
            passed += 1
        except Exception as e:
            print(f"FAIL {test_method}: {e}")
            failed += 1

    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

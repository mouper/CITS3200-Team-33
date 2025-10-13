"""
test_prompt_builder.py — Unit tests for prompt builder functionality.

Tests prompt assembly, system messages, allowed labels, and user payload formatting.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'llm_client', 'src'))

from prompt_builder import (
    build_system_message,
    build_allowed_labels_block,
    build_user_payload,
    assemble_prompt,
)


class TestPromptBuilder:
    """Test cases for prompt builder functions."""

    def test_build_system_message(self):
        """Test system message generation."""
        system = build_system_message()

        assert isinstance(system, str)
        assert "video title classifier" in system.lower()
        assert "exactly one label" in system
        assert "strict JSON" in system
        assert '{"category":"<Label>"}' in system
        assert "no explanations" in system.lower()
        assert "no extra fields" in system.lower()

    def test_build_allowed_labels_block(self):
        """Test allowed labels block generation."""
        test_labels = [
            "Educational & Academic",
            "How-To / Tutorials",
            "Science & Technology"
        ]

        block = build_allowed_labels_block(test_labels)

        assert isinstance(block, str)
        assert "Allowed labels" in block
        assert "choose exactly one" in block
        assert "case-sensitive" in block

        # Check each label appears in the block
        for label in test_labels:
            assert f"- {label}" in block

        assert "Other / Unclear" in block

    def test_build_user_payload_basic(self):
        """Test basic user payload generation."""
        payload = {
            "Title": "Learn Python",
            "Description": "A guide to Python programming",
            "Tags": "python, programming, tutorial",
            "Channel": "CodeAcademy"
        }

        user_msg = build_user_payload(payload)

        assert isinstance(user_msg, str)
        assert 'Title: "Learn Python"' in user_msg
        assert 'Description: "A guide to Python programming"' in user_msg
        assert 'Tags: "python, programming, tutorial"' in user_msg
        assert 'Channel: "CodeAcademy"' in user_msg
        assert 'Return: {"category":"<one label from Allowed>"}' in user_msg

    def test_build_user_payload_empty_fields(self):
        """Test user payload with empty fields."""
        payload = {
            "Title": "Just Title",
            "Description": "",
            "Tags": "",
            "Channel": ""
        }

        user_msg = build_user_payload(payload)

        assert 'Title: "Just Title"' in user_msg
        assert 'Description: ""' in user_msg
        assert 'Tags: ""' in user_msg
        assert 'Channel: ""' in user_msg

    def test_build_user_payload_special_chars(self):
        """Test user payload with special characters and quotes."""
        payload = {
            "Title": 'Video with "quotes" and special chars!',
            "Description": "Description with newlines\nand tabs\tand quotes\"",
            "Tags": "tag1, tag2, tag3",
            "Channel": "Channel with émojis 👍"
        }

        user_msg = build_user_payload(payload)

        # Should wrap values in double quotes; allow raw control chars
        expected_title = f'Title: "{payload["Title"]}"'
        expected_desc = f'Description: "{payload["Description"]}"'
        expected_channel = f'Channel: "{payload["Channel"]}"'

        assert expected_title in user_msg
        assert expected_desc in user_msg
        assert expected_channel in user_msg

    def test_assemble_prompt_basic(self):
        """Test complete prompt assembly."""
        payload = {
            "Title": "Test Video",
            "Description": "Test Description",
            "Tags": "test, video",
            "Channel": "TestChannel"
        }

        labels = ["Educational & Academic", "How-To / Tutorials", "Other / Unclear"]

        system, labels_block, user_msg = assemble_prompt(payload, labels)

        # Check return types
        assert isinstance(system, str)
        assert isinstance(labels_block, str)
        assert isinstance(user_msg, str)

        # Check content
        assert "classifier" in system
        assert "Allowed labels" in labels_block
        assert 'Title: "Test Video"' in user_msg

        # Verify order is correct for Chat API
        assert system == build_system_message()
        assert labels_block == build_allowed_labels_block(labels)
        assert user_msg == build_user_payload(payload)

    def test_assemble_prompt_empty_labels(self):
        """Test prompt assembly with empty labels list."""
        payload = {"Title": "Test", "Description": "", "Tags": "", "Channel": ""}
        labels = []

        system, labels_block, user_msg = assemble_prompt(payload, labels)

        assert "Allowed labels" in labels_block
        assert "choose exactly one" in labels_block
        # Should still include the instruction about unclear cases
        assert "Other / Unclear" in labels_block

    def test_assemble_prompt_complex_content(self):
        """Test prompt assembly with complex content."""
        payload = {
            "Title": "Advanced Python: Decorators & Metaclasses Explained",
            "Description": "Deep dive into Python's advanced features. We'll cover decorators, metaclasses, and design patterns. Visit example.com for code samples.",
            "Tags": "python, advanced, tutorial, decorators, metaclasses",
            "Channel": "Python Mastery 🐍"
        }

        labels = [
            "Educational & Academic",
            "How-To / Tutorials",
            "Science & Technology",
            "Other / Unclear"
        ]

        system, labels_block, user_msg = assemble_prompt(payload, labels)

        # Check that the complex content is properly formatted
        assert "Advanced Python: Decorators & Metaclasses Explained" in user_msg
        assert "Deep dive into Python's advanced features" in user_msg
        assert "decorators, metaclasses" in user_msg
        assert "Python Mastery 🐍" in user_msg

        # Check that system and labels are properly formatted
        assert len(labels) == len([line for line in labels_block.split('\n') if line.startswith('- ')])

    def test_prompt_structure_consistency(self):
        """Test that prompt structure is consistent."""
        payload1 = {"Title": "Video 1", "Description": "Desc 1", "Tags": "tag1", "Channel": "Channel1"}
        payload2 = {"Title": "Video 2", "Description": "Desc 2", "Tags": "tag2", "Channel": "Channel2"}

        labels = ["Label1", "Label2"]

        system1, labels_block1, user_msg1 = assemble_prompt(payload1, labels)
        system2, labels_block2, user_msg2 = assemble_prompt(payload2, labels)

        # System and labels block should be identical for same labels
        assert system1 == system2
        assert labels_block1 == labels_block2

        # User messages should be different
        assert user_msg1 != user_msg2

        # But should have same structure
        assert user_msg1.count('Title:') == user_msg2.count('Title:') == 1
        assert user_msg1.count('Description:') == user_msg2.count('Description:') == 1
        assert user_msg1.count('Tags:') == user_msg2.count('Tags:') == 1
        assert user_msg1.count('Channel:') == user_msg2.count('Channel:') == 1
        assert user_msg1.count('Return:') == user_msg2.count('Return:') == 1


def run_tests():
    """Run all tests and report results."""
    test_instance = TestPromptBuilder()

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

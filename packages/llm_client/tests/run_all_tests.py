#!/usr/bin/env python3
"""
run_all_tests.py — Run all test suites for the llm-client package.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))


def run_test_file(test_file_path):
    """Run a single test file and return (passed, failed) counts."""
    print(f"\n{'='*50}")
    print(f"Running tests from: {test_file_path.name}")
    print(f"{'='*50}")

    # Import the test module
    module_name = test_file_path.stem
    spec = __import__(f"{module_name}", fromlist=["run_tests"])

    # Run the tests
    success = spec.run_tests()
    return success


def main():
    """Run all test files in the tests directory."""
    tests_dir = Path(__file__).parent
    test_files = [
        tests_dir / "test_metadata_triage.py",
        tests_dir / "test_prompt_builder.py"
    ]

    all_passed = True

    for test_file in test_files:
        if test_file.exists():
            success = run_test_file(test_file)
            all_passed = all_passed and success
        else:
            print(f"❌ Test file not found: {test_file}")
            all_passed = False

    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print(f"{'='*50}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Test Runner Tool

Ensures all tests are run within the Poetry environment with proper dependencies.

Usage:
    poetry run python tools/development/testing/run_tests.py
    poetry run python tools/development/testing/run_tests.py tests/server/
    poetry run python tools/development/testing/run_tests.py tests/ui/test_ui.py
"""

import sys
import subprocess
import os
from pathlib import Path


def check_poetry_available():
    """Check if Poetry is available."""
    try:
        result = subprocess.run(
            ["poetry", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def main():
    """Main test runner function."""
    print("Internal Assistant Test Runner")
    print("=" * 50)

    # Check if we're already in Poetry environment
    in_poetry = os.environ.get("POETRY_ACTIVE") == "1"

    if in_poetry:
        print("Running in Poetry environment")
    else:
        print("Checking Poetry availability...")
        if not check_poetry_available():
            print("Error: Poetry not found")
            print("Install Poetry: https://python-poetry.org/docs/#installation")
            return 1
        print("Poetry available")

    # Determine test arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests"]

    # Run pytest with Poetry
    print(f"\nRunning tests: {' '.join(args)}")

    try:
        if in_poetry:
            cmd = ["pytest"] + args + ["-v"]
        else:
            cmd = ["poetry", "run", "pytest"] + args + ["-v"]

        result = subprocess.run(cmd)
        return result.returncode

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\nTest execution error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
    
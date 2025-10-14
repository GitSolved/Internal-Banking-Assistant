#!/usr/bin/env python3
"""
Test Runner Script - Enforces Poetry Usage

This script ensures all tests are run within the Poetry environment,
preventing dependency availability issues.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py specific_test.py   # Run specific test
    python run_tests.py --help            # Show help

Author: Claude Code Assistant  
Date: 2025-08-20
Purpose: Enforce Poetry usage for testing
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
    print("🧪 INTERNAL ASSISTANT TEST RUNNER")
    print("=" * 50)

    # Check if we're already in Poetry environment
    in_poetry = os.environ.get("POETRY_ACTIVE") == "1"

    if in_poetry:
        print("✅ Already running in Poetry environment")
    else:
        print("🔍 Checking Poetry availability...")
        if not check_poetry_available():
            print("❌ Poetry not found!")
            print(
                "📥 Please install Poetry: https://python-poetry.org/docs/#installation"
            )
            return 1
        print("✅ Poetry available")

    # Determine test arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests"]

    # If no specific test args provided, run verification first
    if args == ["tests"]:
        print("\n🔍 Running environment verification first...")
        try:
            if in_poetry:
                verify_cmd = ["python", "tools/verify_environment.py", "--quick"]
            else:
                verify_cmd = [
                    "poetry",
                    "run",
                    "python",
                    "tools/verify_environment.py",
                    "--quick",
                ]

            result = subprocess.run(verify_cmd, timeout=60)
            if result.returncode != 0:
                print("❌ Environment verification failed!")
                return 1
            print("✅ Environment verification passed!")
        except Exception as e:
            print(f"⚠️  Environment verification error: {e}")

    # Run pytest with Poetry
    print(f"\n🚀 Running tests: {' '.join(args)}")

    try:
        if in_poetry:
            cmd = ["pytest"] + args + ["-v"]
        else:
            cmd = ["poetry", "run", "pytest"] + args + ["-v"]

        result = subprocess.run(cmd)
        return result.returncode

    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Script to clean up Qdrant database locks and stale processes.
Run this when you get "Storage folder is already accessed by another instance" errors.
"""

import os
import shutil
import sys
from pathlib import Path
import psutil
import signal


def find_and_kill_qdrant_processes():
    """Find and kill any Python processes that might be locking Qdrant."""
    killed = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] == "python.exe" and proc.info["cmdline"]:
                cmdline = " ".join(proc.info["cmdline"])
                if "internal_assistant" in cmdline or "qdrant" in cmdline.lower():
                    print(f"Killing process {proc.info['pid']}: {cmdline}")
                    proc.kill()
                    killed.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed


def cleanup_qdrant_locks():
    """Remove Qdrant lock files and temporary data."""
    qdrant_path = Path("local_data/internal_assistant/qdrant")

    if not qdrant_path.exists():
        print(f"Qdrant path {qdrant_path} does not exist, nothing to clean")
        return

    print(f"Cleaning up Qdrant locks in {qdrant_path}")

    # Remove lock files
    for lock_file in qdrant_path.rglob("*.lock"):
        try:
            lock_file.unlink()
            print(f"Removed lock file: {lock_file}")
        except Exception as e:
            print(f"Failed to remove {lock_file}: {e}")

    # Remove .tmp files
    for tmp_file in qdrant_path.rglob("*.tmp"):
        try:
            tmp_file.unlink()
            print(f"Removed temp file: {tmp_file}")
        except Exception as e:
            print(f"Failed to remove {tmp_file}: {e}")


def main():
    print("🧹 Internal Assistant Qdrant Cleanup Tool")
    print("=" * 50)

    # Kill stale processes
    print("\n1. Checking for stale processes...")
    killed = find_and_kill_qdrant_processes()
    if killed:
        print(f"✅ Killed {len(killed)} stale processes: {killed}")
        import time

        time.sleep(2)  # Wait for processes to fully terminate
    else:
        print("✅ No stale processes found")

    # Clean up locks
    print("\n2. Cleaning up Qdrant locks...")
    cleanup_qdrant_locks()

    print("\n✅ Cleanup complete! You should now be able to run 'make run'")
    print("\nIf you still get lock errors, try:")
    print("  1. Close all terminals/IDE sessions")
    print("  2. Run this script again")
    print("  3. Restart your computer if necessary")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        sys.exit(1)

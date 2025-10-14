#!/usr/bin/env python3
"""
Logging Control Tool

Controls logging levels and manages log files for Internal Assistant.

Usage:
    poetry run python tools/maintenance/logging_control.py set-level INFO
    poetry run python tools/maintenance/logging_control.py show
    poetry run python tools/maintenance/logging_control.py cleanup --keep-days 7
    poetry run python tools/maintenance/logging_control.py tail
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional


def set_log_level(level: str) -> None:
    """Set the logging level for the current session."""
    valid_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]

    if level.upper() not in valid_levels:
        print(
            f"Error: Invalid log level '{level}'. Valid levels: {', '.join(valid_levels)}"
        )
        sys.exit(1)

    # Set environment variable
    os.environ["PGPT_LOG_LEVEL"] = level.upper()
    print(f"Log level set to: {level.upper()}")
    print(
        "Note: This only affects new processes. Restart Internal Assistant for changes to take effect."
    )


def show_current_logs(log_dir: str = "local_data/logs") -> None:
    """Show information about current log files."""
    log_path = Path(log_dir)

    if not log_path.exists():
        print(f"Log directory '{log_dir}' does not exist.")
        return

    print(f"\nLog files in '{log_dir}':")
    print("-" * 50)

    total_size = 0
    log_files = []

    for file_path in log_path.glob("*.log*"):
        size = file_path.stat().st_size
        total_size += size
        log_files.append((file_path.name, size))

    if not log_files:
        print("No log files found.")
        return

    # Sort by size (largest first)
    log_files.sort(key=lambda x: x[1], reverse=True)

    for filename, size in log_files:
        size_mb = size / (1024 * 1024)
        print(f"{filename:<30} {size_mb:>8.2f} MB")

    total_mb = total_size / (1024 * 1024)
    print("-" * 50)
    print(f"Total log files: {len(log_files)}")
    print(f"Total size: {total_mb:.2f} MB")


def cleanup_logs(
    log_dir: str = "local_data/logs", keep_days: Optional[int] = None
) -> None:
    """Clean up old log files."""
    log_path = Path(log_dir)

    if not log_path.exists():
        print(f"Log directory '{log_dir}' does not exist.")
        return

    import time

    current_time = time.time()

    removed_count = 0
    removed_size = 0

    for file_path in log_path.glob("*.log*"):
        if keep_days is not None:
            # Check file age
            file_age_days = (current_time - file_path.stat().st_mtime) / (24 * 3600)
            if file_age_days <= keep_days:
                continue

        size = file_path.stat().st_size
        try:
            file_path.unlink()
            removed_count += 1
            removed_size += size
            print(f"Removed: {file_path.name}")
        except Exception as e:
            print(f"Failed to remove {file_path.name}: {e}")

    if removed_count > 0:
        removed_mb = removed_size / (1024 * 1024)
        print(
            f"\nCleanup complete: {removed_count} files removed, {removed_mb:.2f} MB freed"
        )
    else:
        print("No files to remove.")


def show_log_tail(
    log_file: str = "local_data/logs/internal_assistant.log", lines: int = 20
) -> None:
    """Show the last few lines of a log file."""
    log_path = Path(log_file)

    if not log_path.exists():
        print(f"Log file '{log_file}' does not exist.")
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            print(f"\nLast {len(last_lines)} lines of {log_file}:")
            print("-" * 80)
            for line in last_lines:
                print(line.rstrip())
    except Exception as e:
        print(f"Error reading log file: {e}")


def main():
    parser = argparse.ArgumentParser(description="Internal Assistant Logging Control")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Set log level command
    set_parser = subparsers.add_parser("set-level", help="Set logging level")
    set_parser.add_argument(
        "level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        help="Log level to set",
    )

    # Show logs command
    show_parser = subparsers.add_parser("show", help="Show current log files")
    show_parser.add_argument(
        "--dir",
        default="local_data/logs",
        help="Log directory (default: local_data/logs)",
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old log files")
    cleanup_parser.add_argument(
        "--dir",
        default="local_data/logs",
        help="Log directory (default: local_data/logs)",
    )
    cleanup_parser.add_argument(
        "--keep-days", type=int, help="Keep files newer than N days"
    )
    cleanup_parser.add_argument(
        "--all", action="store_true", help="Remove all log files"
    )

    # Tail command
    tail_parser = subparsers.add_parser("tail", help="Show last lines of log file")
    tail_parser.add_argument(
        "--file",
        default="local_data/logs/internal_assistant.log",
        help="Log file to show",
    )
    tail_parser.add_argument(
        "--lines", type=int, default=20, help="Number of lines to show"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "set-level":
        set_log_level(args.level)
    elif args.command == "show":
        show_current_logs(args.dir)
    elif args.command == "cleanup":
        if args.all:
            cleanup_logs(args.dir)
        else:
            cleanup_logs(args.dir, args.keep_days)
    elif args.command == "tail":
        show_log_tail(args.file, args.lines)


if __name__ == "__main__":
    main()

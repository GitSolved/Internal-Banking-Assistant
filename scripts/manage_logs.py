#!/usr/bin/env python3
"""
Log Management Utility for Internal Assistant

This unified script manages log files with multiple cleanup strategies:
- Interactive mode: Manual cleanup with user confirmation
- Automatic mode: Scheduled/startup cleanup with multiple criteria
- Display mode: Show log file information and status

Replaces: cleanup_recent_logs.py + auto_cleanup_logs.py
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Default settings
DEFAULT_LOG_DIR = "Logs"
DEFAULT_KEEP_SESSIONS = 7   # Keep last 7 session logs
DEFAULT_KEEP_DAYS = 7       # Keep logs for 7 days
DEFAULT_MAX_SIZE_MB = 100   # Max total log size in MB


def get_log_files(log_dir: str = DEFAULT_LOG_DIR) -> List[Tuple[Path, float, str, int]]:
    """Get all log files with their modification times, types, and sizes."""
    log_path = Path(log_dir)
    
    if not log_path.exists():
        print(f"Log directory '{log_dir}' does not exist.")
        return []
    
    log_files = []
    for file_path in log_path.glob("*.log*"):
        try:
            mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size
            
            # Determine log type
            if file_path.name == "pytest.log":
                log_type = "pytest"
            elif file_path.name.startswith("SessionLog"):
                log_type = "session"
            else:
                log_type = "other"
            
            log_files.append((file_path, mtime, log_type, size))
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")
    
    return log_files


def show_log_status(log_dir: str = DEFAULT_LOG_DIR) -> None:
    """Display current log file status and information."""
    print(f"\nLog Status for '{log_dir}':")
    print("-" * 50)
    
    log_files = get_log_files(log_dir)
    
    if not log_files:
        print("No log files found.")
        return
    
    # Group by type
    by_type = {"session": [], "pytest": [], "other": []}
    total_size = 0
    
    for file_path, mtime, log_type, size in log_files:
        by_type[log_type].append((file_path, mtime, size))
        total_size += size
    
    # Sort each type by modification time (newest first)
    for log_type in by_type:
        by_type[log_type].sort(key=lambda x: x[1], reverse=True)
    
    print(f"Total files: {len(log_files)}")
    print(f"Total size: {total_size / (1024 * 1024):.2f} MB")
    print()
    
    # Show breakdown by type
    for log_type, files in by_type.items():
        if not files:
            continue
            
        type_size = sum(size for _, _, size in files)
        print(f"{log_type.capitalize()} logs: {len(files)} files, {type_size / (1024 * 1024):.2f} MB")
        
        for file_path, mtime, size in files[:5]:  # Show first 5
            age_hours = (time.time() - mtime) / 3600
            size_mb = size / (1024 * 1024)
            print(f"  • {file_path.name} - {size_mb:.2f} MB ({age_hours:.1f}h old)")
        
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
        print()


def cleanup_by_session_count(log_files: List[Tuple[Path, float, str, int]], keep_count: int, dry_run: bool = False) -> int:
    """Keep only the most recent N session logs."""
    session_logs = [(f, m, t, s) for f, m, t, s in log_files if t == "session"]
    
    if len(session_logs) <= keep_count:
        return 0
    
    # Sort by modification time (newest first)
    session_logs.sort(key=lambda x: x[1], reverse=True)
    
    # Files to remove
    files_to_remove = session_logs[keep_count:]
    
    if dry_run:
        print(f"Would remove {len(files_to_remove)} old session logs:")
        for file_path, mtime, log_type, size in files_to_remove:
            print(f"  - {file_path.name}")
        return len(files_to_remove)
    
    removed_count = 0
    for file_path, mtime, log_type, size in files_to_remove:
        try:
            file_path.unlink()
            removed_count += 1
            print(f"Removed old session log: {file_path.name}")
        except Exception as e:
            print(f"Failed to remove {file_path.name}: {e}")
    
    return removed_count


def cleanup_by_age(log_files: List[Tuple[Path, float, str, int]], keep_days: int, dry_run: bool = False) -> int:
    """Remove log files older than N days."""
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 3600)
    
    old_files = [(f, m, t, s) for f, m, t, s in log_files if m < cutoff_time]
    
    if dry_run:
        print(f"Would remove {len(old_files)} files older than {keep_days} days:")
        for file_path, mtime, log_type, size in old_files:
            age_days = (current_time - mtime) / (24 * 3600)
            print(f"  - {file_path.name} ({age_days:.1f} days old)")
        return len(old_files)
    
    removed_count = 0
    for file_path, mtime, log_type, size in old_files:
        try:
            file_path.unlink()
            removed_count += 1
            age_days = (current_time - mtime) / (24 * 3600)
            print(f"Removed old log: {file_path.name} ({age_days:.1f} days old)")
        except Exception as e:
            print(f"Failed to remove {file_path.name}: {e}")
    
    return removed_count


def cleanup_by_size(log_files: List[Tuple[Path, float, str, int]], max_size_mb: int, dry_run: bool = False) -> int:
    """Remove oldest logs if total size exceeds limit."""
    total_size_mb = sum(size for _, _, _, size in log_files) / (1024 * 1024)
    
    if total_size_mb <= max_size_mb:
        return 0
    
    # Sort by modification time (oldest first)
    sorted_files = sorted(log_files, key=lambda x: x[1])
    
    files_to_remove = []
    current_size_mb = total_size_mb
    
    for file_path, mtime, log_type, size in sorted_files:
        if current_size_mb <= max_size_mb:
            break
        
        files_to_remove.append((file_path, mtime, log_type, size))
        current_size_mb -= size / (1024 * 1024)
    
    if dry_run:
        total_remove_mb = sum(size for _, _, _, size in files_to_remove) / (1024 * 1024)
        print(f"Would remove {len(files_to_remove)} files ({total_remove_mb:.2f} MB) to meet size limit:")
        for file_path, mtime, log_type, size in files_to_remove:
            print(f"  - {file_path.name} ({size / (1024 * 1024):.2f} MB)")
        return len(files_to_remove)
    
    removed_count = 0
    for file_path, mtime, log_type, size in files_to_remove:
        file_size_mb = size / (1024 * 1024)
        try:
            file_path.unlink()
            removed_count += 1
            print(f"Removed for size limit: {file_path.name} ({file_size_mb:.2f} MB)")
        except Exception as e:
            print(f"Failed to remove {file_path.name}: {e}")
    
    return removed_count


def interactive_cleanup(log_dir: str = DEFAULT_LOG_DIR, keep_count: int = 7) -> None:
    """Interactive cleanup mode with user confirmation."""
    print(f"Interactive cleanup for log directory: {log_dir}")
    
    log_files = get_log_files(log_dir)
    
    if not log_files:
        print("No log files found.")
        return
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Found {len(log_files)} log files")
    print(f"Will keep the {min(keep_count, len(log_files))} most recent files")
    
    # Separate files to keep and remove
    files_to_keep = log_files[:keep_count]
    files_to_remove = log_files[keep_count:]
    
    if not files_to_remove:
        print("No files to remove.")
        return
    
    # Show what will be kept
    print("\\nKeeping these files:")
    for file_path, mtime, log_type, size in files_to_keep:
        size_mb = size / (1024 * 1024)
        age_hours = (time.time() - mtime) / 3600
        print(f"  ✓ {file_path.name} ({size_mb:.2f} MB, {age_hours:.1f}h old)")
    
    # Show what will be removed
    total_remove_size = sum(size for _, _, _, size in files_to_remove)
    total_remove_mb = total_remove_size / (1024 * 1024)
    
    print(f"\\nWould remove {len(files_to_remove)} older files ({total_remove_mb:.2f} MB):")
    for file_path, mtime, log_type, size in files_to_remove:
        size_mb = size / (1024 * 1024)
        age_hours = (time.time() - mtime) / 3600
        print(f"  - {file_path.name} ({size_mb:.2f} MB, {age_hours:.1f}h old)")
    
    # Confirm with user
    print(f"\\nWARNING: This will permanently delete {len(files_to_remove)} files and free {total_remove_mb:.2f} MB")
    response = input("Continue? [y/N]: ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("Cleanup cancelled.")
        return
    
    # Perform removal
    removed_count = 0
    removed_size = 0
    
    for file_path, mtime, log_type, size in files_to_remove:
        try:
            file_path.unlink()
            removed_count += 1
            removed_size += size
            print(f"  ✓ Removed {file_path.name}")
        except Exception as e:
            print(f"  ✗ Failed to remove {file_path.name}: {e}")
    
    if removed_count > 0:
        removed_mb = removed_size / (1024 * 1024)
        print(f"\\nCleanup complete: {removed_count} files removed, {removed_mb:.2f} MB freed")


def auto_cleanup_logs(
    log_dir: str = DEFAULT_LOG_DIR,
    keep_sessions: int = DEFAULT_KEEP_SESSIONS,
    keep_days: int = DEFAULT_KEEP_DAYS,
    max_size_mb: int = DEFAULT_MAX_SIZE_MB,
    dry_run: bool = False
) -> None:
    """Automatically clean up logs based on multiple criteria."""
    print(f"Auto-cleanup for log directory: {log_dir}")
    
    if dry_run:
        print("DRY RUN - No files will be removed")
    
    log_files = get_log_files(log_dir)
    
    if not log_files:
        print("No log files found.")
        return
    
    total_files = len(log_files)
    total_size_mb = sum(size for _, _, _, size in log_files) / (1024 * 1024)
    
    print(f"Found {total_files} log files ({total_size_mb:.2f} MB total)")
    print(f"Cleanup criteria: {keep_sessions} sessions, {keep_days} days, {max_size_mb} MB limit")
    
    if dry_run:
        print("\\nDry run - would perform the following cleanup:")
        removed_sessions = cleanup_by_session_count(log_files, keep_sessions, dry_run=True)
        removed_age = cleanup_by_age(log_files, keep_days, dry_run=True)
        removed_size = cleanup_by_size(log_files, max_size_mb, dry_run=True)
        
        total_would_remove = removed_sessions + removed_age + removed_size
        print(f"\\nTotal files that would be removed: {total_would_remove}")
        return
    
    # Perform actual cleanup
    print("\\nPerforming cleanup...")
    removed_sessions = cleanup_by_session_count(log_files, keep_sessions)
    
    # Refresh file list after session cleanup
    log_files = get_log_files(log_dir)
    removed_age = cleanup_by_age(log_files, keep_days)
    
    # Refresh file list after age cleanup
    log_files = get_log_files(log_dir)
    removed_size = cleanup_by_size(log_files, max_size_mb)
    
    total_removed = removed_sessions + removed_age + removed_size
    
    if total_removed > 0:
        print(f"\\nCleanup complete: {total_removed} files removed")
        
        # Show final status
        remaining_files = get_log_files(log_dir)
        remaining_size_mb = sum(size for _, _, _, size in remaining_files) / (1024 * 1024)
        print(f"Remaining: {len(remaining_files)} files ({remaining_size_mb:.2f} MB)")
    else:
        print("\\nNo cleanup needed")


def main():
    parser = argparse.ArgumentParser(
        description="Manage log files with multiple cleanup strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current log status
  python manage_logs.py --status
  
  # Interactive cleanup (keep 5 most recent)
  python manage_logs.py --interactive --keep-count 5
  
  # Automatic cleanup with default settings
  python manage_logs.py --auto
  
  # Dry run to see what would be removed
  python manage_logs.py --auto --dry-run
  
  # Custom automatic cleanup
  python manage_logs.py --auto --keep-sessions 10 --keep-days 14 --max-size 200
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--status', action='store_true', 
                           help='Show log file status and information')
    mode_group.add_argument('--interactive', action='store_true',
                           help='Interactive cleanup with user confirmation')
    mode_group.add_argument('--auto', action='store_true',
                           help='Automatic cleanup using multiple criteria')
    
    # Common options
    parser.add_argument('--log-dir', default=DEFAULT_LOG_DIR, 
                       help=f'Log directory (default: {DEFAULT_LOG_DIR})')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without removing files')
    
    # Interactive mode options
    parser.add_argument('--keep-count', type=int, default=7,
                       help='Number of recent files to keep in interactive mode (default: 7)')
    
    # Auto mode options
    parser.add_argument('--keep-sessions', type=int, default=DEFAULT_KEEP_SESSIONS, 
                       help=f'Number of recent session logs to keep (default: {DEFAULT_KEEP_SESSIONS})')
    parser.add_argument('--keep-days', type=int, default=DEFAULT_KEEP_DAYS,
                       help=f'Keep logs newer than N days (default: {DEFAULT_KEEP_DAYS})')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE_MB,
                       help=f'Maximum total log size in MB (default: {DEFAULT_MAX_SIZE_MB})')
    
    args = parser.parse_args()
    
    # Validation
    if args.keep_count < 1:
        print("Error: keep-count must be at least 1")
        sys.exit(1)
    
    if args.keep_sessions < 1:
        print("Error: keep-sessions must be at least 1")
        sys.exit(1)
    
    if args.keep_days < 1:
        print("Error: keep-days must be at least 1")
        sys.exit(1)
    
    if args.max_size < 1:
        print("Error: max-size must be at least 1 MB")
        sys.exit(1)
    
    # Execute based on mode
    if args.status:
        show_log_status(args.log_dir)
    
    elif args.interactive:
        if args.dry_run:
            print("Dry run mode not applicable for interactive cleanup")
            sys.exit(1)
        interactive_cleanup(args.log_dir, args.keep_count)
    
    elif args.auto:
        auto_cleanup_logs(
            log_dir=args.log_dir,
            keep_sessions=args.keep_sessions,
            keep_days=args.keep_days,
            max_size_mb=args.max_size,
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    main()
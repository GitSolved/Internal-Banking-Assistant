#!/usr/bin/env python3
"""
Model Analysis and Cleanup Utility for Internal Assistant

This script analyzes model files and identifies duplicates for cleanup.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def get_file_info(file_path: Path) -> Tuple[int, str]:
    """Get file size and hash."""
    try:
        size = file_path.stat().st_size
        file_hash = calculate_file_hash(file_path)
        return size, file_hash
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, ""

def analyze_models_directory(models_dir: str = "models") -> Dict[str, List[Path]]:
    """Analyze models directory for duplicate files."""
    models_path = Path(models_dir)
    
    if not models_path.exists():
        print(f"Models directory '{models_dir}' does not exist.")
        return {}
    
    print(f"🔍 Analyzing models directory: {models_path}")
    print("=" * 60)
    
    # Find all files
    all_files = []
    for file_path in models_path.rglob("*"):
        if file_path.is_file():
            all_files.append(file_path)
    
    print(f"Found {len(all_files)} files")
    
    # Group files by hash
    hash_groups: Dict[str, List[Path]] = {}
    total_size = 0
    
    for file_path in all_files:
        size, file_hash = get_file_info(file_path)
        if file_hash:
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(file_path)
            total_size += size
    
    # Analyze duplicates
    duplicates_found = 0
    space_wasted = 0
    
    print(f"\n📊 Analysis Results:")
    print("=" * 60)
    
    for file_hash, files in hash_groups.items():
        if len(files) > 1:
            duplicates_found += len(files) - 1
            file_size = files[0].stat().st_size
            space_wasted += file_size * (len(files) - 1)
            
            print(f"\n🔴 Duplicate Group (Hash: {file_hash[:8]}...)")
            print(f"   File size: {file_size / (1024*1024):.2f} MB")
            print(f"   Copies: {len(files)}")
            print(f"   Space wasted: {file_size * (len(files) - 1) / (1024*1024):.2f} MB")
            
            for i, file_path in enumerate(files):
                rel_path = file_path.relative_to(models_path)
                print(f"   {i+1}. {rel_path}")
    
    # Summary
    print(f"\n📈 Summary:")
    print("=" * 60)
    print(f"Total files: {len(all_files)}")
    print(f"Unique files: {len([g for g in hash_groups.values() if len(g) == 1])}")
    print(f"Duplicate groups: {len([g for g in hash_groups.values() if len(g) > 1])}")
    print(f"Duplicate files: {duplicates_found}")
    print(f"Total size: {total_size / (1024*1024*1024):.2f} GB")
    print(f"Space wasted: {space_wasted / (1024*1024*1024):.2f} GB")
    
    return hash_groups

def cleanup_duplicates(hash_groups: Dict[str, List[Path]], dry_run: bool = True) -> None:
    """Clean up duplicate files, keeping the first one in each group."""
    if dry_run:
        print(f"\n🔍 DRY RUN - No files will be removed")
    else:
        print(f"\n🧹 CLEANING UP DUPLICATES")
    
    print("=" * 60)
    
    total_removed = 0
    total_space_freed = 0
    
    for file_hash, files in hash_groups.items():
        if len(files) > 1:
            # Keep the first file, remove the rest
            keep_file = files[0]
            remove_files = files[1:]
            
            file_size = keep_file.stat().st_size
            space_to_free = file_size * len(remove_files)
            
            print(f"\n📁 Group: {file_hash[:8]}...")
            print(f"   Keeping: {keep_file.name}")
            print(f"   Removing {len(remove_files)} duplicates")
            print(f"   Space to free: {space_to_free / (1024*1024):.2f} MB")
            
            if not dry_run:
                for file_path in remove_files:
                    try:
                        file_path.unlink()
                        total_removed += 1
                        total_space_freed += file_size
                        print(f"   ✓ Removed: {file_path.name}")
                    except Exception as e:
                        print(f"   ❌ Failed to remove {file_path.name}: {e}")
            else:
                for file_path in remove_files:
                    print(f"   - Would remove: {file_path.name}")
    
    if dry_run:
        print(f"\n📊 DRY RUN SUMMARY:")
        print(f"Files that would be removed: {total_removed}")
        print(f"Space that would be freed: {total_space_freed / (1024*1024*1024):.2f} GB")
    else:
        print(f"\n✅ CLEANUP COMPLETE:")
        print(f"Files removed: {total_removed}")
        print(f"Space freed: {total_space_freed / (1024*1024*1024):.2f} GB")

def main():
    parser = argparse.ArgumentParser(description="Analyze and clean up model files")
    parser.add_argument('--models-dir', default='models', help='Models directory (default: models)')
    parser.add_argument('--cleanup', action='store_true', help='Actually remove duplicate files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without removing files')
    
    args = parser.parse_args()
    
    # Analyze models directory
    hash_groups = analyze_models_directory(args.models_dir)
    
    if not hash_groups:
        return
    
    # Check if there are duplicates
    duplicates = [g for g in hash_groups.values() if len(g) > 1]
    if not duplicates:
        print("\n✅ No duplicates found!")
        return
    
    # Offer cleanup
    if args.cleanup or args.dry_run:
        cleanup_duplicates(hash_groups, dry_run=args.dry_run)
    else:
        print(f"\n💡 To clean up duplicates, run:")
        print(f"   python scripts/analyze_models.py --dry-run")
        print(f"   python scripts/analyze_models.py --cleanup")

if __name__ == "__main__":
    main()

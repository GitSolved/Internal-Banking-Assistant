#!/usr/bin/env python3
"""
Direct Storage Cleanup Tool

This tool directly modifies storage files to fix inconsistent states
without requiring access to the running application or Qdrant.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def backup_storage_files():
    """Create backup of storage files before cleanup."""
    base_path = Path("local_data/internal_assistant")
    backup_path = Path("local_data/backup_before_cleanup")

    if backup_path.exists():
        shutil.rmtree(backup_path)

    backup_path.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        "docstore.json",
        "index_store.json",
        "graph_store.json",
        "image__vector_store.json"
    ]

    backed_up = []
    for file_name in files_to_backup:
        source = base_path / file_name
        if source.exists():
            dest = backup_path / file_name
            shutil.copy2(source, dest)
            backed_up.append(file_name)
            print(f"[BACKUP] Backed up {file_name}")

    print(f"[BACKUP] Created backup at: {backup_path}")
    return backup_path, backed_up

def clean_docstore():
    """Clean the document store of orphaned metadata."""
    docstore_path = Path("local_data/internal_assistant/docstore.json")

    if not docstore_path.exists():
        print("[CLEAN] No docstore.json found")
        return 0

    with open(docstore_path, 'r') as f:
        docstore_data = json.load(f)

    # Check current state
    data_count = len(docstore_data.get("docstore/data", {}))
    metadata_count = len(docstore_data.get("docstore/metadata", {}))
    ref_doc_count = len(docstore_data.get("docstore/ref_doc_info", {}))

    print(f"[CLEAN] Current docstore state:")
    print(f"  - Document data: {data_count}")
    print(f"  - Metadata entries: {metadata_count}")
    print(f"  - Ref doc info: {ref_doc_count}")

    # Clean everything - start fresh
    cleaned_data = {
        "docstore/data": {},
        "docstore/metadata": {},
        "docstore/ref_doc_info": {}
    }

    with open(docstore_path, 'w') as f:
        json.dump(cleaned_data, f, indent=2)

    print(f"[CLEAN] Cleaned docstore.json - removed {metadata_count} orphaned metadata entries")
    return metadata_count

def clean_index_store():
    """Clean the index store of orphaned references."""
    index_store_path = Path("local_data/internal_assistant/index_store.json")

    if not index_store_path.exists():
        print("[CLEAN] No index_store.json found")
        return 0

    with open(index_store_path, 'r') as f:
        index_data = json.load(f)

    # Count current entries
    index_entries = len(index_data.get("index_store/data", {}))

    print(f"[CLEAN] Current index store state:")
    print(f"  - Index entries: {index_entries}")

    # Clean everything
    cleaned_data = {
        "index_store/data": {}
    }

    with open(index_store_path, 'w') as f:
        json.dump(cleaned_data, f, indent=2)

    print(f"[CLEAN] Cleaned index_store.json - removed {index_entries} orphaned index entries")
    return index_entries

def clean_qdrant_if_accessible():
    """Try to clean Qdrant data if possible."""
    qdrant_path = Path("local_data/internal_assistant/qdrant")

    if not qdrant_path.exists():
        print("[CLEAN] No Qdrant directory found")
        return 0

    # Check if there's a lock file
    lock_file = qdrant_path / ".lock"
    if lock_file.exists():
        print("[CLEAN] Qdrant is locked by another process - skipping Qdrant cleanup")
        print("[CLEAN] Collection will be automatically recreated when application starts")
        return 0

    # If no lock, we can safely clean
    try:
        # Remove the entire qdrant directory
        shutil.rmtree(qdrant_path)
        print("[CLEAN] Removed Qdrant directory - will be recreated on startup")
        return 1
    except Exception as e:
        print(f"[CLEAN] Could not remove Qdrant directory: {e}")
        return 0

def verify_cleanup():
    """Verify that cleanup was successful."""
    print("\n[VERIFY] Verifying cleanup results...")

    # Check docstore
    docstore_path = Path("local_data/internal_assistant/docstore.json")
    if docstore_path.exists():
        with open(docstore_path, 'r') as f:
            docstore_data = json.load(f)

        data_count = len(docstore_data.get("docstore/data", {}))
        metadata_count = len(docstore_data.get("docstore/metadata", {}))

        if data_count == 0 and metadata_count == 0:
            print("[VERIFY] [OK] Docstore is clean")
        else:
            print(f"[VERIFY] [WARN] Docstore still has {data_count} data, {metadata_count} metadata")

    # Check index store
    index_store_path = Path("local_data/internal_assistant/index_store.json")
    if index_store_path.exists():
        with open(index_store_path, 'r') as f:
            index_data = json.load(f)

        index_entries = len(index_data.get("index_store/data", {}))

        if index_entries == 0:
            print("[VERIFY] [OK] Index store is clean")
        else:
            print(f"[VERIFY] [WARN] Index store still has {index_entries} entries")

    # Check Qdrant
    qdrant_path = Path("local_data/internal_assistant/qdrant")
    if not qdrant_path.exists():
        print("[VERIFY] [OK] Qdrant directory cleaned")
    else:
        print("[VERIFY] [INFO] Qdrant directory exists (may be locked by running application)")

def main():
    parser = argparse.ArgumentParser(
        description="Direct storage cleanup tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool directly cleans storage files without requiring access to the running application.
It's designed to fix inconsistent states where metadata exists but document content is missing.

IMPORTANT: Stop the main application before running this tool for best results.

Examples:
  # Clean all storage with backup
  python direct_cleanup.py clean --backup

  # Clean without backup (fast)
  python direct_cleanup.py clean

  # Show current state without cleaning
  python direct_cleanup.py status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean all storage files')
    clean_parser.add_argument('--backup', action='store_true', help='Create backup before cleaning')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show current storage status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'status':
        # Show current status
        print("[STATUS] Current storage status:")

        docstore_path = Path("local_data/internal_assistant/docstore.json")
        if docstore_path.exists():
            with open(docstore_path, 'r') as f:
                docstore_data = json.load(f)

            data_count = len(docstore_data.get("docstore/data", {}))
            metadata_count = len(docstore_data.get("docstore/metadata", {}))
            print(f"  Docstore - Data: {data_count}, Metadata: {metadata_count}")
        else:
            print("  Docstore: Not found")

        index_store_path = Path("local_data/internal_assistant/index_store.json")
        if index_store_path.exists():
            with open(index_store_path, 'r') as f:
                index_data = json.load(f)

            index_entries = len(index_data.get("index_store/data", {}))
            print(f"  Index store - Entries: {index_entries}")
        else:
            print("  Index store: Not found")

        qdrant_path = Path("local_data/internal_assistant/qdrant")
        if qdrant_path.exists():
            print(f"  Qdrant: Directory exists")
            lock_file = qdrant_path / ".lock"
            if lock_file.exists():
                print("  Qdrant: LOCKED (application running)")
            else:
                print("  Qdrant: Unlocked")
        else:
            print("  Qdrant: Not found")

        return

    elif args.command == 'clean':
        print("[CLEANUP] Starting direct storage cleanup...")

        # Create backup if requested
        if args.backup:
            backup_path, backed_up = backup_storage_files()
            print(f"[CLEANUP] Backup created with {len(backed_up)} files")

        # Clean each storage component
        docstore_cleaned = clean_docstore()
        index_cleaned = clean_index_store()
        qdrant_cleaned = clean_qdrant_if_accessible()

        # Verify results
        verify_cleanup()

        # Summary
        total_cleaned = docstore_cleaned + index_cleaned + qdrant_cleaned
        print(f"\n[SUMMARY] Cleanup completed:")
        print(f"  - Docstore metadata removed: {docstore_cleaned}")
        print(f"  - Index entries removed: {index_cleaned}")
        print(f"  - Qdrant cleaned: {'Yes' if qdrant_cleaned else 'No/Locked'}")
        print(f"  - Total items cleaned: {total_cleaned}")

        print(f"\n[NEXT STEPS]:")
        print(f"  1. Restart the application")
        print(f"  2. The system will automatically:")
        print(f"     - Recreate missing Qdrant collection")
        print(f"     - Initialize clean storage backends")
        print(f"     - Remove any remaining orphaned UI references")
        print(f"  3. Upload documents fresh - they will be properly indexed")

        if args.backup:
            print(f"\n[RESTORE] If needed, restore from backup:")
            print(f"  Backup location: {backup_path}")

if __name__ == "__main__":
    main()
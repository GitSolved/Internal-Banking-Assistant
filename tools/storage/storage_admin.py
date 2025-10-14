#!/usr/bin/env python3
"""
Storage Administration Tool for Internal Assistant

Provides administrative access to storage recovery and management functions.
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    # Attempt to set console to UTF-8 mode
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass  # Ignore if this fails

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from internal_assistant.di import create_application_injector
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.ingest.storage_management_service import StorageManagementService
from internal_assistant.server.ingest.storage_consistency_service import StorageConsistencyService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_services():
    """Initialize and return required services."""
    injector = create_application_injector()
    ingest_service = injector.get(IngestService)

    management_service = StorageManagementService(
        ingest_service.storage_context,
        ingest_service
    )

    consistency_service = StorageConsistencyService(ingest_service.storage_context)

    return ingest_service, management_service, consistency_service


def cmd_diagnose(args):
    """Run comprehensive storage diagnosis."""
    print("[DIAGNOSE] Running comprehensive storage diagnosis...")

    _, management_service, _ = get_services()
    diagnosis = management_service.diagnose_storage_health()

    print(f"\n[REPORT] Storage Health Report")
    print("=" * 50)
    print(f"Overall Health: {diagnosis['overall_health'].upper()}")
    print(f"Timestamp: {diagnosis['timestamp']}")

    print(f"\n[COMPONENTS] Component Status:")
    for component, status in diagnosis['components'].items():
        health_icon = "[OK]" if status.get('status') == 'healthy' else "[WARN]" if status.get('status') == 'degraded' else "[ERROR]"
        print(f"  {health_icon} {component}: {status.get('status', 'unknown')}")
        if status.get('error'):
            print(f"    Error: {status['error']}")

    if diagnosis['consistency_report']:
        consistency = diagnosis['consistency_report']
        print(f"\n[CONSISTENCY] Consistency Report:")
        print(f"  Total Documents: {consistency.get('total_documents', 'unknown')}")
        print(f"  Total Vectors: {consistency.get('total_vectors', 'unknown')}")
        print(f"  Healthy Documents: {consistency.get('healthy_documents', 'unknown')}")
        print(f"  Issues Found: {consistency.get('issues_count', 'unknown')}")

        if consistency.get('critical_issues', 0) > 0:
            print(f"  [CRITICAL] Critical Issues: {consistency['critical_issues']}")

    print(f"\n[RECOMMENDATIONS] Recommendations:")
    for rec in diagnosis['recommendations']:
        print(f"  - {rec}")

    return diagnosis['overall_health'] != 'critical'


def cmd_check_consistency(args):
    """Check storage consistency."""
    print("[CONSISTENCY] Checking storage consistency...")

    _, _, consistency_service = get_services()
    report = consistency_service.check_consistency()

    summary = consistency_service.generate_report_summary(report)
    print(f"\n{summary}")

    if args.repair and report.inconsistencies:
        print(f"\n[REPAIR] Auto-repairing inconsistencies...")
        repair_stats = consistency_service.repair_inconsistencies(report, auto_repair=True)
        print(f"Repair Results: {repair_stats}")

    return len(report.critical_issues) == 0


def cmd_emergency_clear(args):
    """Emergency clear all documents."""
    if not args.force:
        print("[ERROR] Emergency clear requires --force flag for safety")
        return False

    print("[EMERGENCY] Clearing all documents from storage...")
    print("[WARNING] This action cannot be undone!")

    if not args.yes:
        response = input("Are you sure? Type 'CLEAR ALL' to confirm: ")
        if response != "CLEAR ALL":
            print("Operation cancelled.")
            return False

    _, management_service, _ = get_services()
    results = management_service.emergency_clear_all_documents(force=True)

    print(f"\n[RESULTS] Clearance Results:")
    print(f"  Documents cleared from docstore: {results.get('docstore', 0)}")
    print(f"  Vectors cleared from vector store: {results.get('vector_store', 0)}")
    print(f"  Metadata cleared from index store: {results.get('index_store', 0)}")
    print(f"  Errors encountered: {results.get('errors', 0)}")

    return results.get('errors', 0) == 0


def cmd_recreate_collection(args):
    """Force recreate the Qdrant collection."""
    print("[RECREATE] Force recreating Qdrant collection...")

    if not args.force:
        print("[ERROR] Collection recreation requires --force flag for safety")
        return False

    _, management_service, _ = get_services()
    success = management_service.force_recreate_collection()

    if success:
        print("[SUCCESS] Collection successfully recreated")
    else:
        print("[ERROR] Collection recreation failed")

    return success


def cmd_backup(args):
    """Create storage backup."""
    print("[BACKUP] Creating storage backup...")

    _, management_service, _ = get_services()
    backup_path = management_service.backup_storage_state(args.name)

    print(f"[SUCCESS] Backup created at: {backup_path}")
    return True


def cmd_restore(args):
    """Restore from storage backup."""
    backup_path = Path(args.backup_path)

    if not backup_path.exists():
        print(f"[ERROR] Backup path does not exist: {backup_path}")
        return False

    if not args.force:
        print("[ERROR] Restore requires --force flag for safety")
        return False

    print(f"[RESTORE] Restoring storage from backup: {backup_path}")
    print("[WARNING] This will overwrite current storage!")

    if not args.yes:
        response = input("Are you sure? Type 'RESTORE' to confirm: ")
        if response != "RESTORE":
            print("Operation cancelled.")
            return False

    _, management_service, _ = get_services()
    success = management_service.restore_storage_state(backup_path, force=True)

    if success:
        print("[SUCCESS] Storage successfully restored")
    else:
        print("[ERROR] Storage restoration failed")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Storage Administration Tool for Internal Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Diagnose storage health
  python storage_admin.py diagnose

  # Check consistency and auto-repair
  python storage_admin.py check-consistency --repair

  # Emergency clear all documents (dangerous!)
  python storage_admin.py emergency-clear --force --yes

  # Recreate missing collection
  python storage_admin.py recreate-collection --force

  # Create backup
  python storage_admin.py backup --name emergency_backup

  # Restore from backup (dangerous!)
  python storage_admin.py restore /path/to/backup --force --yes
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Run comprehensive storage diagnosis')

    # Check consistency command
    consistency_parser = subparsers.add_parser('check-consistency', help='Check storage consistency')
    consistency_parser.add_argument('--repair', action='store_true', help='Auto-repair found issues')

    # Emergency clear command
    clear_parser = subparsers.add_parser('emergency-clear', help='Emergency clear all documents')
    clear_parser.add_argument('--force', action='store_true', help='Force operation (required)')
    clear_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    # Recreate collection command
    recreate_parser = subparsers.add_parser('recreate-collection', help='Force recreate Qdrant collection')
    recreate_parser.add_argument('--force', action='store_true', help='Force operation (required)')

    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create storage backup')
    backup_parser.add_argument('--name', help='Backup name (default: auto-generated)')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_path', help='Path to backup directory')
    restore_parser.add_argument('--force', action='store_true', help='Force operation (required)')
    restore_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Execute command
        if args.command == 'diagnose':
            success = cmd_diagnose(args)
        elif args.command == 'check-consistency':
            success = cmd_check_consistency(args)
        elif args.command == 'emergency-clear':
            success = cmd_emergency_clear(args)
        elif args.command == 'recreate-collection':
            success = cmd_recreate_collection(args)
        elif args.command == 'backup':
            success = cmd_backup(args)
        elif args.command == 'restore':
            success = cmd_restore(args)
        else:
            print(f"Unknown command: {args.command}")
            success = False

        if success:
            print("\n[SUCCESS] Operation completed successfully")
            sys.exit(0)
        else:
            print("\n[ERROR] Operation failed or encountered issues")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
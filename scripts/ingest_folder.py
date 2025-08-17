#!/usr/bin/env python3

import os
import re
import argparse
import logging
import shutil
import json
import time
import gc
from pathlib import Path

from internal_assistant.di import global_injector
from internal_assistant.server.ingest.ingest_service import IngestService
from internal_assistant.server.ingest.ingest_watcher import IngestWatcher
from internal_assistant.settings.settings import Settings

logger = logging.getLogger(__name__)

log_dir = "C:/Users/admin/Projects/internal-assistant/Logs"
pattern = re.compile(r"pgpt_ingestion(\d+)\.log$")
existing_logs = [f for f in os.listdir(log_dir) if pattern.match(f)]
max_num = max([int(pattern.match(f).group(1)) for f in existing_logs], default=0)
new_log = f"pgpt_ingestion{max_num + 1}.log"

class LocalIngestWorker:
    def __init__(self, ingest_service: IngestService, setting: Settings, max_attempts: int = 2, checkpoint_file: str = "ingestion_checkpoint.json") -> None:
        self.ingest_service = ingest_service
        self.total_documents = 0
        self.current_document_count = 0
        self._files_under_root_folder: list[Path] = []
        self.is_local_ingestion_enabled = setting.data.local_ingestion.enabled
        self.allowed_local_folders = setting.data.local_ingestion.allow_ingest_from
        self.max_attempts = max_attempts
        self.checkpoint_file = checkpoint_file

    def _validate_folder(self, folder_path: Path) -> None:
        if not self.is_local_ingestion_enabled:
            raise ValueError(
                "Local ingestion is disabled. You can enable it in settings `ingestion.enabled`"
            )
        if "*" in self.allowed_local_folders:
            return
        for allowed_folder in self.allowed_local_folders:
            if not folder_path.is_relative_to(allowed_folder):
                raise ValueError(f"Folder {folder_path} is not allowed for ingestion")

    def _find_all_files_in_folder(self, root_path: Path, ignored: list[str]) -> None:
        """Search all files under the root folder recursively."""
        for file_path in root_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('~') and file_path.name not in ignored:
                self.total_documents += 1
                self._files_under_root_folder.append(file_path)
            elif file_path.is_dir() and file_path.name not in ignored:
                self._find_all_files_in_folder(file_path, ignored)

    def _quarantine_file(self, file_path: Path) -> None:
        """Move a defective file to a quarantined directory."""
        quarantine_dir = file_path.parent / "quarantined"
        quarantine_dir.mkdir(exist_ok=True)
        try:
            shutil.move(str(file_path), str(quarantine_dir / file_path.name))
            logger.warning(f"Moved defective file to {quarantine_dir / file_path.name}")
        except Exception as e:
            logger.error(f"Failed to move defective file {file_path}: {e}")

    def ingest_folder(self, folder_path: Path, ignored: list[str], resume: bool = True) -> None:
        # Validate folder once before processing
        self._validate_folder(folder_path)
        self._find_all_files_in_folder(folder_path, ignored)
        self._ingest_all(self._files_under_root_folder, resume)

    def _ingest_all(self, files_to_ingest: list[Path], resume: bool = True) -> None:
        logger.info(f"Starting to ingest {len(files_to_ingest)} files")
        logger.info(f"First few files: {[str(f) for f in files_to_ingest[:5]]}")
        
        # Checkpoint file for resume capability
        checkpoint_file = Path(self.checkpoint_file)
        
        if not resume and checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Checkpoint file cleared - starting fresh")
        
        processed_files = self._load_checkpoint(checkpoint_file)
        
        successful = 0
        failed = 0
        permanently_failed = []
        
        # Filter out already processed files
        remaining_files = [f for f in files_to_ingest if str(f) not in processed_files]
        logger.info(f"Resuming: {len(remaining_files)} files remaining (already processed: {len(processed_files)})")
        
        for i, file_path in enumerate(remaining_files, 1):
            success = self._process_file_with_retry(file_path, i, len(remaining_files))
            
            if success:
                successful += 1
                self._save_checkpoint(checkpoint_file, str(file_path))
            else:
                permanently_failed.append(file_path)
                failed += 1
            
            # Progress report every 10 files
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(remaining_files)} processed. Success: {successful}, Failed: {failed}")
                
                # Memory cleanup every 100 files
                if i % 100 == 0:
                    gc.collect()
                    logger.info("Memory cleanup performed")
        
        logger.info(f"Ingestion complete! Total: {len(files_to_ingest)}, Success: {successful}, Failed: {failed}")
        
        if permanently_failed:
            logger.warning(f"Files that failed after {self.max_attempts} attempts: {len(permanently_failed)}")
            for failed_file in permanently_failed:
                logger.warning(f"  - {failed_file}")
        
        # Clean up checkpoint file on successful completion
        if failed == 0 and checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Checkpoint file removed after successful completion")
        
        # Final statistics
        total_processed = len(files_to_ingest)
        success_rate = (successful / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"Final Statistics:")
        logger.info(f"  Total files: {total_processed}")
        logger.info(f"  Already processed: {len(processed_files)}")
        logger.info(f"  Newly processed: {len(remaining_files)}")
        logger.info(f"  Success rate: {success_rate:.1f}%")
        logger.info(f"  Quarantined files: {len(permanently_failed)}")
        
        if permanently_failed:
            logger.info(f"Check the 'quarantined' folders for files that couldn't be processed")

    def _process_file_with_retry(self, file_path: Path, file_num: int, total_files: int) -> bool:
        """Process a file with retry logic. Returns True if successful, False if permanently failed."""
        max_attempts = self.max_attempts
        
        for attempt in range(1, max_attempts + 1):
            try:
                attempt_msg = f" (attempt {attempt}/{max_attempts})" if attempt > 1 else ""
                logger.info(f"[{file_num}/{total_files}] Started ingesting file={file_path}{attempt_msg}")
                
                self.ingest_service.ingest_file(file_path.name, file_path)
                logger.info(f"[{file_num}/{total_files}] ✓ Completed ingesting file={file_path}")
                return True
                
            except Exception as e:
                logger.error(f"[{file_num}/{total_files}] ✗ Attempt {attempt} failed for {file_path}: {e}")
                
                if attempt == max_attempts:
                    logger.error(f"[{file_num}/{total_files}] ✗ PERMANENTLY FAILED after {max_attempts} attempts: {file_path}")
                    self._quarantine_file(file_path)
                    return False
                else:
                    logger.info(f"[{file_num}/{total_files}] Will retry {file_path} in next attempt")
                    # Brief pause before retry
                    time.sleep(1)
        
        return False

    def _load_checkpoint(self, checkpoint_file: Path) -> set:
        """Load processed files from checkpoint."""
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load checkpoint file: {e}")
                return set()
        return set()

    def _save_checkpoint(self, checkpoint_file: Path, processed_file: str) -> None:
        """Save processed file to checkpoint."""
        processed_files = self._load_checkpoint(checkpoint_file)
        processed_files.add(processed_file)
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(list(processed_files), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def ingest_on_watch(self, changed_path: Path) -> None:
        logger.info("Detected change in at path=%s, ingesting", changed_path)
        self._do_ingest_one(changed_path)

    def _do_ingest_one(self, changed_path: Path) -> None:
        try:
            if changed_path.exists():
                logger.info(f"Started ingesting file={changed_path}")
                self.ingest_service.ingest_file(changed_path.name, changed_path)
                logger.info(f"Completed ingesting file={changed_path}")
        except BaseException as e:
            logger.error(f"Failed to ingest document: {changed_path}, with exception: {e}")
            self._quarantine_file(changed_path)

parser = argparse.ArgumentParser(prog="ingest_folder.py")
parser.add_argument("folder", help="Folder to ingest")
parser.add_argument(
    "--watch",
    help="Watch for changes",
    action=argparse.BooleanOptionalAction,
    default=False,
)
parser.add_argument(
    "--ignored",
    nargs="*",
    help="List of files/directories to ignore",
    default=[],
)
parser.add_argument(
    "--log-file",
    help="Optional path to a log file. If provided, logs will be written to this file.",
    type=str,
    default=None,
)
parser.add_argument(
    "--max-attempts",
    help="Maximum number of retry attempts for failed files (default: 2)",
    type=int,
    default=2,
)
parser.add_argument(
    "--resume",
    help="Resume from previous checkpoint if available",
    action="store_true",
    default=True,
)
parser.add_argument(
    "--checkpoint-file",
    help="Custom checkpoint file name (default: ingestion_checkpoint.json)",
    type=str,
    default="ingestion_checkpoint.json",
)

def main():
    """Main function for CLI execution."""
    args = parser.parse_args()

    if args.log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            args.log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2,  # Keep 2 backup files + current = 3 total files
            mode="a"
        )
        file_handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(file_handler)

    root_path = Path(args.folder)
    if not root_path.exists():
        raise ValueError(f"Path {args.folder} does not exist")

    ingest_service = global_injector.get(IngestService)
    settings = global_injector.get(Settings)
    worker = LocalIngestWorker(ingest_service, settings, args.max_attempts, args.checkpoint_file)
    
    # Log configuration information
    logger.info(f"Starting ingestion with configuration:")
    logger.info(f"  Target folder: {root_path}")
    logger.info(f"  Max retry attempts: {args.max_attempts}")
    logger.info(f"  Resume from checkpoint: {args.resume}")
    logger.info(f"  Checkpoint file: {args.checkpoint_file}")
    logger.info(f"  Log file: {args.log_file or 'Console only'}")
    
    if args.ignored:
        logger.info(f"Skipping following files and directories: {args.ignored}")
    
    worker.ingest_folder(root_path, args.ignored, args.resume)

    if args.watch:
        logger.info(f"Watching {args.folder} for changes, press Ctrl+C to stop...")
        watcher = IngestWatcher(args.folder, worker.ingest_on_watch)
        watcher.start()


if __name__ == "__main__":
    main()
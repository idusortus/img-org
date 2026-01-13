"""Safe image deletion with staging and undo capability."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from send2trash import send2trash

from image_organizer.utils.config import Config
from image_organizer.utils.logger import setup_logger

logger = setup_logger(__name__)


class SafeImageDeleter:
    """Manages safe deletion of images with staging and undo support."""

    def __init__(self, config: Config):
        """
        Initialize the safe image deleter.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.staging_dir = config.get_staging_dir()
        self.operations_log = config.get_operations_log()

        # Ensure staging directory exists
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def stage_for_deletion(
        self,
        file_paths: List[Path],
        reason: str = "duplicate",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Stage files for deletion by moving them to staging area.

        Args:
            file_paths: List of file paths to stage
            reason: Reason for deletion (e.g., 'duplicate', 'similar')
            metadata: Optional metadata about the staged files

        Returns:
            Operation ID for undo/tracking

        Raises:
            FileNotFoundError: If any file doesn't exist
            PermissionError: If file cannot be moved
        """
        operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        operation_dir = self.staging_dir / operation_id

        operation_dir.mkdir(parents=True, exist_ok=True)

        staged_files: List[Dict[str, Any]] = []

        logger.info(f"Staging {len(file_paths)} files for deletion")

        for file_path in file_paths:
            if not file_path.exists():
                logger.warning(f"File not found, skipping: {file_path}")
                continue

            # Check if file is in a protected folder
            if self.config.is_path_protected(file_path):
                logger.warning(
                    f"Skipping protected file: {file_path}"
                )
                continue

            try:
                # Move file to staging area (preserving filename)
                staged_path = operation_dir / file_path.name

                # Handle filename conflicts
                counter = 1
                while staged_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    staged_path = operation_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                shutil.move(str(file_path), str(staged_path))

                staged_files.append(
                    {
                        "original_path": str(file_path),
                        "staged_path": str(staged_path),
                        "size": staged_path.stat().st_size,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                logger.debug(f"Staged: {file_path} -> {staged_path}")

            except Exception as e:
                logger.error(f"Failed to stage {file_path}: {e}")
                continue

        # Save operation metadata
        operation_metadata = {
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "files_staged": len(staged_files),
            "files": staged_files,
            "metadata": metadata or {},
            "status": "staged",
        }

        metadata_file = operation_dir / "operation.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(operation_metadata, f, indent=2)

        # Log to operations log
        self._log_operation(operation_metadata)

        logger.info(
            f"Staged {len(staged_files)} files (operation: {operation_id})"
        )

        return operation_id

    def undo_staging(self, operation_id: str) -> bool:
        """
        Undo a staging operation by restoring files to original locations.

        Args:
            operation_id: ID of the operation to undo

        Returns:
            True if successful, False otherwise
        """
        operation_dir = self.staging_dir / operation_id

        if not operation_dir.exists():
            logger.error(f"Operation not found: {operation_id}")
            return False

        metadata_file = operation_dir / "operation.json"
        if not metadata_file.exists():
            logger.error(f"Operation metadata not found: {operation_id}")
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                operation_metadata = json.load(f)

            restored_count = 0
            for file_info in operation_metadata["files"]:
                staged_path = Path(file_info["staged_path"])
                original_path = Path(file_info["original_path"])

                if not staged_path.exists():
                    logger.warning(
                        f"Staged file not found: {staged_path}"
                    )
                    continue

                # Restore file to original location
                original_path.parent.mkdir(parents=True, exist_ok=True)

                # Check if original location is now occupied
                if original_path.exists():
                    logger.warning(
                        f"Original location occupied, cannot restore: {original_path}"
                    )
                    continue

                shutil.move(str(staged_path), str(original_path))
                restored_count += 1
                logger.debug(f"Restored: {staged_path} -> {original_path}")

            # Update operation metadata
            operation_metadata["status"] = "undone"
            operation_metadata["undo_timestamp"] = datetime.now().isoformat()
            operation_metadata["files_restored"] = restored_count

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(operation_metadata, f, indent=2)

            logger.info(
                f"Restored {restored_count}/{len(operation_metadata['files'])} files"
            )

            return restored_count > 0

        except Exception as e:
            logger.error(f"Error undoing operation {operation_id}: {e}")
            return False

    def confirm_deletion(
        self,
        operation_id: str,
        use_recycle_bin: bool = True,
    ) -> bool:
        """
        Permanently delete staged files (move to recycle bin or delete).

        Args:
            operation_id: ID of the staging operation
            use_recycle_bin: Move to recycle bin instead of permanent deletion

        Returns:
            True if successful, False otherwise
        """
        operation_dir = self.staging_dir / operation_id

        if not operation_dir.exists():
            logger.error(f"Operation not found: {operation_id}")
            return False

        metadata_file = operation_dir / "operation.json"
        if not metadata_file.exists():
            logger.error(f"Operation metadata not found: {operation_id}")
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                operation_metadata = json.load(f)

            deleted_count = 0
            for file_info in operation_metadata["files"]:
                staged_path = Path(file_info["staged_path"])

                if not staged_path.exists():
                    logger.warning(f"File not found: {staged_path}")
                    continue

                try:
                    if use_recycle_bin:
                        send2trash(str(staged_path))
                        logger.debug(f"Moved to recycle bin: {staged_path}")
                    else:
                        staged_path.unlink()
                        logger.debug(f"Permanently deleted: {staged_path}")

                    deleted_count += 1

                except Exception as e:
                    logger.error(f"Failed to delete {staged_path}: {e}")
                    continue

            # Update operation metadata
            operation_metadata["status"] = "deleted"
            operation_metadata["deletion_timestamp"] = datetime.now().isoformat()
            operation_metadata["files_deleted"] = deleted_count
            operation_metadata["used_recycle_bin"] = use_recycle_bin

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(operation_metadata, f, indent=2)

            # Clean up empty operation directory
            if not any(operation_dir.iterdir()):
                operation_dir.rmdir()

            logger.info(
                f"Deleted {deleted_count}/{len(operation_metadata['files'])} files "
                f"({'recycle bin' if use_recycle_bin else 'permanent'})"
            )

            return deleted_count > 0

        except Exception as e:
            logger.error(f"Error confirming deletion {operation_id}: {e}")
            return False

    def list_staged_operations(self) -> List[Dict[str, Any]]:
        """
        List all staged operations.

        Returns:
            List of operation metadata dictionaries
        """
        operations = []

        if not self.staging_dir.exists():
            return operations

        for operation_dir in sorted(self.staging_dir.iterdir()):
            if not operation_dir.is_dir():
                continue

            metadata_file = operation_dir / "operation.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    operations.append(metadata)
            except Exception as e:
                logger.warning(
                    f"Error reading operation metadata {operation_dir}: {e}"
                )
                continue

        return operations

    def clean_old_operations(self, max_age_days: int = 30) -> int:
        """
        Clean up old staging operations.

        Args:
            max_age_days: Maximum age in days for staging operations

        Returns:
            Number of operations cleaned up
        """
        if not self.staging_dir.exists():
            return 0

        cleaned = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

        for operation_dir in self.staging_dir.iterdir():
            if not operation_dir.is_dir():
                continue

            # Check operation age
            if operation_dir.stat().st_mtime < cutoff:
                try:
                    shutil.rmtree(operation_dir)
                    cleaned += 1
                    logger.debug(f"Cleaned old operation: {operation_dir.name}")
                except Exception as e:
                    logger.warning(f"Failed to clean {operation_dir}: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} old staging operations")

        return cleaned

    def _log_operation(self, operation_metadata: Dict[str, Any]) -> None:
        """
        Log operation to operations log file.

        Args:
            operation_metadata: Operation metadata to log
        """
        try:
            self.operations_log.parent.mkdir(parents=True, exist_ok=True)

            # Append to operations log
            with open(self.operations_log, "a", encoding="utf-8") as f:
                log_entry = {
                    "timestamp": operation_metadata["timestamp"],
                    "operation_id": operation_metadata["operation_id"],
                    "reason": operation_metadata["reason"],
                    "files_count": operation_metadata["files_staged"],
                    "status": operation_metadata["status"],
                }
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.warning(f"Failed to log operation: {e}")

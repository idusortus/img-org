"""File scanner for discovering images in directories."""

import os
from pathlib import Path
from typing import List, Set

from tqdm import tqdm

from image_organizer.utils.config import Config
from image_organizer.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageScanner:
    """Scans directories for image files with progress tracking."""

    # Supported image extensions
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".heic",
        ".heif",
        ".tiff",
        ".tif",
    }

    def __init__(self, config: Config, show_progress: bool = True):
        """
        Initialize the image scanner.

        Args:
            config: Configuration instance
            show_progress: Show progress bar during scanning
        """
        self.config = config
        self.show_progress = show_progress

    def scan_directory(
        self, directory: Path, recursive: bool = True, skip_hidden: bool = True
    ) -> List[Path]:
        """
        Scan a directory for image files.

        Args:
            directory: Directory path to scan
            recursive: Recursively scan subdirectories
            skip_hidden: Skip hidden files and folders

        Returns:
            List of image file paths

        Raises:
            FileNotFoundError: If directory doesn't exist
            PermissionError: If directory is not accessible
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        logger.info(f"Scanning directory: {directory}")

        try:
            # First pass: count total files for progress bar
            all_files = self._discover_files(directory, recursive, skip_hidden)
            total_files = len(all_files)

            logger.info(f"Found {total_files} files to check")

            # Second pass: filter image files with progress
            image_files: List[Path] = []

            if self.show_progress:
                file_iter = tqdm(all_files, desc="Filtering images", unit="file")
            else:
                file_iter = all_files

            for file_path in file_iter:
                if self._is_image_file(file_path):
                    image_files.append(file_path)

            logger.info(f"Found {len(image_files)} image files")
            return image_files

        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            raise

    def _discover_files(
        self, directory: Path, recursive: bool, skip_hidden: bool
    ) -> List[Path]:
        """
        Discover all files in a directory.

        Args:
            directory: Directory to scan
            recursive: Scan subdirectories
            skip_hidden: Skip hidden files/folders

        Returns:
            List of all file paths
        """
        files: List[Path] = []

        try:
            if recursive:
                for root, dirs, filenames in os.walk(directory):
                    root_path = Path(root)

                    # Skip hidden directories if requested
                    if skip_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        # Also check for Windows hidden attribute
                        dirs[:] = [
                            d
                            for d in dirs
                            if not self._is_hidden_windows(root_path / d)
                        ]

                    # Skip symlinks and junctions to avoid loops
                    dirs[:] = [
                        d for d in dirs if not (root_path / d).is_symlink()
                    ]

                    for filename in filenames:
                        file_path = root_path / filename

                        # Skip hidden files
                        if skip_hidden and (
                            filename.startswith(".")
                            or self._is_hidden_windows(file_path)
                        ):
                            continue

                        # Skip symlinks
                        if file_path.is_symlink():
                            continue

                        files.append(file_path)
            else:
                # Non-recursive: only immediate children
                for item in directory.iterdir():
                    if item.is_file():
                        if skip_hidden and (
                            item.name.startswith(".")
                            or self._is_hidden_windows(item)
                        ):
                            continue
                        if not item.is_symlink():
                            files.append(item)

        except PermissionError as e:
            logger.warning(f"Permission denied accessing directory: {e}")

        return files

    def _is_image_file(self, file_path: Path) -> bool:
        """
        Check if a file is a supported image type.

        Args:
            file_path: File path to check

        Returns:
            True if file is a supported image
        """
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def _is_hidden_windows(self, path: Path) -> bool:
        """
        Check if a path is hidden on Windows.

        Args:
            path: Path to check

        Returns:
            True if path is hidden on Windows
        """
        if os.name != "nt":
            return False

        try:
            import ctypes

            FILE_ATTRIBUTE_HIDDEN = 0x02
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            return attrs != -1 and (attrs & FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            return False

    def scan_multiple_directories(
        self, directories: List[Path], recursive: bool = True, skip_hidden: bool = True
    ) -> List[Path]:
        """
        Scan multiple directories for images.

        Args:
            directories: List of directory paths
            recursive: Recursively scan subdirectories
            skip_hidden: Skip hidden files and folders

        Returns:
            Combined list of unique image file paths
        """
        all_images: Set[Path] = set()

        for directory in directories:
            try:
                images = self.scan_directory(directory, recursive, skip_hidden)
                all_images.update(images)
            except Exception as e:
                logger.error(f"Error scanning {directory}: {e}")
                continue

        return sorted(list(all_images))

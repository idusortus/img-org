"""Duplicate detection using imagededup library."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from imagededup.methods import AHash, DHash, PHash, WHash
    IMAGEDEDUP_AVAILABLE = True
except ImportError:
    IMAGEDEDUP_AVAILABLE = False
    AHash = DHash = PHash = WHash = None

from image_organizer.utils.config import Config
from image_organizer.utils.logger import setup_logger

logger = setup_logger(__name__)


class DuplicateDetector:
    """Detects duplicate and near-duplicate images using imagededup."""

    def __init__(self, config: Config, show_progress: bool = True):
        """
        Initialize the duplicate detector.

        Args:
            config: Configuration instance
            show_progress: Show progress during detection
        """
        self.config = config
        self.show_progress = show_progress
        self.hash_method = config.get("hash_method", "phash")
        self.threshold = config.get("similarity_threshold", 10)

        # Initialize the appropriate hasher
        self.hasher = self._get_hasher()

    def _get_hasher(self) -> object:
        """
        Get the appropriate imagededup hasher based on configuration.

        Returns:
            Hasher instance
        """
        if not IMAGEDEDUP_AVAILABLE:
            raise ImportError(
                "imagededup is not installed. For now, only local scanning with imagededup is supported.\n"
                "Note: imagededup requires C++ build tools on Windows.\n"
                "Alternative: Use Google Drive scanning which works without imagededup."
            )
        
        hash_methods = {
            "phash": PHash,
            "dhash": DHash,
            "ahash": AHash,
            "whash": WHash,
        }

        hasher_class = hash_methods.get(self.hash_method.lower())
        if not hasher_class:
            logger.warning(
                f"Unknown hash method '{self.hash_method}', using PHash"
            )
            hasher_class = PHash

        logger.info(f"Using {hasher_class.__name__} for duplicate detection")
        return hasher_class(verbose=self.show_progress)

    def find_duplicates(
        self,
        image_paths: List[Path],
        threshold: Optional[int] = None,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find duplicate and near-duplicate images.

        Args:
            image_paths: List of image file paths to analyze
            threshold: Optional Hamming distance threshold (overrides config)

        Returns:
            Dictionary mapping primary images to list of duplicates with scores
            Format: {'image1.jpg': [('duplicate1.jpg', 0.0), ('duplicate2.jpg', 2.5)]}
        """
        if not image_paths:
            logger.warning("No images provided for duplicate detection")
            return {}

        threshold = threshold if threshold is not None else self.threshold

        logger.info(
            f"Finding duplicates in {len(image_paths)} images "
            f"(threshold: {threshold})"
        )

        # Convert Path objects to strings for imagededup
        image_dir = self._find_common_parent(image_paths)
        
        try:
            # Use imagededup to find duplicates
            duplicates = self.hasher.find_duplicates(
                image_dir=str(image_dir) if image_dir else None,
                max_distance_threshold=threshold,
                scores=True,
                recursive=True,
            )

            logger.info(f"Found {len(duplicates)} duplicate groups")
            return duplicates

        except Exception as e:
            logger.error(f"Error during duplicate detection: {e}")
            raise

    def find_duplicates_to_remove(
        self,
        image_paths: List[Path],
        threshold: Optional[int] = None,
    ) -> List[str]:
        """
        Find duplicate images to remove (keeping one per group).

        This uses imagededup's find_duplicates_to_remove which returns
        a single list of files that can be safely removed.

        Args:
            image_paths: List of image file paths
            threshold: Optional Hamming distance threshold

        Returns:
            List of image file paths to remove
        """
        if not image_paths:
            return []

        threshold = threshold if threshold is not None else self.threshold

        image_dir = self._find_common_parent(image_paths)

        try:
            files_to_remove = self.hasher.find_duplicates_to_remove(
                image_dir=str(image_dir) if image_dir else None,
                max_distance_threshold=threshold,
                recursive=True,
            )

            logger.info(f"Identified {len(files_to_remove)} files to remove")
            return files_to_remove

        except Exception as e:
            logger.error(f"Error finding files to remove: {e}")
            raise

    def _find_common_parent(self, paths: List[Path]) -> Optional[Path]:
        """
        Find the common parent directory for a list of paths.

        Args:
            paths: List of file paths

        Returns:
            Common parent directory or None
        """
        if not paths:
            return None

        # Get all unique parent directories
        parents = {p.parent for p in paths}

        # If all files are in the same directory, return it
        if len(parents) == 1:
            return list(parents)[0]

        # Find common ancestor
        common_parts = list(paths[0].parts)
        for path in paths[1:]:
            parts = list(path.parts)
            # Find where paths diverge
            for i, (a, b) in enumerate(zip(common_parts, parts)):
                if a != b:
                    common_parts = common_parts[:i]
                    break
            else:
                # One path is a parent of the other
                common_parts = common_parts[:min(len(common_parts), len(parts))]

        if common_parts:
            return Path(*common_parts)
        
        return None

    def compute_hash(self, image_path: Path) -> str:
        """
        Compute perceptual hash for a single image.

        Args:
            image_path: Path to image file

        Returns:
            Hash string
        """
        try:
            hash_value = self.hasher.encode_image(image_file=str(image_path))
            return hash_value
        except Exception as e:
            logger.error(f"Error computing hash for {image_path}: {e}")
            raise

    def compute_hashes(
        self, image_paths: List[Path]
    ) -> Dict[str, str]:
        """
        Compute perceptual hashes for multiple images.

        Args:
            image_paths: List of image paths

        Returns:
            Dictionary mapping file paths to hash strings
        """
        image_dir = self._find_common_parent(image_paths)

        try:
            encoding_map = self.hasher.encode_images(
                image_dir=str(image_dir) if image_dir else None,
                recursive=True,
            )

            logger.info(f"Computed hashes for {len(encoding_map)} images")
            return encoding_map

        except Exception as e:
            logger.error(f"Error computing hashes: {e}")
            raise

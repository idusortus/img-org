"""Cross-platform duplicate detection (local + cloud)."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from image_organizer.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class FileInfo:
    """Information about a file (local or cloud)."""
    
    platform: str  # "local" or "drive"
    path: str  # File path (local) or Drive file ID
    name: str
    size: int
    md5: str
    modified: Optional[str] = None
    drive_url: Optional[str] = None  # Google Drive web link


@dataclass
class CrossPlatformDuplicate:
    """A file that exists on multiple platforms."""
    
    md5: str
    name: str
    size: int
    local_files: List[FileInfo]
    drive_files: List[FileInfo]
    
    @property
    def total_files(self) -> int:
        """Total number of files across platforms."""
        return len(self.local_files) + len(self.drive_files)
    
    @property
    def local_space(self) -> int:
        """Space used by local copies."""
        return sum(f.size for f in self.local_files)
    
    @property
    def drive_space(self) -> int:
        """Space used by Drive copies."""
        return sum(f.size for f in self.drive_files)


class CrossPlatformDetector:
    """Detects duplicates across local files and Google Drive."""
    
    def __init__(self):
        """Initialize cross-platform detector."""
        self.local_files: Dict[str, FileInfo] = {}  # md5 -> FileInfo
        self.drive_files: Dict[str, FileInfo] = {}  # md5 -> FileInfo
        
    def add_local_file(
        self,
        path: Path,
        md5: Optional[str] = None,
        size: Optional[int] = None,
        modified: Optional[str] = None,
    ) -> None:
        """
        Add a local file to the detection pool.
        
        Args:
            path: Local file path
            md5: MD5 hash (will compute if not provided)
            size: File size in bytes
            modified: Modification date (ISO format)
        """
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return
            
        # Compute MD5 if not provided
        if md5 is None:
            md5 = self._compute_md5(path)
            
        # Get size if not provided
        if size is None:
            size = path.stat().st_size
            
        file_info = FileInfo(
            platform="local",
            path=str(path),
            name=path.name,
            size=size,
            md5=md5,
            modified=modified,
        )
        
        # Store in dictionary (md5 as key)
        if md5 not in self.local_files:
            self.local_files[md5] = []
        if not isinstance(self.local_files[md5], list):
            self.local_files[md5] = [self.local_files[md5]]
        self.local_files[md5].append(file_info)
        
    def add_drive_file(
        self,
        file_id: str,
        name: str,
        size: int,
        md5: str,
        modified: Optional[str] = None,
        web_url: Optional[str] = None,
    ) -> None:
        """
        Add a Google Drive file to the detection pool.
        
        Args:
            file_id: Google Drive file ID
            name: File name
            size: File size in bytes
            md5: MD5 checksum from Drive API
            modified: Modification date (ISO format)
            web_url: Google Drive web view link
        """
        file_info = FileInfo(
            platform="drive",
            path=file_id,
            name=name,
            size=size,
            md5=md5,
            modified=modified,
            drive_url=web_url,
        )
        
        # Store in dictionary (md5 as key)
        if md5 not in self.drive_files:
            self.drive_files[md5] = []
        if not isinstance(self.drive_files[md5], list):
            self.drive_files[md5] = [self.drive_files[md5]]
        self.drive_files[md5].append(file_info)
        
    def find_cross_platform_duplicates(self) -> List[CrossPlatformDuplicate]:
        """
        Find files that exist on both local and Google Drive.
        
        Returns:
            List of cross-platform duplicates
        """
        duplicates = []
        
        # Find MD5 hashes that exist in both platforms
        local_md5s = set(self.local_files.keys())
        drive_md5s = set(self.drive_files.keys())
        common_md5s = local_md5s & drive_md5s
        
        logger.info(
            f"Found {len(common_md5s)} cross-platform duplicate groups "
            f"(local: {len(local_md5s)}, drive: {len(drive_md5s)})"
        )
        
        for md5 in common_md5s:
            local_list = self.local_files[md5]
            drive_list = self.drive_files[md5]
            
            # Ensure lists
            if not isinstance(local_list, list):
                local_list = [local_list]
            if not isinstance(drive_list, list):
                drive_list = [drive_list]
                
            # Create duplicate entry
            duplicate = CrossPlatformDuplicate(
                md5=md5,
                name=local_list[0].name,  # Use first local file's name
                size=local_list[0].size,
                local_files=local_list,
                drive_files=drive_list,
            )
            duplicates.append(duplicate)
            
        # Sort by size (largest first)
        duplicates.sort(key=lambda d: d.size, reverse=True)
        
        return duplicates
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about cross-platform duplicates.
        
        Returns:
            Dictionary with statistics
        """
        duplicates = self.find_cross_platform_duplicates()
        
        total_local_space = sum(d.local_space for d in duplicates)
        total_drive_space = sum(d.drive_space for d in duplicates)
        total_files = sum(d.total_files for d in duplicates)
        
        return {
            "duplicate_groups": len(duplicates),
            "total_files": total_files,
            "local_space_mb": total_local_space / (1024 * 1024),
            "drive_space_mb": total_drive_space / (1024 * 1024),
            "potential_savings_mb": min(total_local_space, total_drive_space) / (1024 * 1024),
        }
    
    def _compute_md5(self, path: Path) -> str:
        """
        Compute MD5 hash of a file.
        
        Args:
            path: File path
            
        Returns:
            MD5 hash as hexadecimal string
        """
        md5 = hashlib.md5()
        
        try:
            with open(path, "rb") as f:
                # Read in chunks for memory efficiency
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute MD5 for {path}: {e}")
            raise
    
    def reset(self) -> None:
        """Clear all stored files."""
        self.local_files = {}
        self.drive_files = {}

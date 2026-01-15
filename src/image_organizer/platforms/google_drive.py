"""
Google Drive integration for duplicate detection.

Provides OAuth authentication, file listing, and duplicate detection using
Drive API v3 MD5 checksums and thumbnail-based perceptual hashing.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

try:
    from imagededup.methods import PHash
    IMAGEDEDUP_AVAILABLE = True
except ImportError:
    IMAGEDEDUP_AVAILABLE = False
    PHash = None

logger = logging.getLogger(__name__)

# Google Drive API scopes
# Updated to include write permissions for moving files and creating folders
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",  # Create and modify files created by this app
    "https://www.googleapis.com/auth/drive",  # Full Drive access (needed for moving existing files)
]

# Image MIME types supported by Google Drive
IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/tiff",
]

# Document MIME types for duplicate detection
DOCUMENT_MIME_TYPES = [
    # Microsoft Office formats
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # .ppt
    # PDF
    "application/pdf",
    # Text formats
    "text/plain",  # .txt
    "text/csv",  # .csv
    "text/tab-separated-values",  # .tsv
    # Google Workspace formats
    "application/vnd.google-apps.document",  # Google Docs
    "application/vnd.google-apps.spreadsheet",  # Google Sheets
    "application/vnd.google-apps.presentation",  # Google Slides
    # Other common formats
    "application/rtf",  # .rtf
    "application/vnd.oasis.opendocument.text",  # .odt
    "application/vnd.oasis.opendocument.spreadsheet",  # .ods
    "application/vnd.oasis.opendocument.presentation",  # .odp
]

# Document MIME types for duplicate detection
DOCUMENT_MIME_TYPES = [
    # Microsoft Office formats
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # .ppt
    # PDF
    "application/pdf",
    # Text formats
    "text/plain",  # .txt
    "text/csv",  # .csv
    "text/tab-separated-values",  # .tsv
    # Google Workspace formats
    "application/vnd.google-apps.document",  # Google Docs
    "application/vnd.google-apps.spreadsheet",  # Google Sheets
    "application/vnd.google-apps.presentation",  # Google Slides
    # Other common formats
    "application/rtf",  # .rtf
    "application/vnd.oasis.opendocument.text",  # .odt
    "application/vnd.oasis.opendocument.spreadsheet",  # .ods
    "application/vnd.oasis.opendocument.presentation",  # .odp
]


class GoogleDriveClient:
    """Client for interacting with Google Drive API."""

    def __init__(
        self,
        credentials_file: Optional[Path] = None,
        token_file: Optional[Path] = None,
    ):
        """
        Initialize Google Drive client.

        Args:
            credentials_file: Path to OAuth client secrets JSON file
            token_file: Path to store/load OAuth tokens
        """
        self.credentials_file = credentials_file or Path.home() / ".image-organizer" / "credentials.json"
        self.token_file = token_file or Path.home() / ".image-organizer" / "token.json"
        
        self.credentials: Optional[Credentials] = None
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive using OAuth 2.0.

        Returns:
            True if authentication successful, False otherwise
        """
        # Load existing token if available
        if self.token_file.exists():
            try:
                self.credentials = Credentials.from_authorized_user_file(
                    str(self.token_file), SCOPES
                )
                logger.info("Loaded existing OAuth token")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
                self.credentials = None
        
        # Refresh token if expired
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                self.credentials.refresh(Request())
                logger.info("Refreshed OAuth token")
            except Exception as e:
                logger.warning(f"Failed to refresh token: {e}")
                self.credentials = None
        
        # Start new OAuth flow if no valid credentials
        if not self.credentials or not self.credentials.valid:
            if not self.credentials_file.exists():
                logger.error(
                    f"Credentials file not found: {self.credentials_file}\n"
                    "Please download OAuth 2.0 credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/apis/credentials\n"
                    "2. Create OAuth 2.0 Client ID (Desktop application)\n"
                    f"3. Save as {self.credentials_file}"
                )
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                self.credentials = flow.run_local_server(port=0)
                logger.info("Completed OAuth flow")
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                return False
        
        # Save credentials for next run
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as f:
                f.write(self.credentials.to_json())
            logger.info(f"Saved OAuth token to {self.token_file}")
        except Exception as e:
            logger.warning(f"Failed to save token: {e}")
        
        # Build Drive service
        try:
            self.service = build("drive", "v3", credentials=self.credentials)
            logger.info("Google Drive service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")
            return False
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name for the new folder
            parent_id: Parent folder ID (None = root)
        
        Returns:
            Folder ID if created successfully, None otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            
            if parent_id:
                file_metadata["parents"] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields="id, name"
            ).execute()
            
            folder_id = folder.get("id")
            logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
        
        except HttpError as e:
            if e.resp.status == 409:  # Folder already exists
                logger.warning(f"Folder '{folder_name}' already exists")
                # Try to find existing folder
                return self._find_folder_by_name(folder_name)
            else:
                logger.error(f"Failed to create folder: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return None
    
    def move_file(self, file_id: str, target_folder_id: str) -> bool:
        """
        Move a file to a different folder.
        
        Args:
            file_id: ID of the file to move
            target_folder_id: ID of the destination folder
        
        Returns:
            True if moved successfully, False otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Get current parents
            file = self.service.files().get(
                fileId=file_id,
                fields="parents"
            ).execute()
            
            previous_parents = ",".join(file.get("parents", []))
            
            # Move the file
            self.service.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
                fields="id, parents"
            ).execute()
            
            logger.info(f"Moved file {file_id} to folder {target_folder_id}")
            return True
        
        except HttpError as e:
            logger.error(f"Failed to move file {file_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to move file {file_id}: {e}")
            return False
    
    def move_duplicates_to_folder(
        self,
        duplicates: Dict[str, List[Dict[str, Any]]],
        folder_name: Optional[str] = None,
        keep_strategy: str = "first",
    ) -> Tuple[int, int, str]:
        """
        Move duplicate files to a review folder.
        
        Args:
            duplicates: Dict of MD5 -> list of file dicts (from find_exact_duplicates_by_md5)
            folder_name: Name for review folder (auto-generated if None)
            keep_strategy: Which file to keep in original location
                - "first": Keep first file in list (default)
                - "last": Keep last file in list
                - "newest": Keep newest file (by modifiedTime)
                - "oldest": Keep oldest file (by modifiedTime)
                - "largest": Keep largest file
                - "smallest": Keep smallest file
        
        Returns:
            Tuple of (files_moved, files_kept, folder_id)
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        # Generate folder name with timestamp if not provided
        if not folder_name:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            folder_name = f"Duplicates_{timestamp}"
            
            # Check if folder exists, add seconds if collision
            existing = self._find_folder_by_name(folder_name)
            if existing:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                folder_name = f"Duplicates_{timestamp}"
        
        # Create folder
        folder_id = self.create_folder(folder_name)
        if not folder_id:
            logger.error("Failed to create review folder")
            return (0, 0, "")
        
        logger.info(f"Created review folder: {folder_name} ({folder_id})")
        
        files_moved = 0
        files_kept = 0
        
        # Process each duplicate group
        for md5, file_list in duplicates.items():
            if len(file_list) < 2:
                continue
            
            # Determine which file to keep
            if keep_strategy == "last":
                keep_idx = len(file_list) - 1
            elif keep_strategy == "newest":
                keep_idx = max(range(len(file_list)), key=lambda i: file_list[i].get("modifiedTime", ""))
            elif keep_strategy == "oldest":
                keep_idx = min(range(len(file_list)), key=lambda i: file_list[i].get("modifiedTime", ""))
            elif keep_strategy == "largest":
                keep_idx = max(range(len(file_list)), key=lambda i: int(file_list[i].get("size", 0)))
            elif keep_strategy == "smallest":
                keep_idx = min(range(len(file_list)), key=lambda i: int(file_list[i].get("size", 0)))
            else:  # "first" or default
                keep_idx = 0
            
            # Move all except the one we're keeping
            for i, file in enumerate(file_list):
                if i == keep_idx:
                    logger.info(f"Keeping: {file.get('name')} (ID: {file.get('id')})")
                    files_kept += 1
                else:
                    logger.info(f"Moving: {file.get('name')} (ID: {file.get('id')})")
                    if self.move_file(file.get("id"), folder_id):
                        files_moved += 1
        
        logger.info(f"Moved {files_moved} files, kept {files_kept} files")
        return (files_moved, files_kept, folder_id)
    
    def trash_file(self, file_id: str) -> bool:
        """
        Move a file to Google Drive trash.
        
        Args:
            file_id: ID of the file to trash
        
        Returns:
            True if trashed successfully, False otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            self.service.files().update(
                fileId=file_id,
                body={"trashed": True}
            ).execute()
            
            logger.info(f"Trashed file {file_id}")
            return True
        
        except HttpError as e:
            logger.error(f"Failed to trash file {file_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to trash file {file_id}: {e}")
            return False
    
    def trash_duplicates(
        self,
        duplicates: Dict[str, List[Dict[str, Any]]],
        keep_strategy: str = "first",
    ) -> Tuple[int, int]:
        """
        Trash duplicate files (moves to Google Drive trash, 30-day recovery).
        
        Args:
            duplicates: Dict of MD5 -> list of file dicts (from find_exact_duplicates_by_md5)
            keep_strategy: Which file to keep
                - "first": Keep first file in list (default)
                - "last": Keep last file in list
                - "newest": Keep newest file (by modifiedTime)
                - "oldest": Keep oldest file (by modifiedTime)
                - "largest": Keep largest file
                - "smallest": Keep smallest file
        
        Returns:
            Tuple of (files_trashed, files_kept)
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        files_trashed = 0
        files_kept = 0
        
        # Process each duplicate group
        for md5, file_list in duplicates.items():
            if len(file_list) < 2:
                continue
            
            # Determine which file to keep
            if keep_strategy == "last":
                keep_idx = len(file_list) - 1
            elif keep_strategy == "newest":
                keep_idx = max(range(len(file_list)), key=lambda i: file_list[i].get("modifiedTime", ""))
            elif keep_strategy == "oldest":
                keep_idx = min(range(len(file_list)), key=lambda i: file_list[i].get("modifiedTime", ""))
            elif keep_strategy == "largest":
                keep_idx = max(range(len(file_list)), key=lambda i: int(file_list[i].get("size", 0)))
            elif keep_strategy == "smallest":
                keep_idx = min(range(len(file_list)), key=lambda i: int(file_list[i].get("size", 0)))
            else:  # "first" or default
                keep_idx = 0
            
            # Trash all except the one we're keeping
            for i, file in enumerate(file_list):
                if i == keep_idx:
                    logger.info(f"Keeping: {file.get('name')} (ID: {file.get('id')})")
                    files_kept += 1
                else:
                    logger.info(f"Trashing: {file.get('name')} (ID: {file.get('id')})")
                    if self.trash_file(file.get("id")):
                        files_trashed += 1
        
        logger.info(f"Trashed {files_trashed} files, kept {files_kept} files")
        return (files_trashed, files_kept)
    
    def list_image_files(
        self,
        max_results: Optional[int] = None,
        page_size: int = 100,
        folder_id: Optional[str] = None,
        folder_name: Optional[str] = None,
        recursive: bool = True,
        mime_types: Optional[List[str]] = None,
        exclude_mime_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all image files in Google Drive.

        Args:
            max_results: Maximum number of files to return (None for all)
            page_size: Number of files per page (max 1000)
            folder_id: Specific folder ID to scan (optional)
            folder_name: Folder name to search for (optional, finds first match)
            recursive: Include subfolders (default: True)
            mime_types: Only include these MIME types (e.g., ['image/jpeg'])
            exclude_mime_types: Exclude these MIME types (e.g., ['image/gif'])

        Returns:
            List of file metadata dictionaries
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        # Resolve folder_name to folder_id if provided
        if folder_name and not folder_id:
            folder_id = self._find_folder_by_name(folder_name)
            if not folder_id:
                logger.warning(f"Folder '{folder_name}' not found, scanning entire Drive")
        
        # Determine which MIME types to scan
        if mime_types:
            # Use exactly the types provided by caller
            target_mime_types = mime_types
            logger.info(f"Scanning MIME types: {', '.join(target_mime_types)}")
        else:
            # Default to images if none specified
            target_mime_types = IMAGE_MIME_TYPES
        
        if exclude_mime_types:
            # Remove excluded types
            target_mime_types = [mt for mt in target_mime_types if mt not in exclude_mime_types]
            if not target_mime_types:
                logger.warning(f"All MIME types excluded, scanning all types instead")
                target_mime_types = IMAGE_MIME_TYPES
            else:
                logger.info(f"Excluding MIME types: {', '.join(exclude_mime_types)}")
        
        # Build query for image files
        mime_queries = [f"mimeType='{mime}'" for mime in target_mime_types]
        query = f"({' or '.join(mime_queries)}) and trashed=false"
        
        # Add folder constraint if specified
        if folder_id:
            if recursive:
                # Get all subfolders
                subfolder_ids = self._get_all_subfolders(folder_id)
                subfolder_ids.append(folder_id)  # Include parent folder
                
                # Build query for all folders
                folder_queries = [f"'{fid}' in parents" for fid in subfolder_ids]
                query += f" and ({' or '.join(folder_queries)})"
                logger.info(f"Scanning folder and {len(subfolder_ids)-1} subfolders")
            else:
                query += f" and '{folder_id}' in parents"
                logger.info(f"Scanning folder {folder_id} (non-recursive)")
        
        # Fields to request (partial fields for efficiency)
        fields = "nextPageToken, files(id, name, mimeType, size, md5Checksum, createdTime, modifiedTime, thumbnailLink)"
        
        files = []
        page_token = None
        
        logger.info(f"Listing image files from Google Drive (query: {query})")
        
        try:
            while True:
                # Execute request with pagination
                results = self._execute_with_retry(
                    self.service.files().list,
                    q=query,
                    spaces="drive",
                    fields=fields,
                    pageSize=min(page_size, 1000),
                    pageToken=page_token,
                )
                
                page_files = results.get("files", [])
                files.extend(page_files)
                
                logger.debug(f"Retrieved {len(page_files)} files (total: {len(files)})")
                
                # Check if we've reached max_results
                if max_results and len(files) >= max_results:
                    files = files[:max_results]
                    break
                
                # Check for next page
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
        
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise
        
        logger.info(f"Found {len(files)} image files in Google Drive")
        return files
    
    def find_exact_duplicates_by_md5(
        self, 
        files: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find exact duplicates using MD5 checksums.

        Args:
            files: List of file metadata (or None to fetch all)

        Returns:
            Dictionary mapping MD5 hash to list of files with that hash
        """
        if files is None:
            files = self.list_image_files()
        
        # Group files by MD5 checksum
        md5_groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for file in files:
            md5 = file.get("md5Checksum")
            if not md5:
                logger.debug(f"File {file.get('name')} has no MD5 checksum, skipping")
                continue
            
            if md5 not in md5_groups:
                md5_groups[md5] = []
            md5_groups[md5].append(file)
        
        # Filter to only duplicates (2+ files with same MD5)
        duplicates = {
            md5: files_list
            for md5, files_list in md5_groups.items()
            if len(files_list) > 1
        }
        
        total_duplicates = sum(len(files_list) - 1 for files_list in duplicates.values())
        logger.info(
            f"Found {len(duplicates)} duplicate groups with {total_duplicates} duplicate files"
        )
        
        return duplicates
    
    def download_thumbnail(
        self,
        file_id: str,
        output_path: Path,
    ) -> bool:
        """
        Download thumbnail for a file.

        Args:
            file_id: Google Drive file ID
            output_path: Path to save thumbnail

        Returns:
            True if download successful, False otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            # Get file metadata with thumbnail link
            file_metadata = self._execute_with_retry(
                self.service.files().get,
                fileId=file_id,
                fields="thumbnailLink",
            )
            
            thumbnail_link = file_metadata.get("thumbnailLink")
            if not thumbnail_link:
                logger.debug(f"No thumbnail available for file {file_id}")
                return False
            
            # Download thumbnail
            import requests
            response = requests.get(
                thumbnail_link,
                headers={"Authorization": f"Bearer {self.credentials.token}"},
            )
            response.raise_for_status()
            
            # Save to disk
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded thumbnail for {file_id} to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to download thumbnail for {file_id}: {e}")
            return False
    
    def find_near_duplicates_by_phash(
        self,
        files: List[Dict[str, Any]],
        thumbnail_dir: Path,
        threshold: int = 10,
        max_files: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find near-duplicate images using perceptual hashing.
        
        Downloads thumbnails from Google Drive and uses imagededup's PHash
        algorithm to detect visually similar images.

        Args:
            files: List of file metadata dicts from list_image_files()
            thumbnail_dir: Directory to store downloaded thumbnails
            threshold: Hamming distance threshold (0-64, lower = more similar)
            max_files: Maximum number of files to process (for testing)

        Returns:
            Dict mapping file IDs to lists of similar files
            Format: {file_id: [similar_file1, similar_file2, ...]}
        """
        if not IMAGEDEDUP_AVAILABLE:
            raise ImportError(
                "imagededup not installed. Install with: pip install imagededup"
            )
        
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        logger.info(
            f"Starting perceptual hash duplicate detection for {len(files)} files "
            f"(threshold={threshold})"
        )
        
        # Create thumbnail directory
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        # Download thumbnails (with progress tracking)
        files_to_process = files[:max_files] if max_files else files
        downloaded_files = []
        
        for i, file in enumerate(files_to_process, 1):
            file_id = file["id"]
            thumbnail_path = thumbnail_dir / f"{file_id}.jpg"
            
            if i % 10 == 0:
                logger.info(f"Downloaded {i}/{len(files_to_process)} thumbnails")
            
            if self.download_thumbnail(file_id, thumbnail_path):
                downloaded_files.append({**file, "thumbnail_path": str(thumbnail_path)})
        
        logger.info(f"Successfully downloaded {len(downloaded_files)} thumbnails")
        
        if not downloaded_files:
            logger.warning("No thumbnails downloaded, cannot detect duplicates")
            return {}
        
        # Run perceptual hashing
        phasher = PHash()
        
        try:
            # Generate hashes for all thumbnails
            encodings = phasher.encode_images(image_dir=str(thumbnail_dir))
            
            # Find duplicates based on Hamming distance
            duplicates = phasher.find_duplicates(
                encoding_map=encodings,
                max_distance_threshold=threshold,
            )
            
            # Map back to file metadata
            # PHash returns filenames (e.g., "file1.jpg"), we need to map to file IDs
            result = {}
            for filename, similar_filenames in duplicates.items():
                if similar_filenames:  # Only include files with duplicates
                    # Extract file_id from filename (remove .jpg extension)
                    file_id = Path(filename).stem
                    
                    # Find original file metadata
                    original_file = next(
                        (f for f in downloaded_files if f["id"] == file_id),
                        None
                    )
                    
                    # Find similar file metadata
                    similar_files = []
                    for sim_filename in similar_filenames:
                        sim_file_id = Path(sim_filename).stem
                        sim_file = next(
                            (f for f in downloaded_files if f["id"] == sim_file_id),
                            None
                        )
                        if sim_file:
                            similar_files.append(sim_file)
                    
                    if original_file and similar_files:
                        result[file_id] = similar_files
            
            total_duplicates = sum(len(v) for v in result.values())
            logger.info(
                f"Found {len(result)} files with near-duplicates "
                f"({total_duplicates} similar images)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Perceptual hashing failed: {e}")
            return {}
    
    def find_all_duplicates(
        self,
        files: List[Dict[str, Any]],
        thumbnail_dir: Path,
        phash_threshold: int = 10,
        include_near_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Find both exact (MD5) and near (perceptual hash) duplicates.

        Args:
            files: List of file metadata from list_image_files()
            thumbnail_dir: Directory for thumbnail storage
            phash_threshold: Hamming distance threshold for near-duplicates
            include_near_duplicates: Whether to detect near-duplicates

        Returns:
            Dict with 'exact' and 'near' duplicate groups:
            {
                'exact': {md5: [file1, file2, ...]},
                'near': {file_id: [similar_file1, ...]},
                'stats': {...}
            }
        """
        result = {
            'exact': {},
            'near': {},
            'stats': {}
        }
        
        # Find exact duplicates (fast, no downloads)
        logger.info("Finding exact duplicates by MD5...")
        exact_duplicates = self.find_exact_duplicates_by_md5(files)
        result['exact'] = exact_duplicates
        
        # Find near duplicates (slow, requires thumbnail downloads)
        if include_near_duplicates and IMAGEDEDUP_AVAILABLE:
            logger.info("Finding near-duplicates by perceptual hashing...")
            near_duplicates = self.find_near_duplicates_by_phash(
                files, thumbnail_dir, threshold=phash_threshold
            )
            result['near'] = near_duplicates
        elif include_near_duplicates:
            logger.warning(
                "imagededup not available. Install with: pip install imagededup"
            )
        
        # Calculate statistics
        exact_groups = len(exact_duplicates)
        exact_count = sum(len(v) - 1 for v in exact_duplicates.values())
        near_groups = len(result['near'])
        near_count = sum(len(v) for v in result['near'].values())
        
        result['stats'] = {
            'exact_duplicate_groups': exact_groups,
            'exact_duplicate_files': exact_count,
            'near_duplicate_groups': near_groups,
            'near_duplicate_pairs': near_count,
            'total_files_scanned': len(files),
        }
        
        logger.info(
            f"Detection complete: {exact_groups} exact groups ({exact_count} files), "
            f"{near_groups} near-duplicate groups ({near_count} pairs)"
        )
        
        return result
    
    def move_to_trash(self, file_id: str) -> bool:
        """
        Move a file to trash (30-day recovery period).

        Args:
            file_id: Google Drive file ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            self._execute_with_retry(
                self.service.files().update,
                fileId=file_id,
                body={"trashed": True},
            )
            logger.info(f"Moved file {file_id} to trash")
            return True
        
        except HttpError as e:
            logger.error(f"Failed to trash file {file_id}: {e}")
            return False
    
    def restore_from_trash(self, file_id: str) -> bool:
        """
        Restore a file from trash.

        Args:
            file_id: Google Drive file ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            self._execute_with_retry(
                self.service.files().update,
                fileId=file_id,
                body={"trashed": False},
            )
            logger.info(f"Restored file {file_id} from trash")
            return True
        
        except HttpError as e:
            logger.error(f"Failed to restore file {file_id}: {e}")
            return False
    
    def _find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """
        Find folder ID by name (returns first match).

        Args:
            folder_name: Name of folder to find

        Returns:
            Folder ID or None if not found
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            results = self._execute_with_retry(
                self.service.files().list,
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            )
            
            folders = results.get("files", [])
            if folders:
                logger.info(f"Found folder '{folder_name}': {folders[0]['id']}")
                return folders[0]["id"]
            
            return None
        
        except HttpError as e:
            logger.error(f"Error finding folder '{folder_name}': {e}")
            return None
    
    def _get_all_subfolders(self, folder_id: str) -> List[str]:
        """
        Recursively get all subfolder IDs within a folder.

        Args:
            folder_id: Parent folder ID

        Returns:
            List of subfolder IDs (including nested subfolders)
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        all_subfolders = []
        folders_to_process = [folder_id]
        
        try:
            while folders_to_process:
                current_folder = folders_to_process.pop(0)
                
                # Find direct children that are folders
                query = f"'{current_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self._execute_with_retry(
                    self.service.files().list,
                    q=query,
                    spaces="drive",
                    fields="files(id, name)",
                    pageSize=1000,
                )
                
                subfolders = results.get("files", [])
                for subfolder in subfolders:
                    subfolder_id = subfolder["id"]
                    all_subfolders.append(subfolder_id)
                    folders_to_process.append(subfolder_id)  # Process recursively
                
                logger.debug(f"Found {len(subfolders)} subfolders in {current_folder}")
            
            logger.info(f"Found {len(all_subfolders)} total subfolders")
            return all_subfolders
        
        except HttpError as e:
            logger.error(f"Error getting subfolders: {e}")
            return all_subfolders
    
    def _execute_with_retry(
        self,
        api_call,
        max_retries: int = 5,
        **kwargs
    ) -> Any:
        """
        Execute API call with exponential backoff retry.

        Args:
            api_call: API method to call
            max_retries: Maximum number of retries
            **kwargs: Arguments to pass to API call

        Returns:
            API response

        Raises:
            HttpError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                return api_call(**kwargs).execute()
            
            except HttpError as e:
                # Check if error is retryable (429 = rate limit, 500+ = server error)
                if e.resp.status in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2^attempt seconds
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"API error {e.resp.status}, retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or max retries exceeded
                raise
        
        raise RuntimeError(f"Max retries ({max_retries}) exceeded")

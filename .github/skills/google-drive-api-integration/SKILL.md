---
name: google-drive-api-integration
description: Best practices for Google Drive API v3 integration including OAuth, pagination, rate limiting, and efficient batch operations. Use when implementing Google Drive features.
---

# Google Drive API Integration Skill

Comprehensive patterns for robust Google Drive API v3 integration.

## OAuth 2.0 Setup

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',  # Start with readonly
    # Request additional scopes only when needed:
    # 'https://www.googleapis.com/auth/drive.file',
    # 'https://www.googleapis.com/auth/drive',
]

def get_drive_service():
    """Authenticate and return Google Drive service."""
    creds = None
    token_file = 'token.pickle'
    
    # Load existing credentials
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)
```

## Pagination Pattern (CRITICAL)

**Always handle pagination** - Drive API returns 100 files max per request.

```python
def list_all_files(service, query=None, fields='files(id, name, mimeType, size, md5Checksum)'):
    """
    List all files matching query with proper pagination.
    
    Args:
        service: Authenticated Drive API service
        query: Optional query string (e.g., "mimeType contains 'image/'")
        fields: Fields to return (use partial fields for efficiency)
    """
    all_files = []
    page_token = None
    
    while True:
        try:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields=f'nextPageToken, {fields}',
                pageToken=page_token,
                pageSize=100  # Max allowed
            ).execute()
            
            files = results.get('files', [])
            all_files.extend(files)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
            print(f"Retrieved {len(all_files)} files so far...")
            
        except Exception as e:
            print(f"Error during pagination: {e}")
            break
    
    return all_files
```

## Query Patterns

```python
# Images only
query = "mimeType contains 'image/'"

# Specific image types
query = "mimeType='image/jpeg' or mimeType='image/png'"

# Not in trash
query = "trashed=false and mimeType contains 'image/'"

# Modified after date
query = "modifiedTime > '2024-01-01T00:00:00' and mimeType contains 'image/'"

# In specific folder
folder_id = 'abc123'
query = f"'{folder_id}' in parents and mimeType contains 'image/'"

# By name pattern
query = "name contains 'vacation' and mimeType contains 'image/'"

# Larger than 1MB
query = "mimeType contains 'image/' and size > 1048576"
```

## Rate Limiting & Error Handling

```python
import time
from googleapiclient.errors import HttpError

def execute_with_retry(request, max_retries=5):
    """
    Execute API request with exponential backoff for rate limits.
    
    Handles:
        - 429 (rate limit exceeded)
        - 500-503 (server errors)
        - Network timeouts
    """
    for attempt in range(max_retries):
        try:
            return request.execute()
            
        except HttpError as e:
            if e.resp.status in [429, 500, 503]:
                # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                wait_time = 2 ** attempt
                print(f"Rate limit hit. Waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                
                if attempt == max_retries - 1:
                    raise
            else:
                # Other HTTP errors (404, 403, etc.)
                raise
                
        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    return None
```

## Batch Requests (Efficient)

```python
from googleapiclient.http import BatchHttpRequest

def batch_get_file_metadata(service, file_ids: list, fields='id, name, md5Checksum, size'):
    """
    Retrieve metadata for multiple files in a single batch request.
    
    Benefits:
        - Reduces API calls (100 requests -> 1 batch)
        - Avoids rate limits
        - Faster overall
    """
    results = []
    
    def callback(request_id, response, exception):
        if exception:
            print(f"Error for request {request_id}: {exception}")
        else:
            results.append(response)
    
    # Process in batches of 100 (API limit)
    for i in range(0, len(file_ids), 100):
        batch = service.new_batch_http_request()
        batch_ids = file_ids[i:i + 100]
        
        for file_id in batch_ids:
            batch.add(
                service.files().get(fileId=file_id, fields=fields),
                callback=callback
            )
        
        execute_with_retry(batch)
    
    return results
```

## Download Files Efficiently

```python
from googleapiclient.http import MediaIoBaseDownload
import io

def download_file(service, file_id: str, output_path: Path):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    
    with open(output_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download {int(status.progress() * 100)}%")

def download_thumbnail(service, file_id: str) -> bytes:
    """
    Download thumbnail instead of full image (faster, less bandwidth).
    
    Good for:
        - Preview generation
        - Perceptual hashing
        - UI thumbnails
    """
    file_metadata = service.files().get(
        fileId=file_id,
        fields='thumbnailLink'
    ).execute()
    
    thumbnail_link = file_metadata.get('thumbnailLink')
    
    if thumbnail_link:
        # Download thumbnail via HTTP
        import requests
        response = requests.get(thumbnail_link)
        return response.content
    
    return None
```

## Efficient Field Selection

**Only request fields you need** - reduces bandwidth and improves speed.

```python
# Bad - returns ALL metadata
files = service.files().list().execute()

# Good - returns only needed fields
files = service.files().list(
    fields='files(id, name, md5Checksum, size)'
).execute()

# Available fields for images:
USEFUL_FIELDS = [
    'id',                    # Required for operations
    'name',                  # Filename
    'mimeType',             # Image type
    'size',                 # File size in bytes
    'md5Checksum',          # For exact duplicate detection
    'createdTime',          # When uploaded
    'modifiedTime',         # Last modified
    'imageMediaMetadata',   # Width, height, rotation, camera, etc.
    'thumbnailLink',        # Thumbnail URL
    'webViewLink',          # Link to view in browser
    'parents',              # Folder IDs
    'trashed',              # Is in trash
]
```

## Image-Specific Metadata

```python
def get_image_metadata(service, file_id: str):
    """Get detailed image metadata."""
    file_metadata = service.files().get(
        fileId=file_id,
        fields='id, name, size, md5Checksum, imageMediaMetadata, mimeType'
    ).execute()
    
    img_meta = file_metadata.get('imageMediaMetadata', {})
    
    return {
        'id': file_metadata['id'],
        'name': file_metadata['name'],
        'size': int(file_metadata.get('size', 0)),
        'md5': file_metadata.get('md5Checksum'),
        'mime_type': file_metadata.get('mimeType'),
        'width': img_meta.get('width'),
        'height': img_meta.get('height'),
        'rotation': img_meta.get('rotation'),
        'camera_make': img_meta.get('cameraMake'),
        'camera_model': img_meta.get('cameraModel'),
        'date_taken': img_meta.get('time'),
        'location': img_meta.get('location'),
    }
```

## Trash Operations (Safe Deletion)

```python
def move_to_trash(service, file_id: str):
    """
    Move file to trash (30-day recovery window).
    
    ALWAYS use this before permanent deletion.
    """
    service.files().update(
        fileId=file_id,
        body={'trashed': True}
    ).execute()
    print(f"Moved {file_id} to trash (recoverable for 30 days)")

def restore_from_trash(service, file_id: str):
    """Restore file from trash."""
    service.files().update(
        fileId=file_id,
        body={'trashed': False}
    ).execute()

def permanent_delete(service, file_id: str, user_confirmation: str):
    """
    Permanently delete file (CANNOT BE UNDONE).
    
    Only use after:
        1. File is in trash for review period
        2. User provides explicit confirmation
    """
    if user_confirmation != "PERMANENTLY DELETE":
        raise ValueError("Explicit confirmation required for permanent deletion")
    
    service.files().delete(fileId=file_id).execute()
    print(f"Permanently deleted {file_id} (CANNOT BE RECOVERED)")
```

## Quota Management

Google Drive API quotas (default free tier):
- **10,000 requests/day**
- **1,000 requests/100 seconds/user**

```python
class QuotaManager:
    def __init__(self):
        self.request_count = 0
        self.start_time = time.time()
    
    def check_quota(self):
        """Monitor and warn about quota usage."""
        elapsed = time.time() - self.start_time
        
        if elapsed < 100 and self.request_count >= 900:
            print("⚠️  Approaching rate limit (900/1000 requests in 100s)")
            time.sleep(100 - elapsed)
            self.reset()
    
    def increment(self):
        self.request_count += 1
        self.check_quota()
    
    def reset(self):
        self.request_count = 0
        self.start_time = time.time()
```

## Complete Example

```python
def scan_drive_for_duplicate_images(service):
    """Complete workflow for scanning Google Drive."""
    print("Step 1: Listing all images...")
    images = list_all_files(
        service,
        query="mimeType contains 'image/' and trashed=false",
        fields='files(id, name, size, md5Checksum, mimeType)'
    )
    print(f"Found {len(images)} images")
    
    print("Step 2: Finding exact duplicates by MD5...")
    from collections import defaultdict
    hash_map = defaultdict(list)
    
    for img in images:
        if 'md5Checksum' in img:
            hash_map[img['md5Checksum']].append(img)
    
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    print(f"Found {len(duplicates)} duplicate groups")
    
    print("Step 3: Downloading thumbnails for visual confirmation...")
    # Download only thumbnails, not full images
    for hash_value, files in duplicates.items():
        for file in files:
            thumb = download_thumbnail(service, file['id'])
            # Save for review UI
    
    return duplicates
```

## Error Handling Checklist

- ✅ Handle pagination (`nextPageToken`)
- ✅ Implement exponential backoff for rate limits
- ✅ Use batch requests for multiple operations
- ✅ Request only needed fields
- ✅ Download thumbnails instead of full images when possible
- ✅ Move to trash before permanent deletion
- ✅ Log all operations for audit trail
- ✅ Monitor quota usage

## References

- Google Drive API v3 docs: https://developers.google.com/drive/api/v3/reference
- Python quickstart: https://developers.google.com/drive/api/quickstart/python
- See `.github/copilot-instructions.md` for project context

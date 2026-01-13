# Image Organizer - Copilot Instructions

## Project Overview

This project helps users organize images and reduce storage space across multiple platforms, starting with Google Drive and Google Photos.

### Primary Goals
1. **Duplicate Detection & Elimination** - Find and remove duplicate/near-duplicate images
2. **Storage Optimization** - Reduce overall storage footprint
3. **Multi-Platform Support** - Currently targeting Google Drive/Photos and Windows PC, with future expansion
4. **User Confidence & Safety** - Provide visual confirmation and safeguards to ensure no unique/important images are deleted

### Core Strategy
- Use perceptual hashing (pHash, dHash) for detecting near-duplicate images
- Leverage Google Drive API v3 for file operations
- Implement efficient batch processing for large image libraries
- Provide user control over deletion decisions with preview/comparison features

## Technical Context

### Platform Considerations

#### Google Drive & Google Photos
- **API**: Use Google Drive API v3 (via `google-api-python-client`)
- **Authentication**: OAuth 2.0 flow with appropriate scopes
- **Key Scopes Needed**:
  - `https://www.googleapis.com/auth/drive.readonly` - For reading files
  - `https://www.googleapis.com/auth/drive.file` - For app-created files
  - `https://www.googleapis.com/auth/drive` - Full access (if user consents to deletions)
- **Note**: Google Photos API underwent breaking changes (March 31, 2025), limited duplicate detection capabilities
- **File Filtering**: Use `mimeType` queries to filter image types (e.g., `mimeType contains 'image/'`)
- **Metadata**: Access file size, MD5 checksum, creation date, dimensions via API

#### Windows PC (Local File System)
- **File Discovery**: Use `pathlib.Path.rglob()` or `os.walk()` for recursive directory traversal
- **File Filtering**: Filter by extension (`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.heic`, etc.)
- **Metadata**: Use `PIL/Pillow` for EXIF data, `os.stat()` for file size/dates
- **Hash Computation**: Compute MD5/SHA256 directly from file bytes using `hashlib`
- **Performance**: Use multiprocessing/threading for parallel hash computation
- **Permissions**: Handle read-only files, system directories, permission errors gracefully
- **Path Handling**: Use `pathlib` for cross-platform compatibility (though focusing on Windows)
- **Special Considerations**:
  - Windows hidden files/folders (respect user settings)
  - OneDrive/Dropbox sync folders (may overlap with cloud scanning)
  - Network drives and external storage (USB drives, NAS)
  - Junction points and symbolic links (avoid infinite loops)

### Duplicate Detection Approach

#### Methods (in order of implementation priority)
1. **MD5 Hash Matching** (Exact duplicates)
   - Google Drive API provides MD5 checksums via `files.get(fields='md5Checksum')`
   - Fast, efficient for finding identical files
   - Catches exact duplicates, even if renamed

2. **Perceptual Hashing** (Near duplicates)
   - Use Python library `imagehash` or `dhash`
   - Key algorithms:
     - **dHash (Difference Hash)**: Fast, good for similar images
     - **pHash (Perceptual Hash)**: More robust to transformations
     - **aHash (Average Hash)**: Simple but less accurate
   - Compare hash Hamming distance (threshold typically 5-10 for near-duplicates)
   - Requires downloading image or thumbnail for processing

3. **Image Metadata Comparison**
   - File size, dimensions, creation date
   - Quick pre-filter before hash computation
   - Helps group likely duplicates

### Storage Optimization Strategies

Beyond duplicate removal:
1. **Compression Analysis** - Identify poorly compressed images that could be re-encoded
2. **Resolution Downsampling** - Flag oversized images (e.g., 8K photos for web use)
3. **Format Conversion** - Suggest modern formats (WebP, AVIF) for better compression
4. **Unused File Detection** - Find files not accessed in X months
5. **Thumbnail Generation** - Verify Google Drive auto-generates thumbnails to avoid downloads

## Development Guidelines

### Code Style & Structure
- **Language**: Python 3.10+ (for modern type hints and pattern matching)
- **Async/Await**: Use async operations for API calls when processing large batches
- **Error Handling**: Graceful degradation for API rate limits, network issues
- **Progress Tracking**: Implement progress bars (e.g., `tqdm`) for long operations
- **Logging**: Structured logging for debugging and audit trails

### Key Libraries
```python
# Google APIs
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client

# Image processing & hashing
Pillow  # Image manipulation
imagehash  # Perceptual hashing
dhash  # Alternative hashing

# Utilities
tqdm  # Progress bars
pandas  # Data analysis/reporting
tabulate  # Nice output formatting
```

### API Best Practices
- **Pagination**: Always handle `nextPageToken` for large file lists
- **Rate Limiting**: Implement exponential backoff for 429 errors
- **Batch Requests**: Use batch endpoints when available
- **Partial Fields**: Request only needed fields (e.g., `fields='files(id,name,md5Checksum,size)'`)
- **Caching**: Cache file metadata locally to avoid redundant API calls

### Testing Considerations
- Use Google Drive API test accounts with controlled datasets
- Create test fixtures with known duplicates (exact, near, false positives)
- Mock API responses for unit tests to avoid rate limits
- Test edge cases: large files, uncommon formats, corrupted images

## Critical: Images Are Personal Data

### User Confidence & Deletion Safety

**Images are among the most personal and irreplaceable data users possess.** Family photos, memories, and important moments cannot be recreated if accidentally deleted. This project MUST prioritize user confidence and safety above all else.

#### Core Safety Principles
1. **Visual Confirmation Required** - Users must SEE what they're deleting before it happens
2. **Reversible Actions** - All deletions should be staged/reversible until user explicitly confirms
3. **Conservative Matching** - When in doubt, DON'T mark as duplicate
4. **Clear Communication** - Explain WHY images are considered duplicates with evidence
5. **No Surprises** - Never auto-delete without explicit user consent

#### Staging/Trash Mechanism
Implement a multi-stage deletion workflow:

1. **Detection Phase**: Identify potential duplicates
2. **Review Phase**: User reviews side-by-side comparisons with metadata
3. **Staging Phase**: Move to "Pending Deletion" folder (not deleted yet)
4. **Confirmation Phase**: User explicitly confirms final deletion
5. **Execution Phase**: Permanent deletion OR move to system trash/recycle bin

**Implementation Approaches:**
- **Local Files**: Move to temporary `.image-organizer-staging/` folder before deletion
- **Google Drive**: Move to trash first (allows 30-day recovery), then optionally empty trash
- **Visual Interface**: Show thumbnail grid of "To Be Deleted" vs "To Keep" with easy swap controls
- **Undo Stack**: Maintain operation history for multi-step undo

#### Visual Confirmation Features
- **Side-by-side image viewer** with zoom and metadata comparison
- **Difference highlighting** to show what's different between near-duplicates
- **Quality indicators** (resolution, file size, compression artifacts)
- **EXIF data display** (date taken, camera, location if available)
- **File path/location display** to understand context
- **Duplicate group visualization** (show all images in a cluster, not just pairs)

## Security & Privacy

### Data Handling
- **Local Processing**: Download images temporarily for hashing, delete immediately after
- **No Cloud Storage**: Don't upload image data to third-party services
- **Token Storage**: Securely store OAuth tokens (use keyring or encrypted config)
- **User Consent**: Always preview deletions before executing
- **Audit Log**: Keep record of deleted files (optional user feature)

### OAuth Scopes
- Request minimal scopes initially (readonly)
- Prompt for elevated permissions only when needed (delete operations)
- Explain scope usage clearly to users

## User Experience

### CLI Design (Initial MVP)
```bash
# Scan for duplicates (specify platform)
image-organizer scan --platform google-drive --threshold 5
image-organizer scan --platform windows --path "C:\Users\John\Pictures" --threshold 5
image-organizer scan --platform all  # Scan all configured platforms

# Review duplicates interactively (REQUIRED before deletion)
image-organizer review --duplicates-file duplicates.json
# Opens visual interface showing side-by-side comparisons

# Stage files for deletion (move to staging area)
image-organizer stage --duplicates-file duplicates.json

# Preview what will be deleted (dry-run)
image-organizer cleanup --dry-run --show-thumbnails

# Execute cleanup (move to trash/recycle bin first)
image-organizer cleanup --confirm --use-trash

# Undo last operation
image-organizer undo

# Permanently empty staging area (REQUIRES EXPLICIT CONFIRMATION)
image-organizer empty-staging --confirm
```

### Interactive Features (Safety-First Design)
- **Side-by-side image comparison viewer** with zoom, pan, and metadata overlay
- **Smart suggestions** (not automatic) for lower-quality duplicates - user always decides
- **Whitelist/blacklist folders** (e.g., never touch "Family Photos" folder)
- **Multi-level undo capability**:
  - Undo staging decisions
  - Restore from staging area
  - Recover from system trash/recycle bin
  - Export operation log for manual recovery
- **Confidence scoring**: Display similarity percentage and reasoning
- **Batch review modes**: 
  - "Show only exact matches" (MD5 identical)
  - "Show questionable matches" (for manual review)
  - "Show all matches" (default)
- **Quick preview**: Hover over any image for instant enlarged view
- **Keyboard shortcuts**: Fast navigation (Y/N/Skip/Flag for manual review)
- **Safety warnings**: Alert if deleting images without backup, or from critical folders

### Reporting
- Summary statistics (files scanned, duplicates found, space saved)
- CSV/JSON export of findings
- Visual charts (size distribution, duplicate clusters)

## Future Enhancements

### Phase 2 Platforms
- Additional cloud providers (Dropbox, OneDrive, iCloud)
- Photo management apps (Lightroom, Digikam)
- Network Attached Storage (NAS)
- External drives (USB, portable HDDs)
- Mobile device integration (Android, iOS)

### Advanced Features
- **ML-based similarity** (beyond perceptual hashing) - with explainable AI for user trust
- **Face recognition clustering** - identify which family members are in photos (privacy-focused, local processing)
- **Smart duplicate resolution** - suggest which photo to keep based on quality metrics (user confirms)
- **Backup verification** - ensure backups exist before allowing deletion
- **Automated cleanup policies** - with strict safeguards and user approval
- **Web UI / desktop GUI** - full-featured visual interface
- **"Protected folders" feature** - mark certain directories as never-scan
- **Duplicate timeline visualization** - show when duplicates were created

## Important Notes

### Google API Limitations
- **Google Photos API**: Limited scope as of April 2025 - focus on Google Drive instead
- **Quota Limits**: 10,000 requests/day (default free tier) - design for efficiency
- **Download Limits**: Large files may hit bandwidth caps - use thumbnails when possible
- **Scope Changes**: Monitor Google API deprecation announcements

### Perceptual Hashing Trade-offs
- **Threshold Tuning**: Lower = more false negatives, higher = more false positives
- **Format Sensitivity**: JPEG artifacts may affect similarity scores
- **Performance**: Processing thousands of images takes time - optimize with parallelism

## Code Examples & References

When implementing features, refer to:
- [Google Drive API v3 Python Quickstart](https://developers.google.com/drive/api/quickstart/python)
- [imagehash library documentation](https://github.com/JohannesBuchner/imagehash)
- [Perceptual hashing best practices](https://benhoyt.com/writings/duplicate-image-detection/)

## Implementation Phases

### Phase 1: Foundation (MVP)
**Goal**: Core duplicate detection for local Windows files

- Set up Python project structure with Poetry/pip
- Implement MD5 hash-based exact duplicate detection
- Basic CLI for scanning directories
- Staging mechanism (no actual deletion yet)
- JSON report generation
- See `IMPLEMENTATION_PLAN.md` for detailed tasks

### Phase 2: Perceptual Hashing
**Goal**: Near-duplicate detection

- Integrate `imagehash` library
- Implement dHash/pHash comparison
- Threshold tuning utilities
- Enhanced reporting with similarity scores

### Phase 3: Safety & Review UI
**Goal**: Visual confirmation system

- Side-by-side image comparison viewer
- Staging area management
- Undo/rollback capabilities
- Protected folders configuration
- Safe deletion to recycle bin

### Phase 4: Google Drive Integration
**Goal**: Cloud storage support

- OAuth authentication flow
- Drive API pagination and batching
- Thumbnail-based duplicate detection
- Google Drive trash integration
- Cross-platform duplicate detection (local + cloud)

### Phase 5: Advanced Features
**Goal**: Enhanced automation and intelligence

- ML-based similarity detection
- Automated quality assessment
- Compression analysis
- Batch operations
- Web UI (optional)

## Skills and Prompts

This project includes GitHub Copilot skills and prompts in `.github/`:

- **Skills** (`.github/skills/`): Automatically loaded contextual guides
  - `safe-image-deletion` - Deletion safety patterns
  - `image-duplicate-detection` - Duplicate detection workflows
  - `google-drive-api-integration` - Drive API best practices

- **Prompts** (`.github/prompts/`): Task-specific prompt templates
  - `review-deletion-candidates.prompt.md` - Generate review UI
  - `optimize-api-calls.prompt.md` - Audit API efficiency
  - `add-safety-checks.prompt.md` - Add safety validation

Refer to these when implementing related features.

## Conversation Style

When pair-programming with developers on this project:
- Suggest concrete code implementations, not just concepts
- **Always emphasize safety-first design in suggestions**
- Highlight potential API gotchas (rate limits, pagination, error codes)
- **Question any feature that could lead to accidental data loss**
- Offer multiple approaches with trade-off analysis
- Reference specific library functions and parameters
- Provide runnable code snippets with proper error handling
- **Remind developers: these are people's irreplaceable memories - treat with care**
- Suggest defensive coding practices (validate, confirm, log, allow undo)
- Encourage comprehensive testing with real-world edge cases

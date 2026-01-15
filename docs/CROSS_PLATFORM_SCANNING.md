# Cross-Platform Duplicate Detection

**Find duplicates across local files AND Google Drive**

The `cross-platform-scan` command helps you identify files that exist in BOTH your local computer and Google Drive, enabling you to:
- **Free up local disk space** by keeping cloud copies
- **Identify already-backed-up files** before syncing
- **Optimize storage** across platforms
- **Avoid redundant backups**

## Quick Start

```bash
# Scan a local folder and compare with Google Drive
image-organizer cross-platform-scan --local-path "C:\Users\John\Pictures"

# Specify output file
image-organizer cross-platform-scan --local-path ~/Downloads --output results.json

# Scan specific image types
image-organizer cross-platform-scan --local-path ~/Photos --extensions .jpg --extensions .png
```

## How It Works

The cross-platform scanner:

1. **Scans your local directory** - Recursively finds all image files and computes MD5 hashes
2. **Scans Google Drive** - Fetches all images and their MD5 checksums via Drive API
3. **Matches by MD5** - Files with identical MD5 hashes are duplicates (exact copies)
4. **Shows locations** - Reports where each duplicate exists (local paths + Drive IDs)
5. **Calculates savings** - Shows how much space you can recover

## Output

### Console Summary

```
Cross-Platform Duplicate Scanner
Local path: C:\Users\John\Downloads
Google Drive: Authenticating...

Scanning local files...
Found 44 local image files

Scanning Google Drive...
OK Found 242 images in Google Drive

Detecting cross-platform duplicates...

OK Found 3 duplicate groups!
Total files: 12
Local space: 15.3 MB
Drive space: 15.3 MB
💾 Potential savings: 15.3 MB

┏━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ # ┃ File Name            ┃    Size ┃ Local Copies ┃ Drive Copies ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 1 │ vacation.jpg         │ 5.2 MB  │      1       │      1       │
│ 2 │ family-photo.png     │ 8.1 MB  │      2       │      1       │
│ 3 │ screenshot.png       │ 2.0 MB  │      1       │      3       │
└───┴──────────────────────┴─────────┴──────────────┴──────────────┘

OK Results saved to: cross-platform-scan-20260115-123456.json
```

### JSON Output

The JSON file contains detailed information for each duplicate:

```json
{
  "scan_date": "2026-01-15T12:34:56.789",
  "local_path": "C:\\Users\\John\\Downloads",
  "statistics": {
    "duplicate_groups": 3,
    "total_files": 12,
    "local_space_mb": 15.3,
    "drive_space_mb": 15.3,
    "potential_savings_mb": 15.3
  },
  "duplicates": [
    {
      "md5": "a1b2c3d4e5f6...",
      "name": "vacation.jpg",
      "size": 5452301,
      "local_files": [
        {
          "path": "C:\\Users\\John\\Downloads\\vacation.jpg",
          "name": "vacation.jpg",
          "size": 5452301,
          "modified": "2026-01-10T15:23:45.123456"
        }
      ],
      "drive_files": [
        {
          "id": "1ABC...xyz",
          "name": "vacation.jpg",
          "size": 5452301,
          "modified": "2026-01-10T20:23:45.000Z",
          "url": "https://drive.google.com/file/d/1ABC...xyz/view"
        }
      ]
    }
  ]
}
```

## Common Scenarios

### Scenario 1: Free Up Local Disk Space

**Problem**: Your laptop is running out of space, but all photos are backed up to Drive.

**Solution**:
```bash
# Find duplicates in Pictures folder
image-organizer cross-platform-scan --local-path "C:\Users\John\Pictures"

# Review results - shows which files are safely in Drive
# Manually delete local copies to free up space
```

### Scenario 2: Identify Already-Backed-Up Files

**Problem**: You want to upload files to Drive but don't know which ones are already there.

**Solution**:
```bash
# Scan before uploading
image-organizer cross-platform-scan --local-path ~/Downloads

# JSON file shows which files are already in Drive
# Only upload files NOT in the duplicates list
```

### Scenario 3: Optimize Cloud Storage

**Problem**: You have files in both Drive and locally, taking up space in both places.

**Solution**:
```bash
# Find all cross-platform duplicates
image-organizer cross-platform-scan --local-path ~/Documents

# Decide strategy:
# - Keep Drive copies → Delete local files
# - Keep local copies → Delete from Drive (use drive-trash command)
```

### Scenario 4: Verify Sync Accuracy

**Problem**: You use a sync tool but want to verify files are identical.

**Solution**:
```bash
# Scan synced folder
image-organizer cross-platform-scan --local-path "C:\OneDrive\Photos"

# MD5 match confirms files are EXACT copies
# No match means files differ (version mismatch)
```

## Understanding the Results

### MD5 Hash Matching

- **Exact duplicates only** - Files must be byte-for-byte identical
- **Different names OK** - Files can have different names but same content
- **No false positives** - MD5 match guarantees identical files

### Local vs Drive Copies

**Multiple copies**: A file can exist multiple times on each platform:
- 2 local copies + 1 Drive copy = 3 total files
- 1 local copy + 3 Drive copies = 4 total files

**Example**:
```
vacation.jpg (MD5: abc123)
  Local:
    - C:\Photos\vacation.jpg
    - C:\Backup\vacation.jpg
  Drive:
    - /Family Photos/vacation.jpg
    - /Vacation 2025/vacation.jpg

Total: 4 copies (2 local, 2 Drive)
```

### Space Savings

**Potential savings** = Minimum of (local space, Drive space)

- If you delete all **local** copies → Free up local disk space
- If you delete all **Drive** copies → Free up cloud storage
- You can only save space on ONE platform (must keep at least one copy somewhere)

## Integration with Other Commands

### Delete Local Files

After finding cross-platform duplicates, delete local copies manually:

```bash
# On Windows
del "C:\path\to\duplicate.jpg"

# Use confirm-delete for safety (if in staging)
image-organizer confirm-delete
```

### Delete Drive Files

Use Drive commands to remove cloud copies:

```bash
# Scan Drive for duplicates
image-organizer drive-scan --output drive-dupes.json

# Trash Drive copies
image-organizer drive-trash --input drive-dupes.json --confirm
```

## Command Reference

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--local-path` / `-l` | Local directory to scan (required) | - |
| `--output` / `-o` | Output JSON file path | `cross-platform-scan-<timestamp>.json` |
| `--extensions` / `-e` | File extensions to scan (can specify multiple) | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.heic` |

### Examples

```bash
# Scan Pictures folder
image-organizer cross-platform-scan --local-path "C:\Users\John\Pictures"

# Scan multiple image types
image-organizer cross-platform-scan -l ~/Photos -e .jpg -e .png -e .heic

# Custom output file
image-organizer cross-platform-scan -l ~/Downloads -o my-duplicates.json
```

## Limitations

### What It Does

✅ Detects **exact** duplicates (same MD5 hash)  
✅ Matches files across platforms  
✅ Shows all file locations  
✅ Calculates space usage  

### What It Doesn't Do

❌ Does NOT automatically delete files (manual decision required)  
❌ Does NOT detect near-duplicates (only exact matches)  
❌ Does NOT compare metadata (only file content via MD5)  
❌ Does NOT sync files between platforms  

## Best Practices

### Before Deleting

1. **Verify backups** - Ensure Drive copies are accessible
2. **Check file dates** - Keep the newest/highest quality version
3. **Test with small batch** - Delete a few files first, verify they're safe
4. **Use trash first** - Move to trash, not permanent delete

### For Large Libraries

1. **Scan by folder** - Don't scan entire C:\ drive at once
2. **Use specific extensions** - Limit to needed file types
3. **Review JSON offline** - Edit JSON to select specific files
4. **Batch operations** - Delete in groups, verify after each batch

### Safety

- **Always keep at least one copy** (either local OR Drive)
- **Verify MD5 match** before deleting valuable files
- **Use Drive trash** (30-day recovery) instead of permanent deletion
- **Backup important files** before large cleanup operations

## Troubleshooting

### "Not authenticated" Error

**Solution**: Run `image-organizer drive-auth` first to authenticate with Google Drive.

### Slow Scanning

**Cause**: Large number of local files or Drive files.

**Solutions**:
- Scan smaller directories first
- Limit file extensions with `--extensions`
- Be patient - large libraries take time

### Missing Expected Duplicates

**Reasons**:
- Files have different content (even slight differences change MD5)
- File is edited/modified after upload
- File format conversion (JPG → PNG changes MD5)
- Drive API may not return all files (check Drive web UI)

### High Memory Usage

**Cause**: Processing thousands of files.

**Solutions**:
- Scan smaller directories
- Close other applications
- Upgrade RAM if scanning very large libraries

## Technical Details

### MD5 Hash Computation

- **Local files**: Computed directly from file bytes
- **Drive files**: Retrieved from Drive API (pre-computed by Google)
- **Collision risk**: Negligible for duplicate detection purposes

### Performance

- **Local scanning**: ~100-500 files/second (depends on disk speed)
- **Drive API**: Limited by Google API rate limits (~1000 files/request)
- **Comparison**: Near-instant (hash table lookup)

### Privacy

- **No cloud uploads**: All MD5 computation done locally
- **OAuth authentication**: Secure Google Drive access
- **No third-party services**: Direct Drive API integration

## See Also

- [Google Drive Setup](GOOGLE_DRIVE_SETUP.md) - OAuth configuration
- [Document Scanning](DOCUMENT_SCANNING.md) - Scan Drive documents
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Development roadmap

# Near-Duplicate Detection - Quick Reference

## Commands

### Fast Mode (Exact Duplicates Only)
```bash
# MD5-based, instant results, no downloads
image-organizer drive-scan --output duplicates.json
```

### Comprehensive Mode (Exact + Near-Duplicates)
```bash
# Includes perceptual hashing, downloads thumbnails
image-organizer drive-scan --near-duplicates --threshold 10 --output all-duplicates.json
```

### Testing with Limited Files
```bash
# Scan only first 100 files (for testing)
image-organizer drive-scan --near-duplicates --max-files 100
```

## Threshold Values

| Value | Similarity Level | Best For |
|-------|-----------------|----------|
| 0-3   | Nearly identical | Minor edits only |
| 4-7   | Very similar | Standard crops/resizes |
| **8-12** | **Similar** | **Recommended default** |
| 13-20 | Somewhat similar | Burst photos |
| 21+   | Loose (risky) | Not recommended |

## What Gets Detected

### Exact Duplicates (Always Found)
- ✅ Same file uploaded twice
- ✅ File copied with new name
- ✅ Identical pixel data

### Near-Duplicates (With `--near-duplicates`)
- ✅ Cropped versions
- ✅ Resized versions
- ✅ Color/brightness adjusted
- ✅ Filtered (Instagram, etc.)
- ✅ Screenshots of images
- ✅ Burst photos (similar scenes)
- ✅ Re-encoded (different JPEG quality)
- ✅ Images with text overlays

### Not Detected
- ❌ Completely different images
- ❌ Different subjects/scenes
- ❌ Heavy rotation (>45 degrees)
- ❌ Severely cropped (<50% overlap)

## Output Example

```
═══ Exact Duplicates (MD5) ═══
✓ Found 5 groups (12 duplicate files)
Space savings: 45.3 MB

═══ Near-Duplicates (Perceptual Hash) ═══
✓ Found 8 files with similar images (20 total pairs)
```

## Performance

| Files | Exact Only | With Near-Duplicates |
|-------|-----------|---------------------|
| 100   | ~2 sec    | ~30 sec |
| 500   | ~5 sec    | ~2 min |
| 1,000 | ~10 sec   | ~5 min |
| 5,000 | ~30 sec   | ~20 min |

## Troubleshooting

### "imagededup not installed"
```bash
pip install imagededup
```

### Near-duplicates too strict (missing matches)
```bash
# Increase threshold (more lenient)
image-organizer drive-scan --near-duplicates --threshold 15
```

### Near-duplicates too loose (false positives)
```bash
# Decrease threshold (more strict)
image-organizer drive-scan --near-duplicates --threshold 5
```

### Slow performance
```bash
# Scan in batches
image-organizer drive-scan --near-duplicates --max-files 500 --output batch1.json
image-organizer drive-scan --near-duplicates --max-files 500 --output batch2.json
```

### Save thumbnails for reuse
```bash
# First scan - downloads thumbnails
image-organizer drive-scan --near-duplicates --thumbnail-dir ~/my-thumbnails

# Later scans - reuses same thumbnails (faster!)
image-organizer drive-scan --near-duplicates --threshold 8 --thumbnail-dir ~/my-thumbnails
```

## API Reference

### Python API

```python
from image_organizer.platforms.google_drive import GoogleDriveClient
from pathlib import Path

client = GoogleDriveClient()
client.authenticate()

# Get all image files
files = client.list_image_files()

# Find exact duplicates only (fast)
exact_dupes = client.find_exact_duplicates_by_md5(files)

# Find near-duplicates only
near_dupes = client.find_near_duplicates_by_phash(
    files, 
    thumbnail_dir=Path("/tmp/thumbnails"),
    threshold=10
)

# Find both (recommended)
results = client.find_all_duplicates(
    files,
    thumbnail_dir=Path("/tmp/thumbnails"),
    phash_threshold=10,
    include_near_duplicates=True
)

print(f"Exact: {results['stats']['exact_duplicate_groups']} groups")
print(f"Near: {results['stats']['near_duplicate_groups']} groups")
```

## Next Steps

After scanning:

1. **Review Results**: Open the JSON output file
2. **Verify Duplicates**: Check sample groups manually
3. **Adjust Threshold**: Re-run with different threshold if needed
4. **Plan Cleanup**: Decide which files to keep/delete
5. **Use Review UI**: (Coming in Phase 3.7) Visual side-by-side comparison

## Related Commands

```bash
# Authenticate first (one-time)
image-organizer drive-auth --credentials ~/credentials.json

# List files without duplicate detection
image-organizer drive-scan --list-only

# Check help
image-organizer drive-scan --help
```

## Tips

1. **Start with exact duplicates** - Fast and safe
2. **Try threshold 10 first** - Good balance
3. **Scan in batches** - For large libraries (1000+ files)
4. **Save thumbnails** - Reuse for multiple scans with different thresholds
5. **Review manually** - Don't auto-delete without checking!

---

**Last Updated**: January 13, 2026  
**Feature Version**: Phase 3.3 Complete  
**Test Coverage**: 32 tests passing, 63% google_drive.py coverage

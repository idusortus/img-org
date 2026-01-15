# Document Duplicate Scanning

The `drive-scan-docs` command scans Google Drive for duplicate documents instead of images.

## Quick Start

```bash
# Scan all documents
image-organizer drive-scan-docs --output docs-duplicates.json

# Scan specific folder
image-organizer drive-scan-docs --folder-name "Work Documents" --output work-dups.json
```

## Supported Document Types

### Default Scanning (all types)
- **Microsoft Office**: .docx, .doc, .xlsx, .xls, .pptx, .ppt
- **PDF**: .pdf
- **Text**: .txt, .csv, .tsv
- **Google Workspace**: Google Docs, Google Sheets, Google Slides
- **OpenDocument**: .odt, .ods, .odp
- **Other**: .rtf

## Common Usage

### Scan PDFs Only
```bash
image-organizer drive-scan-docs --mime-type "application/pdf" --output pdfs.json
```

### Scan Office Documents Only (Word + Excel)
```bash
image-organizer drive-scan-docs \
  --mime-type "application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  --output office-docs.json
```

### Exclude Google Workspace Native Formats
Google Docs/Sheets/Slides don't have MD5 checksums since they're not "files" in the traditional sense. To scan only downloadable documents:

```bash
image-organizer drive-scan-docs \
  --exclude-mime-type "application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation" \
  --output downloadable-docs.json
```

### Scan Specific Folder
```bash
# By folder name
image-organizer drive-scan-docs --folder-name "Tax Documents" --output taxes.json

# By folder ID
image-organizer drive-scan-docs --folder-id "1a2b3c4d5e6f" --output folder-dups.json

# Without subfolders
image-organizer drive-scan-docs --folder-name "Contracts" --no-recursive --output contracts.json
```

### Just List Documents (No Duplicate Detection)
```bash
image-organizer drive-scan-docs --list-only
```

## Complete MIME Types Reference

### Microsoft Office
- **Word**: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (.docx)
- **Word (old)**: `application/msword` (.doc)
- **Excel**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (.xlsx)
- **Excel (old)**: `application/vnd.ms-excel` (.xls)
- **PowerPoint**: `application/vnd.openxmlformats-officedocument.presentationml.presentation` (.pptx)
- **PowerPoint (old)**: `application/vnd.ms-powerpoint` (.ppt)

### PDF & Text
- **PDF**: `application/pdf`
- **Plain text**: `text/plain` (.txt)
- **CSV**: `text/csv`
- **TSV**: `text/tab-separated-values`

### Google Workspace
- **Google Docs**: `application/vnd.google-apps.document`
- **Google Sheets**: `application/vnd.google-apps.spreadsheet`
- **Google Slides**: `application/vnd.google-apps.presentation`

### OpenDocument
- **Text**: `application/vnd.oasis.opendocument.text` (.odt)
- **Spreadsheet**: `application/vnd.oasis.opendocument.spreadsheet` (.ods)
- **Presentation**: `application/vnd.oasis.opendocument.presentation` (.odp)

### Other
- **RTF**: `application/rtf`

## How It Works

1. **Lists files**: Queries Google Drive API for document files
2. **MD5 checksums**: Groups files by their MD5 hash (no downloads required)
3. **Duplicate detection**: Files with identical MD5 = exact duplicates
4. **Reports results**: Shows duplicate groups and potential space savings

## Output Format

Same JSON format as image scanning:

```json
{
  "md5-checksum-here": [
    {
      "id": "drive-file-id",
      "name": "document.pdf",
      "size": "1048576",
      "md5": "md5-checksum-here"
    },
    {
      "id": "another-drive-file-id",
      "name": "document-copy.pdf",
      "size": "1048576",
      "md5": "md5-checksum-here"
    }
  ]
}
```

## Limitations

1. **Google Workspace files**: Native Google Docs/Sheets/Slides don't have MD5 checksums (they're not stored as binary files). They'll be listed but may not participate in duplicate detection properly.

2. **No near-duplicates**: Unlike images, document scanning only supports exact MD5 matching (no perceptual/content similarity).

3. **Read-only scopes**: Current authentication only allows scanning, not deletion/modification.

## Next Steps

After scanning, you can:
1. Review the JSON output manually
2. (Future) Use `drive-move-duplicates` to move duplicates to a folder
3. (Future) Use `drive-trash` to move duplicates to trash
4. (Future) Use `drive-review` for interactive side-by-side comparison

## Tips

- **Start small**: Test with `--folder-name` first before scanning entire Drive
- **Use exclusions**: Skip Google Workspace native formats for cleaner results
- **Check file types**: Use `--list-only` to see what's in a folder before scanning
- **Export lists**: Save output with `--output` for batch processing later

## Examples

### Scan Downloads folder for duplicate PDFs
```bash
image-organizer drive-scan-docs \
  --folder-name "Downloads" \
  --mime-type "application/pdf" \
  --output downloads-pdfs.json
```

### Find duplicate contracts (Word + PDF)
```bash
image-organizer drive-scan-docs \
  --folder-name "Legal/Contracts" \
  --mime-type "application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf" \
  --output contract-dups.json
```

### List all text files in a project folder
```bash
image-organizer drive-scan-docs \
  --folder-name "Project Notes" \
  --mime-type "text/plain,text/csv" \
  --list-only
```

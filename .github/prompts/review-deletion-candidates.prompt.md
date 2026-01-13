---
name: Review Deletion Candidates
description: Generate a comprehensive side-by-side comparison report for duplicate images pending deletion
tags: [duplicates, review, safety, reporting]
---

# Review Deletion Candidates

You are helping generate a safe, visual review interface for duplicate images before deletion.

## Context

The user has run duplicate detection and needs to review the results before any files are deleted. This is a **critical safety step** - we're dealing with irreplaceable personal photos.

## Your Task

Generate code or a report that:

1. **Creates side-by-side comparisons** showing:
   - Thumbnail of each image in duplicate group
   - File path/location
   - File size
   - Image dimensions (width x height)
   - Creation/modification date
   - Quality indicators (resolution, compression)
   - Similarity score (if near-duplicate)

2. **Recommends which to keep** based on:
   - Higher resolution = prefer
   - Larger file size (less compressed) = prefer
   - Better quality (fewer artifacts) = prefer
   - Earlier creation date = prefer (original)
   - **BUT**: Always mark as "suggestion" - user decides

3. **Provides clear actions**:
   - Swap keep/delete decision
   - Skip group (keep all)
   - Add to protected list
   - View full-size comparison

4. **Includes safety warnings**:
   - Number of files to be deleted
   - Total space to be freed
   - Reminder that files go to staging first
   - Undo capability available

## Output Format

Generate either:
- HTML report with embedded thumbnails
- Terminal UI with ASCII art previews
- JSON structure for custom UI
- Markdown report with image links

## Example Structure

```
Duplicate Group 1 (Exact Match - MD5 identical)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[KEEP]                          [DELETE]
┌──────────────────┐           ┌──────────────────┐
│  [Thumbnail]     │           │  [Thumbnail]     │
└──────────────────┘           └──────────────────┘

vacation_2024.jpg              vacation_2024 (1).jpg
C:\Photos\Summer\              C:\Downloads\
2.4 MB | 3000x2000             2.4 MB | 3000x2000
Created: 2024-06-15            Modified: 2024-06-16

✅ RECOMMENDED: Keep left (earlier date)

[S] Swap | [K] Keep Both | [D] Delete Both | [N] Next

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Safety Reminders

- Never auto-confirm deletions
- Always show thumbnails, not just filenames
- Group images by confidence level (exact vs near matches)
- Allow easy reversal of all decisions
- Highlight if file is from a potentially important folder

## Required Information

If any of this information is missing in the input, ask for it:
- Duplicate groups data (file paths, hashes, similarity scores)
- Image metadata (dimensions, dates, sizes)
- Thumbnail paths or data
- User's protected folder list (if any)

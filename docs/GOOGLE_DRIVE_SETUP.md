# Google Drive Setup Guide

This guide walks you through setting up Google Drive integration for Image Organizer.

## Prerequisites

- Google account
- Python 3.10+ with Image Organizer installed
- Web browser

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: "Image Organizer" (or any name)
4. Click "Create"
5. Wait for project creation (takes ~30 seconds)

## Step 2: Enable Google Drive API

1. In the Cloud Console, select your new project
2. Go to **APIs & Services** → **Library**
3. Search for "Google Drive API"
4. Click "Google Drive API"
5. Click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
3. If prompted, configure consent screen:
   - Click "CONFIGURE CONSENT SCREEN"
   - Choose "External" (unless you have Google Workspace)
   - Fill in required fields:
     - App name: "Image Organizer"
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - Skip "Scopes" section (click "Save and Continue")
   - Add yourself as test user:
     - Click "+ ADD USERS"
     - Enter your Gmail address
     - Click "Add"
   - Click "Save and Continue"
   - Click "Back to Dashboard"

4. Back in Credentials page, click "+ CREATE CREDENTIALS" → "OAuth client ID"
5. Choose application type: **Desktop app**
6. Name: "Image Organizer Desktop" (or any name)
7. Click "Create"
8. Click "Download JSON" in the popup
9. Save the file (e.g., `~/Downloads/credentials.json`)

**Important**: Keep this file secure! It contains your OAuth client secrets.

## Step 4: Authenticate Image Organizer

Run the authentication command:

```bash
image-organizer drive-auth --credentials ~/Downloads/credentials.json
```

What happens:
1. Opens your web browser
2. Asks you to sign in to Google
3. Shows permission request:
   - "View and download your Google Drive files"
   - "View metadata for files in your Google Drive"
4. Click "Continue" (or "Allow")
5. Browser shows "The authentication flow has completed"
6. Token saved to `~/.image-organizer/token.json`

## Step 5: Test the Connection

List your Google Drive images:

```bash
image-organizer drive-scan --list-only --max-files 10
```

You should see a table with your first 10 image files from Drive.

## Step 6: Scan for Duplicates

### Option A: Fast Scan (Exact Duplicates Only)

```bash
image-organizer drive-scan --output drive-duplicates.json
```

This will:
- List all images in your Google Drive
- Detect exact duplicates using MD5 checksums
- Save results to `drive-duplicates.json`

**No images are downloaded** - duplicate detection uses Drive's built-in MD5 checksums!

### Option B: Comprehensive Scan (Exact + Near-Duplicates)

```bash
image-organizer drive-scan --near-duplicates --threshold 10 --output all-duplicates.json
```

This will:
- Find exact duplicates (MD5-based, instant)
- Download thumbnails (400x400px)
- Find near-duplicates using perceptual hashing
- Detect edited, cropped, resized, or similar images

**What counts as "near-duplicate"?**
- Cropped or resized versions
- Screenshots of the same image
- Color-adjusted or filtered versions
- Similar photos from a burst sequence
- Re-encoded versions with different compression

**Threshold values** (0-64, lower = more strict):
- `0-5`: Very similar (almost identical)
- `5-10`: Similar (recommended default)
- `10-20`: Somewhat similar
- `20+`: Loose matching (may have false positives)

## Troubleshooting

### "Credentials file not found"
- Make sure you downloaded the JSON file from Step 3
- Use the full path: `image-organizer drive-auth --credentials /full/path/to/credentials.json`

### "Access blocked: This app's request is invalid"
- Go back to Step 3 and ensure you configured the OAuth consent screen
- Make sure you added yourself as a test user
- Check that you enabled the Google Drive API in Step 2

### "Token expired" or "Invalid authentication"
- Delete the old token: `rm ~/.image-organizer/token.json`
- Re-run authentication: `image-organizer drive-auth`

### "Rate limit exceeded"
- Google Drive API has quotas (10,000 requests/day for free tier)
- Image Organizer automatically retries with exponential backoff
- For large libraries, consider scanning in batches: `drive-scan --max-files 1000`

## Privacy & Security

### What permissions does Image Organizer need?

**Read-only access to your Drive files**:
- `https://www.googleapis.com/auth/drive.readonly`
- `https://www.googleapis.com/auth/drive.metadata.readonly`

**Why these permissions?**:
- List image files in your Drive
- Read MD5 checksums for duplicate detection
- Download thumbnails for perceptual hashing (near-duplicate detection)

**We do NOT**:
- Upload or modify your files
- Access files outside Google Drive
- Share your data with third parties
- Store your files on our servers (thumbnails are temporary)

### Where are credentials stored?

- **OAuth credentials**: `~/.image-organizer/credentials.json` (you provide this)
- **OAuth tokens**: `~/.image-organizer/token.json` (generated during auth)
- **Config**: `~/.image-organizer/config.json`

All stored locally on your machine. No cloud storage.

### Can I revoke access?

Yes, anytime:
1. Go to [Google Account Security](https://myaccount.google.com/permissions)
2. Find "Image Organizer"
3. Click "Remove Access"
4. Delete local tokens: `rm ~/.image-organizer/token.json`

## Next Steps

- **Review duplicates**: Use the review command (coming in Phase 3.2)
- **Cross-platform scan**: Detect duplicates across local and Drive (Phase 3.3)
- **Safe deletion**: Stage and confirm deletions with undo capability

## API Quotas

**Google Drive API Free Tier**:
- 10,000 requests per day
- 1,000 requests per 100 seconds per user

**Image Organizer usage**:
- Listing 1,000 images: ~10 requests (pagination)
- Detecting duplicates: 0 requests (uses MD5 from list response)
- Moving to trash: 1 request per file

**Tip**: For large libraries (10,000+ images), run scans during off-peak hours or upgrade to paid quota.

## Support

Having trouble? Check:
- [Image Organizer GitHub Issues](https://github.com/yourusername/image-organizer/issues)
- [Google Drive API Documentation](https://developers.google.com/drive/api/guides/about-sdk)
- [OAuth 2.0 Troubleshooting](https://developers.google.com/identity/protocols/oauth2/resources/troubleshooting)

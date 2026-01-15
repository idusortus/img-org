# Image Organizer - Quick Start Guide

**Get up and running in 5 minutes**

## Prerequisites

- **Python 3.10 or higher** - [Download Python](https://www.python.org/downloads/)
- **Git** (optional) - For cloning the repository

Check your Python version:
```bash
python --version
# or
python3 --version
```

---

## Installation

### Option 1: Install from Source (Development Mode)

**Best for**: Development, testing, customization

```bash
# 1. Clone the repository
git clone https://github.com/idusortus/img-org.git
cd img-org

# 2. Install core dependencies
pip install Pillow imagehash tqdm send2trash click rich tabulate numpy

# 3. Install the package (without problematic imagededup build)
pip install --no-deps -e .

# 4. Verify installation
image-organizer --version
```

**Note**: `imagededup` requires C++ build tools on Windows. For now, Google Drive features work without it. Local file scanning will be updated to use `imagehash` directly in a future update.

### Option 2: Install with Google Drive Support

**Google Drive features work immediately** with the basic installation above.

To add full Google Drive API dependencies explicitly:

```bash
# Install Google Drive dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Verify Drive commands are available
image-organizer drive-auth --help
```

### Option 3: Install for Development

If you want to contribute or run tests:

```bash
# Install with development tools
pip install -e ".[dev]"

# Install everything (including Google Drive)
pip install -e ".[google-drive,dev]"
```

---

## Verify Installation

Test that the CLI is working:

```bash
# Check version
image-organizer --version

# See available commands
image-organizer --help

# List specific command help
image-organizer scan --help
```

**Expected output**: Version number and command list

---

## Quick Test: Local File Scanning

### 1. Create Test Images (Optional)

Run the demo script to generate sample images:

```bash
python demo.py
```

This creates a `demo_images/` folder with test images and duplicates.

### 2. Scan for Duplicates

```bash
# Scan a directory for duplicates
image-organizer scan --path demo_images --output duplicates.json

# Or scan your Pictures folder (Windows)
image-organizer scan --path "C:\Users\YourName\Pictures" --output duplicates.json

# Or scan your Pictures folder (Mac/Linux)
image-organizer scan --path ~/Pictures --output duplicates.json
```

### 3. Review Results

If duplicates were found:

```bash
# Interactive review with visual comparison
image-organizer review --input duplicates.json

# This will:
# - Show side-by-side comparisons
# - Display metadata (resolution, size, date)
# - Auto-recommend which to keep/delete
# - Stage files for deletion (reversible)
```

---

## Google Drive Setup (Optional)

### Prerequisites

1. **Google Cloud Project** with Drive API enabled
2. **OAuth 2.0 Credentials** (Desktop app type)

### Get Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing)
3. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
4. Choose **"Desktop app"** as application type
5. Download the JSON file (save as `credentials.json`)

### Authenticate

```bash
# Run authentication (opens browser)
image-organizer drive-auth --credentials ~/Downloads/credentials.json

# Follow browser prompts to authorize
# Token saved to ~/.image-organizer/token.json
```

**⚠️ Advanced Protection Users**: If you see "Error 400: policy_enforced", your Google account has Advanced Protection enabled, which blocks unverified third-party apps. You'll need to temporarily disable it at [myaccount.google.com/security](https://myaccount.google.com/security) → Advanced Protection Program → Turn off. **Remember to re-enable it after using the tool.** See [Troubleshooting](#google-drive-authentication-fails) section for details.

### Test Drive Access

```bash
# List first 10 images in your Drive
image-organizer drive-scan --max-files 10 --list-only

# Find exact duplicates (fast, no downloads)
image-organizer drive-scan --output drive-duplicates.json

# Find exact + near-duplicates (slower, downloads thumbnails)
image-organizer drive-scan --near-duplicates --threshold 10
```

---

## Common Workflows

### Local Duplicate Cleanup

```bash
# 1. Scan for duplicates
image-organizer scan --path ~/Pictures --output duplicates.json

# 2. Review and stage deletions
image-organizer review --input duplicates.json

# 3. List what's staged
image-organizer list-staging

# 4. Confirm deletion (to recycle bin)
image-organizer confirm-delete <operation-id>

# Or undo if you change your mind
image-organizer undo <operation-id>
```

### Protect Important Folders

```bash
# Mark folders as protected (won't scan them)
image-organizer protect --folder "Family Photos"
image-organizer protect --folder "Wedding"

# View protected folders
image-organizer protect --help
```

### Google Drive Cleanup

```bash
# 1. Authenticate (one-time)
image-organizer drive-auth --credentials ~/credentials.json

# 2. Scan for duplicates
image-organizer drive-scan --near-duplicates --output drive-dups.json

# 3. Review results
# (Integration with review UI coming in Phase 3.7)
```

---

## Troubleshooting

### "command not found: image-organizer"

**Cause**: Package not installed or not in PATH

**Solution**:
```bash
# Verify installation
pip list | grep image-organizer

# If not installed
pip install -e .

# If installed but not in PATH (Windows)
# Add Python Scripts to PATH or use:
python -m image_organizer.cli --help
```

### "ModuleNotFoundError: No module named 'image_organizer'"

**Cause**: Not running from correct directory or package not installed

**Solution**:
```bash
# Make sure you're in the project directory
cd /path/to/img-org

# Install package
pip install -e .
```

### Google Drive Authentication Fails

**Cause 1**: Invalid credentials file or missing Drive API

**Solution**:
1. Verify credentials.json is valid OAuth 2.0 Desktop app type
2. Enable Google Drive API in Cloud Console
3. Check scopes match (drive.readonly, drive.metadata.readonly)
4. Delete `~/.image-organizer/token.json` and re-authenticate

**Cause 2**: "Access blocked: ApiTemplate is not approved by Advanced Protection" (Error 400: policy_enforced)

**Solution**:
- **Google Advanced Protection Program** blocks unverified third-party apps
- **Most users don't have this** - standard Gmail accounts work fine
- **Workaround Options**:
  1. Use a Google account WITHOUT Advanced Protection (recommended)
  2. Temporarily disable Advanced Protection:
     - Visit [myaccount.google.com/security](https://myaccount.google.com/security)
     - Scroll to "Advanced Protection Program"
     - Click "Turn off" and follow prompts
     - **⚠️ Remember to re-enable it after using the tool**
  3. Download photos via [Google Takeout](https://takeout.google.com/) and scan locally
- **Note**: Getting app verified by Google is not feasible for personal projects (requires security audit, $15k-$75k cost)

### "No duplicates found" (but you know there are some)

**Cause**: Threshold too strict or wrong hash method

**Solution**:
```bash
# Try different hash method
image-organizer scan --path ~/Pictures --hash-method dhash

# Increase threshold (more permissive)
image-organizer scan --path ~/Pictures --threshold 15

# For exact duplicates only
image-organizer scan --path ~/Pictures --threshold 0
```

---

## Next Steps

- Read [README.md](README.md) for complete feature overview
- Review [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for development roadmap
- Check [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines
- Explore [docs/](docs/) folder for detailed guides

---

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/idusortus/img-org/issues)
- **Documentation**: See `docs/` folder
- **Examples**: Run `python demo.py` for working example

---

**⚠️ Safety Reminder**: This tool handles personal photos. Always backup important images before cleanup operations. The tool uses staging and recycle bin to prevent accidental permanent deletion.

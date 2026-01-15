# Image Organizer

**Intelligent image duplicate detection and storage optimization with safety-first design.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> ⚠️ **Status**: Alpha - Under active development

## Overview

Image Organizer helps you find and eliminate duplicate/near-duplicate images across multiple platforms while ensuring you never accidentally delete precious memories. 

**Key Features:**
- 🔍 **Smart Detection** - Finds exact duplicates (MD5) and visually similar images (perceptual hashing)
- 🛡️ **Safety First** - Multi-stage workflow: detect → review → stage → confirm → delete
- 👁️ **Visual Confirmation** - See side-by-side comparisons before any deletion
- 🔒 **Protected Folders** - Mark directories as off-limits (Family Photos, Wedding, etc.)
- ↩️ **Multi-level Undo** - Restore files with full operation history
- 🗑️ **Recycle Bin Integration** - Files go to recycle bin first, not permanent deletion
- 🌐 **Multi-platform** - Windows local files (Phase 1) + Google Drive (Phase 4)

## Why Image Organizer?

**Images are personal data.** Family photos, memories, and important moments cannot be recreated if accidentally deleted. Unlike other tools, Image Organizer prioritizes user confidence and safety:

- ✅ **You see what you're deleting** - Visual confirmation required
- ✅ **Reversible actions** - All deletions staged first, can be undone
- ✅ **Conservative matching** - When in doubt, we don't mark as duplicate
- ✅ **Clear communication** - Explains WHY images are duplicates with evidence
- ✅ **No surprises** - Never auto-delete without explicit consent

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/image-organizer.git
cd image-organizer

# Install dependencies
pip install -e .

# Or with development tools
pip install -e ".[dev]"
```

### Basic Usage

**Local Files:**
```bash
# Step 1: Scan for duplicates in local directories
image-organizer scan --path "C:\Users\John\Pictures" --output duplicates.json

# Step 2: Review duplicates interactively with visual comparison
image-organizer review --input duplicates.json

# The review command will:
# - Show side-by-side comparisons with metadata
# - Highlight quality differences (resolution, file size, date)
# - Recommend which images to keep/delete
# - Auto-stage selected files for deletion

# Step 3: Confirm deletion (moves to recycle bin by default)
image-organizer confirm-delete <operation-id>

# Or undo if you change your mind
image-organizer undo <operation-id>

# Protect important folders (they'll be skipped during scanning)
image-organizer protect --folder "Family Photos"
image-organizer protect --folder "Wedding"

# List staged operations
image-organizer list-staging
```

**Google Drive:**
```bash
# Step 1: Authenticate with Google Drive (one-time setup)
image-organizer drive-auth --credentials ~/Downloads/credentials.json

# Step 2a: Scan for exact duplicates (fast, MD5-based, no downloads)
image-organizer drive-scan --output drive-duplicates.json

# Step 2b: Scan for document duplicates (Word, PDF, Excel, etc.)
image-organizer drive-scan-docs --output docs-duplicates.json

# Step 3: Move duplicates to review folder or trash them
image-organizer drive-move-duplicates --input drive-duplicates.json --keep-strategy newest
image-organizer drive-trash --input drive-duplicates.json --keep-strategy largest
```

**Cross-Platform (Local + Drive):**
```bash
# Find files that exist in BOTH locations
image-organizer cross-platform-scan --local-path ~/Pictures --output cross-dups.json

# This helps you:
# - Free up local disk space (keep cloud copies)
# - Identify already-backed-up files
# - Optimize storage across platforms
```

## Technology Stack

- **Python 3.10+** - Modern Python with type hints
- **imagededup** - Production-tested duplicate detection engine (by idealo)
- **Click** - Elegant CLI framework
- **Rich** - Beautiful terminal output
- **Send2Trash** - Safe deletion to recycle bin
- **Google Drive API v3** - Drive integration with OAuth 2.0

## Project Status

### Phase 1: Foundation ✅ COMPLETE (Jan 13, 2026)
- [x] Project setup and structure
- [x] File scanner implementation (Windows support)
- [x] imagededup integration (all 4 hash methods)
- [x] Staging mechanism with operation metadata
- [x] Basic CLI (scan, protect, undo, list-staging)
- [x] Safety features (protected folders, recycle bin)
- [x] 36% test coverage (11 tests passing)

### Phase 2: Visual Review Interface 🔄 IN PROGRESS
- [x] ReviewUI class with Rich terminal output ✅ NEW
- [x] Side-by-side duplicate comparison ✅ NEW
- [x] Metadata display (resolution, size, date, quality score) ✅ NEW
- [x] CLI `review` command ✅ NEW
- [x] CLI `confirm-delete` command ✅ NEW
- [x] Protected folders (from Phase 1) ✅
- [x] Multi-level undo (from Phase 1) ✅
- [ ] Interactive keyboard controls (currently auto-recommend)
- [ ] Enhanced CLI with live preview

**Current Status**: Core review interface working! Can scan, review with visual comparison, and stage deletions safely.

### Phase 3: Google Drive Integration ✅ COMPLETE (Jan 15, 2026)
- [x] OAuth 2.0 authentication
- [x] Drive file listing with pagination and filtering
- [x] MD5-based exact duplicate detection
- [x] Document duplicate scanning (Word, PDF, Excel, etc.)
- [x] Move duplicates to folder with timestamp naming
- [x] Trash operations with 30-day recovery
- [x] Execute operations from JSON files
- [x] Cross-platform scanning (local + Drive)
- [x] Folder and MIME type filtering
- [x] 14 CLI commands total
- [x] 32 tests passing, 38% coverage

**Available Commands:**
- **Scanning**: `scan`, `drive-scan`, `drive-scan-docs`, `cross-platform-scan`, `review`
- **Operations**: `drive-move-duplicates`, `drive-trash`, `drive-execute`, `confirm-delete`
- **Safety**: `protect`, `unprotect`, `list-staging`, `undo`, `drive-auth`

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for complete roadmap.

### Phase 4: Advanced Features 📋 PLANNED
- [ ] Perceptual hashing for near-duplicate detection
- [ ] ML-based similarity detection
- [ ] Web UI (Flask/FastAPI + React)
- [ ] Additional platform support (Dropbox, OneDrive, iCloud)

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for complete roadmap.

## Documentation

- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Complete development roadmap
- [GitHub Copilot Instructions](.github/copilot-instructions.md) - Development guidelines
- [Skills](.github/skills/) - Contextual development guides
- [Prompts](.github/prompts/) - Task-specific templates

## Contributing

Contributions are welcome! This project emphasizes:
- **Safety first** - All features must preserve user data integrity
- **User trust** - Clear communication and no surprises
- **Code quality** - Type hints, tests, and documentation required

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [imagededup](https://github.com/idealo/imagededup) by idealo - Excellent duplicate detection library
- [difPy](https://github.com/elisemercury/Duplicate-Image-Finder) - Inspiration for MSE-based comparison
- Community contributors and testers

---

**⚠️ Important**: This tool handles personal photos. Always backup your images before running any cleanup operations. While we implement extensive safety measures, you are responsible for your data.

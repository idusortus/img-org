---
name: safe-image-deletion
description: Guide for implementing safe image deletion workflows with staging, visual confirmation, and rollback capabilities. Use this when implementing any feature that deletes or moves images.
---

# Safe Image Deletion Skill

**CRITICAL**: Images are irreplaceable personal data. This skill ensures no unique images are accidentally deleted.

## Core Safety Principles

### Must Always
1. **Stage before delete** - Move files to staging area, never delete directly
2. **Visual confirmation required** - Show thumbnails/previews before any permanent action
3. **Explicit user confirmation** - Require user to type confirmation or click multiple times
4. **Maintain undo capability** - Keep metadata to reverse operations
5. **Log all operations** - Audit trail for recovery

### Must Never
1. Never auto-delete without explicit user approval
2. Never skip the staging phase
3. Never delete files from "protected" or whitelisted folders
4. Never proceed if backup verification fails (when configured)
5. Never delete on first confirmation - always use two-step confirmation

## Implementation Pattern

### For Local Files (Windows/PC)

```python
from pathlib import Path
import shutil
import json
from datetime import datetime

class SafeImageDeleter:
    def __init__(self, staging_dir=".image-organizer-staging"):
        self.staging_dir = Path.home() / staging_dir
        self.staging_dir.mkdir(exist_ok=True)
        self.operation_log = self.staging_dir / "operations.json"
        
    def stage_for_deletion(self, file_path: Path, reason: str, duplicate_of: Path = None):
        """Move file to staging area with metadata for recovery."""
        if not file_path.exists():
            raise FileNotFoundError(f"Cannot stage non-existent file: {file_path}")
            
        # Create staging subdirectory preserving relative structure
        staged_path = self.staging_dir / file_path.name
        shutil.move(str(file_path), str(staged_path))
        
        # Log operation for undo capability
        operation = {
            "timestamp": datetime.now().isoformat(),
            "original_path": str(file_path),
            "staged_path": str(staged_path),
            "reason": reason,
            "duplicate_of": str(duplicate_of) if duplicate_of else None,
            "file_size": staged_path.stat().st_size,
            "status": "staged"
        }
        
        self._append_to_log(operation)
        return staged_path
    
    def confirm_deletion(self, user_confirmation: str) -> bool:
        """Require explicit confirmation before permanent deletion."""
        # User must type exact phrase
        if user_confirmation != "DELETE STAGED FILES PERMANENTLY":
            return False
            
        # Move to system recycle bin (not permanent delete)
        from send2trash import send2trash
        
        staged_files = list(self.staging_dir.glob("*"))
        for file_path in staged_files:
            if file_path != self.operation_log:
                send2trash(str(file_path))
                self._update_log_status(file_path, "deleted")
        
        return True
    
    def undo_staging(self, file_path: Path = None):
        """Restore staged files to original locations."""
        # Implementation for rollback
        pass
```

### For Google Drive

```python
class SafeGoogleDriveDeleter:
    def stage_for_deletion(self, service, file_id: str):
        """Move file to trash (30-day recovery window)."""
        # Use Google Drive's trash feature - allows recovery
        service.files().update(
            fileId=file_id,
            body={'trashed': True}
        ).execute()
        
        # Log operation
        self._log_operation(file_id, "moved_to_trash")
    
    def confirm_permanent_deletion(self, service, file_id: str, user_typed_confirmation: str):
        """Permanently delete after explicit confirmation."""
        if user_typed_confirmation != "PERMANENTLY DELETE":
            raise ValueError("User confirmation required")
            
        # Only after explicit confirmation
        service.files().delete(fileId=file_id).execute()
```

## Visual Confirmation Requirements

### Generate Preview Grid
```python
def generate_deletion_preview(duplicate_groups: list) -> str:
    """Create HTML preview showing what will be deleted vs kept."""
    html = """
    <html>
    <style>
        .comparison { display: flex; border: 2px solid red; }
        .keep { border-color: green; }
        .delete { border-color: red; opacity: 0.7; }
    </style>
    <body>
    """
    
    for group in duplicate_groups:
        html += "<div class='comparison'>"
        for image in group:
            css_class = "keep" if image.keep else "delete"
            html += f"""
            <div class='{css_class}'>
                <img src='{image.thumbnail}' />
                <p>{image.path}</p>
                <p>Size: {image.size} | Quality: {image.quality_score}</p>
            </div>
            """
        html += "</div>"
    
    html += "</body></html>"
    return html
```

## Protected Folders Pattern

```python
PROTECTED_PATTERNS = [
    "*/Family Photos/*",
    "*/Wedding/*",
    "*/Kids/*",
    "*/.git/*",  # Never touch version control
]

def is_protected(file_path: Path) -> bool:
    """Check if file is in a protected location."""
    for pattern in PROTECTED_PATTERNS:
        if file_path.match(pattern):
            return True
    return False

def check_before_staging(file_path: Path):
    """Pre-staging validation."""
    if is_protected(file_path):
        raise PermissionError(
            f"File {file_path} is in a protected folder. "
            f"Remove from whitelist to proceed."
        )
```

## Undo/Rollback Implementation

```python
def undo_last_operation(self):
    """Restore most recent deletion operation."""
    with open(self.operation_log) as f:
        operations = json.load(f)
    
    # Get last operation that hasn't been undone
    last_op = next(
        (op for op in reversed(operations) if op["status"] != "undone"),
        None
    )
    
    if not last_op:
        print("No operations to undo")
        return
    
    # Restore file
    staged_path = Path(last_op["staged_path"])
    original_path = Path(last_op["original_path"])
    
    if staged_path.exists():
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_path), str(original_path))
        self._update_log_status(staged_path, "undone")
        print(f"Restored: {original_path}")
```

## CLI Safety Pattern

When implementing CLI commands, always follow this order:

1. **Scan** - Detect duplicates (read-only, safe)
2. **Review** - Show visual comparison (read-only, safe)
3. **Stage** - Move to staging area (reversible)
4. **Preview** - Show what's in staging with thumbnails
5. **Confirm** - Require explicit typed confirmation
6. **Execute** - Move to recycle bin/trash (still recoverable)
7. **Undo** - Restore from staging if needed

## Error Messages

Use clear, safety-focused error messages:

```python
# Good
"⚠️  SAFETY CHECK FAILED: Cannot delete files from 'Family Photos' folder. "
"This folder is protected. To proceed, remove it from the protected list "
"in settings."

# Bad
"Error: Protected folder"
```

## Testing Requirements

Always test with:
- Non-existent files (should fail gracefully)
- Protected folders (should block with clear message)
- Interrupted operations (should be recoverable)
- System crashes mid-delete (staging should survive)
- Duplicate file names in staging area

## References

- See `.github/copilot-instructions.md` for full safety guidelines
- Use `send2trash` library for cross-platform recycle bin support
- Keep operation logs in JSON for easy parsing and recovery

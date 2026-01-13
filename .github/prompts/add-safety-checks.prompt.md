---
name: Add Safety Checks
description: Add comprehensive safety checks and validation to image deletion code
tags: [safety, validation, deletion, error-handling]
---

# Add Safety Checks

You are reviewing code that deletes or moves images. **Images are irreplaceable personal data** - add every possible safety check.

## Required Safety Layers

### Layer 1: Pre-Deletion Validation

```python
def validate_before_deletion(file_path: Path):
    """Run all safety checks before allowing deletion."""
    
    # Check 1: File exists
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot delete non-existent file: {file_path}")
    
    # Check 2: Is it actually a file (not a directory)
    if not file_path.is_file():
        raise ValueError(f"Cannot delete directory as file: {file_path}")
    
    # Check 3: Protected folder check
    if is_protected_folder(file_path):
        raise PermissionError(
            f"File is in protected folder: {file_path.parent}\n"
            f"Remove folder from protected list to proceed."
        )
    
    # Check 4: File is readable (not locked/in-use)
    try:
        with open(file_path, 'rb') as f:
            f.read(1)
    except PermissionError:
        raise PermissionError(f"File is locked or in use: {file_path}")
    
    # Check 5: Is it an image file
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']
    if file_path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Not an image file: {file_path}")
    
    return True
```

### Layer 2: User Confirmation

```python
def require_confirmation(files_to_delete: list[Path], deletion_type="staging"):
    """Require explicit user confirmation with summary."""
    
    # Calculate impact
    total_size = sum(f.stat().st_size for f in files_to_delete)
    total_count = len(files_to_delete)
    
    # Show summary
    print("\n" + "="*60)
    print("⚠️  DELETION SUMMARY")
    print("="*60)
    print(f"Files to delete: {total_count}")
    print(f"Total size: {total_size / (1024*1024):.2f} MB")
    print(f"Action: Move to {deletion_type}")
    print("\nFiles will be moved to:", staging_dir if deletion_type == "staging" else "Recycle Bin")
    print("You can undo this operation.")
    print("="*60)
    
    # Require typed confirmation
    if deletion_type == "permanent":
        required_text = "DELETE PERMANENTLY"
        print(f"\n⚠️  WARNING: This cannot be undone!")
    else:
        required_text = "PROCEED"
    
    print(f"\nType '{required_text}' to confirm: ", end='')
    user_input = input().strip()
    
    if user_input != required_text:
        print("❌ Cancelled - confirmation text did not match")
        return False
    
    return True
```

### Layer 3: Staged Deletion

```python
def stage_for_deletion(file_path: Path) -> Path:
    """
    Move to staging area (not deleted yet).
    
    Returns:
        Path to staged file
    """
    # NEVER delete directly - always stage first
    staging_dir = Path.home() / ".image-organizer-staging"
    staging_dir.mkdir(exist_ok=True)
    
    # Preserve original path in metadata
    metadata = {
        'original_path': str(file_path.absolute()),
        'staged_at': datetime.now().isoformat(),
        'size': file_path.stat().st_size,
        'md5': compute_md5(file_path)  # For verification
    }
    
    # Generate unique staged filename
    staged_path = staging_dir / f"{file_path.stem}_{int(time.time())}{file_path.suffix}"
    
    # Move (not copy) to staging
    shutil.move(str(file_path), str(staged_path))
    
    # Save metadata for undo
    metadata_path = staged_path.with_suffix('.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return staged_path
```

### Layer 4: Logging & Audit Trail

```python
def log_deletion_operation(operation_type: str, file_path: Path, success: bool, error=None):
    """Maintain audit trail of all deletion operations."""
    log_file = Path.home() / ".image-organizer-staging" / "operations.log"
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'operation': operation_type,  # 'stage', 'delete', 'undo'
        'file': str(file_path),
        'success': success,
        'error': str(error) if error else None,
        'user': os.getenv('USERNAME') or os.getenv('USER')
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
```

### Layer 5: Undo Capability

```python
def undo_last_deletion() -> bool:
    """Restore most recently staged file."""
    staging_dir = Path.home() / ".image-organizer-staging"
    
    # Find most recent metadata file
    metadata_files = sorted(
        staging_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if not metadata_files:
        print("No operations to undo")
        return False
    
    latest = metadata_files[0]
    with open(latest) as f:
        metadata = json.load(f)
    
    # Restore file
    staged_file = latest.with_suffix('.jpg')  # Adjust extension
    original_path = Path(metadata['original_path'])
    
    if staged_file.exists():
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_file), str(original_path))
        latest.unlink()  # Remove metadata
        
        print(f"✅ Restored: {original_path}")
        log_deletion_operation('undo', original_path, True)
        return True
    
    return False
```

## Protected Folders Feature

```python
PROTECTED_FOLDERS = [
    "Family Photos",
    "Wedding",
    "Kids",
    "Important",
    ".git",
    "Backup"
]

def is_protected_folder(file_path: Path) -> bool:
    """Check if file is in protected location."""
    path_str = str(file_path.absolute()).lower()
    
    for protected in PROTECTED_FOLDERS:
        if protected.lower() in path_str:
            return True
    
    return False

def add_to_protected_list(folder_path: Path):
    """Allow users to protect additional folders."""
    config_file = Path.home() / ".image-organizer" / "config.json"
    config_file.parent.mkdir(exist_ok=True)
    
    # Load existing config
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {'protected_folders': []}
    
    # Add to list
    if str(folder_path) not in config['protected_folders']:
        config['protected_folders'].append(str(folder_path))
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Protected: {folder_path}")
```

## Error Messages

Use clear, actionable error messages:

```python
# Bad
"Error: Cannot delete"

# Good
"❌ SAFETY CHECK FAILED: Cannot delete file from protected folder\n"
"   File: C:\\Photos\\Family Photos\\vacation.jpg\n"
"   Protected folder: Family Photos\n\n"
"   To proceed:\n"
"   1. Review why this folder is protected\n"
"   2. If safe, run: image-organizer unprotect 'Family Photos'\n"
"   3. Then retry the deletion\n\n"
"   Or use: image-organizer review --skip-protected"
```

## What to Check in Code

When reviewing deletion code, verify:

- [ ] ✅ Validates file exists before deletion
- [ ] ✅ Checks for protected folders
- [ ] ✅ Stages files instead of direct deletion
- [ ] ✅ Requires explicit user confirmation
- [ ] ✅ Shows summary before deletion
- [ ] ✅ Logs all operations
- [ ] ✅ Provides undo capability
- [ ] ✅ Uses recycle bin/trash when available
- [ ] ✅ Handles file-in-use errors gracefully
- [ ] ✅ Verifies file integrity after move
- [ ] ✅ Has rollback on partial failure
- [ ] ✅ Never uses `os.remove()` directly
- [ ] ✅ Never deletes without staging first

## Your Response Format

For each safety issue found:

```
SAFETY ISSUE: [Description]
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Severity: [CRITICAL/HIGH/MEDIUM]
Location: [Line number or function name]

Current code:
    [Show problematic code]

Risk:
    [What could go wrong]

Required fix:
    [Show corrected code with all safety checks]

Testing:
    [How to verify the fix works]
```

## Additional Recommendations

Suggest:
- Backup verification before allowing deletion
- Duplicate file move (not copy) for disk space
- Checksum verification after staging
- Progress tracking for large operations
- Graceful handling of permission errors
- Platform-specific recycle bin integration

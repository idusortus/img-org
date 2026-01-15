"""Command-line interface for image-organizer."""

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from image_organizer import __version__
from image_organizer.core.detector import DuplicateDetector
from image_organizer.core.scanner import ImageScanner
from image_organizer.core.staging import SafeImageDeleter
from image_organizer.ui.review import ReviewUI
from image_organizer.utils.config import Config
from image_organizer.utils.logger import setup_logger

console = Console()
logger = setup_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="image-organizer")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    Image Organizer - Intelligent duplicate image detection with safety-first design.

    Find and eliminate duplicate/near-duplicate images while ensuring you never
    accidentally delete precious memories.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        import logging

        setup_logger("image-organizer", level=logging.DEBUG)


@cli.command()
@click.option(
    "--path",
    "-p",
    "paths",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory path(s) to scan for images",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for duplicate report (JSON)",
)
@click.option(
    "--threshold",
    "-t",
    type=int,
    help="Similarity threshold (Hamming distance, default: from config)",
)
@click.option(
    "--hash-method",
    "-m",
    type=click.Choice(["phash", "dhash", "ahash", "whash"], case_sensitive=False),
    help="Hash method to use (default: from config)",
)
@click.option(
    "--recursive/--no-recursive",
    "-r/-R",
    default=True,
    help="Recursively scan subdirectories",
)
@click.option(
    "--show-progress/--no-progress",
    default=True,
    help="Show progress bars",
)
@click.pass_context
def scan(
    ctx: click.Context,
    paths: tuple,
    output: Optional[Path],
    threshold: Optional[int],
    hash_method: Optional[str],
    recursive: bool,
    show_progress: bool,
) -> None:
    """
    Scan directories for duplicate images.

    This command scans the specified directories for images and identifies
    duplicates using perceptual hashing. Results are displayed in the terminal
    and optionally saved to a JSON file.

    Example:
        image-organizer scan --path "C:\\Users\\John\\Pictures" --output duplicates.json
    """
    config = Config()

    # Override config with command-line options
    if hash_method:
        config.set("hash_method", hash_method.lower())
    if threshold is not None:
        config.set("similarity_threshold", threshold)

    console.print(
        f"\n[bold cyan]Image Organizer v{__version__}[/bold cyan] - Duplicate Detection\n"
    )

    # Scan for images
    scanner = ImageScanner(config, show_progress=show_progress)

    all_images: List[Path] = []
    for path in paths:
        console.print(f"[yellow]Scanning:[/yellow] {path}")
        try:
            images = scanner.scan_directory(
                Path(path), recursive=recursive, skip_hidden=True
            )
            all_images.extend(images)
        except Exception as e:
            console.print(f"[red]Error scanning {path}:[/red] {e}", err=True)
            continue

    if not all_images:
        console.print("[yellow]No images found to scan.[/yellow]")
        return

    console.print(f"\n[green]Total images found:[/green] {len(all_images)}\n")

    # Detect duplicates
    detector = DuplicateDetector(config, show_progress=show_progress)

    try:
        duplicates = detector.find_duplicates(all_images)

        if not duplicates:
            console.print("[green]✓ No duplicates found![/green]")
            return

        # Display results
        _display_duplicate_results(duplicates)

        # Save to file if requested
        if output:
            _save_duplicates_json(duplicates, output)
            console.print(f"\n[green]✓ Results saved to:[/green] {output}")

    except Exception as e:
        console.print(f"[red]Error during duplicate detection:[/red] {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_staging(ctx: click.Context) -> None:
    """
    List all staged operations (files ready for deletion).

    Shows operations that have been staged but not yet confirmed for deletion.
    """
    config = Config()
    deleter = SafeImageDeleter(config)

    operations = deleter.list_staged_operations()

    if not operations:
        console.print("[yellow]No staged operations found.[/yellow]")
        return

    # Filter for staged (not yet deleted) operations
    staged_ops = [op for op in operations if op.get("status") == "staged"]

    if not staged_ops:
        console.print("[yellow]No staged operations found.[/yellow]")
        return

    console.print(f"\n[bold cyan]Staged Operations:[/bold cyan]\n")

    for op in staged_ops:
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        table.add_row("Operation ID", op["operation_id"])
        table.add_row("Timestamp", op["timestamp"])
        table.add_row("Reason", op["reason"])
        table.add_row("Files", str(op["files_staged"]))
        table.add_row("Status", op["status"])

        console.print(table)
        console.print()


@cli.command()
@click.argument("operation_id")
@click.pass_context
def undo(ctx: click.Context, operation_id: str) -> None:
    """
    Undo a staged operation by restoring files to original locations.

    OPERATION_ID: ID of the operation to undo (from list-staging)
    """
    config = Config()
    deleter = SafeImageDeleter(config)

    console.print(f"\n[yellow]Undoing operation:[/yellow] {operation_id}\n")

    success = deleter.undo_staging(operation_id)

    if success:
        console.print(f"[green]✓ Operation {operation_id} undone successfully![/green]")
    else:
        console.print(f"[red]Failed to undo operation {operation_id}[/red]", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--folder", "-f", required=True, help="Folder name or pattern to protect"
)
@click.pass_context
def protect(ctx: click.Context, folder: str) -> None:
    """
    Add a folder to the protected folders list.

    Protected folders cannot have files deleted from them.
    """
    config = Config()
    config.add_protected_folder(folder)

    console.print(f"[green]✓ Protected folder added:[/green] {folder}")
    console.print("\n[cyan]Current protected folders:[/cyan]")
    for pf in config.get("protected_folders", []):
        console.print(f"  • {pf}")


@cli.command()
@click.option(
    "--folder", "-f", required=True, help="Folder name or pattern to unprotect"
)
@click.pass_context
def unprotect(ctx: click.Context, folder: str) -> None:
    """
    Remove a folder from the protected folders list.
    """
    config = Config()
    config.remove_protected_folder(folder)

    console.print(f"[green]✓ Protected folder removed:[/green] {folder}")


@cli.command()
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file from 'scan' command with duplicate results",
)
@click.option(
    "--auto-select/--no-auto-select",
    default=True,
    help="Auto-select recommended deletions (default: True)",
)
@click.option(
    "--stage/--no-stage",
    default=True,
    help="Stage selected files for deletion (default: True)",
)
@click.pass_context
def review(
    ctx: click.Context,
    input_file: Path,
    auto_select: bool,
    stage: bool,
) -> None:
    """
    Interactively review duplicate detection results.

    Shows side-by-side comparison with metadata (resolution, size, date).
    Allows you to select which images to keep/delete before staging.

    Example:
        image-organizer review --input duplicates.json
    """
    import json

    # Load duplicates from JSON
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            duplicates = json.load(f)
    except Exception as e:
        console.print(f"[red]✗ Error loading duplicates file:[/red] {e}")
        sys.exit(1)

    if not duplicates:
        console.print("[yellow]No duplicates found in input file.[/yellow]")
        return

    # Create review UI
    review_ui = ReviewUI(console)

    # Review duplicates interactively
    console.print("[bold cyan]Starting interactive review...[/bold cyan]\n")
    decisions = review_ui.review_duplicates(
        duplicates, auto_select_recommendations=auto_select
    )

    # Show summary
    to_delete = [Path(p) for p in decisions["delete"]]
    to_keep = [Path(p) for p in decisions["keep"]]

    if not to_delete:
        console.print("[yellow]No files selected for deletion.[/yellow]")
        return

    console.print(f"\n[bold]Review Summary:[/bold]")
    console.print(f"  [green]Files to keep:[/green] {len(to_keep)}")
    console.print(f"  [red]Files to delete:[/red] {len(to_delete)}")

    # Ask for confirmation
    confirmed = review_ui.show_final_confirmation(to_delete, to_keep)

    if not confirmed:
        console.print("[yellow]Review cancelled. No files were staged.[/yellow]")
        return

    # Stage files if requested
    if stage:
        deleter = SafeImageDeleter()
        try:
            operation_id = deleter.stage_for_deletion(
                to_delete,
                reason="Duplicate removal via review",
                metadata={"keep": [str(p) for p in to_keep]},
            )
            console.print(
                f"\n[bold green]✓ {len(to_delete)} files staged for deletion[/bold green]"
            )
            console.print(f"[dim]Operation ID: {operation_id}[/dim]")
            console.print(
                f"\n[yellow]To undo this operation:[/yellow] image-organizer undo {operation_id}"
            )
            console.print(
                f"[yellow]To confirm deletion:[/yellow] image-organizer confirm-delete {operation_id}"
            )
        except Exception as e:
            console.print(f"[red]✗ Error staging files:[/red] {e}")
            sys.exit(1)
    else:
        console.print("[dim]Files not staged (--no-stage flag used).[/dim]")


@cli.command(name="confirm-delete")
@click.argument("operation_id", type=str)
@click.option(
    "--recycle-bin/--permanent",
    default=True,
    help="Move to recycle bin (default) or delete permanently",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt (use with caution!)",
)
@click.pass_context
def confirm_delete(
    ctx: click.Context,
    operation_id: str,
    recycle_bin: bool,
    confirm: bool,
) -> None:
    """
    Confirm deletion of staged files.

    Moves staged files to recycle bin (default) or deletes permanently.
    This action can be undone if using recycle bin.

    Example:
        image-organizer confirm-delete abc123 --recycle-bin
    """
    deleter = SafeImageDeleter()

    # Load operation metadata
    operations = deleter.list_staged_operations()
    operation = next((op for op in operations if op["id"] == operation_id), None)

    if not operation:
        console.print(f"[red]✗ Operation '{operation_id}' not found.[/red]")
        sys.exit(1)

    if operation["status"] != "staged":
        console.print(
            f"[red]✗ Operation '{operation_id}' is not in 'staged' status.[/red]"
        )
        console.print(f"[dim]Current status: {operation['status']}[/dim]")
        sys.exit(1)

    file_count = len(operation["files_staged"])
    action = "moved to recycle bin" if recycle_bin else "permanently deleted"

    # Show confirmation
    if not confirm:
        console.print(f"[bold yellow]⚠ Warning:[/bold yellow]")
        console.print(f"  About to {action}: {file_count} files")
        console.print(f"  Operation: {operation_id}")
        console.print(f"  Reason: {operation.get('reason', 'N/A')}")

        confirm_input = click.prompt(
            "\nType 'DELETE' to confirm",
            type=str,
            default="",
        )

        if confirm_input.upper() != "DELETE":
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Perform deletion
    try:
        success = deleter.confirm_deletion(operation_id, use_recycle_bin=recycle_bin)
        if success:
            console.print(
                f"[bold green]✓ {file_count} files {action}[/bold green]"
            )
        else:
            console.print(f"[red]✗ Deletion failed.[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error during deletion:[/red] {e}")
        sys.exit(1)


@cli.command(name="drive-auth")
@click.option(
    "--credentials",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to OAuth 2.0 credentials JSON file",
)
@click.pass_context
def drive_auth(ctx: click.Context, credentials: Optional[Path]) -> None:
    """
    Authenticate with Google Drive.

    Sets up OAuth 2.0 authentication for Google Drive access.
    Opens a browser window for you to authorize the application.

    To get credentials:
    1. Go to https://console.cloud.google.com/apis/credentials
    2. Create OAuth 2.0 Client ID (Desktop application)
    3. Download the JSON file

    Example:
        image-organizer drive-auth --credentials ~/Downloads/credentials.json
    """
    from image_organizer.platforms.google_drive import GoogleDriveClient

    try:
        client = GoogleDriveClient(credentials_file=credentials)
        console.print("[cyan]Starting OAuth authentication...[/cyan]")
        console.print("[dim]A browser window will open. Please authorize the application.[/dim]\n")
        
        success = client.authenticate()
        
        if success:
            console.print("[bold green]✓ Authentication successful![/bold green]")
            console.print(f"[dim]Token saved to: {client.token_file}[/dim]")
            console.print("\n[yellow]⚠️  Reminder: If you disabled Google Advanced Protection to authenticate,[/yellow]")
            console.print("[yellow]   remember to re-enable it at https://myaccount.google.com/security[/yellow]")
        else:
            console.print("[red]✗ Authentication failed.[/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]✗ Error during authentication:[/red] {e}")
        sys.exit(1)


@cli.command(name="drive-scan-docs")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for duplicate report (JSON)",
)
@click.option(
    "--max-files",
    type=int,
    help="Maximum number of files to scan (for testing)",
)
@click.option(
    "--folder-id",
    type=str,
    help="Scan only files in this folder (by Drive folder ID)",
)
@click.option(
    "--folder-name",
    type=str,
    help="Scan only files in folder with this name (finds first match)",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Include subfolders (default: True)",
)
@click.option(
    "--mime-type",
    type=str,
    help="Only scan specific document type(s), comma-separated (e.g., 'application/pdf,text/csv')",
)
@click.option(
    "--exclude-mime-type",
    type=str,
    help="Exclude specific document type(s), comma-separated",
)
@click.option(
    "--detect-duplicates/--list-only",
    default=True,
    help="Detect duplicates or just list files",
)
@click.pass_context
def drive_scan_docs(
    ctx: click.Context,
    output: Optional[Path],
    max_files: Optional[int],
    folder_id: Optional[str],
    folder_name: Optional[str],
    recursive: bool,
    mime_type: Optional[str],
    exclude_mime_type: Optional[str],
    detect_duplicates: bool,
) -> None:
    """
    Scan Google Drive for duplicate documents.

    Lists all documents in your Google Drive and detects exact duplicates
    using MD5 checksums. Supports Word, Excel, PowerPoint, PDF, text files,
    CSV, and Google Workspace documents.

    Examples:
        # Scan all documents
        image-organizer drive-scan-docs --output docs-duplicates.json
        
        # Scan specific folder
        image-organizer drive-scan-docs --folder-name "Work Documents"
        
        # Only scan PDFs
        image-organizer drive-scan-docs --mime-type "application/pdf"
        
        # Only scan Office documents (Word + Excel)
        image-organizer drive-scan-docs --mime-type "application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Exclude Google Workspace native formats
        image-organizer drive-scan-docs --exclude-mime-type "application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet"
        
        # Just list documents
        image-organizer drive-scan-docs --list-only
    """
    from image_organizer.platforms.google_drive import GoogleDriveClient, DOCUMENT_MIME_TYPES

    try:
        # Authenticate
        client = GoogleDriveClient()
        if not client.authenticate():
            console.print("[red]✗ Authentication failed. Run 'drive-auth' first.[/red]")
            sys.exit(1)
        
        console.print("[yellow]💡 Reminder: If you disabled Google Advanced Protection, re-enable it at https://myaccount.google.com/security[/yellow]\n")
        
        # Show folder context
        if folder_name:
            console.print(f"[cyan]Scanning folder:[/cyan] '{folder_name}' {'(including subfolders)' if recursive else '(this folder only)'}")
        elif folder_id:
            console.print(f"[cyan]Scanning folder ID:[/cyan] {folder_id} {'(including subfolders)' if recursive else '(this folder only)'}")
        else:
            console.print("[cyan]Scanning entire Google Drive for documents...[/cyan]")
        
        # Parse MIME types - default to all document types if none specified
        mime_types_list = None
        if mime_type:
            mime_types_list = [mt.strip() for mt in mime_type.split(',')]
            console.print(f"[dim]Filtering to: {', '.join(mime_types_list)}[/dim]")
        else:
            mime_types_list = DOCUMENT_MIME_TYPES
            console.print("[dim]Scanning for: Word, Excel, PowerPoint, PDF, Text, CSV, Google Docs/Sheets/Slides[/dim]")
        
        exclude_mime_types_list = None
        if exclude_mime_type:
            exclude_mime_types_list = [mt.strip() for mt in exclude_mime_type.split(',')]
            console.print(f"[dim]Excluding: {', '.join(exclude_mime_types_list)}[/dim]")
        
        # List files
        files = client.list_image_files(
            max_results=max_files,
            folder_id=folder_id,
            folder_name=folder_name,
            recursive=recursive,
            mime_types=mime_types_list,
            exclude_mime_types=exclude_mime_types_list,
        )
        
        console.print(f"[bold green]✓ Found {len(files)} document files[/bold green]\n")
        
        # Show sample
        if files:
            table = Table(title="Sample Documents", show_header=True, header_style="bold cyan")
            table.add_column("#", width=4)
            table.add_column("Name", width=40)
            table.add_column("Type", width=12)
            table.add_column("Size", justify="right", width=10)
            table.add_column("Modified", justify="right", width=12)
            
            for i, file in enumerate(files[:10], 1):
                size_bytes = int(file.get("size", 0))
                size_mb = size_bytes / (1024 * 1024)
                modified = file.get("modifiedTime", "Unknown")[:10]
                mime = file.get("mimeType", "")
                
                # Friendly type names
                if "pdf" in mime:
                    type_display = "PDF"
                elif "word" in mime or ".document" in mime:
                    type_display = "Word"
                elif "excel" in mime or ".spreadsheet" in mime:
                    type_display = "Excel"
                elif "powerpoint" in mime or ".presentation" in mime:
                    type_display = "PowerPoint"
                elif "text/plain" in mime:
                    type_display = "Text"
                elif "text/csv" in mime:
                    type_display = "CSV"
                else:
                    type_display = mime.split("/")[-1][:12]
                
                # Format size
                if size_mb >= 0.01:
                    size_display = f"{size_mb:.2f} MB"
                elif size_bytes >= 1024:
                    size_display = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_display = f"{size_bytes} B"
                
                name_display = file.get("name", "Unknown")
                if len(name_display) > 40:
                    name_display = name_display[:37] + "..."
                
                table.add_row(
                    str(i),
                    name_display,
                    type_display,
                    size_display,
                    modified,
                )
            
            console.print(table)
            
            if len(files) > 10:
                console.print(f"[dim]... and {len(files) - 10} more files[/dim]\n")
        
        # Detect duplicates
        if detect_duplicates and files:
            console.print("[cyan]Detecting duplicates (MD5 checksums)...[/cyan]")
            duplicates = client.find_exact_duplicates_by_md5(files)
            
            if duplicates:
                # Calculate space savings
                total_duplicate_size = 0
                duplicate_count = 0
                for md5, dup_files in duplicates.items():
                    file_size = int(dup_files[0].get("size", 0))
                    num_duplicates = len(dup_files) - 1
                    duplicate_count += num_duplicates
                    total_duplicate_size += file_size * num_duplicates
                
                savings_mb = total_duplicate_size / (1024 * 1024)
                savings_gb = savings_mb / 1024
                
                console.print(
                    f"[bold green]✓ Found {len(duplicates)} duplicate groups "
                    f"({duplicate_count} duplicate files)[/bold green]"
                )
                console.print(f"[bold yellow]💾 Potential space savings: {savings_gb:.2f} GB ({savings_mb:.0f} MB)[/bold yellow]\n")
                
                # Show sample duplicates
                table = Table(title="Duplicate Groups (Sample)", show_header=True, header_style="bold red")
                table.add_column("Group", width=6)
                table.add_column("File Name", width=40)
                table.add_column("Size", justify="right", width=10)
                table.add_column("ID", width=25)
                
                for group_num, (md5, dup_files) in enumerate(list(duplicates.items())[:5], 1):
                    for file_num, file in enumerate(dup_files, 1):
                        size_bytes = int(file.get("size", 0))
                        size_mb = size_bytes / (1024 * 1024)
                        
                        if size_mb >= 0.01:
                            size_display = f"{size_mb:.2f} MB"
                        elif size_bytes >= 1024:
                            size_display = f"{size_bytes / 1024:.1f} KB"
                        else:
                            size_display = f"{size_bytes} B"
                        
                        name_display = file["name"]
                        if len(name_display) > 40:
                            name_display = name_display[:37] + "..."
                        
                        table.add_row(
                            f"{group_num}" if file_num == 1 else "",
                            name_display,
                            size_display,
                            file["id"][:20] + "...",
                        )
                
                console.print(table)
                
                if len(duplicates) > 5:
                    console.print(f"[dim]... and {len(duplicates) - 5} more duplicate groups[/dim]\n")
                
                # Save to file
                if output:
                    with output.open("w") as f:
                        json.dump(duplicates, f, indent=2)
                    console.print(f"[bold green]✓ Results saved to {output}[/bold green]")
                    console.print("[dim]You can edit this file to select which duplicates to remove[/dim]")
            else:
                console.print("[green]✓ No duplicates found![/green]")
                if output:
                    with output.open("w") as f:
                        json.dump({}, f, indent=2)
                    console.print(f"[dim]Empty results saved to {output}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Error scanning Google Drive:[/red] {e}")
        logger.exception("Drive document scan error")
        sys.exit(1)


@cli.command(name="drive-scan")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for duplicate report (JSON)",
)
@click.option(
    "--max-files",
    type=int,
    help="Maximum number of files to scan (for testing)",
)
@click.option(
    "--folder-id",
    type=str,
    help="Scan specific folder by ID (get from Drive URL)",
)
@click.option(
    "--folder-name",
    type=str,
    help="Scan specific folder by name (finds first match)",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Include subfolders (default: True)",
)
@click.option(
    "--mime-type",
    type=str,
    help="Only scan specific MIME type(s), comma-separated (e.g., 'image/jpeg' or 'image/jpeg,image/png')",
)
@click.option(
    "--exclude-mime-type",
    type=str,
    help="Exclude specific MIME type(s), comma-separated (e.g., 'image/gif,image/webp')",
)
@click.option(
    "--detect-duplicates/--list-only",
    default=True,
    help="Detect duplicates or just list files",
)
@click.option(
    "--near-duplicates/--exact-only",
    default=False,
    help="Also detect near-duplicates using perceptual hashing (slower)",
)
@click.option(
    "--threshold",
    "-t",
    type=int,
    default=10,
    help="Perceptual hash distance threshold (0-64, lower = more similar)",
)
@click.option(
    "--thumbnail-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory to store thumbnails (default: temp directory)",
)
@click.pass_context
def drive_scan(
    ctx: click.Context,
    output: Optional[Path],
    max_files: Optional[int],
    folder_id: Optional[str],
    folder_name: Optional[str],
    recursive: bool,
    mime_type: Optional[str],
    exclude_mime_type: Optional[str],
    detect_duplicates: bool,
    near_duplicates: bool,
    threshold: int,
    thumbnail_dir: Optional[Path],
) -> None:
    """
    Scan Google Drive for duplicate images.

    Lists all images in your Google Drive and detects exact duplicates
    using MD5 checksums (no download required). Optionally detects
    near-duplicates using perceptual hashing (requires thumbnail downloads).

    Examples:
        # Exact duplicates only (fast)
        image-organizer drive-scan --output duplicates.json
        
        # Scan specific folder by name
        image-organizer drive-scan --folder-name "2024 Photos" --output 2024-dups.json
        
        # Scan specific folder and subfolders
        image-organizer drive-scan --folder-id "abc123xyz" --recursive
        
        # Scan folder without subfolders
        image-organizer drive-scan --folder-name "Vacation" --no-recursive
        
        # Only scan JPEG images
        image-organizer drive-scan --mime-type "image/jpeg"
        
        # Only scan JPEGs and PNGs
        image-organizer drive-scan --mime-type "image/jpeg,image/png"
        
        # Exclude GIFs from scan
        image-organizer drive-scan --exclude-mime-type "image/gif"
        
        # Include near-duplicates (slower, more comprehensive)
        image-organizer drive-scan --near-duplicates --threshold 10
        
        # Just list files without detection
        image-organizer drive-scan --list-only
    """
    from image_organizer.platforms.google_drive import GoogleDriveClient
    import tempfile

    try:
        # Authenticate
        client = GoogleDriveClient()
        if not client.authenticate():
            console.print("[red]✗ Authentication failed. Run 'drive-auth' first.[/red]")
            sys.exit(1)
        
        console.print("[yellow]💡 Reminder: If you disabled Google Advanced Protection, re-enable it at https://myaccount.google.com/security[/yellow]\n")
        
        # Show folder context if specified
        if folder_name:
            console.print(f"[cyan]Scanning folder:[/cyan] '{folder_name}' {'(including subfolders)' if recursive else '(this folder only)'}")
        elif folder_id:
            console.print(f"[cyan]Scanning folder ID:[/cyan] {folder_id} {'(including subfolders)' if recursive else '(this folder only)'}")
        else:
            console.print("[cyan]Scanning entire Google Drive for images...[/cyan]")
        
        # Parse MIME type filters
        mime_types_list = None
        if mime_type:
            mime_types_list = [mt.strip() for mt in mime_type.split(',')]
            console.print(f"[dim]Filtering to: {', '.join(mime_types_list)}[/dim]")
        
        exclude_mime_types_list = None
        if exclude_mime_type:
            exclude_mime_types_list = [mt.strip() for mt in exclude_mime_type.split(',')]
            console.print(f"[dim]Excluding: {', '.join(exclude_mime_types_list)}[/dim]")
        
        # List files
        files = client.list_image_files(
            max_results=max_files,
            folder_id=folder_id,
            folder_name=folder_name,
            recursive=recursive,
            mime_types=mime_types_list,
            exclude_mime_types=exclude_mime_types_list,
        )
        
        console.print(f"[bold green]✓ Found {len(files)} image files in Google Drive[/bold green]\n")
        
        # Show sample
        if files:
            table = Table(title="Sample Files", show_header=True, header_style="bold cyan")
            table.add_column("#", width=4)
            table.add_column("Name")
            table.add_column("Size", justify="right")
            table.add_column("Modified", justify="right")
            
            for i, file in enumerate(files[:10], 1):
                size_mb = int(file.get("size", 0)) / (1024 * 1024)
                modified = file.get("modifiedTime", "Unknown")[:10]
                table.add_row(
                    str(i),
                    file.get("name", "Unknown"),
                    f"{size_mb:.2f} MB",
                    modified,
                )
            
            console.print(table)
            
            if len(files) > 10:
                console.print(f"[dim]... and {len(files) - 10} more files[/dim]\n")
        
        # Detect duplicates if requested
        if detect_duplicates and files:
            if near_duplicates:
                # Use combined detection (MD5 + perceptual hash)
                console.print("[cyan]Detecting duplicates (MD5 + perceptual hashing)...[/cyan]")
                console.print(f"[dim]This may take a while for large libraries...[/dim]\n")
                
                # Use temp directory if not specified
                if thumbnail_dir is None:
                    thumbnail_dir = Path(tempfile.mkdtemp(prefix="image_organizer_"))
                    console.print(f"[dim]Using temp directory: {thumbnail_dir}[/dim]\n")
                
                results = client.find_all_duplicates(
                    files,
                    thumbnail_dir=thumbnail_dir,
                    phash_threshold=threshold,
                    include_near_duplicates=True,
                )
                
                exact_dupes = results['exact']
                near_dupes = results['near']
                stats = results['stats']
                
                # Display results
                console.print("\n[bold cyan]═══ Exact Duplicates (MD5) ═══[/bold cyan]")
                if exact_dupes:
                    # Calculate space savings
                    total_duplicate_size = 0
                    for md5, dup_files in exact_dupes.items():
                        file_size = int(dup_files[0].get("size", 0))
                        num_duplicates = len(dup_files) - 1
                        total_duplicate_size += file_size * num_duplicates
                    
                    savings_mb = total_duplicate_size / (1024 * 1024)
                    
                    console.print(
                        f"[bold green]✓ Found {stats['exact_duplicate_groups']} groups "
                        f"({stats['exact_duplicate_files']} duplicate files)[/bold green]"
                    )
                    console.print(f"[yellow]Space savings: {savings_mb:.1f} MB[/yellow]\n")
                    
                    # Show sample
                    sample_md5, sample_files = next(iter(exact_dupes.items()))
                    console.print("[cyan]Example exact duplicate group:[/cyan]")
                    for i, file in enumerate(sample_files[:3], 1):
                        console.print(f"  {i}. {file.get('name')}")
                    if len(sample_files) > 3:
                        console.print(f"  ... and {len(sample_files) - 3} more")
                else:
                    console.print("[yellow]No exact duplicates found[/yellow]")
                
                console.print("\n[bold cyan]═══ Near-Duplicates (Perceptual Hash) ═══[/bold cyan]")
                if near_dupes:
                    console.print(
                        f"[bold green]✓ Found {stats['near_duplicate_groups']} files with similar images "
                        f"({stats['near_duplicate_pairs']} total pairs)[/bold green]\n"
                    )
                    
                    # Show sample
                    sample_id, similar_files = next(iter(near_dupes.items()))
                    sample_file = next(f for f in files if f['id'] == sample_id)
                    console.print("[cyan]Example near-duplicate group:[/cyan]")
                    console.print(f"  Original: {sample_file.get('name')}")
                    console.print(f"  Similar to:")
                    for i, sim in enumerate(similar_files[:3], 1):
                        console.print(f"    {i}. {sim.get('name')}")
                    if len(similar_files) > 3:
                        console.print(f"    ... and {len(similar_files) - 3} more")
                else:
                    console.print("[yellow]No near-duplicates found[/yellow]")
                
                # Save to JSON if requested
                if output:
                    output_data = {
                        "exact_duplicates": {
                            md5: [{"id": f["id"], "name": f["name"], "size": f.get("size")} 
                                  for f in files_list]
                            for md5, files_list in exact_dupes.items()
                        },
                        "near_duplicates": {
                            file_id: [{"id": f["id"], "name": f["name"]} 
                                      for f in similar]
                            for file_id, similar in near_dupes.items()
                        },
                        "stats": stats,
                    }
                    output.write_text(json.dumps(output_data, indent=2))
                    console.print(f"\n[green]✓ Results saved to:[/green] {output}")
                
            else:
                # Fast MD5-only detection
                console.print("[cyan]Detecting exact duplicates by MD5 checksum...[/cyan]")
                duplicates = client.find_exact_duplicates_by_md5(files)
                
                if duplicates:
                    # Calculate space savings
                    total_duplicate_size = 0
                    for md5, dup_files in duplicates.items():
                        # Keep one, delete the rest
                        file_size = int(dup_files[0].get("size", 0))
                        num_duplicates = len(dup_files) - 1
                        total_duplicate_size += file_size * num_duplicates
                    
                    savings_mb = total_duplicate_size / (1024 * 1024)
                    
                    console.print(
                        f"[bold green]✓ Found {len(duplicates)} duplicate groups[/bold green]\n"
                    )
                    console.print(
                        f"[yellow]Potential space savings: {savings_mb:.1f} MB[/yellow]\n"
                    )
                    
                    # Show sample duplicate group
                    sample_md5, sample_files = next(iter(duplicates.items()))
                    console.print("[cyan]Example duplicate group:[/cyan]")
                    for i, file in enumerate(sample_files, 1):
                        console.print(f"  {i}. {file.get('name')}")
                    
                    # Save to JSON if requested
                    if output:
                        # Convert to standard format
                        json_duplicates = {}
                        for md5, dup_files in duplicates.items():
                            # Use first file as "original"
                            original = dup_files[0]
                            others = dup_files[1:]
                            
                            json_duplicates[original["id"]] = [
                                {
                                    "id": f["id"],
                                    "name": f["name"],
                                    "size": f.get("size"),
                                    "md5": md5,
                                }
                                for f in others
                            ]
                        
                        _save_duplicates_json(json_duplicates, output)
                        console.print(f"\n[green]✓ Results saved to:[/green] {output}")
                else:
                    console.print("[yellow]No duplicates found![/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ Error scanning Drive:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command(name="drive-move-duplicates")
@click.option(
    "--input",
    "-i",
    "input_file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="JSON file from drive-scan or drive-scan-docs",
)
@click.option(
    "--folder-name",
    type=str,
    help="Name for the review folder (auto-generated with timestamp if not specified)",
)
@click.option(
    "--keep-strategy",
    type=click.Choice(["first", "last", "newest", "oldest", "largest", "smallest"]),
    default="first",
    help="Which file to keep in original location",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be moved without actually moving files",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt (use with caution!)",
)
@click.pass_context
def drive_move_duplicates(
    ctx: click.Context,
    input_file: Path,
    folder_name: Optional[str],
    keep_strategy: str,
    dry_run: bool,
    confirm: bool,
) -> None:
    """
    Move duplicate files to a review folder in Google Drive.
    
    This command moves duplicates detected by drive-scan or drive-scan-docs
    to a new folder for review. One file from each duplicate group is kept
    in its original location based on the keep strategy.
    
    The folder name is auto-generated with a timestamp (e.g., "Duplicates_2026-01-15_1430")
    unless you specify a custom name.
    
    Examples:
        # Move duplicates, keep first file in each group
        image-organizer drive-move-duplicates --input docs-scan-001.json
        
        # Move duplicates to custom folder, keep newest
        image-organizer drive-move-duplicates \\
            --input full-scan-001.json \\
            --folder-name "Images to Review" \\
            --keep-strategy newest
        
        # Dry run to preview what would happen
        image-organizer drive-move-duplicates \\
            --input docs-scan-001.json \\
            --keep-strategy largest \\
            --dry-run
        
        # Skip confirmation prompt
        image-organizer drive-move-duplicates \\
            --input scan.json \\
            --confirm
    """
    from image_organizer.platforms.google_drive import GoogleDriveClient

    try:
        # Load duplicates JSON
        with input_file.open("r") as f:
            duplicates = json.load(f)
        
        if not duplicates:
            console.print("[yellow]No duplicates found in input file.[/yellow]")
            return
        
        # Count total files
        total_files = sum(len(files) for files in duplicates.values())
        duplicate_count = sum(len(files) - 1 for files in duplicates.values())
        
        console.print(f"[cyan]Loaded {len(duplicates)} duplicate groups ({duplicate_count} files to move)[/cyan]\n")
        
        # Show strategy info
        strategy_desc = {
            "first": "first file in each group",
            "last": "last file in each group",
            "newest": "newest file (by modified date)",
            "oldest": "oldest file (by modified date)",
            "largest": "largest file (by size)",
            "smallest": "smallest file (by size)",
        }
        console.print(f"[bold]Keep strategy:[/bold] {strategy_desc[keep_strategy]}")
        console.print(f"[bold]Folder name:[/bold] {folder_name or 'Auto-generated with timestamp'}\n")
        
        # Show sample of what will be moved
        console.print("[bold cyan]Sample duplicate groups:[/bold cyan]")
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Group", width=6)
        table.add_column("Action", width=8)
        table.add_column("File Name", width=50)
        table.add_column("Size", justify="right", width=10)
        
        for group_num, (md5, file_list) in enumerate(list(duplicates.items())[:3], 1):
            # Determine keep index (simplified for display)
            if keep_strategy == "last":
                keep_idx = len(file_list) - 1
            else:  # "first" for preview
                keep_idx = 0
            
            for i, file in enumerate(file_list):
                action = "[green]KEEP[/green]" if i == keep_idx else "[yellow]MOVE[/yellow]"
                size_bytes = int(file.get("size", 0))
                size_mb = size_bytes / (1024 * 1024)
                size_display = f"{size_mb:.2f} MB" if size_mb >= 0.01 else f"{size_bytes / 1024:.1f} KB"
                
                name_display = file.get("name", "Unknown")
                if len(name_display) > 50:
                    name_display = name_display[:47] + "..."
                
                table.add_row(
                    f"{group_num}" if i == 0 else "",
                    action,
                    name_display,
                    size_display,
                )
        
        console.print(table)
        
        if len(duplicates) > 3:
            console.print(f"[dim]... and {len(duplicates) - 3} more groups[/dim]\n")
        
        # Confirmation
        if not dry_run and not confirm:
            console.print("[bold yellow]⚠️  This will move files in Google Drive![/bold yellow]")
            console.print("[yellow]The files will remain accessible in the review folder.[/yellow]")
            response = click.prompt(
                "\nProceed with moving duplicates?",
                type=click.Choice(["yes", "no"], case_sensitive=False),
                default="no"
            )
            if response.lower() != "yes":
                console.print("[yellow]Cancelled by user.[/yellow]")
                return
        
        if dry_run:
            console.print("\n[bold cyan]🔍 DRY RUN - No files will be moved[/bold cyan]")
            console.print(f"[dim]Would move {duplicate_count} files to review folder[/dim]")
            console.print(f"[dim]Would keep {len(duplicates)} files in original locations[/dim]")
            return
        
        # Authenticate
        client = GoogleDriveClient()
        if not client.authenticate():
            console.print("[red]✗ Authentication failed. Run 'drive-auth' first.[/red]")
            console.print("[yellow]💡 Note: You may need to re-authenticate to grant write permissions[/yellow]")
            sys.exit(1)
        
        # Move duplicates
        console.print("\n[cyan]Moving duplicates...[/cyan]")
        with console.status("[bold green]Processing..."):
            moved, kept, folder_id = client.move_duplicates_to_folder(
                duplicates,
                folder_name=folder_name,
                keep_strategy=keep_strategy,
            )
        
        # Show results
        console.print(f"\n[bold green]✓ Successfully moved {moved} files![/bold green]")
        console.print(f"[green]✓ Kept {kept} files in original locations[/green]")
        console.print(f"\n[cyan]Review folder ID:[/cyan] {folder_id}")
        console.print(f"[cyan]View in Drive:[/cyan] https://drive.google.com/drive/folders/{folder_id}")
        console.print(f"\n[yellow]💡 Tip:[/yellow] You can move files back manually if needed")
        
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON file:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error moving duplicates:[/red] {e}")
        logger.exception("Drive move error")
        sys.exit(1)


def _display_duplicate_results(duplicates: dict) -> None:
    """Display duplicate detection results in a formatted table."""
    console.print(f"[bold green]Found {len(duplicates)} duplicate groups:[/bold green]\n")

    for primary, dups in list(duplicates.items())[:10]:  # Show first 10 groups
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Primary Image")
        table.add_column("Duplicate")
        table.add_column("Similarity")

        primary_name = Path(primary).name
        table.add_row("[bold]{primary_name}[/bold]", "", "")

        for dup_path, score in dups:
            dup_name = Path(dup_path).name
            similarity = f"{100 - (score * 100 / 64):.1f}%"
            table.add_row("", dup_name, similarity)

        console.print(table)
        console.print()

    if len(duplicates) > 10:
        console.print(f"[dim]... and {len(duplicates) - 10} more groups[/dim]\n")


def _save_duplicates_json(duplicates: dict, output_path: Path) -> None:
    """Save duplicate results to JSON file."""
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(duplicates, f, indent=2)


def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

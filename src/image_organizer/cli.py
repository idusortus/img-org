"""Command-line interface for image-organizer."""

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

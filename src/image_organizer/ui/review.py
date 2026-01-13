"""
Visual review interface for duplicate detection.

Provides side-by-side comparison of duplicates with interactive controls.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text
from rich import box
from PIL import Image

logger = logging.getLogger(__name__)


class ImageMetadata:
    """Image metadata for comparison."""
    
    def __init__(self, path: Path):
        """
        Initialize metadata for an image.
        
        Args:
            path: Path to the image file
        """
        self.path = path
        self.size_bytes = path.stat().st_size if path.exists() else 0
        self.modified = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None
        
        # Try to get image dimensions
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.format: Optional[str] = None
        
        try:
            with Image.open(path) as img:
                self.width, self.height = img.size
                self.format = img.format
        except Exception as e:
            logger.debug(f"Could not read image metadata for {path}: {e}")
    
    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def resolution(self) -> Optional[str]:
        """Resolution as 'WIDTHxHEIGHT' or None."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    @property
    def megapixels(self) -> Optional[float]:
        """Resolution in megapixels."""
        if self.width and self.height:
            return (self.width * self.height) / 1_000_000
        return None
    
    def quality_score(self) -> float:
        """
        Calculate quality score for comparison.
        
        Higher is better. Based on resolution and file size.
        """
        score = 0.0
        
        # Resolution contributes most to quality
        if self.megapixels:
            score += self.megapixels * 100
        
        # Larger file size often means less compression (better quality)
        score += self.size_mb * 10
        
        return score


class DuplicateGroup:
    """A group of duplicate images with one original."""
    
    def __init__(self, original: Path, duplicates: List[Tuple[Path, float]]):
        """
        Initialize duplicate group.
        
        Args:
            original: Path to the original/reference image
            duplicates: List of (duplicate_path, similarity_score) tuples
        """
        self.original = original
        self.duplicates = duplicates
        self.original_metadata = ImageMetadata(original)
        self.duplicate_metadata = [
            (ImageMetadata(dup[0]), dup[1]) for dup in duplicates
        ]
        
        # Track user decisions
        self.to_delete: Set[Path] = set()
        self.to_keep: Set[Path] = {original}
        self.skipped = False
    
    def get_recommended_keep(self) -> Path:
        """
        Get recommended image to keep (highest quality).
        
        Returns:
            Path to the recommended image to keep
        """
        all_images = [(self.original, self.original_metadata)]
        all_images.extend([
            (dup_meta[0].path, dup_meta[0]) 
            for dup_meta in self.duplicate_metadata
        ])
        
        # Sort by quality score (highest first)
        all_images.sort(key=lambda x: x[1].quality_score(), reverse=True)
        
        return all_images[0][0]
    
    def get_recommended_delete(self) -> List[Path]:
        """
        Get recommended images to delete (lower quality).
        
        Returns:
            List of paths to delete
        """
        recommended_keep = self.get_recommended_keep()
        
        to_delete = []
        if self.original != recommended_keep:
            to_delete.append(self.original)
        
        for dup_meta, _ in self.duplicate_metadata:
            if dup_meta.path != recommended_keep:
                to_delete.append(dup_meta.path)
        
        return to_delete


class ReviewUI:
    """Terminal-based review interface using Rich."""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize review UI.
        
        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()
    
    def review_duplicates(
        self,
        duplicates: Dict[str, List[Tuple[str, float]]],
        auto_select_recommendations: bool = True,
    ) -> Dict[str, List[str]]:
        """
        Interactive review of duplicate groups.
        
        Args:
            duplicates: Dictionary mapping original paths to list of (duplicate_path, similarity)
            auto_select_recommendations: Pre-select recommended deletions
        
        Returns:
            Dictionary with 'keep' and 'delete' lists of file paths
        """
        # Convert to DuplicateGroup objects
        groups = []
        for original_str, dup_list in duplicates.items():
            original_path = Path(original_str)
            dup_paths = [(Path(d[0]), d[1]) for d in dup_list]
            group = DuplicateGroup(original_path, dup_paths)
            
            # Auto-select recommendations if requested
            if auto_select_recommendations:
                group.to_keep = {group.get_recommended_keep()}
                group.to_delete = set(group.get_recommended_delete())
            
            groups.append(group)
        
        # Show summary
        self._show_summary(groups)
        
        # Review each group interactively
        for i, group in enumerate(groups, 1):
            self.console.print()
            self._review_group(group, i, len(groups))
        
        # Collect final decisions
        all_keep = set()
        all_delete = set()
        
        for group in groups:
            if not group.skipped:
                all_keep.update(group.to_keep)
                all_delete.update(group.to_delete)
        
        return {
            "keep": [str(p) for p in all_keep],
            "delete": [str(p) for p in all_delete],
        }
    
    def _show_summary(self, groups: List[DuplicateGroup]) -> None:
        """Show summary of duplicate groups."""
        total_duplicates = sum(len(g.duplicates) for g in groups)
        
        # Calculate potential space savings
        potential_savings = 0
        for group in groups:
            for dup_meta, _ in group.duplicate_metadata:
                potential_savings += dup_meta.size_bytes
        
        savings_mb = potential_savings / (1024 * 1024)
        
        summary = Table(title="Duplicate Detection Summary", box=box.ROUNDED)
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green")
        
        summary.add_row("Duplicate Groups", str(len(groups)))
        summary.add_row("Total Duplicates", str(total_duplicates))
        summary.add_row("Potential Space Savings", f"{savings_mb:.1f} MB")
        
        self.console.print(summary)
        self.console.print()
        self.console.print(
            "[yellow]Review each group and choose which images to keep/delete.[/yellow]"
        )
        self.console.print(
            "[dim]Controls: [K]eep, [D]elete, [S]kip, [A]ccept recommendation, [Q]uit[/dim]"
        )
    
    def _review_group(
        self, 
        group: DuplicateGroup, 
        group_num: int, 
        total_groups: int
    ) -> None:
        """
        Review a single duplicate group interactively.
        
        Args:
            group: DuplicateGroup to review
            group_num: Current group number
            total_groups: Total number of groups
        """
        # Create comparison table
        table = Table(
            title=f"Duplicate Group {group_num}/{total_groups}",
            box=box.DOUBLE,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("#", style="dim", width=3)
        table.add_column("File", style="cyan")
        table.add_column("Resolution", justify="right")
        table.add_column("Size", justify="right")
        table.add_column("Date Modified", justify="right")
        table.add_column("Quality Score", justify="right")
        table.add_column("Similarity", justify="right")
        table.add_column("Action", justify="center")
        
        recommended_keep = group.get_recommended_keep()
        
        # Add original
        action_style = "green" if group.original in group.to_keep else "red"
        action_text = "KEEP ✓" if group.original in group.to_keep else "DELETE ✗"
        if group.original == recommended_keep:
            action_text += " [dim](recommended)[/dim]"
        
        table.add_row(
            "0",
            str(group.original.name),
            group.original_metadata.resolution or "N/A",
            f"{group.original_metadata.size_mb:.2f} MB",
            group.original_metadata.modified.strftime("%Y-%m-%d") if group.original_metadata.modified else "N/A",
            f"{group.original_metadata.quality_score():.1f}",
            "100%",
            f"[{action_style}]{action_text}[/{action_style}]",
        )
        
        # Add duplicates
        for idx, (dup_meta, similarity) in enumerate(group.duplicate_metadata, 1):
            action_style = "green" if dup_meta.path in group.to_keep else "red"
            action_text = "KEEP ✓" if dup_meta.path in group.to_keep else "DELETE ✗"
            if dup_meta.path == recommended_keep:
                action_text += " [dim](recommended)[/dim]"
            
            table.add_row(
                str(idx),
                str(dup_meta.path.name),
                dup_meta.resolution or "N/A",
                f"{dup_meta.size_mb:.2f} MB",
                dup_meta.modified.strftime("%Y-%m-%d") if dup_meta.modified else "N/A",
                f"{dup_meta.quality_score():.1f}",
                f"{100 - similarity:.1f}%",
                f"[{action_style}]{action_text}[/{action_style}]",
            )
        
        self.console.print(table)
        
        # Get user input
        self.console.print()
        self.console.print(
            "[yellow]Choose action: [K]eep #, [D]elete #, [S]kip group, "
            "[A]ccept recommendation, [Q]uit[/yellow]"
        )
        
        # For now, just auto-accept recommendations
        # TODO: Add interactive input handling
        self.console.print("[dim]Auto-accepting recommendation for this group.[/dim]")
    
    def show_final_confirmation(
        self, 
        to_delete: List[Path],
        to_keep: List[Path]
    ) -> bool:
        """
        Show final confirmation before deletion.
        
        Args:
            to_delete: List of files marked for deletion
            to_keep: List of files to keep
        
        Returns:
            True if user confirms, False otherwise
        """
        total_size = sum(p.stat().st_size for p in to_delete if p.exists())
        size_mb = total_size / (1024 * 1024)
        
        panel = Panel(
            f"[bold red]Delete {len(to_delete)} files[/bold red]\n"
            f"[bold green]Keep {len(to_keep)} files[/bold green]\n\n"
            f"[yellow]Space to recover: {size_mb:.1f} MB[/yellow]",
            title="Final Confirmation",
            box=box.DOUBLE,
        )
        
        self.console.print(panel)
        
        # Show sample of files to delete
        self.console.print("\n[red]Files to delete (sample):[/red]")
        for i, path in enumerate(to_delete[:10], 1):
            self.console.print(f"  {i}. {path}")
        
        if len(to_delete) > 10:
            self.console.print(f"  ... and {len(to_delete) - 10} more")
        
        # For now, return True (auto-confirm)
        # TODO: Add interactive confirmation
        return True

"""
End-to-end demo script to showcase the complete workflow.

Creates sample duplicate images, scans them, reviews them, and demonstrates
the safety features.
"""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from image_organizer.core.scanner import ImageScanner
from image_organizer.core.detector import DuplicateDetector
from image_organizer.ui.review import ReviewUI
from image_organizer.utils.config import Config


def create_demo_images(demo_dir: Path) -> None:
    """
    Create sample images for demonstration.
    
    Args:
        demo_dir: Directory to create images in
    """
    print(f"Creating demo images in: {demo_dir}")
    
    # Create a few original images
    originals_dir = demo_dir / "originals"
    originals_dir.mkdir(exist_ok=True)
    
    # Original 1: High quality landscape
    img1 = Image.new("RGB", (1920, 1080), color=(70, 130, 180))  # Steel blue
    img1.save(originals_dir / "landscape_1920x1080.jpg", "JPEG", quality=95)
    
    # Original 2: Medium quality portrait
    img2 = Image.new("RGB", (800, 1200), color=(220, 20, 60))  # Crimson
    img2.save(originals_dir / "portrait_800x1200.jpg", "JPEG", quality=85)
    
    # Original 3: Small image
    img3 = Image.new("RGB", (640, 480), color=(50, 205, 50))  # Lime green
    img3.save(originals_dir / "small_640x480.jpg", "JPEG", quality=75)
    
    # Create duplicates directory
    duplicates_dir = demo_dir / "duplicates"
    duplicates_dir.mkdir(exist_ok=True)
    
    # Duplicate 1: Copy of landscape (exact duplicate)
    shutil.copy(
        originals_dir / "landscape_1920x1080.jpg",
        duplicates_dir / "landscape_copy.jpg"
    )
    
    # Duplicate 2: Lower quality version of landscape
    img1_low = Image.new("RGB", (1280, 720), color=(70, 130, 180))
    img1_low.save(duplicates_dir / "landscape_1280x720.jpg", "JPEG", quality=60)
    
    # Duplicate 3: Copy of portrait
    shutil.copy(
        originals_dir / "portrait_800x1200.jpg",
        duplicates_dir / "portrait_copy.jpg"
    )
    
    # Create protected directory (should be skipped)
    protected_dir = demo_dir / "Family_Photos"
    protected_dir.mkdir(exist_ok=True)
    
    img_protected = Image.new("RGB", (1024, 768), color=(255, 215, 0))  # Gold
    img_protected.save(protected_dir / "important_memory.jpg", "JPEG", quality=90)
    
    print(f"✓ Created 7 images (3 originals, 3 duplicates, 1 protected)")


def main():
    """Run the demo."""
    print("=" * 70)
    print("IMAGE ORGANIZER - END-TO-END DEMO")
    print("=" * 70)
    print()
    
    with TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir) / "demo"
        demo_dir.mkdir()
        
        # Step 1: Create demo images
        print("STEP 1: Creating demo images")
        print("-" * 70)
        create_demo_images(demo_dir)
        print()
        
        # Step 2: Scan for images
        print("STEP 2: Scanning for images")
        print("-" * 70)
        config = Config()
        scanner = ImageScanner(config)
        image_paths = scanner.scan_directory(demo_dir, recursive=True)
        print(f"✓ Found {len(image_paths)} images")
        for path in image_paths:
            print(f"  - {path.relative_to(demo_dir)}")
        print()
        
        # Step 3: Detect duplicates
        print("STEP 3: Detecting duplicates")
        print("-" * 70)
        detector = DuplicateDetector(config, show_progress=True)
        duplicates = detector.find_duplicates(image_paths)
        
        print(f"✓ Found {len(duplicates)} duplicate groups")
        for original, dups in duplicates.items():
            print(f"\n  Original: {Path(original).name}")
            for dup_path, similarity in dups:
                print(f"    → Duplicate: {Path(dup_path).name} (similarity: {100 - similarity:.1f}%)")
        print()
        
        # Step 4: Review duplicates
        print("STEP 4: Reviewing duplicates (auto-recommendation)")
        print("-" * 70)
        if duplicates:
            review_ui = ReviewUI()
            decisions = review_ui.review_duplicates(
                duplicates,
                auto_select_recommendations=True
            )
            
            print(f"\n✓ Review complete")
            print(f"  Files to keep: {len(decisions['keep'])}")
            print(f"  Files to delete: {len(decisions['delete'])}")
            
            print("\n  Recommended for deletion:")
            for file_path in decisions['delete'][:5]:  # Show first 5
                print(f"    - {Path(file_path).name}")
            
            if len(decisions['delete']) > 5:
                print(f"    ... and {len(decisions['delete']) - 5} more")
        else:
            print("  No duplicates found to review")
        print()
        
        # Step 5: Summary
        print("STEP 5: Summary")
        print("-" * 70)
        print("✓ Demo completed successfully!")
        print()
        print("In a real workflow, you would now:")
        print("  1. Review the duplicates interactively")
        print("  2. Stage selected files for deletion")
        print("  3. Confirm deletion (moves to recycle bin)")
        print("  4. Or undo if you change your mind")
        print()
        print("=" * 70)


if __name__ == "__main__":
    main()

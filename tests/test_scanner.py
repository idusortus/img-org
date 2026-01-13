"""Test the image scanner module."""

import tempfile
from pathlib import Path

import pytest

from image_organizer.core.scanner import ImageScanner
from image_organizer.utils.config import Config


@pytest.fixture
def temp_image_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test image files
        (tmpdir_path / "image1.jpg").touch()
        (tmpdir_path / "image2.png").touch()
        (tmpdir_path / "document.txt").touch()  # Not an image
        (tmpdir_path / ".hidden.jpg").touch()  # Hidden file

        # Create subdirectory
        subdir = tmpdir_path / "subdir"
        subdir.mkdir()
        (subdir / "image3.jpg").touch()

        yield tmpdir_path


def test_scanner_finds_images(temp_image_dir):
    """Test that scanner finds image files."""
    config = Config()
    scanner = ImageScanner(config, show_progress=False)

    images = scanner.scan_directory(temp_image_dir, recursive=True, skip_hidden=True)

    # Should find 3 images (excluding .hidden.jpg and document.txt)
    assert len(images) == 3

    image_names = {img.name for img in images}
    assert "image1.jpg" in image_names
    assert "image2.png" in image_names
    assert "image3.jpg" in image_names
    assert "document.txt" not in image_names
    assert ".hidden.jpg" not in image_names


def test_scanner_non_recursive(temp_image_dir):
    """Test non-recursive scanning."""
    config = Config()
    scanner = ImageScanner(config, show_progress=False)

    images = scanner.scan_directory(temp_image_dir, recursive=False, skip_hidden=True)

    # Should find only 2 images in root (excluding subdirectory)
    assert len(images) == 2

    image_names = {img.name for img in images}
    assert "image1.jpg" in image_names
    assert "image2.png" in image_names
    assert "image3.jpg" not in image_names  # In subdirectory


def test_scanner_nonexistent_directory():
    """Test that scanner raises error for nonexistent directory."""
    config = Config()
    scanner = ImageScanner(config, show_progress=False)

    with pytest.raises(FileNotFoundError):
        scanner.scan_directory(Path("/nonexistent/path"))

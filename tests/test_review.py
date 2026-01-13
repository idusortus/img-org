"""Tests for the review UI module."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image

from image_organizer.ui.review import (
    ImageMetadata,
    DuplicateGroup,
    ReviewUI,
)


class TestImageMetadata:
    """Test ImageMetadata class."""

    def test_metadata_from_image(self, tmp_path):
        """Test metadata extraction from an actual image."""
        # Create a test image
        image_path = tmp_path / "test.jpg"
        img = Image.new("RGB", (800, 600), color="red")
        img.save(image_path, "JPEG")

        metadata = ImageMetadata(image_path)

        assert metadata.path == image_path
        assert metadata.width == 800
        assert metadata.height == 600
        assert metadata.resolution == "800x600"
        assert metadata.megapixels == pytest.approx(0.48, abs=0.01)
        assert metadata.size_bytes > 0
        assert metadata.format == "JPEG"

    def test_quality_score_calculation(self, tmp_path):
        """Test quality score calculation."""
        # Create high-quality image
        high_quality_path = tmp_path / "high_quality.jpg"
        img_high = Image.new("RGB", (1920, 1080), color="blue")
        img_high.save(high_quality_path, "JPEG", quality=95)

        # Create low-quality image
        low_quality_path = tmp_path / "low_quality.jpg"
        img_low = Image.new("RGB", (640, 480), color="blue")
        img_low.save(low_quality_path, "JPEG", quality=50)

        high_meta = ImageMetadata(high_quality_path)
        low_meta = ImageMetadata(low_quality_path)

        # High quality should have higher score
        assert high_meta.quality_score() > low_meta.quality_score()


class TestDuplicateGroup:
    """Test DuplicateGroup class."""

    def test_group_initialization(self, tmp_path):
        """Test duplicate group initialization."""
        # Create test images
        original = tmp_path / "original.jpg"
        dup1 = tmp_path / "dup1.jpg"
        dup2 = tmp_path / "dup2.jpg"

        for path in [original, dup1, dup2]:
            img = Image.new("RGB", (800, 600), color="red")
            img.save(path, "JPEG")

        duplicates = [(dup1, 0.0), (dup2, 2.5)]
        group = DuplicateGroup(original, duplicates)

        assert group.original == original
        assert len(group.duplicates) == 2
        assert group.original in group.to_keep
        assert len(group.to_delete) == 0
        assert not group.skipped

    def test_recommended_keep_highest_quality(self, tmp_path):
        """Test that highest quality image is recommended to keep."""
        # Create original (medium quality)
        original = tmp_path / "original.jpg"
        img_original = Image.new("RGB", (800, 600), color="red")
        img_original.save(original, "JPEG", quality=75)

        # Create duplicate (higher quality)
        dup_high = tmp_path / "dup_high.jpg"
        img_high = Image.new("RGB", (1920, 1080), color="red")
        img_high.save(dup_high, "JPEG", quality=95)

        # Create duplicate (lower quality)
        dup_low = tmp_path / "dup_low.jpg"
        img_low = Image.new("RGB", (640, 480), color="red")
        img_low.save(dup_low, "JPEG", quality=50)

        duplicates = [(dup_high, 0.0), (dup_low, 1.0)]
        group = DuplicateGroup(original, duplicates)

        recommended = group.get_recommended_keep()
        assert recommended == dup_high  # Highest quality

    def test_recommended_delete_list(self, tmp_path):
        """Test that lower quality images are recommended for deletion."""
        # Create test images
        original = tmp_path / "original.jpg"
        dup1 = tmp_path / "dup1.jpg"

        for path, size in [(original, (800, 600)), (dup1, (1920, 1080))]:
            img = Image.new("RGB", size, color="red")
            img.save(path, "JPEG")

        duplicates = [(dup1, 0.0)]
        group = DuplicateGroup(original, duplicates)

        recommended_delete = group.get_recommended_delete()
        # dup1 is higher quality, so original should be deleted
        assert original in recommended_delete
        assert dup1 not in recommended_delete


class TestReviewUI:
    """Test ReviewUI class."""

    def test_review_ui_initialization(self):
        """Test ReviewUI initialization."""
        ui = ReviewUI()
        assert ui.console is not None

    def test_review_duplicates_structure(self, tmp_path):
        """Test review_duplicates returns correct structure."""
        # Create test images
        original = tmp_path / "original.jpg"
        dup1 = tmp_path / "dup1.jpg"

        for path in [original, dup1]:
            img = Image.new("RGB", (800, 600), color="red")
            img.save(path, "JPEG")

        duplicates = {
            str(original): [(str(dup1), 0.0)]
        }

        ui = ReviewUI()
        result = ui.review_duplicates(duplicates, auto_select_recommendations=True)

        # Check structure
        assert "keep" in result
        assert "delete" in result
        assert isinstance(result["keep"], list)
        assert isinstance(result["delete"], list)
        
        # Should have recommendations
        assert len(result["keep"]) > 0 or len(result["delete"]) > 0

    def test_final_confirmation_structure(self, tmp_path):
        """Test show_final_confirmation works without errors."""
        # Create test images
        to_delete = [tmp_path / f"delete{i}.jpg" for i in range(3)]
        to_keep = [tmp_path / f"keep{i}.jpg" for i in range(2)]

        for path in to_delete + to_keep:
            img = Image.new("RGB", (800, 600), color="red")
            img.save(path, "JPEG")

        ui = ReviewUI()
        # Should return True (auto-confirm for now)
        result = ui.show_final_confirmation(to_delete, to_keep)
        assert result is True

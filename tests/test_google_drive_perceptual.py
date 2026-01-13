"""
Tests for Google Drive perceptual hashing duplicate detection.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestGoogleDrivePerceptualHashing(unittest.TestCase):
    """Test perceptual hashing for Google Drive."""

    def setUp(self):
        """Set up test fixtures."""
        from image_organizer.platforms.google_drive import GoogleDriveClient
        
        self.client = GoogleDriveClient()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock sample files
        self.sample_files = [
            {
                "id": "file1",
                "name": "image1.jpg",
                "size": "1024000",
                "md5Checksum": "abc123",
            },
            {
                "id": "file2",
                "name": "image2.jpg",
                "size": "1024000",
                "md5Checksum": "abc123",  # Same MD5
            },
            {
                "id": "file3",
                "name": "image3.jpg",
                "size": "2048000",
                "md5Checksum": "def456",
            },
            {
                "id": "file4",
                "name": "image4.jpg",
                "size": "2048000",
                "md5Checksum": "ghi789",
            },
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_find_near_duplicates_not_authenticated(self):
        """Test that perceptual hashing fails when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated"):
            self.client.find_near_duplicates_by_phash(
                self.sample_files, self.temp_dir
            )

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", False)
    def test_find_near_duplicates_imagededup_not_installed(self):
        """Test error when imagededup is not installed."""
        self.client.service = Mock()
        
        with pytest.raises(ImportError, match="imagededup not installed"):
            self.client.find_near_duplicates_by_phash(
                self.sample_files, self.temp_dir
            )

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    @patch("image_organizer.platforms.google_drive.PHash")
    def test_find_near_duplicates_success(self, mock_phash_class):
        """Test successful perceptual hash duplicate detection."""
        # Mock authentication
        self.client.service = Mock()
        
        # Mock thumbnail downloads
        def mock_download(file_id, path):
            # Create a fake image file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fake_image_data")
            return True
        
        self.client.download_thumbnail = Mock(side_effect=mock_download)
        
        # Mock PHash behavior
        mock_phasher = Mock()
        mock_phash_class.return_value = mock_phasher
        
        # Mock encodings
        mock_phasher.encode_images.return_value = {
            "file1.jpg": "hash1",
            "file2.jpg": "hash2",
            "file3.jpg": "hash3",
            "file4.jpg": "hash4",
        }
        
        # Mock duplicates - file1 similar to file2, file3 similar to file4
        mock_phasher.find_duplicates.return_value = {
            "file1.jpg": ["file2.jpg"],
            "file2.jpg": ["file1.jpg"],
            "file3.jpg": ["file4.jpg"],
            "file4.jpg": ["file3.jpg"],
        }
        
        # Run detection
        duplicates = self.client.find_near_duplicates_by_phash(
            self.sample_files, self.temp_dir, threshold=10
        )
        
        # Verify results
        assert len(duplicates) == 4  # All files have near-duplicates
        assert "file1" in duplicates
        assert len(duplicates["file1"]) == 1
        assert duplicates["file1"][0]["id"] == "file2"
        
        # Verify thumbnail downloads
        assert self.client.download_thumbnail.call_count == 4
        
        # Verify PHash was used correctly
        mock_phasher.encode_images.assert_called_once()
        mock_phasher.find_duplicates.assert_called_once_with(
            encoding_map=mock_phasher.encode_images.return_value,
            max_distance_threshold=10,
        )

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    @patch("image_organizer.platforms.google_drive.PHash")
    def test_find_near_duplicates_no_thumbnails_downloaded(self, mock_phash_class):
        """Test handling when no thumbnails can be downloaded."""
        self.client.service = Mock()
        
        # Mock failed thumbnail downloads
        self.client.download_thumbnail = Mock(return_value=False)
        
        # Run detection
        duplicates = self.client.find_near_duplicates_by_phash(
            self.sample_files, self.temp_dir
        )
        
        # Should return empty dict
        assert duplicates == {}
        
        # Verify PHash was never called
        mock_phash_class.return_value.encode_images.assert_not_called()

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    @patch("image_organizer.platforms.google_drive.PHash")
    def test_find_near_duplicates_with_max_files(self, mock_phash_class):
        """Test perceptual hashing with max_files limit."""
        self.client.service = Mock()
        
        # Mock thumbnail downloads
        self.client.download_thumbnail = Mock(return_value=True)
        
        # Mock PHash
        mock_phasher = Mock()
        mock_phash_class.return_value = mock_phasher
        mock_phasher.encode_images.return_value = {"file1.jpg": "hash1"}
        mock_phasher.find_duplicates.return_value = {}
        
        # Run detection with max_files=1
        self.client.find_near_duplicates_by_phash(
            self.sample_files, self.temp_dir, max_files=1
        )
        
        # Should only download 1 thumbnail
        assert self.client.download_thumbnail.call_count == 1

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    @patch("image_organizer.platforms.google_drive.PHash")
    def test_find_near_duplicates_phash_error(self, mock_phash_class):
        """Test handling of perceptual hashing errors."""
        self.client.service = Mock()
        
        # Mock thumbnail downloads
        self.client.download_thumbnail = Mock(return_value=True)
        
        # Mock PHash to raise error
        mock_phasher = Mock()
        mock_phash_class.return_value = mock_phasher
        mock_phasher.encode_images.side_effect = Exception("PHash failed")
        
        # Should not raise, but return empty dict
        duplicates = self.client.find_near_duplicates_by_phash(
            self.sample_files, self.temp_dir
        )
        
        assert duplicates == {}

    def test_find_all_duplicates_not_authenticated(self):
        """Test find_all_duplicates fails when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated"):
            self.client.find_all_duplicates(
                self.sample_files, self.temp_dir
            )

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    @patch("image_organizer.platforms.google_drive.PHash")
    def test_find_all_duplicates_success(self, mock_phash_class):
        """Test combined MD5 + perceptual hash detection."""
        # Mock authentication
        mock_service = Mock()
        self.client.service = mock_service
        
        # Mock thumbnail downloads
        self.client.download_thumbnail = Mock(return_value=True)
        
        # Mock PHash
        mock_phasher = Mock()
        mock_phash_class.return_value = mock_phasher
        mock_phasher.encode_images.return_value = {
            "file3.jpg": "hash3",
            "file4.jpg": "hash4",
        }
        mock_phasher.find_duplicates.return_value = {
            "file3.jpg": ["file4.jpg"],
        }
        
        # Run combined detection
        results = self.client.find_all_duplicates(
            self.sample_files,
            self.temp_dir,
            phash_threshold=10,
            include_near_duplicates=True,
        )
        
        # Verify structure
        assert "exact" in results
        assert "near" in results
        assert "stats" in results
        
        # Verify exact duplicates (MD5)
        exact = results["exact"]
        assert len(exact) == 1  # file1 and file2 have same MD5
        assert "abc123" in exact
        assert len(exact["abc123"]) == 2
        
        # Verify near duplicates
        near = results["near"]
        assert "file3" in near
        
        # Verify stats
        stats = results["stats"]
        assert stats["exact_duplicate_groups"] == 1
        assert stats["exact_duplicate_files"] == 1  # 2 files - 1 = 1 duplicate
        assert stats["total_files_scanned"] == 4

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", False)
    def test_find_all_duplicates_without_imagededup(self):
        """Test find_all_duplicates when imagededup not available."""
        self.client.service = Mock()
        
        # Run with include_near_duplicates=True but imagededup not available
        results = self.client.find_all_duplicates(
            self.sample_files,
            self.temp_dir,
            include_near_duplicates=True,
        )
        
        # Should still find exact duplicates
        assert len(results["exact"]) == 1
        
        # Near duplicates should be empty
        assert results["near"] == {}

    @patch("image_organizer.platforms.google_drive.IMAGEDEDUP_AVAILABLE", True)
    def test_find_all_duplicates_skip_near_duplicates(self):
        """Test find_all_duplicates with include_near_duplicates=False."""
        self.client.service = Mock()
        
        # Run without near-duplicate detection
        results = self.client.find_all_duplicates(
            self.sample_files,
            self.temp_dir,
            include_near_duplicates=False,
        )
        
        # Should only have exact duplicates
        assert len(results["exact"]) == 1
        assert results["near"] == {}
        
        # Thumbnail download should not be called
        # (no need to mock since it won't be called)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

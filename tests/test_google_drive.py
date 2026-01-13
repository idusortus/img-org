"""Tests for Google Drive integration."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, MagicMock, patch

import pytest

from image_organizer.platforms.google_drive import GoogleDriveClient


class TestGoogleDriveClient:
    """Test GoogleDriveClient class."""

    def test_initialization(self, tmp_path):
        """Test client initialization."""
        creds_file = tmp_path / "credentials.json"
        token_file = tmp_path / "token.json"
        
        client = GoogleDriveClient(
            credentials_file=creds_file,
            token_file=token_file,
        )
        
        assert client.credentials_file == creds_file
        assert client.token_file == token_file
        assert client.credentials is None
        assert client.service is None

    def test_authentication_no_credentials_file(self, tmp_path):
        """Test authentication fails when credentials file doesn't exist."""
        client = GoogleDriveClient(
            credentials_file=tmp_path / "nonexistent.json",
            token_file=tmp_path / "token.json",
        )
        
        result = client.authenticate()
        assert result is False

    @patch("image_organizer.platforms.google_drive.Credentials")
    @patch("image_organizer.platforms.google_drive.build")
    def test_authentication_with_existing_token(
        self, mock_build, mock_credentials_class, tmp_path
    ):
        """Test authentication with existing valid token."""
        # Create mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials_class.from_authorized_user_file.return_value = mock_creds
        
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Create token file
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps({"token": "test_token"}))
        
        client = GoogleDriveClient(
            credentials_file=tmp_path / "credentials.json",
            token_file=token_file,
        )
        
        result = client.authenticate()
        
        assert result is True
        assert client.service == mock_service

    def test_list_image_files_not_authenticated(self):
        """Test listing files fails when not authenticated."""
        client = GoogleDriveClient()
        
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.list_image_files()

    @patch("image_organizer.platforms.google_drive.build")
    def test_find_exact_duplicates_by_md5(self, mock_build):
        """Test MD5-based duplicate detection."""
        # Mock the service
        mock_service = MagicMock()
        
        # Create test files with duplicate MD5s
        files = [
            {"id": "1", "name": "image1.jpg", "md5Checksum": "abc123", "size": "1000"},
            {"id": "2", "name": "image2.jpg", "md5Checksum": "abc123", "size": "1000"},
            {"id": "3", "name": "image3.jpg", "md5Checksum": "def456", "size": "2000"},
            {"id": "4", "name": "image4.jpg", "md5Checksum": "def456", "size": "2000"},
            {"id": "5", "name": "image5.jpg", "md5Checksum": "ghi789", "size": "3000"},
        ]
        
        client = GoogleDriveClient()
        client.service = mock_service
        
        duplicates = client.find_exact_duplicates_by_md5(files)
        
        # Should find 2 duplicate groups (abc123 and def456)
        assert len(duplicates) == 2
        assert "abc123" in duplicates
        assert "def456" in duplicates
        assert len(duplicates["abc123"]) == 2
        assert len(duplicates["def456"]) == 2
        
        # Single file (ghi789) should not be in duplicates
        assert "ghi789" not in duplicates

    def test_find_exact_duplicates_no_md5(self):
        """Test that files without MD5 are skipped."""
        files = [
            {"id": "1", "name": "image1.jpg", "size": "1000"},  # No MD5
            {"id": "2", "name": "image2.jpg", "md5Checksum": "abc123", "size": "1000"},
        ]
        
        client = GoogleDriveClient()
        client.service = MagicMock()
        
        duplicates = client.find_exact_duplicates_by_md5(files)
        
        # No duplicates (only one file has MD5)
        assert len(duplicates) == 0

    @patch("image_organizer.platforms.google_drive.build")
    def test_move_to_trash_not_authenticated(self, mock_build):
        """Test moving to trash fails when not authenticated."""
        client = GoogleDriveClient()
        
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.move_to_trash("file_id")

    @patch("image_organizer.platforms.google_drive.build")
    def test_restore_from_trash_not_authenticated(self, mock_build):
        """Test restoring from trash fails when not authenticated."""
        client = GoogleDriveClient()
        
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.restore_from_trash("file_id")

    def test_execute_with_retry_success(self):
        """Test retry logic succeeds on first attempt."""
        client = GoogleDriveClient()
        
        mock_api_call = MagicMock()
        mock_api_call.return_value.execute.return_value = {"result": "success"}
        
        result = client._execute_with_retry(mock_api_call, test_arg="value")
        
        assert result == {"result": "success"}
        mock_api_call.assert_called_once_with(test_arg="value")

    @patch("time.sleep")  # Mock sleep to speed up test
    def test_execute_with_retry_eventual_success(self, mock_sleep):
        """Test retry logic succeeds after failures."""
        from googleapiclient.errors import HttpError
        from unittest.mock import Mock
        
        client = GoogleDriveClient()
        
        # Mock API call that fails twice then succeeds
        mock_api_call = MagicMock()
        mock_resp_429 = Mock()
        mock_resp_429.status = 429  # Rate limit
        
        mock_api_call.return_value.execute.side_effect = [
            HttpError(mock_resp_429, b"Rate limited"),
            HttpError(mock_resp_429, b"Rate limited"),
            {"result": "success"},
        ]
        
        result = client._execute_with_retry(mock_api_call, max_retries=3)
        
        assert result == {"result": "success"}
        assert mock_api_call.return_value.execute.call_count == 3
        assert mock_sleep.call_count == 2  # Should sleep 2 times (1s, 2s)

    def test_execute_with_retry_max_retries_exceeded(self):
        """Test retry logic fails after max retries."""
        from googleapiclient.errors import HttpError
        from unittest.mock import Mock
        
        client = GoogleDriveClient()
        
        mock_api_call = MagicMock()
        mock_resp_429 = Mock()
        mock_resp_429.status = 429
        
        mock_api_call.return_value.execute.side_effect = HttpError(
            mock_resp_429, b"Rate limited"
        )
        
        with pytest.raises(HttpError):
            client._execute_with_retry(mock_api_call, max_retries=3)

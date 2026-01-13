"""Platform-specific implementations for different storage backends."""

from image_organizer.platforms.google_drive import GoogleDriveClient

try:
    from image_organizer.platforms.local import LocalFileSystem
    __all__ = ["LocalFileSystem", "GoogleDriveClient"]
except ImportError:
    __all__ = ["GoogleDriveClient"]

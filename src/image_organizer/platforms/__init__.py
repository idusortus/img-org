"""Platform-specific implementations for different storage backends."""

from image_organizer.platforms.local import LocalFileSystem

__all__ = ["LocalFileSystem"]

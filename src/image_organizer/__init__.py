"""
Image Organizer - Intelligent duplicate image detection and storage optimization.

This package helps users organize images and reduce storage space by finding and
eliminating duplicate/near-duplicate images with a safety-first approach.
"""

__version__ = "0.1.0"
__author__ = "Image Organizer Contributors"

from image_organizer.core.detector import DuplicateDetector
from image_organizer.core.scanner import ImageScanner
from image_organizer.core.staging import SafeImageDeleter

__all__ = ["DuplicateDetector", "ImageScanner", "SafeImageDeleter", "__version__"]

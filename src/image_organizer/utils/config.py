"""Configuration management for image-organizer."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from image_organizer.utils.logger import setup_logger

logger = setup_logger(__name__)


class Config:
    """Manages user configuration and settings."""

    DEFAULT_CONFIG_DIR = Path.home() / ".image-organizer"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
    DEFAULT_STAGING_DIR = DEFAULT_CONFIG_DIR / "staging"
    DEFAULT_OPERATIONS_LOG = DEFAULT_CONFIG_DIR / "operations.log"

    DEFAULT_SETTINGS = {
        "protected_folders": [
            "Family Photos",
            "Wedding",
            "Kids",
            "Vacation",
            "Important",
        ],
        "similarity_threshold": 10,  # Hamming distance for perceptual hashing
        "hash_method": "phash",  # phash, dhash, ahash, whash
        "platforms": {"local": {"enabled": True}, "google_drive": {"enabled": False}},
        "safety": {
            "require_visual_confirmation": True,
            "use_recycle_bin": True,
            "max_undo_history_days": 30,
        },
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to config file (default: ~/.image-organizer/config.json)
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.settings: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file or create with defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                logger.debug(f"Loaded configuration from {self.config_file}")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid config file: {e}. Using defaults.")
                self.settings = self.DEFAULT_SETTINGS.copy()
        else:
            logger.info("No config file found. Creating with defaults.")
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save()

    def save(self) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)
        logger.debug(f"Saved configuration to {self.config_file}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., 'safety.use_recycle_bin')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        target = self.settings
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()

    def add_protected_folder(self, folder: str) -> None:
        """
        Add a folder to the protected folders list.

        Args:
            folder: Folder name or pattern to protect
        """
        protected = self.get("protected_folders", [])
        if folder not in protected:
            protected.append(folder)
            self.set("protected_folders", protected)
            logger.info(f"Added protected folder: {folder}")

    def remove_protected_folder(self, folder: str) -> None:
        """
        Remove a folder from the protected folders list.

        Args:
            folder: Folder name or pattern to unprotect
        """
        protected = self.get("protected_folders", [])
        if folder in protected:
            protected.remove(folder)
            self.set("protected_folders", protected)
            logger.info(f"Removed protected folder: {folder}")

    def is_path_protected(self, path: Path) -> bool:
        """
        Check if a path is in a protected folder.

        Args:
            path: Path to check

        Returns:
            True if path is protected
        """
        protected_folders = self.get("protected_folders", [])
        path_str = str(path).lower()
        return any(
            protected.lower() in path_str for protected in protected_folders
        )

    def get_staging_dir(self) -> Path:
        """Get the staging directory path."""
        return self.DEFAULT_STAGING_DIR

    def get_operations_log(self) -> Path:
        """Get the operations log file path."""
        return self.DEFAULT_OPERATIONS_LOG

import os
from typing import Optional


class FileSystemManager:
    """Centralized filesystem management with predefined directory structure"""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize with base directory and standard subdirectories

        Args:
            base_dir: Optional base directory (defaults to script location)
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.directories = {
            "log": "log",
            "config": "config",
            "temp_file": "temp_file",
            "report": "report",
        }
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        for dir_name in self.directories.values():
            dir_path = self.get_full_path(dir_name)
            os.makedirs(dir_path, exist_ok=True)

    def get_full_path(self, dir_type: str,
                      filename: Optional[str] = None) -> str:
        """
        Get full path for a directory type and optional filename

        Args:
            dir_type: One of 'log', 'config', 'temp', 'report', 'api_responses'
            filename: Optional filename to append to path

        Returns:
            Full absolute path
        """
        if dir_type not in self.directories:
            raise ValueError(
                f"Invalid directory type: {dir_type}. "
                f"Valid types are: {list(self.directories.keys())}"
            )

        path = os.path.join(self.base_dir, self.directories[dir_type])
        if filename:
            path = os.path.join(path, filename)
        return path

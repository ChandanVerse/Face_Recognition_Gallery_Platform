"""
Local filesystem storage service for managing image uploads and downloads
"""
import os
import shutil
from pathlib import Path
from typing import BinaryIO
import io

from backend.config.settings import get_settings

settings = get_settings()


class StorageService:
    """Handles file storage operations on local filesystem"""

    def __init__(self):
        self.base_path = Path(settings.STORAGE_BASE_PATH)
        self.base_url = settings.STORAGE_BASE_URL
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Ensure base storage directory and subdirectories exist"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "galleries").mkdir(exist_ok=True)
        (self.base_path / "reference").mkdir(exist_ok=True)
        print(f"[OK] Storage directory ready: {self.base_path.absolute()}")

    def _ensure_directory_exists(self, file_path: str):
        """Create parent directories for a file path if they don't exist"""
        full_path = self.base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_data: bytes | BinaryIO, file_path: str, content_type: str = "image/jpeg") -> str:
        """
        Upload file to local filesystem

        Args:
            file_data: File content as bytes or file-like object
            file_path: Relative path (e.g., "galleries/123/photo1.jpg" or "galleries/123/photo1.webp")
            content_type: MIME type (ignored for local storage, kept for compatibility)

        Returns:
            file_path of saved file
        """
        try:
            # Ensure parent directory exists
            self._ensure_directory_exists(file_path)

            full_path = self.base_path / file_path

            # Handle both bytes and file-like objects
            if isinstance(file_data, bytes):
                with open(full_path, 'wb') as f:
                    f.write(file_data)
            else:
                with open(full_path, 'wb') as f:
                    shutil.copyfileobj(file_data, f)

            print(f"[OK] Uploaded: {file_path}")
            return file_path

        except Exception as e:
            print(f"[ERROR] Error uploading file: {e}")
            raise

    def download_file(self, file_path: str) -> bytes:
        """
        Download file from local filesystem

        Args:
            file_path: Relative path (e.g., "galleries/123/photo1.jpg" or "galleries/123/photo1.webp")

        Returns:
            File content as bytes
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(full_path, 'rb') as f:
                return f.read()

        except Exception as e:
            print(f"[ERROR] Error downloading file: {e}")
            raise

    def download_to_file(self, file_path: str, local_path: str | Path):
        """Copy file from storage to another local path"""
        try:
            source_path = self.base_path / file_path

            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            shutil.copy2(source_path, local_path)

        except Exception as e:
            print(f"[ERROR] Error copying file: {e}")
            raise

    def generate_url(self, file_path: str) -> str:
        """
        Generate a URL for accessing a file via FastAPI static file serving

        Args:
            file_path: Relative path (e.g., "galleries/123/photo1.jpg" or "galleries/123/photo1.webp")

        Returns:
            Static URL (e.g., "https://recommendations.vosmos.events:7008/storage/galleries/123/photo1.jpg" or ".../photo1.webp")
        """
        # Replace backslashes with forward slashes for URLs
        url_path = file_path.replace("\\", "/")
        return f"{self.base_url}/{url_path}"

    # Alias for compatibility with existing code
    def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Alias for generate_url() for backward compatibility
        Note: expiration parameter is ignored for local storage
        """
        return self.generate_url(file_path)

    def delete_file(self, file_path: str):
        """Delete a file from local filesystem"""
        try:
            full_path = self.base_path / file_path

            if full_path.exists():
                full_path.unlink()
                print(f"[OK] Deleted: {file_path}")
            else:
                print(f"[WARN] File not found for deletion: {file_path}")

        except Exception as e:
            print(f"[ERROR] Error deleting file: {e}")
            raise

    def list_files(self, prefix: str = "") -> list[str]:
        """List all files with given prefix"""
        try:
            search_path = self.base_path / prefix if prefix else self.base_path

            if not search_path.exists():
                return []

            # Recursively find all files under the prefix path
            files = []
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    # Get relative path from base storage directory
                    relative_path = file_path.relative_to(self.base_path)
                    files.append(str(relative_path).replace("\\", "/"))

            return files

        except Exception as e:
            print(f"[ERROR] Error listing files: {e}")
            raise

    def delete_directory(self, dir_path: str):
        """Delete an entire directory and its contents"""
        try:
            full_path = self.base_path / dir_path

            if full_path.exists() and full_path.is_dir():
                shutil.rmtree(full_path)
                print(f"[OK] Deleted directory: {dir_path}")
            else:
                print(f"[WARN] Directory not found for deletion: {dir_path}")

        except Exception as e:
            print(f"[ERROR] Error deleting directory: {e}")
            raise


__all__ = ["StorageService"]

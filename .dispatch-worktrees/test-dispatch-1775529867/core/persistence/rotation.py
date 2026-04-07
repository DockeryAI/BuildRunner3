"""
File rotation and compression for BuildRunner storage

Features:
- Automatic file rotation when size exceeds threshold
- Gzip compression of rotated files
- Automatic cleanup of old files
"""

import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileRotator:
    """Handles file rotation and compression."""

    def __init__(
        self,
        max_size_bytes: int = 1_000_000,  # 1MB default
        retention_days: int = 30,
        compress: bool = True,
    ):
        """
        Initialize file rotator.

        Args:
            max_size_bytes: Maximum file size before rotation (default 1MB)
            retention_days: Number of days to retain old files
            compress: Whether to compress rotated files
        """
        self.max_size_bytes = max_size_bytes
        self.retention_days = retention_days
        self.compress = compress

    def should_rotate(self, file_path: Path) -> bool:
        """
        Check if file should be rotated.

        Args:
            file_path: Path to file to check

        Returns:
            True if file exceeds max size
        """
        if not file_path.exists():
            return False

        return file_path.stat().st_size >= self.max_size_bytes

    def rotate_file(self, file_path: Path) -> Optional[Path]:
        """
        Rotate a file by renaming it with timestamp.

        Args:
            file_path: Path to file to rotate

        Returns:
            Path to rotated file (or compressed file if compression enabled)
        """
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None

        try:
            # Generate timestamp for rotated file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = file_path.parent / f"{file_path.stem}.{timestamp}{file_path.suffix}"

            # Rename original file
            file_path.rename(rotated_path)
            logger.info(f"Rotated file: {file_path} -> {rotated_path}")

            # Compress if enabled
            if self.compress:
                compressed_path = self._compress_file(rotated_path)
                return compressed_path

            return rotated_path

        except Exception as e:
            logger.error(f"Failed to rotate file {file_path}: {e}")
            return None

    def _compress_file(self, file_path: Path) -> Path:
        """
        Compress a file using gzip.

        Args:
            file_path: Path to file to compress

        Returns:
            Path to compressed file
        """
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")

        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove original file after compression
            file_path.unlink()
            logger.info(f"Compressed file: {file_path} -> {compressed_path}")

            return compressed_path

        except Exception as e:
            logger.error(f"Failed to compress file {file_path}: {e}")
            # If compression fails, keep original file
            if compressed_path.exists():
                compressed_path.unlink()
            return file_path

    def cleanup_old_files(self, directory: Path, pattern: str = "*"):
        """
        Remove files older than retention period.

        Args:
            directory: Directory to clean up
            pattern: Glob pattern for files to check (default: all files)
        """
        if not directory.exists():
            return

        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0

        try:
            for file_path in directory.glob(pattern):
                if not file_path.is_file():
                    continue

                # Check file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old file: {file_path}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old files from {directory}")

        except Exception as e:
            logger.error(f"Failed to cleanup old files in {directory}: {e}")

    def get_rotated_files(self, original_path: Path) -> list[Path]:
        """
        Get list of rotated versions of a file.

        Args:
            original_path: Original file path

        Returns:
            List of rotated file paths, sorted by modification time (newest first)
        """
        directory = original_path.parent
        base_name = original_path.stem
        extension = original_path.suffix

        # Pattern matches: filename.TIMESTAMP.ext and filename.TIMESTAMP.ext.gz
        pattern = f"{base_name}.*{extension}*"

        rotated_files = []
        for file_path in directory.glob(pattern):
            # Skip the original file
            if file_path == original_path:
                continue

            rotated_files.append(file_path)

        # Sort by modification time (newest first)
        rotated_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return rotated_files

    def decompress_file(self, compressed_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decompress a gzipped file.

        Args:
            compressed_path: Path to compressed file
            output_path: Path for decompressed file (default: removes .gz extension)

        Returns:
            Path to decompressed file
        """
        if not compressed_path.exists():
            raise FileNotFoundError(f"Compressed file not found: {compressed_path}")

        if output_path is None:
            # Remove .gz extension
            if compressed_path.suffix == ".gz":
                output_path = compressed_path.with_suffix("")
            else:
                output_path = compressed_path.with_suffix(".decompressed")

        try:
            with gzip.open(compressed_path, "rb") as f_in:
                with open(output_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"Decompressed file: {compressed_path} -> {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to decompress file {compressed_path}: {e}")
            raise


def rotate_if_needed(file_path: Path, rotator: Optional[FileRotator] = None) -> bool:
    """
    Convenience function to rotate a file if it exceeds size threshold.

    Args:
        file_path: Path to file to check and rotate
        rotator: FileRotator instance (creates default if None)

    Returns:
        True if file was rotated
    """
    if rotator is None:
        rotator = FileRotator()

    if rotator.should_rotate(file_path):
        rotated = rotator.rotate_file(file_path)
        return rotated is not None

    return False

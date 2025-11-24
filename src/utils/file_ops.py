import os
import shutil
import logging
from typing import List
import tempfile


class FileMerger:
    """
    Handles merging of downloaded chunks into a single file.
    Demonstrates file I/O operations and error handling in production code.
    """

    def __init__(self, buffer_size: int = 8192 * 8):  # 64KB buffer
        self.buffer_size = buffer_size
        self.logger = logging.getLogger(__name__)

    def merge_files(self, chunk_files: List[str], output_file: str):
        """
        Merge multiple chunk files into a single output file.
        Demonstrates sequential file processing with error recovery.
        """
        self.logger.info(f"Merging {len(chunk_files)} chunks into {output_file}")

        # Validate all chunk files exist and are readable
        valid_chunk_files = []
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                valid_chunk_files.append(chunk_file)
            else:
                self.logger.warning(f"Chunk file missing or empty: {chunk_file}")

        if not valid_chunk_files:
            raise ValueError("No valid chunk files to merge")

        # Use temporary file to ensure atomic operation
        temp_output = output_file + '.tmp'

        try:
            with open(temp_output, 'wb') as output:
                for i, chunk_file in enumerate(sorted(valid_chunk_files, key=self._get_chunk_number)):
                    self.logger.debug(f"Merging chunk {i}: {chunk_file}")

                    try:
                        with open(chunk_file, 'rb') as chunk:
                            while True:
                                buffer = chunk.read(self.buffer_size)
                                if not buffer:
                                    break
                                output.write(buffer)

                        self.logger.debug(f"Successfully merged {chunk_file}")

                    except IOError as e:
                        self.logger.error(f"Failed to merge chunk {chunk_file}: {e}")
                        raise

            # Atomic rename to final file
            shutil.move(temp_output, output_file)
            self.logger.info(f"Successfully created merged file: {output_file}")

        except Exception as e:
            # Cleanup temporary file on error
            if os.path.exists(temp_output):
                os.remove(temp_output)
            self.logger.error(f"File merging failed: {e}")
            raise

    def _get_chunk_number(self, chunk_file_path: str) -> int:
        """Extract chunk number from filename for proper ordering"""
        try:
            # Expected format: filename.part0, filename.part1, etc.
            base_name = os.path.basename(chunk_file_path)
            part_suffix = base_name.split('.part')[-1]
            return int(part_suffix)
        except (ValueError, IndexError):
            self.logger.warning(f"Could not parse chunk number from {chunk_file_path}, using 0")
            return 0

    def validate_merged_file(self, output_file: str, expected_size: int) -> bool:
        """Validate that merged file has correct size"""
        if not os.path.exists(output_file):
            return False

        actual_size = os.path.getsize(output_file)
        if actual_size != expected_size:
            self.logger.warning(
                f"File size mismatch. Expected: {expected_size}, Got: {actual_size}"
            )
            return False

        return True


class FileValidator:
    """Utility class for file validation operations"""

    @staticmethod
    def is_valid_filename(filename: str) -> bool:
        """Check if filename is valid for the current OS"""
        if not filename or not filename.strip():
            return False

        # Check for invalid characters (Windows has more restrictions)
        invalid_chars = '<>:"/\\|?*'
        if any(char in filename for char in invalid_chars):
            return False

        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False

        return True

    @staticmethod
    def ensure_directory_exists(file_path: str):
        """Ensure the directory for a file exists"""
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
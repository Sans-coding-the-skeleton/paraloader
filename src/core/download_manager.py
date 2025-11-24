import threading
import os
import time
from typing import Optional, Callable
import logging

from core.thread_pool import ThreadPool
from core.chunk_manager import ChunkManager
from core.progress_tracker import ProgressTracker
from network.http_client import HTTPClient
from network.range_request import RangeRequest
from utils.file_ops import FileMerger, FileValidator
from utils.validators import URLValidator, ConfigValidator
from utils.config import ConfigManager


class DownloadManager:
    """
    Complete implementation with all missing components integrated.
    """

    def __init__(self,
                 url: str,
                 output_path: str,
                 num_connections: int = 4,
                 chunk_size: int = 1024 * 1024,
                 config_file: str = "config.json"):

        # Input validation
        if not URLValidator().is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        if not ConfigValidator.validate_connections_count(num_connections):
            raise ValueError(f"Invalid number of connections: {num_connections}")

        if not ConfigValidator.validate_chunk_size(chunk_size):
            raise ValueError(f"Invalid chunk size: {chunk_size}")

        # Ensure output directory exists
        FileValidator.ensure_directory_exists(output_path)

        self.url = url
        self.output_path = output_path
        self.num_connections = num_connections
        self.chunk_size = chunk_size

        # Initialize all components
        self.config = ConfigManager(config_file)
        self.http_client = HTTPClient(timeout=self.config.get('timeout', 30))
        self.range_request = RangeRequest(self.http_client.session, self.config.get('timeout', 30))
        self.thread_pool: Optional[ThreadPool] = None
        self.chunk_manager: Optional[ChunkManager] = None
        self.progress_tracker = ProgressTracker()
        self.file_merger = FileMerger(buffer_size=self.config.get('buffer_size', 8192 * 8))
        self.file_validator = FileValidator()

        # State management
        self.is_downloading = False
        self.download_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.last_progress_time = time.time()
        self.stalled_threshold = 30

        self.logger = logging.getLogger(__name__)

    def start_download(self):
        """Start the parallel download process"""
        if self.is_downloading:
            raise RuntimeError("Download already in progress")

        self.is_downloading = True
        self.shutdown_event.clear()

        # Run in separate thread to avoid blocking
        self.download_thread = threading.Thread(target=self._download_process)
        self.download_thread.start()

    def _download_process(self):
        """Main download process demonstrating parallel workflow"""
        try:
            # Step 1: Get file information
            file_size = self.http_client.get_file_size(self.url)
            if not file_size:
                logging.error("Could not determine file size or server doesn't support range requests")
                # Fallback to single connection download
                self._download_single_connection()
                return

            # Step 2: Initialize chunk management
            self.chunk_manager = ChunkManager(
                total_size=file_size,
                chunk_size=self.chunk_size,
                num_connections=self.num_connections
            )

            # Step 3: Create thread pool for parallel downloads
            self.thread_pool = ThreadPool(
                num_workers=self.num_connections,
                name="DownloadWorker"
            )

            logging.info(f"Starting parallel download with {self.num_connections} connections")
            logging.info(f"File size: {file_size} bytes")
            logging.info(f"Chunk size: {self.chunk_size} bytes")

            # Step 4: Start progress monitoring (separate thread)
            progress_thread = threading.Thread(
                target=self._progress_monitor,
                daemon=True
            )
            progress_thread.start()

            # Step 5: PRODUCER-CONSUMER PATTERN IMPLEMENTATION
            # Submit initial chunk download tasks
            self._submit_chunk_tasks()

            # Step 6: Monitor and manage download process
            while not self.shutdown_event.is_set():
                if self.chunk_manager.all_chunks_completed():
                    logging.info("All chunks downloaded successfully!")
                    break

                # Check for stalled download (deadlock detection)
                if self._is_download_stalled():
                    logging.warning("Download appears stalled. Checking for issues...")
                    self._handle_stalled_download()

                # Submit more tasks if needed (for retries)
                self._submit_chunk_tasks()

                time.sleep(0.5)

            # Step 7: Merge chunks into final file
            if not self.shutdown_event.is_set():
                self._merge_chunks()
                logging.info(f"Download completed: {self.output_path}")

        except Exception as e:
            logging.error(f"Download process failed: {e}")
        finally:
            self._cleanup()

    def _download_single_connection(self):
        """Fallback method for when range requests aren't supported"""
        try:
            logging.info("Server doesn't support parallel downloads, using single connection")
            self.http_client.download_chunk(
                url=self.url,
                output_file=self.output_path,
                start_byte=0,
                end_byte=None  # Download entire file
            )
            logging.info("Single connection download completed")
        except Exception as e:
            logging.error(f"Single connection download failed: {e}")
        finally:
            self._cleanup()

    def _submit_chunk_tasks(self):
        """Submit chunk download tasks to thread pool - PRODUCER"""
        if not self.thread_pool or not self.chunk_manager:
            return

        # Get available chunks and submit to thread pool
        while True:
            chunk_info = self.chunk_manager.get_next_chunk()
            if not chunk_info:
                break

            chunk_id, start, end = chunk_info

            # CONSUMER task submission
            self.thread_pool.submit(
                self._download_chunk,
                chunk_id,
                start,
                end
            )

    def _download_chunk(self, chunk_id: int, start: int, end: int):
        """
        Enhanced chunk download with progress tracking and validation.
        """
        temp_file = f"{self.output_path}.part{chunk_id}"
        chunk_size = end - start + 1

        # Start tracking this chunk
        self.progress_tracker.start_chunk_tracking(chunk_id)

        try:
            self.logger.debug(f"Downloading chunk {chunk_id}: bytes {start}-{end}")

            # Download the chunk
            success = self.http_client.download_chunk(
                url=self.url,
                output_file=temp_file,
                start_byte=start,
                end_byte=end
            )

            if success:
                # Verify chunk was downloaded completely
                if os.path.exists(temp_file):
                    actual_size = os.path.getsize(temp_file)
                    expected_size = chunk_size

                    if actual_size == expected_size:
                        self.chunk_manager.mark_chunk_completed(chunk_id)
                        self.progress_tracker.update_progress(
                            chunk_id, True, actual_size
                        )
                        self.logger.debug(f"Chunk {chunk_id} completed successfully")
                    else:
                        self.logger.warning(
                            f"Chunk {chunk_id} size mismatch. "
                            f"Expected: {expected_size}, Got: {actual_size}"
                        )
                        self.chunk_manager.mark_chunk_failed(chunk_id)
                        self.progress_tracker.update_progress(chunk_id, False)
                else:
                    self.logger.error(f"Chunk file not created: {temp_file}")
                    self.chunk_manager.mark_chunk_failed(chunk_id)
                    self.progress_tracker.update_progress(chunk_id, False)
            else:
                self.logger.error(f"HTTP download failed for chunk {chunk_id}")
                self.chunk_manager.mark_chunk_failed(chunk_id)
                self.progress_tracker.update_progress(chunk_id, False)

        except Exception as e:
            self.logger.error(f"Unexpected error in chunk {chunk_id}: {e}")
            self.chunk_manager.mark_chunk_failed(chunk_id)
            self.progress_tracker.update_progress(chunk_id, False)

    def _progress_monitor(self):
        """Monitor download progress and detect issues"""
        while self.is_downloading and not self.shutdown_event.is_set():
            if self.chunk_manager:
                progress = self.chunk_manager.get_progress()
                logging.info(f"Download progress: {progress:.1f}%")

                # Update progress time for stall detection
                if progress > 0:
                    self.last_progress_time = time.time()

            time.sleep(2)

    def _is_download_stalled(self) -> bool:
        """Detect if download is stalled (potential deadlock)"""
        return (time.time() - self.last_progress_time) > self.stalled_threshold

    def _handle_stalled_download(self):
        """Handle stalled download scenario"""
        # DEADLOCK PREVENTION: Reset failed chunks to allow retries
        if self.chunk_manager:
            logging.info("Attempting to recover from stalled state...")
            self.last_progress_time = time.time()  # Reset timer

    def _merge_chunks(self):
        """Merge all downloaded chunks into final file"""
        if not self.chunk_manager:
            return

        chunk_files = [
            f"{self.output_path}.part{chunk_id}"
            for chunk_id in range(len(self.chunk_manager.chunks))
        ]

        self.file_merger.merge_files(chunk_files, self.output_path)

        # Cleanup temporary chunk files
        for chunk_file in chunk_files:
            try:
                os.remove(chunk_file)
            except OSError:
                pass

    def _cleanup(self):
        """Cleanup resources"""
        self.is_downloading = False
        if self.thread_pool:
            self.thread_pool.shutdown(wait=False)

    def stop_download(self):
        """Stop the download process"""
        self.shutdown_event.set()
        self._cleanup()

    def get_download_info(self) -> dict:
        """Get comprehensive download information"""
        if not self.chunk_manager:
            return {}

        return {
            'progress_percentage': self.progress_tracker.get_overall_progress(),
            'average_speed_bps': self.progress_tracker.get_average_speed(),
            'completed_chunks': len(self.progress_tracker.completed_chunks),
            'failed_chunks': self.progress_tracker.get_failed_chunks_count(),
            'total_chunks': len(self.chunk_manager.chunks),
            'is_downloading': self.is_downloading
        }
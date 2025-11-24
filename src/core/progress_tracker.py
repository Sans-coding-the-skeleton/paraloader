import threading
import time
from typing import Dict, Set
import logging


class ProgressTracker:
    """
    Tracks download progress across multiple threads with thread-safe operations.
    Demonstrates shared state management in concurrent environments.
    """

    def __init__(self):
        self.completed_chunks: Set[int] = set()
        self.failed_chunks: Set[int] = set()
        self.chunk_speeds: Dict[int, float] = {}
        self.chunk_start_times: Dict[int, float] = {}
        self.lock = threading.RLock()  # Reentrant lock for nested calls
        self.total_bytes = 0
        self.downloaded_bytes = 0

    def update_progress(self, chunk_id: int, success: bool, bytes_downloaded: int = 0):
        """
        Update progress for a chunk. Thread-safe method demonstrating
        coordinated state updates.
        """
        with self.lock:  # SYNCHRONIZATION: Protecting shared state
            if success:
                self.completed_chunks.add(chunk_id)
                if chunk_id in self.failed_chunks:
                    self.failed_chunks.remove(chunk_id)

                # Calculate download speed for this chunk
                if chunk_id in self.chunk_start_times:
                    download_time = time.time() - self.chunk_start_times[chunk_id]
                    if download_time > 0:
                        speed = bytes_downloaded / download_time
                        self.chunk_speeds[chunk_id] = speed

                    # Clean up
                    del self.chunk_start_times[chunk_id]

                self.downloaded_bytes += bytes_downloaded
            else:
                self.failed_chunks.add(chunk_id)
                if chunk_id in self.completed_chunks:
                    self.completed_chunks.remove(chunk_id)

    def start_chunk_tracking(self, chunk_id: int):
        """Start tracking time for a chunk download"""
        with self.lock:
            self.chunk_start_times[chunk_id] = time.time()

    def get_overall_progress(self) -> float:
        """Get overall progress percentage"""
        with self.lock:
            total_chunks = len(self.completed_chunks) + len(self.failed_chunks)
            if total_chunks == 0:
                return 0.0
            return (len(self.completed_chunks) / total_chunks) * 100

    def get_average_speed(self) -> float:
        """Calculate average download speed across all chunks"""
        with self.lock:
            if not self.chunk_speeds:
                return 0.0
            return sum(self.chunk_speeds.values()) / len(self.chunk_speeds)

    def get_failed_chunks_count(self) -> int:
        """Get count of failed chunks"""
        with self.lock:
            return len(self.failed_chunks)

    def reset(self):
        """Reset all progress tracking"""
        with self.lock:
            self.completed_chunks.clear()
            self.failed_chunks.clear()
            self.chunk_speeds.clear()
            self.chunk_start_times.clear()
            self.total_bytes = 0
            self.downloaded_bytes = 0
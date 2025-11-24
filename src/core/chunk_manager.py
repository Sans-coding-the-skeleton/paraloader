import threading
import os
from typing import List, Tuple, Optional
import logging


class ChunkManager:
    """
    Manages file chunks for parallel downloading with synchronization.
    Demonstrates resource coordination and conflict resolution.
    """

    def __init__(self, total_size: int, chunk_size: int, num_connections: int):
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.num_connections = num_connections
        self.chunks: List[Tuple[int, int]] = []
        self.completed_chunks = set()
        self.failed_chunks = set()
        self.lock = threading.Lock()  # SYNCHRONIZATION primitive
        self.retry_count = {}
        self.max_retries = 3

        self._calculate_chunks()

    def _calculate_chunks(self):
        """Calculate byte ranges for each chunk - demonstrates work division"""
        chunk_ranges = []
        for i in range(self.num_connections):
            start = i * self.chunk_size
            end = start + self.chunk_size - 1

            # Ensure we don't go beyond file size
            if end >= self.total_size:
                end = self.total_size - 1

            # Last chunk gets any remaining bytes
            if i == self.num_connections - 1:
                end = self.total_size - 1

            if start < self.total_size:
                chunk_ranges.append((start, end))

        self.chunks = chunk_ranges

    def get_next_chunk(self) -> Optional[Tuple[int, int, int]]:
        """
        Thread-safe method to get next chunk for processing.
        Demonstrates COORDINATION between threads competing for work.

        Returns: (chunk_id, start_byte, end_byte) or None if all chunks taken
        """
        with self.lock:  # CRITICAL SECTION - prevents race conditions
            for chunk_id, (start, end) in enumerate(self.chunks):
                if (chunk_id not in self.completed_chunks and
                        chunk_id not in self.failed_chunks):
                    # Mark as in-progress by adding to failed (temporarily)
                    # This prevents another thread from taking the same chunk
                    self.failed_chunks.add(chunk_id)
                    return chunk_id, start, end

            return None

    def mark_chunk_completed(self, chunk_id: int):
        """Mark a chunk as successfully downloaded"""
        with self.lock:  # SYNCHRONIZED access to shared state
            if chunk_id in self.failed_chunks:
                self.failed_chunks.remove(chunk_id)
            self.completed_chunks.add(chunk_id)

    def mark_chunk_failed(self, chunk_id: int):
        """Mark a chunk as failed - allows retry logic"""
        with self.lock:
            self.retry_count[chunk_id] = self.retry_count.get(chunk_id, 0) + 1

            if self.retry_count[chunk_id] <= self.max_retries:
                # Remove from failed to allow retry
                self.failed_chunks.remove(chunk_id)
            else:
                # Permanent failure
                logging.error(f"Chunk {chunk_id} failed after {self.max_retries} retries")

    def all_chunks_completed(self) -> bool:
        """Check if all chunks are downloaded"""
        return len(self.completed_chunks) == len(self.chunks)

    def get_progress(self) -> float:
        """Get download progress percentage"""
        with self.lock:
            return (len(self.completed_chunks) / len(self.chunks)) * 100
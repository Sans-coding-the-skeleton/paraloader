import requests
import logging
from typing import Optional


class HTTPClient:
    """HTTP client supporting range requests for parallel downloads"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

        # Optimize connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # Increased connection pool
            pool_maxsize=10,  # Allow more simultaneous connections
            max_retries=2,  # Retry failed requests
            pool_block=False  # Don't block when pool is full
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Set optimized headers
        self.session.headers.update({
            'User-Agent': 'ParallelDownloader/1.0',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def get_file_size(self, url: str) -> Optional[int]:
        """Check if server supports range requests and get file size"""
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()

            # Check if server supports range requests
            accept_ranges = response.headers.get('Accept-Ranges', 'none').lower()
            content_length = response.headers.get('Content-Length')

            if accept_ranges != 'bytes' or not content_length:
                logging.warning("Server doesn't support byte range requests")
                return None

            return int(content_length)

        except Exception as e:
            logging.error(f"Error getting file info: {e}")
            return None

    def download_chunk(self, url: str, output_file: str, start_byte: int, end_byte: int = None) -> bool:
        """Download a specific byte range, returns True if successful"""
        headers = {}
        if end_byte is not None:
            headers = {'Range': f'bytes={start_byte}-{end_byte}'}

        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return True

        except Exception as e:
            logging.error(f"Download failed: {e}")
            return False
import requests
from typing import Tuple, Optional


class RangeRequest:
    """
    Handles HTTP range requests for chunk downloading.
    Demonstrates network I/O with proper error handling.
    """

    def __init__(self, session: requests.Session, timeout: int = 30):
        self.session = session
        self.timeout = timeout

    def download_range(self, url: str, start_byte: int, end_byte: int) -> Tuple[bool, bytes]:
        """
        Download a specific byte range from a URL.
        Returns (success, data) tuple.
        """
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            # Verify we got a partial content response
            if response.status_code != 206:  # Partial Content
                return False, b""

            return True, response.content

        except requests.exceptions.RequestException as e:
            return False, b""

    def get_content_range(self, url: str, range_header: str) -> Optional[Tuple[int, int, int]]:
        """
        Get actual content range from server response.
        Returns (start, end, total) or None if failed.
        """
        headers = {'Range': range_header}

        try:
            response = self.session.head(url, headers=headers, timeout=self.timeout)
            content_range = response.headers.get('Content-Range')

            if content_range:
                # Parse: "bytes 0-999/1000" -> (0, 999, 1000)
                range_info = content_range.split(' ')[1]
                range_part, total_part = range_info.split('/')
                start, end = map(int, range_part.split('-'))
                total = int(total_part)
                return start, end, total

        except (requests.exceptions.RequestException, ValueError, IndexError):
            pass

        return None
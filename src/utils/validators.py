import re
from urllib.parse import urlparse
import logging


class URLValidator:
    """Validates URLs for the downloader"""

    def __init__(self):
        self.supported_schemes = {'http', 'https'}
        self.logger = logging.getLogger(__name__)

    def is_valid_url(self, url: str) -> bool:
        """Validate if URL is properly formatted and supported"""
        if not url or not isinstance(url, str):
            return False

        try:
            result = urlparse(url)

            # Check scheme
            if result.scheme not in self.supported_schemes:
                self.logger.warning(f"Unsupported URL scheme: {result.scheme}")
                return False

            # Check netloc (domain)
            if not result.netloc:
                self.logger.warning("URL missing domain")
                return False

            # Basic domain validation
            if not self._is_valid_domain(result.netloc):
                return False

            return True

        except Exception as e:
            self.logger.error(f"URL validation error: {e}")
            return False

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain name format"""
        # Remove port if present
        domain = domain.split(':')[0]

        # Basic domain pattern validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(domain_pattern, domain))


class ConfigValidator:
    """Validates configuration parameters"""

    @staticmethod
    def validate_connections_count(connections: int) -> bool:
        """Validate number of parallel connections"""
        return 1 <= connections <= 16  # Reasonable limits

    @staticmethod
    def validate_chunk_size(chunk_size: int) -> bool:
        """Validate chunk size"""
        return 1024 <= chunk_size <= 1024 * 1024 * 100  # 100KB to 100MB

    @staticmethod
    def validate_output_path(path: str) -> bool:
        """Validate output file path"""
        from .file_ops import FileValidator
        filename = os.path.basename(path)
        return FileValidator.is_valid_filename(filename)
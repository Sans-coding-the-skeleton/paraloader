import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.download_manager import DownloadManager


class TestDownloadManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_download.iso")

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('src.core.download_manager.HttpClient')
    def test_successful_parallel_download(self, mock_http_client):
        """Test successful parallel download (Proxmox ISO)"""
        print("Testing successful parallel download...")

        # Mock the HTTP client
        mock_client = MagicMock()
        mock_http_client.return_value = mock_client

        # Mock file info response
        mock_client.get_file_info.return_value = {
            'size': 1831886848,
            'accept_ranges': True
        }

        # Mock chunk downloads
        mock_client.download_chunk.return_value = True

        manager = DownloadManager(
            url="https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso",
            output_path=self.test_file,
            connections=4
        )

        result = manager.start_download()

        self.assertTrue(result)
        self.assertEqual(manager.file_size, 1831886848)
        print("✅ Parallel download test passed")

    @patch('src.core.download_manager.HttpClient')
    def test_single_connection_fallback(self, mock_http_client):
        """Test fallback to single connection when range requests not supported"""
        print("Testing single connection fallback...")

        mock_client = MagicMock()
        mock_http_client.return_value = mock_client

        # Mock server that doesn't support range requests
        mock_client.get_file_info.return_value = {
            'size': 154872,
            'accept_ranges': False
        }

        mock_client.download_entire_file.return_value = True

        manager = DownloadManager(
            url="https://www.examplefile.com/file-download/202",
            output_path=self.test_file,
            connections=4
        )

        result = manager.start_download()

        self.assertTrue(result)
        mock_client.download_entire_file.assert_called_once()
        print("✅ Single connection fallback test passed")

    @patch('src.core.download_manager.HttpClient')
    def test_dns_resolution_error(self, mock_http_client):
        """Test handling of DNS resolution errors"""
        print("Testing DNS resolution error handling...")

        mock_client = MagicMock()
        mock_http_client.return_value = mock_client

        # Mock DNS resolution error
        from requests.exceptions import ConnectionError
        mock_client.get_file_info.side_effect = ConnectionError("DNS resolution failed")

        manager = DownloadManager(
            url="https://updates.adobe.com/AdobeReader/win/2024/update_2024.001.20142.exe",
            output_path=self.test_file,
            connections=4
        )

        result = manager.start_download()

        self.assertFalse(result)
        print("✅ DNS error handling test passed")

    def test_chunk_size_calculation(self):
        """Test proper chunk size calculation"""
        print("Testing chunk size calculation...")

        manager = DownloadManager(
            url="https://example.com/test.iso",
            output_path=self.test_file,
            connections=4
        )

        manager.file_size = 1831886848  # Same as Proxmox ISO

        chunk_size = manager._calculate_chunk_size()
        expected_size = 1048576  # 1MB chunks based on your logs

        self.assertEqual(chunk_size, expected_size)
        print("✅ Chunk size calculation test passed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
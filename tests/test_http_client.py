import unittest
from unittest.mock import patch, MagicMock
import requests
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.http_client import HttpClient
from requests.exceptions import ConnectionError, Timeout, SSLError


class TestHttpClient(unittest.TestCase):

    def setUp(self):
        self.http_client = HttpClient()

    @patch('utils.http_client.requests.head')
    def test_successful_file_info(self, mock_head):
        """Test successful file info retrieval (Proxmox example)"""
        print("Testing successful file info retrieval...")

        mock_response = MagicMock()
        mock_response.headers = {
            'content-length': '1831886848',
            'accept-ranges': 'bytes'
        }
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        file_info = self.http_client.get_file_info(
            "https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso"
        )

        self.assertEqual(file_info['size'], 1831886848)
        self.assertTrue(file_info['accept_ranges'])
        print("✅ File info retrieval test passed")

    @patch('utils.http_client.requests.head')
    def test_no_range_support(self, mock_head):
        """Test file info for server without range support"""
        print("Testing no range support handling...")

        mock_response = MagicMock()
        mock_response.headers = {
            'content-length': '154872'
            # No accept-ranges header
        }
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        file_info = self.http_client.get_file_info(
            "https://www.examplefile.com/file-download/202"
        )

        self.assertEqual(file_info['size'], 154872)
        self.assertFalse(file_info['accept_ranges'])
        print("✅ No range support test passed")

    @patch('utils.http_client.requests.head')
    def test_connection_error_handling(self, mock_head):
        """Test handling of connection errors"""
        print("Testing connection error handling...")

        mock_head.side_effect = ConnectionError("DNS resolution failed")

        file_info = self.http_client.get_file_info(
            "https://updates.adobe.com/AdobeReader/win/2024/update_2024.001.20142.exe"
        )

        self.assertIsNone(file_info)
        print("✅ Connection error handling test passed")

    @patch('utils.http_client.requests.head')
    def test_ssl_error_handling(self, mock_head):
        """Test handling of SSL errors"""
        print("Testing SSL error handling...")

        mock_head.side_effect = SSLError("Certificate verification failed")

        file_info = self.http_client.get_file_info(
            "https://ipv4.download.thinkbroadband.com/5GB.zip"
        )

        self.assertIsNone(file_info)
        print("✅ SSL error handling test passed")

    @patch('utils.http_client.requests.get')
    def test_successful_chunk_download(self, mock_get):
        """Test successful chunk download"""
        print("Testing chunk download...")

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'test data chunk']
        mock_response.status_code = 206  # Partial content
        mock_get.return_value = mock_response

        result = self.http_client.download_chunk(
            "https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso",
            start_byte=0,
            end_byte=999,
            chunk_file="test_chunk.dat"
        )

        self.assertTrue(result)
        print("✅ Chunk download test passed")

    @patch('utils.http_client.requests.get')
    def test_server_unavailable(self, mock_get):
        """Test handling of server 503 errors"""
        print("Testing server unavailable handling...")

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.reason = "Service Temporarily Unavailable"
        mock_get.return_value = mock_response

        result = self.http_client.download_chunk(
            "https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso",
            start_byte=0,
            end_byte=999,
            chunk_file="test_chunk.dat"
        )

        self.assertFalse(result)
        print("✅ Server unavailable test passed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
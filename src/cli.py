#!/usr/bin/env python3
import argparse
import sys
import os
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.download_manager import DownloadManager


def setup_logging(verbose: bool):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def main():
    parser = argparse.ArgumentParser(
        description='Parallel File Downloader',
        usage='%(prog)s [OPTIONS] URL OUTPUT_FILE'
    )
    parser.add_argument(
        'url',
        help='URL of the file to download (e.g., https://example.com/file.zip)'
    )
    parser.add_argument(
        'output',
        help='Output file path (e.g., downloaded_file.zip)'
    )
    parser.add_argument(
        '-c', '--connections',
        type=int,
        default=4,
        help='Number of parallel connections (default: 4)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        print(f"Starting download...")
        print(f"URL: {args.url}")
        print(f"Output: {args.output}")
        print(f"Connections: {args.connections}")
        print("Press Ctrl+C to stop...")

        downloader = DownloadManager(
            url=args.url,
            output_path=args.output,
            num_connections=args.connections
        )

        downloader.start_download()

        # Wait for completion
        while downloader.is_downloading:
            import time
            time.sleep(1)

        # Check if file was actually downloaded
        if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
            file_size = os.path.getsize(args.output)
            print(f"✅ Download completed successfully!")
            print(f"📁 File location: {os.path.abspath(args.output)}")
            print(f"📊 File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        else:
            print("❌ Download failed - no file was created")
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Stopping download...")
        if 'downloader' in locals():
            downloader.stop_download()
    except Exception as e:
        logging.error(f"Download failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
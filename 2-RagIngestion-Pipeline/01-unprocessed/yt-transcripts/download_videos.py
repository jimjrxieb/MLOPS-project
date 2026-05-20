#!/usr/bin/env python3
"""
CLI tool for downloading YouTube transcripts for JADE Night Learning

Usage:
    # Download single video
    python download_videos.py --video "https://www.youtube.com/watch?v=VIDEO_ID"

    # Download playlist
    python download_videos.py --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"

    # Download from file (one URL per line)
    python download_videos.py --file videos.txt

    # Download with custom chunk size
    python download_videos.py --video URL --chunk-size 500

Author: Claude + Jimmie
Date: October 29, 2025
"""

import argparse
from pathlib import Path
from youtube_downloader import YouTubeTranscriptDownloader


def load_urls_from_file(file_path: Path) -> list:
    """Load video URLs from text file (one per line)"""
    urls = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube transcripts for JADE Night Learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download single video
  python download_videos.py --video "https://www.youtube.com/watch?v=oBf5lrmquYI"

  # Download playlist
  python download_videos.py --playlist "https://www.youtube.com/playlist?list=PLy7NrYWoggjwPggqtFsI_zMAwvG0SqYCb"

  # Download from file
  python download_videos.py --file learning_videos.txt

  # Custom output directory
  python download_videos.py --video URL --output /custom/path

  # Custom chunk size (words per chunk)
  python download_videos.py --video URL --chunk-size 500
        """
    )

    parser.add_argument(
        '--video',
        type=str,
        help='Single video URL to download'
    )

    parser.add_argument(
        '--playlist',
        type=str,
        help='Playlist URL to download all videos from'
    )

    parser.add_argument(
        '--file',
        type=Path,
        help='Text file with video URLs (one per line)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output directory (default: ../unprocessed/night-learning/)'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=300,
        help='Words per chunk (default: 300)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    args = parser.parse_args()

    # Validate inputs
    if not any([args.video, args.playlist, args.file]):
        parser.error("Must specify --video, --playlist, or --file")

    # Set output directory
    if args.output:
        output_dir = args.output
    else:
        # Default: ../unprocessed/night-learning/
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / "unprocessed" / "night-learning"

    # Create downloader
    downloader = YouTubeTranscriptDownloader(
        output_dir=output_dir,
        chunk_size=args.chunk_size,
        verbose=not args.quiet
    )

    # Download videos
    if args.video:
        print(f"\n🎥 Downloading single video...")
        success = downloader.download_video(args.video)
        exit(0 if success else 1)

    elif args.playlist:
        print(f"\n📋 Downloading playlist...")
        stats = downloader.download_playlist(args.playlist)
        print(f"\n{'='*60}")
        print(f"✅ Playlist download complete!")
        print(f"   Success: {stats['success']}")
        print(f"   Failed: {stats['failed']}")
        print(f"{'='*60}\n")
        exit(0 if stats['failed'] == 0 else 1)

    elif args.file:
        if not args.file.exists():
            print(f"❌ File not found: {args.file}")
            exit(1)

        print(f"\n📄 Loading URLs from {args.file}...")
        urls = load_urls_from_file(args.file)
        print(f"   Found {len(urls)} URLs\n")

        stats = {'success': 0, 'failed': 0}

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]")
            success = downloader.download_video(url)

            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

        print(f"\n{'='*60}")
        print(f"✅ Batch download complete!")
        print(f"   Success: {stats['success']}")
        print(f"   Failed: {stats['failed']}")
        print(f"{'='*60}\n")
        exit(0 if stats['failed'] == 0 else 1)


if __name__ == "__main__":
    main()

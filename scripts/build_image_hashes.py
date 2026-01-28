#!/usr/bin/env python3
"""
Build image hash mapping for S3 fallback.

Run this script to compute SHA256 hashes from local images,
enabling S3 URL resolution for specimens without local images.

Usage:
    python scripts/build_image_hashes.py ~/Documents/projects/AAFC/pyproj/resized
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.images.s3_client import ImageHashMapping


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/build_image_hashes.py <image_directory>")
        print("Example: python scripts/build_image_hashes.py ~/Documents/projects/AAFC/pyproj/resized")
        sys.exit(1)

    image_dir = Path(sys.argv[1]).expanduser()

    if not image_dir.exists():
        print(f"Error: Directory not found: {image_dir}")
        sys.exit(1)

    print(f"Building hash mapping from: {image_dir}")
    print("This may take a few minutes for large directories...")

    mapping = ImageHashMapping()
    count = mapping.build_from_directory(image_dir, pattern="*.JPG")

    print(f"\nCompleted! Hashed {count} images.")
    print(f"Cache saved to: {mapping.cache_path}")


if __name__ == "__main__":
    main()

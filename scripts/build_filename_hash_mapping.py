#!/usr/bin/env python3
"""
Build filename → SHA256 mapping from local image directory.

This creates a JSON mapping file that the mobile review server can use
to resolve camera filenames (DSC_0320.JPG) to content-addressed S3 paths.

Usage:
    python scripts/build_filename_hash_mapping.py --images ~/Documents/projects/AAFC/pyproj/resized
    python scripts/build_filename_hash_mapping.py --images /path/to/images --output mapping.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def build_mapping(image_dir: Path, extensions: tuple = (".jpg", ".jpeg", ".JPG", ".JPEG")) -> Dict[str, str]:
    """
    Build mapping from camera filenames to SHA256 hashes.

    Args:
        image_dir: Directory containing images
        extensions: File extensions to process

    Returns:
        Dict mapping filename (without extension) to SHA256 hash
    """
    mapping = {}

    image_files = [f for f in image_dir.iterdir() if f.suffix in extensions]
    total = len(image_files)

    print(f"Processing {total} images from {image_dir}")

    for i, img_path in enumerate(sorted(image_files), 1):
        try:
            sha256 = compute_sha256(img_path)
            # Key is the filename stem (e.g., "DSC_0320" from "DSC_0320.jpg")
            mapping[img_path.stem] = sha256

            if i % 100 == 0 or i == total:
                print(f"  Processed {i}/{total} images...")

        except Exception as e:
            print(f"  Error processing {img_path.name}: {e}", file=sys.stderr)

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Build filename → SHA256 mapping")
    parser.add_argument(
        "--images", "-i",
        type=Path,
        default=Path.home() / "Documents/projects/AAFC/pyproj/resized",
        help="Directory containing images"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "filename_hash_mapping.json",
        help="Output JSON file path"
    )

    args = parser.parse_args()

    if not args.images.exists():
        print(f"Error: Image directory not found: {args.images}", file=sys.stderr)
        sys.exit(1)

    # Build the mapping
    mapping = build_mapping(args.images)

    if not mapping:
        print("Error: No images found to process", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Save mapping
    with open(args.output, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

    print(f"\n✅ Saved mapping for {len(mapping)} images to {args.output}")

    # Show sample
    print("\nSample mappings:")
    for key in list(mapping.keys())[:3]:
        print(f"  {key} → {mapping[key][:16]}...")


if __name__ == "__main__":
    main()

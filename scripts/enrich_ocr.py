#!/usr/bin/env python3
"""
Enrich specimens with OCR text coordinates.

Runs Apple Vision OCR on specimen images to capture bounding boxes
for detected text, enabling spatial analysis and field location tracking.

Usage:
    # Enrich all specimens in a JSONL file
    python scripts/enrich_ocr.py --input raw.jsonl --output enriched.jsonl

    # Enrich specific specimens
    python scripts/enrich_ocr.py --specimens DSC_0487 DSC_0320 --images ./images

    # Enrich with progress bar
    python scripts/enrich_ocr.py --input raw.jsonl --output enriched.jsonl --progress
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr.enrichment import (
    enrich_specimen,
    batch_enrich,
    get_enrichment_stats,
    EnrichmentResult,
)
from src.ocr.apple_vision import AppleVisionOCR
from src.images.s3_client import HerbariumImageResolver, ImageHashMapping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_specimens_from_jsonl(jsonl_path: Path) -> list:
    """Load specimen IDs from JSONL file."""
    specimens = []
    with open(jsonl_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Extract specimen ID from image filename
                image = data.get("image", "")
                specimen_id = Path(image).stem if image else None
                if specimen_id:
                    specimens.append({
                        "specimen_id": specimen_id,
                        "data": data,
                    })
    return specimens


def save_enriched_jsonl(
    specimens: list,
    enrichment_map: dict,
    output_path: Path,
) -> int:
    """Save enriched specimens to JSONL file."""
    count = 0
    with open(output_path, "w") as f:
        for spec in specimens:
            specimen_id = spec["specimen_id"]
            data = spec["data"].copy()

            # Add OCR regions if available
            if specimen_id in enrichment_map:
                result = enrichment_map[specimen_id]
                if result.success and result.regions:
                    data["ocr_regions"] = result.regions
                    count += 1

            f.write(json.dumps(data) + "\n")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Enrich specimens with OCR text coordinates"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        help="Input JSONL file with specimens",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSONL file with enriched specimens",
    )
    parser.add_argument(
        "--specimens",
        nargs="+",
        help="Specific specimen IDs to enrich",
    )
    parser.add_argument(
        "--images",
        type=Path,
        help="Directory containing specimen images",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of specimens to process",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bar",
    )
    parser.add_argument(
        "--no-zones",
        action="store_true",
        help="Skip spatial zone classification",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without running OCR",
    )

    args = parser.parse_args()

    # Check OCR availability
    ocr = AppleVisionOCR()
    if not ocr.is_available:
        logger.error("Apple Vision OCR not available on this platform")
        sys.exit(1)

    logger.info("Apple Vision OCR available")

    # Determine specimen list
    if args.input:
        logger.info(f"Loading specimens from: {args.input}")
        specimens = load_specimens_from_jsonl(args.input)
        specimen_ids = [s["specimen_id"] for s in specimens]
    elif args.specimens:
        specimen_ids = args.specimens
        specimens = [{"specimen_id": sid, "data": {}} for sid in specimen_ids]
    else:
        parser.error("Either --input or --specimens is required")

    if args.limit:
        specimen_ids = specimen_ids[:args.limit]
        specimens = specimens[:args.limit]

    logger.info(f"Processing {len(specimen_ids)} specimens")

    if args.dry_run:
        for sid in specimen_ids[:10]:
            print(f"  Would process: {sid}")
        if len(specimen_ids) > 10:
            print(f"  ... and {len(specimen_ids) - 10} more")
        return

    # Set up image resolver
    image_dir = args.images or Path("data/images")
    hash_mapping = ImageHashMapping()
    resolver = HerbariumImageResolver(
        local_dir=image_dir if image_dir.exists() else None,
        hash_mapping=hash_mapping,
        s3_first=False,
    )
    logger.info(f"Image resolver: local={image_dir}, icloud={resolver.icloud_dir}")

    def resolve_image(specimen_id: str) -> Path | None:
        resolved = resolver.resolve(specimen_id, None)
        return Path(resolved) if resolved else None

    # Progress callback
    def progress(current: int, total: int, specimen_id: str):
        if args.progress:
            pct = (current / total) * 100
            print(f"\r[{current}/{total}] {pct:.1f}% - {specimen_id}", end="", flush=True)

    # Run enrichment
    results = list(batch_enrich(
        specimen_ids,
        resolve_image,
        ocr_engine=ocr,
        include_zones=not args.no_zones,
        progress_callback=progress,
    ))

    if args.progress:
        print()  # Newline after progress

    # Show stats
    stats = get_enrichment_stats(results)
    logger.info(f"Enrichment complete:")
    logger.info(f"  Successful: {stats['successful']}/{stats['total']}")
    logger.info(f"  Total regions: {stats['total_regions']}")
    logger.info(f"  Avg regions/specimen: {stats['avg_regions_per_specimen']:.1f}")
    logger.info(f"  Avg time/specimen: {stats['avg_time_per_specimen_ms']:.0f}ms")

    if stats["errors"]:
        logger.warning(f"  Errors: {len(stats['errors'])}")
        for sid, err in list(stats["errors"].items())[:5]:
            logger.warning(f"    {sid}: {err}")

    # Save output if requested
    if args.output and args.input:
        enrichment_map = {r.specimen_id: r for r in results}
        count = save_enriched_jsonl(specimens, enrichment_map, args.output)
        logger.info(f"Saved {count} enriched specimens to: {args.output}")
    elif args.output:
        # Just save the regions as JSON
        output_data = {
            r.specimen_id: r.regions
            for r in results if r.success
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Saved regions to: {args.output}")


if __name__ == "__main__":
    main()

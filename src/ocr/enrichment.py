"""
OCR enrichment for specimen images.

Runs Apple Vision OCR to capture text bounding boxes and spatial coordinates
for specimens that were extracted without local OCR.

Usage:
    from src.ocr.enrichment import enrich_specimen, batch_enrich

    # Single specimen
    regions = enrich_specimen(image_path)

    # Batch enrichment with progress
    results = batch_enrich(specimens, image_resolver, progress_callback)
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from src.ocr.apple_vision import AppleVisionOCR
from src.spatial import classify_zone, BoundingBox

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Result of OCR enrichment for a specimen."""

    specimen_id: str
    success: bool
    regions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0


def enrich_specimen(
    image_path: Path,
    ocr_engine: Optional[AppleVisionOCR] = None,
    include_zones: bool = True,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Run OCR on specimen image to capture text regions with coordinates.

    Args:
        image_path: Path to specimen image
        ocr_engine: Optional pre-initialized OCR engine
        include_zones: Whether to classify regions into spatial zones

    Returns:
        Tuple of (regions list, error message or None)
    """
    if ocr_engine is None:
        ocr_engine = AppleVisionOCR()

    if not ocr_engine.is_available:
        return [], "Apple Vision OCR not available on this platform"

    if not image_path.exists():
        return [], f"Image not found: {image_path}"

    # Run OCR
    blocks, error = ocr_engine.extract_text(image_path)

    if error:
        return [], error

    if not blocks:
        return [], None  # No text found, but not an error

    # Convert blocks to enrichment format
    regions = []
    for block in blocks:
        region = {
            "text": block["text"],
            "confidence": block["confidence"],
            "bounds": block["bounds"],  # {x, y, width, height} normalized 0-1
        }

        # Add zone classification if requested
        if include_zones:
            bounds = block["bounds"]
            bbox = BoundingBox(
                x=bounds["x"],
                y=bounds["y"],
                width=bounds["width"],
                height=bounds["height"],
            )
            zone = classify_zone(bbox)
            # Convert ZoneInfo to serializable format
            region["zone"] = zone.to_dict() if hasattr(zone, "to_dict") else str(zone)

        regions.append(region)

    return regions, None


def batch_enrich(
    specimen_ids: List[str],
    resolve_image: Callable[[str], Optional[Path]],
    ocr_engine: Optional[AppleVisionOCR] = None,
    include_zones: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Iterator[EnrichmentResult]:
    """
    Batch enrich specimens with OCR regions.

    Args:
        specimen_ids: List of specimen IDs to process
        resolve_image: Function to resolve specimen ID to image path
        ocr_engine: Optional pre-initialized OCR engine
        include_zones: Whether to classify regions into spatial zones
        progress_callback: Optional callback(current, total, specimen_id)

    Yields:
        EnrichmentResult for each specimen
    """
    if ocr_engine is None:
        ocr_engine = AppleVisionOCR()

    if not ocr_engine.is_available:
        for specimen_id in specimen_ids:
            yield EnrichmentResult(
                specimen_id=specimen_id,
                success=False,
                error="Apple Vision OCR not available",
            )
        return

    total = len(specimen_ids)

    for i, specimen_id in enumerate(specimen_ids):
        start_time = time.time()

        if progress_callback:
            progress_callback(i + 1, total, specimen_id)

        # Resolve image path
        image_path = resolve_image(specimen_id)
        if image_path is None:
            yield EnrichmentResult(
                specimen_id=specimen_id,
                success=False,
                error="Image not found",
            )
            continue

        # Enrich
        regions, error = enrich_specimen(
            Path(image_path),
            ocr_engine=ocr_engine,
            include_zones=include_zones,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        if error:
            yield EnrichmentResult(
                specimen_id=specimen_id,
                success=False,
                error=error,
                processing_time_ms=processing_time_ms,
            )
        else:
            yield EnrichmentResult(
                specimen_id=specimen_id,
                success=True,
                regions=regions,
                processing_time_ms=processing_time_ms,
            )


def enrich_and_update_specimen(
    specimen: Any,
    image_path: Path,
    ocr_engine: Optional[AppleVisionOCR] = None,
) -> EnrichmentResult:
    """
    Enrich a specimen object with OCR regions in-place.

    Args:
        specimen: Specimen object with ocr_regions attribute
        image_path: Path to specimen image
        ocr_engine: Optional pre-initialized OCR engine

    Returns:
        EnrichmentResult with status
    """
    start_time = time.time()

    regions, error = enrich_specimen(image_path, ocr_engine)
    processing_time_ms = (time.time() - start_time) * 1000

    if error:
        return EnrichmentResult(
            specimen_id=getattr(specimen, "specimen_id", str(specimen)),
            success=False,
            error=error,
            processing_time_ms=processing_time_ms,
        )

    # Update specimen in-place
    if hasattr(specimen, "ocr_regions"):
        specimen.ocr_regions = regions
    elif hasattr(specimen, "metadata"):
        specimen.metadata["ocr_regions"] = regions

    return EnrichmentResult(
        specimen_id=getattr(specimen, "specimen_id", str(specimen)),
        success=True,
        regions=regions,
        processing_time_ms=processing_time_ms,
    )


def get_enrichment_stats(results: List[EnrichmentResult]) -> Dict[str, Any]:
    """
    Calculate statistics from enrichment results.

    Args:
        results: List of EnrichmentResult objects

    Returns:
        Dict with success/failure counts and timing stats
    """
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    total_regions = sum(len(r.regions or []) for r in successful)
    total_time_ms = sum(r.processing_time_ms for r in results)

    return {
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "total_regions": total_regions,
        "avg_regions_per_specimen": total_regions / len(successful) if successful else 0,
        "total_time_ms": total_time_ms,
        "avg_time_per_specimen_ms": total_time_ms / len(results) if results else 0,
        "errors": {r.specimen_id: r.error for r in failed},
    }

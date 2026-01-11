#!/usr/bin/env python3
"""
Herbarium Review Server

Single-command server for reviewing herbarium specimens.
Supports both local development and production modes.

Usage:
    python mobile/run_server.py                    # Local dev mode (default)
    python mobile/run_server.py --mode production  # Production with auth
    python mobile/run_server.py --data ~/path/to/raw.jsonl
    python mobile/run_server.py --port 8080
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Literal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.data.loader import (
    find_latest_extraction,
    load_specimens_for_review,
    DEFAULT_AAFC_OUTPUT,
)
from src.review.engine import ReviewPriority, ReviewStatus, SpecimenReview
from src.images.s3_client import HerbariumImageResolver, ImageHashMapping
from src.spatial.zone_detector import DWC_ZONE_HINTS, VerticalZone, HorizontalZone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# In-memory specimen store (loaded at startup)
specimens: Dict[str, SpecimenReview] = {}
ocr_regions: Dict[str, List[Dict]] = {}  # OCR bounding boxes per specimen
image_dir: Optional[Path] = None
image_resolver: Optional[HerbariumImageResolver] = None

# Review state persistence
REVIEW_STATE_FILE = Path(__file__).parent.parent / "data" / "review_state.json"


def load_ocr_regions(enriched_path: Path) -> Dict[str, List[Dict]]:
    """Load OCR regions from enriched JSONL file."""
    regions = {}
    if not enriched_path.exists():
        logger.warning(f"Enriched JSONL not found: {enriched_path}")
        return regions

    try:
        with open(enriched_path) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # Extract specimen ID from image filename
                    image = data.get("image", "")
                    specimen_id = Path(image).stem if image else None
                    if specimen_id and "ocr_regions" in data:
                        regions[specimen_id] = data["ocr_regions"]
        logger.info(f"Loaded OCR regions for {len(regions)} specimens")
    except Exception as e:
        logger.error(f"Error loading OCR regions: {e}")

    return regions


def load_review_state() -> Dict:
    """Load persisted review state from disk."""
    if REVIEW_STATE_FILE.exists():
        try:
            with open(REVIEW_STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load review state: {e}")
    return {}


def save_review_state():
    """Save current review state to disk."""
    state = {}
    for sid, specimen in specimens.items():
        # Only save specimens with review activity
        if (specimen.notes or specimen.review_notes or
            specimen.status != ReviewStatus.PENDING or
            specimen.flagged or specimen.reextraction_requested or
            specimen.reextraction_regions):
            state[sid] = {
                "notes": specimen.notes,
                "review_notes": specimen.review_notes,
                "status": specimen.status.value,
                "priority": specimen.priority.name,
                "flagged": specimen.flagged,
                "reextraction_requested": specimen.reextraction_requested,
                "reextraction_regions": specimen.reextraction_regions,
                "corrections": specimen.corrections,
            }

    try:
        REVIEW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REVIEW_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        logger.debug(f"Saved review state for {len(state)} specimens")
    except Exception as e:
        logger.error(f"Failed to save review state: {e}")


def apply_review_state(specimens: Dict[str, SpecimenReview], state: Dict):
    """Apply persisted review state to loaded specimens."""
    for sid, data in state.items():
        if sid in specimens:
            specimen = specimens[sid]
            specimen.notes = data.get("notes")
            specimen.review_notes = data.get("review_notes")
            if data.get("status"):
                specimen.status = ReviewStatus(data["status"])
            if data.get("priority"):
                specimen.priority = ReviewPriority[data["priority"]]
            specimen.flagged = data.get("flagged", False)
            specimen.reextraction_requested = data.get("reextraction_requested", False)
            specimen.reextraction_regions = data.get("reextraction_regions", [])
            specimen.corrections = data.get("corrections", {})
    logger.info(f"Applied review state for {len(state)} specimens")


def create_app(
    data_path: Optional[Path] = None,
    images_path: Optional[Path] = None,
    mode: Literal["local", "production"] = "local",
) -> FastAPI:
    """Create FastAPI app with mode-specific configuration.

    Args:
        data_path: Path to raw.jsonl extraction file
        images_path: Path to specimen images directory
        mode: Server mode - 'local' (no auth) or 'production' (requires auth)
    """
    global specimens, image_dir, image_resolver

    is_production = mode == "production"

    app = FastAPI(
        title="Herbarium Review",
        description="Server for herbarium specimen review",
        version="1.0.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
    )

    # Configure CORS based on mode
    if is_production:
        allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
        allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
        if not allowed_origins:
            allowed_origins = []  # Strict: no CORS if not configured
    else:
        allowed_origins = ["*"]  # Allow all for local dev

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load specimen data
    global ocr_regions
    try:
        specimen_list = load_specimens_for_review(data_path)
        specimens = {s.specimen_id: s for s in specimen_list}
        logger.info(f"Loaded {len(specimens)} specimens")

        # Apply any persisted review state
        review_state = load_review_state()
        if review_state:
            apply_review_state(specimens, review_state)

        # Load OCR regions from enriched JSONL (if available)
        enriched_path = data_path.parent / "enriched.jsonl"
        ocr_regions = load_ocr_regions(enriched_path)
    except FileNotFoundError as e:
        logger.error(f"Failed to load specimens: {e}")
        specimens = {}

    # Set up image directory
    if images_path:
        image_dir = images_path
    else:
        # Default: look for images in common locations
        project_root = Path(__file__).parent.parent
        aafc_base = DEFAULT_AAFC_OUTPUT
        candidates = [
            project_root / "data" / "images",  # Project local images
            aafc_base / "images",
            aafc_base / "data" / "images",
            Path.home() / "Pictures" / "herbarium",
        ]
        for candidate in candidates:
            if candidate.exists():
                image_dir = candidate
                break

    if image_dir:
        logger.info(f"Serving images from: {image_dir}")
    else:
        logger.warning("No image directory found - will use S3 fallback only")

    # Initialize image resolver
    # Use local-first if images are available locally (iCloud or configured dir)
    # This avoids needing hash mapping for S3 content-addressed paths
    hash_mapping = ImageHashMapping()
    image_resolver = HerbariumImageResolver(
        local_dir=image_dir,
        hash_mapping=hash_mapping,
        s3_first=False,  # Prefer local files over S3
    )
    logger.info(f"Image resolver: local_dir={image_dir}, icloud_dir={image_resolver.icloud_dir}, s3_first={image_resolver.s3_first}")
    if image_resolver.icloud_dir and image_resolver.icloud_dir.exists():
        logger.info(f"iCloud images available at: {image_resolver.icloud_dir}")

    # Note: Hash mapping is built on-demand or via CLI flag
    # Run with --build-hashes to pre-build the mapping
    if len(hash_mapping) > 0:
        logger.info(f"Using cached hash mapping: {len(hash_mapping)} entries")

    # === API Routes ===

    @app.get("/")
    async def root():
        """Redirect to mobile UI."""
        return RedirectResponse(url="/index.html")

    @app.get("/api/v1/queue")
    async def get_queue(
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """Get the review queue with optional filters."""
        queue = list(specimens.values())

        # Filter by status
        if status:
            try:
                status_enum = ReviewStatus(status.lower())
                queue = [s for s in queue if s.status == status_enum]
            except ValueError:
                pass

        # Filter by priority
        if priority:
            try:
                priority_enum = ReviewPriority[priority.upper()]
                queue = [s for s in queue if s.priority == priority_enum]
            except KeyError:
                pass

        # Sort by priority (critical first)
        queue.sort(key=lambda s: s.priority.value)

        # Paginate
        total = len(queue)
        queue = queue[offset:offset + limit]

        return {
            "specimens": [specimen_to_dict(s) for s in queue],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
            },
        }

    @app.get("/api/v1/specimen/{specimen_id}")
    async def get_specimen(specimen_id: str):
        """Get a single specimen by ID."""
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        return {"specimen": specimen_to_detail_dict(specimen)}

    @app.get("/api/v1/statistics")
    async def get_statistics():
        """Get queue statistics."""
        status_counts = {}
        priority_counts = {}

        for s in specimens.values():
            status_key = s.status.value.upper()
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

            priority_key = s.priority.name
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1

        return {
            "total_specimens": len(specimens),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
        }

    @app.get("/api/v1/images/{specimen_id}")
    async def get_image(specimen_id: str):
        """Serve specimen image from local directory or redirect to S3."""
        # Get specimen to check for SHA256 hash
        specimen = specimens.get(specimen_id)
        sha256_hash = getattr(specimen, 'sha256_hash', None) if specimen else None

        # Resolve image URL/path
        print(f"DEBUG: Resolving image for {specimen_id}, hash={sha256_hash}, resolver={image_resolver}", flush=True)
        resolved = image_resolver.resolve(specimen_id, sha256_hash)
        print(f"DEBUG: Resolved to: {resolved}", flush=True)

        if not resolved:
            raise HTTPException(status_code=404, detail=f"Image not found for {specimen_id}")

        # If it's an S3 URL, redirect to it
        if image_resolver.is_s3_url(resolved):
            return RedirectResponse(url=resolved, status_code=302)

        # Otherwise serve local file
        image_path = Path(resolved)
        if image_path.exists():
            ext = image_path.suffix.lower()
            media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            return FileResponse(image_path, media_type=media_type)

        raise HTTPException(status_code=404, detail=f"Image not found for {specimen_id}")

    @app.post("/api/v1/specimen/{specimen_id}/approve")
    async def approve_specimen(specimen_id: str):
        """Quick-approve a specimen."""
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        specimen.status = ReviewStatus.APPROVED
        save_review_state()
        return {"status": "approved", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/reject")
    async def reject_specimen(specimen_id: str, notes: Optional[str] = None):
        """Reject a specimen."""
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        specimen.status = ReviewStatus.REJECTED
        if notes:
            specimen.notes = notes
        save_review_state()
        return {"status": "rejected", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/flag")
    async def flag_specimen(specimen_id: str, notes: Optional[str] = None):
        """Flag a specimen for expert review."""
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        specimen.flagged = True
        if notes:
            specimen.notes = notes
        save_review_state()
        return {"status": "flagged", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/request-reextraction")
    async def request_reextraction(specimen_id: str, notes: Optional[str] = None):
        """
        Request re-extraction for a specimen.

        Use this when the image is good but extraction failed or was incomplete.
        Different from 'reject' (bad data) or 'flag' (needs expert review).
        """
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        specimen.status = ReviewStatus.PENDING  # Back to pending for re-processing
        specimen.reextraction_requested = True
        if notes:
            specimen.review_notes = notes  # Workflow feedback, not canonical data
        save_review_state()
        return {"status": "reextraction_requested", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/request-region-reextraction")
    async def request_region_reextraction(specimen_id: str, request: Request):
        """
        Request re-extraction for specific OCR regions.

        Accepts a list of region indices to re-extract, with optional notes.
        This enables targeted re-extraction of problem areas rather than
        re-processing the entire specimen.

        Request body:
            {
                "region_indices": [0, 3, 5],
                "notes": "Optional notes about what's wrong"
            }
        """
        from datetime import datetime

        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        body = await request.json()
        region_indices = body.get("region_indices", [])
        notes = body.get("notes", "")

        if not region_indices:
            raise HTTPException(status_code=400, detail="No regions specified")

        # Get OCR regions for this specimen
        specimen_ocr = ocr_regions.get(specimen_id, [])

        # Build region re-extraction records
        new_regions = []
        for idx in region_indices:
            if 0 <= idx < len(specimen_ocr):
                region = specimen_ocr[idx]
                new_regions.append({
                    "region_index": idx,
                    "bounds": region.get("bounds", {}),
                    "text": region.get("text", ""),
                    "confidence": region.get("confidence", 0),
                    "zone": region.get("zone", {}),
                    "requested_at": datetime.now(datetime.timezone.utc).isoformat(),
                    "notes": notes,
                })

        if not new_regions:
            raise HTTPException(status_code=400, detail="No valid region indices")

        # Append to existing reextraction_regions (don't replace)
        if not hasattr(specimen, "reextraction_regions") or specimen.reextraction_regions is None:
            specimen.reextraction_regions = []
        specimen.reextraction_regions.extend(new_regions)

        # Also set the general reextraction flag
        specimen.reextraction_requested = True
        specimen.status = ReviewStatus.PENDING

        save_review_state()

        return {
            "status": "region_reextraction_requested",
            "specimen_id": specimen_id,
            "regions_queued": len(new_regions),
            "total_pending_regions": len(specimen.reextraction_regions),
        }

    @app.delete("/api/v1/specimen/{specimen_id}/reextraction-regions")
    async def clear_reextraction_regions(specimen_id: str):
        """Clear all pending region re-extraction requests for a specimen."""
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        cleared_count = len(specimen.reextraction_regions) if hasattr(specimen, "reextraction_regions") else 0
        specimen.reextraction_regions = []

        # If no general re-extraction was requested, clear that flag too
        if not specimen.review_notes:  # Only if no notes suggesting manual re-extraction
            specimen.reextraction_requested = False

        save_review_state()

        return {
            "status": "cleared",
            "specimen_id": specimen_id,
            "regions_cleared": cleared_count,
        }

    @app.put("/api/v1/specimen/{specimen_id}")
    async def update_specimen(specimen_id: str, request: Request):
        """
        Update specimen review metadata (notes, priority, etc).

        This updates workflow/review data, not canonical DwC fields.
        """
        specimen = specimens.get(specimen_id)
        if not specimen:
            raise HTTPException(status_code=404, detail="Specimen not found")

        body = await request.json()

        # Update allowed review fields
        if "notes" in body:
            specimen.notes = body["notes"]
        if "review_notes" in body:
            specimen.review_notes = body["review_notes"]
        if "priority" in body:
            try:
                specimen.priority = ReviewPriority[body["priority"].upper()]
            except KeyError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid priority: {body['priority']}"
                )

        save_review_state()
        return {"status": "updated", "specimen_id": specimen_id}

    # Mount static files for the mobile UI
    mobile_dir = Path(__file__).parent
    app.mount("/", StaticFiles(directory=str(mobile_dir), html=True), name="static")

    return app


def specimen_to_dict(s: SpecimenReview) -> dict:
    """Convert specimen to queue list format."""
    # Get primary fields for display
    dwc = s.dwc_fields
    scientific_name = dwc.get("scientificName", {}).get("value", "Unknown species")
    catalog_number = dwc.get("catalogNumber", {}).get("value", "")

    return {
        "id": s.specimen_id,
        "catalog_number": catalog_number,
        "scientific_name": scientific_name,
        "status": s.status.value.upper(),
        "priority": s.priority.name,
        "quality_score": round(s.quality_score, 1),
        "completeness": round(s.completeness_score, 1),
        "flagged": s.flagged,
        "critical_issues": len(s.gbif_taxonomy_issues),
    }


def specimen_to_detail_dict(s: SpecimenReview) -> dict:
    """Convert specimen to detail view format with enhanced provenance and zone hints."""
    # Transform fields for the mobile UI
    fields = {}
    for field_name, field_data in s.dwc_fields.items():
        # Get zone hint for this field if available
        zone_hint = None
        if field_name in DWC_ZONE_HINTS:
            vertical, horizontal = DWC_ZONE_HINTS[field_name]
            zone_hint = {
                "vertical": vertical.value,
                "horizontal": horizontal.value,
                "description": get_zone_description(vertical, horizontal),
            }

        fields[field_name] = {
            "value": field_data.get("value", ""),
            "confidence": field_data.get("confidence", 0.0),
            "corrected_value": None,
            # Field-level provenance (inherits from specimen for now)
            "provenance": {
                "model": s.model,
                "provider": s.provider,
                "method": "vision_extraction",
            },
            # Zone hint for where this field typically appears
            "zone_hint": zone_hint,
        }

    return {
        "id": s.specimen_id,
        "fields": fields,
        "review": {
            "status": s.status.value.upper(),
            "priority": s.priority.name,
            "notes": s.notes or "",
            "review_notes": s.review_notes or "",
            "flagged": s.flagged,
            "reextraction_requested": s.reextraction_requested,
            "reextraction_regions": s.reextraction_regions if hasattr(s, "reextraction_regions") else [],
        },
        "gbif_validation": {
            "taxonomy_verified": s.gbif_taxonomy_verified,
            "taxonomy_issues": s.gbif_taxonomy_issues,
            "locality_verified": s.gbif_locality_verified,
            "locality_issues": s.gbif_locality_issues,
        },
        "issues": {
            "critical": s.gbif_taxonomy_issues,
            "warnings": s.gbif_locality_issues,
        },
        "provenance": {
            "model": s.model,
            "provider": s.provider,
            "timestamp": s.extraction_timestamp,
            "history": s.provenance_history if hasattr(s, "provenance_history") else [],
        },
        # OCR regions with bounding boxes for visual overlay
        "ocr_regions": ocr_regions.get(s.specimen_id, []),
    }


def get_zone_description(vertical: VerticalZone, horizontal: HorizontalZone) -> str:
    """Get human-readable description of zone location."""
    zone_descriptions = {
        (VerticalZone.TOP, HorizontalZone.LEFT): "Upper-left area (headers)",
        (VerticalZone.TOP, HorizontalZone.CENTER): "Top center (type status, institution)",
        (VerticalZone.TOP, HorizontalZone.RIGHT): "Upper-right area",
        (VerticalZone.MIDDLE, HorizontalZone.LEFT): "Middle-left (collector info)",
        (VerticalZone.MIDDLE, HorizontalZone.CENTER): "Center (species name)",
        (VerticalZone.MIDDLE, HorizontalZone.RIGHT): "Middle-right (date, numbers)",
        (VerticalZone.BOTTOM, HorizontalZone.LEFT): "Lower-left (country, province)",
        (VerticalZone.BOTTOM, HorizontalZone.CENTER): "Bottom center (locality)",
        (VerticalZone.BOTTOM, HorizontalZone.RIGHT): "Lower-right (catalog number)",
    }
    return zone_descriptions.get((vertical, horizontal), f"{vertical.value}-{horizontal.value}")


def main():
    parser = argparse.ArgumentParser(
        description="Herbarium specimen review server"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "production"],
        default="local",
        help="Server mode: 'local' (no auth) or 'production' (requires auth)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="Path to raw.jsonl extraction file",
    )
    parser.add_argument(
        "--images",
        type=Path,
        help="Path to specimen images directory",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to run server on (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    # Production mode checks
    if args.mode == "production":
        missing = []
        if not os.environ.get("JWT_SECRET_KEY"):
            missing.append("JWT_SECRET_KEY")
        if not os.environ.get("AUTH_USERS"):
            missing.append("AUTH_USERS")
        if missing:
            logger.error(f"Production mode requires environment variables: {', '.join(missing)}")
            logger.error("See docs/SECURITY.md for configuration instructions")
            sys.exit(1)

    app = create_app(data_path=args.data, images_path=args.images, mode=args.mode)

    mode_label = "Production" if args.mode == "production" else "Local Development"
    print(f"\n{'='*60}")
    print(f"  Herbarium Review Server ({mode_label})")
    print(f"{'='*60}")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Mode: {args.mode}")
    print(f"  Specimens loaded: {len(specimens)}")
    print(f"  Images: {image_dir or 'Not configured'}")
    if args.mode == "local":
        print(f"  API docs: http://{args.host}:{args.port}/docs")
    else:
        print(f"  API docs: Disabled (production mode)")
    print(f"{'='*60}\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

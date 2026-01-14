"""
Extraction module for herbarium specimen data.

Provides confidence-based routing for optimal accuracy/cost balance
with comprehensive provenance tracking.
"""

from .confidence_router import ConfidenceRouter
from .provenance import (
    ExtractionProvenance,
    FieldProvenance,
    # AAFC batch manifest utilities
    capture_git_provenance,
    capture_system_info,
    create_manifest,
    create_provenance,
    estimate_extraction_cost,
    get_code_version,
    get_prompt_hash,
    save_manifest,
    track_provenance,
    validate_reproducibility,
)

__all__ = [
    "ConfidenceRouter",
    "ExtractionProvenance",
    "FieldProvenance",
    "create_provenance",
    "estimate_extraction_cost",
    "get_code_version",
    "get_prompt_hash",
    # AAFC batch manifest utilities
    "capture_git_provenance",
    "capture_system_info",
    "create_manifest",
    "save_manifest",
    "validate_reproducibility",
    "track_provenance",
]

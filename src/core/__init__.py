"""
Herbarium Core Library

Shared foundation for herbarium digitization tools:
- provenance: Git capture, manifests, audit trails
- schema: Darwin Core schema management
- protocols: OCREngine, Extractor, Storage interfaces
- storage: JSON, SQLite, Postgres backends

This module provides the common infrastructure used by both
herbarium-specimen-tools (review workflow) and extraction pipelines.
"""

__version__ = "0.1.0"

from .provenance import (
    capture_git_provenance,
    capture_system_info,
    create_manifest,
    save_manifest,
    validate_reproducibility,
    track_provenance,
)

from .schema import (
    DWC_REQUIRED_FIELDS,
    DWC_ALL_FIELDS,
    DwcRecord,
)

__all__ = [
    # Provenance
    "capture_git_provenance",
    "capture_system_info",
    "create_manifest",
    "save_manifest",
    "validate_reproducibility",
    "track_provenance",
    # Schema
    "DWC_REQUIRED_FIELDS",
    "DWC_ALL_FIELDS",
    "DwcRecord",
]

"""
OCR module for herbarium specimen text extraction.

Provides hybrid cascade: Apple Vision → Rules → Claude Vision
"""

from .apple_vision import AppleVisionOCR, create_apple_vision_ocr
from .rules_engine import RulesEngine
from .hybrid_cascade import HybridCascadeOCR
from .enrichment import (
    enrich_specimen,
    batch_enrich,
    EnrichmentResult,
    get_enrichment_stats,
)

__all__ = [
    "AppleVisionOCR",
    "create_apple_vision_ocr",
    "RulesEngine",
    "HybridCascadeOCR",
    # Enrichment
    "enrich_specimen",
    "batch_enrich",
    "EnrichmentResult",
    "get_enrichment_stats",
]

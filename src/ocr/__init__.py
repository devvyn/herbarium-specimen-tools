"""
OCR module for herbarium specimen text extraction.

Provides hybrid cascade: Apple Vision → Rules → Claude Vision
"""

from .apple_vision import AppleVisionOCR, create_apple_vision_ocr
from .enrichment import (
    EnrichmentResult,
    batch_enrich,
    enrich_specimen,
    get_enrichment_stats,
)
from .hybrid_cascade import HybridCascadeOCR
from .rules_engine import RulesEngine

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

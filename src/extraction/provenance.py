"""
Extraction-specific provenance tracking.

This module provides field-level and specimen-level provenance tracking
for the extraction pipeline. It builds on the core provenance utilities.

For generic provenance utilities (git capture, manifests), use:
    from src.core.provenance import capture_git_provenance, create_manifest

This module adds:
- FieldProvenance: Track how each DwC field was extracted
- ExtractionProvenance: Complete provenance for a specimen extraction
- Cost estimation utilities
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Re-export core provenance utilities for backward compatibility
from src.core.provenance import (
    capture_git_provenance,
    capture_system_info,
    create_manifest,
    get_code_version,
    get_content_hash as get_prompt_hash,  # Alias for backward compat
    save_manifest,
    track_provenance,
    validate_reproducibility,
)

logger = logging.getLogger(__name__)


@dataclass
class FieldProvenance:
    """
    Provenance for a single Darwin Core field.

    Tracks exactly how this field value was obtained.
    """

    # What value was extracted
    value: str
    confidence: float

    # Which model extracted it
    model: str  # "gpt-4o-mini", "gpt-4o", "apple-vision", "claude-sonnet-3.5"
    provider: str  # "openai", "apple", "anthropic"
    extraction_method: str  # "direct", "ocr_text", "confidence_routing"

    # When and how
    timestamp: str  # ISO 8601 UTC
    processing_time_ms: float  # How long this extraction took

    # Cost tracking
    estimated_cost_usd: float  # Estimated cost for this field

    # Re-extraction tracking
    original_confidence: Optional[float] = None  # If re-extracted, what was original?
    original_model: Optional[str] = None  # What model produced original?
    improvement: Optional[float] = None  # Confidence improvement (new - old)

    # Validation provenance
    gbif_validated: bool = False
    gbif_cache_hit: bool = False  # Was GBIF result from cache?
    gbif_timestamp: Optional[str] = None

    # Version tracking
    code_version: Optional[str] = None  # Git commit hash
    prompt_version: Optional[str] = None  # Prompt template hash

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ExtractionProvenance:
    """
    Complete provenance for a specimen extraction.

    Tracks all models, methods, and decisions in extraction pipeline.
    """

    # Specimen identification
    image_path: str
    specimen_id: str
    timestamp: str  # When extraction started

    # Overall extraction metadata
    extraction_strategy: str  # "hybrid_cascade", "confidence_routing", "direct"
    total_processing_time_ms: float
    total_estimated_cost_usd: float

    # Model usage statistics
    models_used: List[str] = field(default_factory=list)  # ["apple-vision", "gpt-4o"]
    api_calls_made: int = 0
    cache_hits: int = 0

    # Field-level provenance
    fields: Dict[str, FieldProvenance] = field(default_factory=dict)

    # Validation provenance
    validation_method: Optional[str] = None  # "gbif_pygbif", "ipni_fallback"
    validation_cache_hit: bool = False
    validation_timestamp: Optional[str] = None

    # Environment
    code_version: Optional[str] = None
    python_version: Optional[str] = None
    platform: Optional[str] = None

    def add_field(
        self,
        field_name: str,
        value: str,
        confidence: float,
        model: str,
        provider: str,
        extraction_method: str,
        processing_time_ms: float,
        estimated_cost_usd: float = 0.0,
        **kwargs,
    ):
        """Add field extraction provenance."""
        self.fields[field_name] = FieldProvenance(
            value=value,
            confidence=confidence,
            model=model,
            provider=provider,
            extraction_method=extraction_method,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time_ms,
            estimated_cost_usd=estimated_cost_usd,
            code_version=self.code_version,
            **kwargs,
        )

    def mark_field_reextracted(
        self,
        field_name: str,
        new_value: str,
        new_confidence: float,
        new_model: str,
        new_provider: str,
        processing_time_ms: float,
        estimated_cost_usd: float = 0.0,
    ):
        """
        Mark that a field was re-extracted with premium model.

        Preserves original extraction provenance.
        """
        if field_name not in self.fields:
            raise ValueError(f"Field '{field_name}' not found in provenance")

        original = self.fields[field_name]

        # Create new provenance with original values tracked
        self.fields[field_name] = FieldProvenance(
            value=new_value,
            confidence=new_confidence,
            model=new_model,
            provider=new_provider,
            extraction_method="confidence_routing_reextraction",
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time_ms,
            estimated_cost_usd=estimated_cost_usd,
            # Track original
            original_confidence=original.confidence,
            original_model=original.model,
            improvement=new_confidence - original.confidence,
            code_version=self.code_version,
        )

    def add_validation(
        self,
        field_name: str,
        validated: bool,
        cache_hit: bool,
        timestamp: Optional[str] = None,
    ):
        """Add GBIF validation provenance to field."""
        if field_name in self.fields:
            self.fields[field_name].gbif_validated = validated
            self.fields[field_name].gbif_cache_hit = cache_hit
            self.fields[field_name].gbif_timestamp = (
                timestamp or datetime.now(timezone.utc).isoformat()
            )

    def get_summary(self) -> Dict:
        """Get extraction summary statistics."""
        field_count = len(self.fields)
        re_extracted_count = sum(
            1 for f in self.fields.values() if f.original_confidence is not None
        )
        validated_count = sum(1 for f in self.fields.values() if f.gbif_validated)
        cache_hit_count = sum(1 for f in self.fields.values() if f.gbif_cache_hit)

        avg_confidence = (
            sum(f.confidence for f in self.fields.values()) / field_count
            if field_count > 0
            else 0.0
        )

        return {
            "specimen_id": self.specimen_id,
            "extraction_strategy": self.extraction_strategy,
            "total_fields": field_count,
            "fields_re_extracted": re_extracted_count,
            "fields_validated": validated_count,
            "validation_cache_hits": cache_hit_count,
            "avg_confidence": round(avg_confidence, 3),
            "total_processing_time_ms": round(self.total_processing_time_ms, 1),
            "total_cost_usd": round(self.total_estimated_cost_usd, 6),
            "models_used": self.models_used,
            "api_calls_made": self.api_calls_made,
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "specimen_id": self.specimen_id,
            "image_path": self.image_path,
            "timestamp": self.timestamp,
            "extraction_strategy": self.extraction_strategy,
            "total_processing_time_ms": self.total_processing_time_ms,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "models_used": self.models_used,
            "api_calls_made": self.api_calls_made,
            "cache_hits": self.cache_hits,
            "validation_method": self.validation_method,
            "validation_cache_hit": self.validation_cache_hit,
            "validation_timestamp": self.validation_timestamp,
            "code_version": self.code_version,
            "python_version": self.python_version,
            "platform": self.platform,
            "fields": {name: fp.to_dict() for name, fp in self.fields.items()},
            "summary": self.get_summary(),
        }


def create_provenance(
    image_path: str,
    specimen_id: str,
    extraction_strategy: str,
) -> ExtractionProvenance:
    """
    Create new extraction provenance tracker.

    Args:
        image_path: Path to specimen image
        specimen_id: Unique specimen identifier
        extraction_strategy: Name of extraction strategy used

    Returns:
        ExtractionProvenance instance
    """
    import platform
    import sys

    return ExtractionProvenance(
        image_path=image_path,
        specimen_id=specimen_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        extraction_strategy=extraction_strategy,
        total_processing_time_ms=0.0,
        total_estimated_cost_usd=0.0,
        code_version=get_code_version(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=platform.system(),
    )


# Cost constants (approximate, as of 2025)
COSTS_PER_1K_TOKENS = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
    "apple-vision": {"input": 0.0, "output": 0.0},  # Free
}


def estimate_extraction_cost(
    model: str, input_tokens: int = 1500, output_tokens: int = 500
) -> float:
    """
    Estimate cost for an extraction.

    Args:
        model: Model name
        input_tokens: Approximate input tokens (image + prompt)
        output_tokens: Approximate output tokens (JSON response)

    Returns:
        Estimated cost in USD
    """
    if model not in COSTS_PER_1K_TOKENS:
        return 0.0

    costs = COSTS_PER_1K_TOKENS[model]
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]

    return input_cost + output_cost

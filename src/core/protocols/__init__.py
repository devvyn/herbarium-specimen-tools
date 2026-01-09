"""
Protocol interfaces for herbarium digitization pipeline.

These protocols define the contracts that different components must implement,
enabling pluggable OCR engines, extractors, and storage backends.

Uses typing.Protocol for structural subtyping - implementations don't need
to explicitly inherit, they just need to implement the required methods.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class OCRResult:
    """Result from an OCR engine."""

    text: str
    confidence: float
    regions: List[Dict[str, Any]]  # Bounding boxes with text
    metadata: Dict[str, Any]  # Engine-specific metadata


@dataclass
class ExtractionResult:
    """Result from field extraction."""

    fields: Dict[str, Dict[str, Any]]  # field_name -> {value, confidence, ...}
    model: str
    provider: str
    processing_time_ms: float
    cost_usd: float
    raw_response: Optional[str] = None


@runtime_checkable
class OCREngine(Protocol):
    """Protocol for OCR engines (Apple Vision, Tesseract, etc.)."""

    @property
    def name(self) -> str:
        """Engine name for provenance tracking."""
        ...

    @property
    def is_available(self) -> bool:
        """Check if engine is available on this system."""
        ...

    def extract_text(self, image_path: Path) -> OCRResult:
        """Extract text from image.

        Args:
            image_path: Path to specimen image

        Returns:
            OCRResult with text and confidence
        """
        ...


@runtime_checkable
class FieldExtractor(Protocol):
    """Protocol for field extraction (GPT-4, Claude, rules engine, etc.)."""

    @property
    def name(self) -> str:
        """Extractor name for provenance tracking."""
        ...

    @property
    def model(self) -> str:
        """Model identifier (e.g., 'gpt-4o-mini', 'claude-3.5-sonnet')."""
        ...

    @property
    def provider(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic', 'local')."""
        ...

    def extract_fields(
        self,
        image_path: Path,
        ocr_text: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract Darwin Core fields from specimen image.

        Args:
            image_path: Path to specimen image
            ocr_text: Pre-extracted OCR text (optional, for hybrid pipelines)

        Returns:
            ExtractionResult with DwC fields and provenance
        """
        ...


@dataclass
class SpecimenData:
    """Core specimen data for storage."""

    specimen_id: str
    dwc_fields: Dict[str, Dict[str, Any]]
    status: str
    priority: str
    metadata: Dict[str, Any]


@runtime_checkable
class SpecimenStorage(Protocol):
    """Protocol for specimen data storage backends."""

    def get(self, specimen_id: str) -> Optional[SpecimenData]:
        """Get specimen by ID."""
        ...

    def put(self, specimen: SpecimenData) -> None:
        """Store or update specimen."""
        ...

    def delete(self, specimen_id: str) -> bool:
        """Delete specimen. Returns True if existed."""
        ...

    def list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SpecimenData]:
        """List specimens with optional filters."""
        ...

    def count(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> int:
        """Count specimens matching filters."""
        ...


@runtime_checkable
class ValidationService(Protocol):
    """Protocol for validation services (GBIF, IPNI, etc.)."""

    @property
    def name(self) -> str:
        """Service name for provenance tracking."""
        ...

    def validate_taxonomy(
        self,
        scientific_name: str,
    ) -> Dict[str, Any]:
        """Validate scientific name against authoritative source.

        Returns:
            {
                "valid": bool,
                "matched_name": str | None,
                "issues": List[str],
                "source": str,
                "cache_hit": bool,
            }
        """
        ...

    def validate_locality(
        self,
        country: Optional[str],
        state_province: Optional[str],
        locality: Optional[str],
    ) -> Dict[str, Any]:
        """Validate geographic locality.

        Returns:
            {
                "valid": bool,
                "issues": List[str],
                "suggestions": Dict[str, str],
                "source": str,
                "cache_hit": bool,
            }
        """
        ...


__all__ = [
    "OCRResult",
    "ExtractionResult",
    "OCREngine",
    "FieldExtractor",
    "SpecimenData",
    "SpecimenStorage",
    "ValidationService",
]

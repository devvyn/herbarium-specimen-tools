"""
Rules engine adapter conforming to FieldExtractor protocol.

Wraps the existing RulesEngine implementation to provide
a protocol-compliant interface.
"""

import time
from pathlib import Path

from src.core.protocols import ExtractionResult
from src.ocr.rules_engine import RulesEngine


class RulesEngineAdapter:
    """
    Protocol-compliant adapter for rules-based field extraction.

    Implements the FieldExtractor protocol by wrapping RulesEngine.
    """

    def __init__(self):
        """Initialize rules engine adapter."""
        self._engine = RulesEngine()

    @property
    def name(self) -> str:
        """Extractor name for provenance tracking."""
        return "rules-engine"

    @property
    def model(self) -> str:
        """Model identifier."""
        return "regex-patterns-v1"

    @property
    def provider(self) -> str:
        """Provider name."""
        return "local"

    def extract_fields(
        self,
        image_path: Path,
        ocr_text: str | None = None,
    ) -> ExtractionResult:
        """Extract Darwin Core fields from specimen image.

        Note: This extractor requires pre-extracted OCR text.
        It cannot process images directly.

        Args:
            image_path: Path to specimen image (unused, for protocol compatibility)
            ocr_text: Pre-extracted OCR text (required)

        Returns:
            ExtractionResult with DwC fields and provenance
        """
        if not ocr_text:
            return ExtractionResult(
                fields={},
                model=self.model,
                provider=self.provider,
                processing_time_ms=0.0,
                cost_usd=0.0,
                raw_response=None,
            )

        start_time = time.time()

        # Extract fields using rules engine
        dwc_fields, confidences = self._engine.extract_fields(ocr_text)

        processing_time_ms = (time.time() - start_time) * 1000

        # Convert to protocol format: field_name -> {value, confidence, ...}
        fields = {}
        for field_name, value in dwc_fields.items():
            confidence = confidences.get(field_name, 0.5)
            fields[field_name] = {
                "value": value,
                "confidence": confidence,
                "extraction_method": "rules",
            }

        return ExtractionResult(
            fields=fields,
            model=self.model,
            provider=self.provider,
            processing_time_ms=processing_time_ms,
            cost_usd=0.0,  # Free
            raw_response=ocr_text,
        )

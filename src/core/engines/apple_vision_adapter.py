"""
Apple Vision OCR adapter conforming to OCREngine protocol.

Wraps the existing AppleVisionOCR implementation to provide
a protocol-compliant interface.
"""

from pathlib import Path

from src.core.protocols import OCRResult
from src.ocr.apple_vision import AppleVisionOCR


class AppleVisionAdapter:
    """
    Protocol-compliant adapter for Apple Vision OCR.

    Implements the OCREngine protocol by wrapping AppleVisionOCR.
    """

    def __init__(self):
        """Initialize Apple Vision adapter."""
        self._ocr = AppleVisionOCR()

    @property
    def name(self) -> str:
        """Engine name for provenance tracking."""
        return "apple-vision"

    @property
    def is_available(self) -> bool:
        """Check if engine is available on this system."""
        return self._ocr.is_available()

    def extract_text(self, image_path: Path) -> OCRResult:
        """Extract text from image.

        Args:
            image_path: Path to specimen image

        Returns:
            OCRResult with text and confidence
        """
        text_blocks, error = self._ocr.extract_text(image_path)

        if error:
            return OCRResult(
                text="",
                confidence=0.0,
                regions=[],
                metadata={"error": error, "engine": self.name},
            )

        if not text_blocks:
            return OCRResult(
                text="",
                confidence=0.0,
                regions=[],
                metadata={"engine": self.name},
            )

        # Concatenate text blocks
        full_text = "\n".join(block["text"] for block in text_blocks)

        # Calculate average confidence
        avg_confidence = (
            sum(block["confidence"] for block in text_blocks) / len(text_blocks)
        )

        # Convert blocks to regions format
        regions = [
            {
                "text": block["text"],
                "confidence": block["confidence"],
                "bounds": block["bounds"],
            }
            for block in text_blocks
        ]

        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            regions=regions,
            metadata={
                "engine": self.name,
                "block_count": len(text_blocks),
                "cost_usd": 0.0,  # Free
            },
        )

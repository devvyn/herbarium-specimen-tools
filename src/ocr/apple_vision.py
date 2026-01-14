"""
Apple Vision Framework OCR integration.

Uses macOS Vision Framework for fast, free text extraction.
Falls back gracefully on non-macOS platforms.
"""

import logging
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class AppleVisionOCR:
    """
    Apple Vision Framework OCR wrapper.

    Uses macOS Vision API for text recognition. Free and fast.
    Requires macOS 10.15+ (Catalina or later).
    """

    def __init__(self):
        """Initialize Apple Vision OCR."""
        self.available = platform.system() == "Darwin"

        if not self.available:
            logger.warning("Apple Vision OCR not available (requires macOS)")
        else:
            logger.info("Apple Vision OCR initialized")

    def is_available(self) -> bool:
        """Check if Apple Vision is available on this platform."""
        return self.available

    def extract_text(
        self, image_path: Path
    ) -> tuple[list[dict[str, any]], str | None]:
        """
        Extract text from image using Apple Vision.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (text_blocks, error_message)
            text_blocks: List of dicts with 'text', 'confidence', 'bounds'
            error_message: Error string if extraction failed, None otherwise
        """
        if not self.available:
            return [], "Apple Vision not available on this platform"

        if not image_path.exists():
            return [], f"Image not found: {image_path}"

        try:
            # Use Swift script for Vision API access
            swift_script = self._get_swift_script()

            result = subprocess.run(
                ["swift", "-", str(image_path)],
                input=swift_script.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8")
                logger.error(f"Apple Vision extraction failed: {error_msg}")
                return [], error_msg

            # Parse output
            output = result.stdout.decode("utf-8").strip()
            if not output:
                return [], "No text extracted"

            text_blocks = self._parse_output(output)
            return text_blocks, None

        except subprocess.TimeoutExpired:
            return [], "Apple Vision extraction timed out (>30s)"
        except Exception as e:
            logger.error(f"Apple Vision extraction error: {e}")
            return [], str(e)

    def extract_text_simple(self, image_path: Path) -> tuple[str, float]:
        """
        Extract text from image (simple interface).

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (concatenated_text, average_confidence)
        """
        text_blocks, error = self.extract_text(image_path)

        if error:
            return "", 0.0

        if not text_blocks:
            return "", 0.0

        # Concatenate all text
        full_text = "\n".join(block["text"] for block in text_blocks)

        # Calculate average confidence
        avg_confidence = (
            sum(block["confidence"] for block in text_blocks) / len(text_blocks)
        )

        return full_text, avg_confidence

    def _get_swift_script(self) -> str:
        """Get Swift script for Vision API access."""
        return """
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("Usage: swift script.swift <image_path>")
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard let image = NSImage(contentsOf: imageURL) else {
    fputs("Error: Could not load image\\n", stderr)
    exit(1)
}

guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Error: Could not convert to CGImage\\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])

    guard let observations = request.results else {
        print("")
        exit(0)
    }

    for observation in observations {
        guard let candidate = observation.topCandidates(1).first else { continue }

        let text = candidate.string
        let confidence = candidate.confidence
        let bounds = observation.boundingBox

        // Output format: text|||confidence|||x,y,w,h
        print("\\(text)|||\\(confidence)|||\\(bounds.origin.x),\\(bounds.origin.y),\\(bounds.width),\\(bounds.height)")
    }

} catch {
    fputs("Error: \\(error.localizedDescription)\\n", stderr)
    exit(1)
}
"""

    def _parse_output(self, output: str) -> list[dict[str, any]]:
        """Parse Swift script output into structured data."""
        text_blocks = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|||")
            if len(parts) != 3:
                logger.warning(f"Malformed output line: {line}")
                continue

            text = parts[0]
            confidence = float(parts[1])
            bounds_str = parts[2]

            try:
                x, y, w, h = map(float, bounds_str.split(","))
                bounds = {"x": x, "y": y, "width": w, "height": h}
            except ValueError:
                bounds = {"x": 0, "y": 0, "width": 0, "height": 0}

            text_blocks.append(
                {"text": text, "confidence": confidence, "bounds": bounds}
            )

        return text_blocks

    def get_stats(self) -> dict:
        """Get OCR statistics."""
        return {
            "available": self.available,
            "platform": platform.system(),
            "cost_per_extraction": 0.0,  # Free!
        }


def create_apple_vision_ocr() -> AppleVisionOCR:
    """Create Apple Vision OCR instance."""
    return AppleVisionOCR()

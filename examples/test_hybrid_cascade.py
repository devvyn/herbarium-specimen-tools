#!/usr/bin/env python3
"""
Test script for hybrid OCR cascade.

Usage:
    python examples/test_hybrid_cascade.py path/to/specimen/image.jpg

Requirements:
    - macOS for Apple Vision (optional, will use Claude if unavailable)
    - ANTHROPIC_API_KEY environment variable for Claude fallback
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ocr import HybridCascadeOCR


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_hybrid_cascade.py <image_path>")
        print("\nExample:")
        print("  python test_hybrid_cascade.py examples/sample_data/EXAMPLE-001.jpg")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    print("=" * 80)
    print("Hybrid OCR Cascade Test")
    print("=" * 80)
    print(f"Image: {image_path}")
    print()

    # Create cascade
    cascade = HybridCascadeOCR(
        confidence_threshold=0.80,
        min_fields_threshold=8,
        enable_claude_fallback=True,
    )

    print("Cascade Configuration:")
    print(f"  Confidence threshold: 0.80")
    print(f"  Min fields threshold: 8")
    print(f"  Claude fallback: Enabled")
    print()

    print("-" * 80)
    print("Running extraction...")
    print("-" * 80)
    print()

    # Extract
    dwc_fields, confidences, metadata = cascade.extract(image_path)

    if not dwc_fields:
        print("❌ Extraction failed")
        if "apple_vision_error" in metadata:
            print(f"   Apple Vision error: {metadata['apple_vision_error']}")
        if "claude_error" in metadata:
            print(f"   Claude error: {metadata['claude_error']}")
        sys.exit(1)

    # Display results
    print("=" * 80)
    print("Extraction Results")
    print("=" * 80)
    print()

    # Show which stages were used
    stages = " → ".join(metadata["stages_used"])
    print(f"Pipeline: {stages}")
    print(f"Decision: {metadata['cascade_decision']}")
    print()

    # Show extracted fields
    print("Extracted Darwin Core Fields:")
    print("-" * 80)

    sorted_fields = sorted(confidences.items(), key=lambda x: x[1], reverse=True)

    for field, confidence in sorted_fields:
        value = dwc_fields.get(field, "")
        confidence_indicator = "🟢" if confidence >= 0.85 else "🟡" if confidence >= 0.70 else "🔴"

        print(f"{confidence_indicator} {field:20s} [{confidence:.2f}]  {value[:60]}")

    # Show metadata
    print()
    print("Extraction Metadata:")
    print("=" * 80)
    print(f"Processing time:      {metadata['processing_time_ms']:.1f}ms")

    if "estimated_cost_usd" in metadata:
        print(f"Estimated cost:       ${metadata['estimated_cost_usd']:.6f}")

    if "ocr_text_length" in metadata:
        print(f"OCR text length:      {metadata['ocr_text_length']} chars")
        print(f"OCR confidence:       {metadata['ocr_confidence']:.2f}")

    if "claude_input_tokens" in metadata:
        print(f"Claude input tokens:  {metadata['claude_input_tokens']}")
        print(f"Claude output tokens: {metadata['claude_output_tokens']}")

    # Show statistics
    print()
    print("Cascade Statistics:")
    print("=" * 80)
    stats = cascade.get_stats()
    print(f"Total extractions:    {stats['total_extractions']}")
    print(f"Apple Vision used:    {stats['apple_vision_used']}")
    print(f"Rules Engine used:    {stats['rules_engine_used']}")
    print(f"Claude used:          {stats['claude_used']}")
    print(f"Apple Vision failed:  {stats['apple_vision_failed']}")
    print(f"Claude usage rate:    {stats['claude_usage_rate']}")

    # Cost analysis
    print()
    print("Cost Analysis:")
    print("=" * 80)

    if stats["claude_used"] == 0:
        print("✅ FREE extraction! (Apple Vision + Rules only)")
        print("   Cost: $0.00")
        print("   vs Pure Claude: $0.003")
        print("   Savings: 100%")
    else:
        actual_cost = metadata.get("estimated_cost_usd", 0.003)
        pure_claude_cost = 0.003
        savings = ((pure_claude_cost - actual_cost) / pure_claude_cost) * 100

        print(f"Hybrid cascade:      ${actual_cost:.6f}")
        print(f"Pure Claude would be: ${pure_claude_cost:.6f}")
        print(f"Savings:              {savings:.1f}%")

    print()
    print("=" * 80)
    print("✅ Test complete")


if __name__ == "__main__":
    main()

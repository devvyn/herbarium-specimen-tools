#!/usr/bin/env python3
"""
Test script for confidence-based extraction routing.

Usage:
    python examples/test_confidence_routing.py path/to/specimen/image.jpg

Requirements:
    - OPENAI_API_KEY environment variable set
    - Image file with herbarium specimen
"""

import sys
from pathlib import Path

# Add src to path for local testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extraction import ConfidenceRouter


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_confidence_routing.py <image_path>")
        print("\nExample:")
        print("  python test_confidence_routing.py examples/sample_data/EXAMPLE-001.jpg")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    print("=" * 80)
    print("Confidence-Based Extraction Routing Test")
    print("=" * 80)
    print(f"Image: {image_path}")
    print()

    # Create router
    router = ConfidenceRouter(
        base_model="gpt-4o-mini",
        premium_model="gpt-4o",
        confidence_threshold=0.70,
        enable_routing=True,
    )

    print("Step 1: Extracting with gpt-4o-mini (fast, cheap)")
    print("-" * 80)

    # Extract with routing
    dwc_fields, confidences = router.extract_with_routing(image_path)

    if not dwc_fields:
        print("❌ Extraction failed - check OpenAI API key and image format")
        sys.exit(1)

    print(f"\n✅ Extracted {len(dwc_fields)} fields")
    print()

    # Display results
    print("Extracted Darwin Core Fields:")
    print("=" * 80)

    # Sort by confidence (lowest first to highlight re-extracted fields)
    sorted_fields = sorted(confidences.items(), key=lambda x: x[1])

    for field, confidence in sorted_fields:
        value = dwc_fields.get(field, "")
        confidence_indicator = "🔴" if confidence < 0.70 else "🟡" if confidence < 0.85 else "🟢"

        print(f"{confidence_indicator} {field:20s} [{confidence:.2f}]  {value[:60]}")

    # Show statistics
    print()
    print("Extraction Statistics:")
    print("=" * 80)
    stats = router.get_stats()
    print(f"Total extractions:        {stats['total_extractions']}")
    print(f"Fields re-extracted:      {stats['fields_re_extracted']}")
    print(f"Premium API calls:        {stats['premium_api_calls']}")
    print(f"Premium call rate:        {stats['premium_call_rate']}")
    print(f"Avg fields per re-extract: {stats['avg_fields_per_re_extraction']:.1f}")
    print()

    # Cost analysis
    if stats['premium_api_calls'] > 0:
        print("Cost Analysis:")
        print("=" * 80)
        print("With routing:")
        print(f"  Base model calls:    1 × $0.0004 = $0.0004")
        print(f"  Premium model calls: {stats['premium_api_calls']} × $0.0012 ≈ ${stats['premium_api_calls'] * 0.0012:.4f}")
        print(f"  Total:               ${0.0004 + stats['premium_api_calls'] * 0.0012:.4f}")
        print()
        print("Without routing (pure premium model):")
        print(f"  Premium model calls: 1 × $0.0012 = $0.0012")
        print()
        savings = 0.0012 - (0.0004 + stats['premium_api_calls'] * 0.0012)
        savings_pct = (savings / 0.0012) * 100
        print(f"Savings: ${savings:.4f} ({savings_pct:.1f}%)")
    else:
        print("💰 All fields high confidence - no premium model calls needed!")
        print("   Saved $0.0008 vs using premium model")

    print()
    print("=" * 80)
    print("✅ Test complete")


if __name__ == "__main__":
    main()

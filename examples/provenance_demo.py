#!/usr/bin/env python3
"""
Demonstration of comprehensive provenance tracking.

Shows exactly what provenance data is captured during extraction.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extraction.provenance import (
    create_provenance,
    estimate_extraction_cost,
    FieldProvenance,
)


def demo_provenance():
    """Demonstrate provenance tracking for a specimen extraction."""

    print("=" * 80)
    print("Provenance Tracking Demonstration")
    print("=" * 80)
    print()

    # Simulate extraction with confidence routing
    prov = create_provenance(
        image_path="SPECIMEN-001.jpg",
        specimen_id="SPECIMEN-001",
        extraction_strategy="confidence_routing",
    )

    print("Step 1: Base extraction with gpt-4o-mini")
    print("-" * 80)

    # Add fields from base extraction
    prov.add_field(
        field_name="catalogNumber",
        value="ABC-12345",
        confidence=0.95,
        model="gpt-4o-mini",
        provider="openai",
        extraction_method="direct_vision",
        processing_time_ms=1500,
        estimated_cost_usd=estimate_extraction_cost("gpt-4o-mini"),
    )

    prov.add_field(
        field_name="scientificName",
        value="Artemisia frigida",
        confidence=0.65,  # LOW CONFIDENCE - will trigger re-extraction
        model="gpt-4o-mini",
        provider="openai",
        extraction_method="direct_vision",
        processing_time_ms=1500,
        estimated_cost_usd=0.0,  # Already counted above
    )

    prov.add_field(
        field_name="eventDate",
        value="1975-07-15",
        confidence=0.92,
        model="gpt-4o-mini",
        provider="openai",
        extraction_method="direct_vision",
        processing_time_ms=1500,
        estimated_cost_usd=0.0,
    )

    prov.models_used = ["gpt-4o-mini"]
    prov.api_calls_made = 1

    print(f"✅ Extracted 3 fields")
    print(f"   catalogNumber: 0.95 confidence")
    print(f"   scientificName: 0.65 confidence ⚠️  (below 0.70 threshold)")
    print(f"   eventDate: 0.92 confidence")
    print()

    print("Step 2: Re-extract low-confidence field with gpt-4o")
    print("-" * 80)

    # Mark scientificName as re-extracted
    prov.mark_field_reextracted(
        field_name="scientificName",
        new_value="Artemisia frigida Willd.",  # Now includes authority
        new_confidence=0.89,  # Improved from 0.65
        new_model="gpt-4o",
        new_provider="openai",
        processing_time_ms=2000,
        estimated_cost_usd=estimate_extraction_cost("gpt-4o"),
    )

    prov.models_used.append("gpt-4o")
    prov.api_calls_made += 1

    print(f"✅ Re-extracted scientificName")
    print(f"   Original: 'Artemisia frigida' (0.65 confidence, gpt-4o-mini)")
    print(f"   Improved: 'Artemisia frigida Willd.' (0.89 confidence, gpt-4o)")
    print(f"   Improvement: +0.24 confidence")
    print()

    print("Step 3: GBIF validation")
    print("-" * 80)

    # Add validation provenance
    prov.add_validation(
        field_name="scientificName",
        validated=True,
        cache_hit=False,  # First time, API call
    )

    prov.validation_method = "gbif_pygbif"
    prov.validation_cache_hit = False
    prov.cache_hits = 0

    print(f"✅ Validated scientificName against GBIF")
    print(f"   Cache hit: No (API call made)")
    print()

    # Calculate totals
    prov.total_processing_time_ms = 1500 + 2000  # Base + re-extraction
    prov.total_estimated_cost_usd = estimate_extraction_cost(
        "gpt-4o-mini"
    ) + estimate_extraction_cost("gpt-4o")

    print("=" * 80)
    print("Complete Provenance Record")
    print("=" * 80)
    print()

    # Convert to JSON for display
    prov_dict = prov.to_dict()

    # Pretty print key sections
    print("Summary:")
    print(json.dumps(prov_dict["summary"], indent=2))
    print()

    print("Field Provenance (scientificName):")
    print(json.dumps(prov_dict["fields"]["scientificName"], indent=2))
    print()

    print("Full Provenance (JSON):")
    print(json.dumps(prov_dict, indent=2))
    print()

    print("=" * 80)
    print("What This Provenance Tells Us:")
    print("=" * 80)
    print()
    print("✅ Reproducibility: Exact models and prompts used")
    print("✅ Quality Tracking: Confidence scores + improvements")
    print("✅ Cost Accounting: Per-field and total costs")
    print("✅ Performance: Processing time per operation")
    print("✅ Validation: GBIF cache hits vs API calls")
    print("✅ Re-extraction: Which fields improved and by how much")
    print("✅ Version Control: Code version (git hash) recorded")
    print()

    print("Scientific Value:")
    print("-" * 80)
    print("- Know which fields are AI-derived vs OCR")
    print("- Trace quality improvements through pipeline")
    print("- Validate costs for grant reporting")
    print("- Reproduce exact extraction conditions")
    print("- Identify which models work best for which fields")
    print()


if __name__ == "__main__":
    demo_provenance()

#!/usr/bin/env python3
"""
Test script for enhanced data lifecycle tracking.

Demonstrates:
1. Raw vs corrected data distinction
2. Export tracking
3. Change attribution (who/when/why)
4. Modified-after-export detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from review.engine import SpecimenReview, ReviewStatus


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():
    print_section("Enhanced Data Lifecycle Tracking Demo")

    # Create a specimen review with raw AI extraction
    print("\n1. Creating specimen with raw AI extraction...")

    raw_data = {
        "catalogNumber": "AAFC-12345",
        "scientificName": "Setaria Viridis",  # Wrong capitalization
        "eventDate": "1988",
        "country": "Canada",
        "stateProvince": "Saskatchewan",
        "locality": "iield Habitat",  # OCR error: "iield" instead of "field"
    }

    review = SpecimenReview(
        specimen_id="specimen_001",
        dwc_fields=raw_data.copy(),
        raw_extraction=raw_data.copy(),
        extraction_timestamp="2025-12-03T10:00:00Z",
        model="gpt-4o-mini",
        provider="openai",
    )

    print(f"   Raw extraction fields: {len(review.raw_extraction)}")
    print(f"   Export status: {review.export_status}")
    print(f"   Has corrections: {review.has_corrections()}")

    # Show raw vs corrected distinction
    print_section("2. Correcting Fields (with Audit Trail)")

    print("\n   Correcting scientificName (capitalization)...")
    review.apply_correction(
        field="scientificName",
        new_value="Setaria viridis",
        corrected_by="curator_alice",
        reason="Corrected genus capitalization"
    )

    print("\n   Correcting locality (OCR error)...")
    review.apply_correction(
        field="locality",
        new_value="Field Habitat",
        corrected_by="curator_alice",
        reason="Fixed OCR error: iield -> Field"
    )

    print(f"\n   ✅ Corrected fields: {review.get_corrected_fields()}")
    print(f"   ✅ Uncorrected fields: {review.get_uncorrected_fields()}")
    print(f"   ✅ Has corrections: {review.has_corrections()}")

    # Show correction metadata
    print("\n   Correction audit trail:")
    for field, correction in review.corrections.items():
        print(f"\n   Field: {field}")
        print(f"     Original: {correction['original_value']}")
        print(f"     Corrected: {correction['value']}")
        print(f"     By: {correction['corrected_by']}")
        print(f"     At: {correction['corrected_at']}")
        print(f"     Was AI extracted: {correction['was_ai_extracted']}")
        print(f"     Reason: {correction['reason']}")

    # Test export tracking
    print_section("3. Export Tracking")

    print(f"\n   Before export:")
    print(f"     Export status: {review.export_status}")
    print(f"     Needs export: {review.needs_export()}")
    print(f"     Export count: {review.export_count}")

    print("\n   Exporting to GBIF...")
    review.mark_exported(
        export_format="DwC-A",
        destination="GBIF portal",
        exported_by="export_bot"
    )

    print(f"\n   After export:")
    print(f"     Export status: {review.export_status}")
    print(f"     Needs export: {review.needs_export()}")
    print(f"     Export count: {review.export_count}")
    print(f"     Last export: {review.last_export_timestamp}")

    # Test modified-after-export detection
    print_section("4. Modified-After-Export Detection")

    print(f"\n   Current status: {review.export_status}")

    print("\n   Making another correction after export...")
    review.apply_correction(
        field="scientificName",
        new_value="Setaria viridis (L.) Beauv.",
        corrected_by="supervisor_bob",
        reason="Added authority"
    )

    print(f"\n   After modification:")
    print(f"     Export status: {review.export_status}")
    print(f"     Needs export: {review.needs_export()}")
    print(f"     ⚠️  Specimen was modified after export!")

    # Show export history
    print("\n   Export history:")
    for i, export in enumerate(review.export_history, 1):
        print(f"\n   Export #{i}:")
        print(f"     Timestamp: {export['export_timestamp']}")
        print(f"     Format: {export['export_format']}")
        print(f"     Destination: {export['destination']}")
        print(f"     Exported by: {export['exported_by']}")
        print(f"     Corrections at export: {export['corrections_count']}")

    # Show complete lifecycle data
    print_section("5. Complete Lifecycle Data")

    lifecycle = review.to_dict()["lifecycle"]

    print(f"\n   Raw extraction (immutable original):")
    print(f"     {lifecycle['raw_extraction']}")

    print(f"\n   Current data (includes corrections):")
    print(f"     {review.dwc_fields}")

    print(f"\n   Lifecycle summary:")
    print(f"     Has corrections: {lifecycle['has_corrections']}")
    print(f"     Corrected fields: {lifecycle['corrected_fields']}")
    print(f"     Uncorrected fields: {lifecycle['uncorrected_fields']}")
    print(f"     Export status: {lifecycle['export_status']}")
    print(f"     Export count: {lifecycle['export_count']}")
    print(f"     Needs export: {lifecycle['needs_export']}")

    # Test re-export
    print_section("6. Re-Export After Modifications")

    print("\n   Re-exporting updated specimen...")
    review.mark_exported(
        export_format="CSV",
        destination="S3 bucket",
        exported_by="curator_alice"
    )

    print(f"\n   After re-export:")
    print(f"     Export status: {review.export_status}")
    print(f"     Export count: {review.export_count}")
    print(f"     Needs export: {review.needs_export()}")

    print("\n   Export history now has {len(review.export_history)} entries:")
    for i, export in enumerate(review.export_history, 1):
        print(f"     #{i}: {export['export_format']} to {export['destination']} ({export['corrections_count']} corrections)")

    # Query examples
    print_section("7. Query Examples (What You Can Now Answer)")

    print("\n   Q: Show me all specimens with uncorrected fields")
    if review.get_uncorrected_fields():
        print(f"     ✅ This specimen has {len(review.get_uncorrected_fields())} uncorrected fields:")
        print(f"        {review.get_uncorrected_fields()}")
    else:
        print(f"     This specimen has no uncorrected fields")

    print("\n   Q: What percentage of AI extractions required correction?")
    total_fields = len(review.raw_extraction)
    corrected_fields = len(review.get_corrected_fields())
    correction_rate = (corrected_fields / total_fields * 100) if total_fields > 0 else 0
    print(f"     ✅ {corrected_fields}/{total_fields} fields corrected ({correction_rate:.1f}%)")

    print("\n   Q: Has this specimen been exported to GBIF?")
    gbif_exports = [e for e in review.export_history if "GBIF" in e['destination']]
    if gbif_exports:
        print(f"     ✅ Yes, exported on {gbif_exports[0]['export_timestamp']}")
    else:
        print(f"     No GBIF exports found")

    print("\n   Q: Which specimens changed since last export?")
    if review.export_status == "modified_after_export":
        print(f"     ✅ This specimen was modified after export")
        last_export = review.export_history[-1] if review.export_history else None
        if last_export:
            corrections_since = len(review.corrections) - last_export['corrections_count']
            print(f"        {corrections_since} new correction(s) since last export")
    else:
        print(f"     This specimen has not been modified since last export")

    print("\n   Q: Who corrected this field and why?")
    field = "scientificName"
    if field in review.corrections:
        c = review.corrections[field]
        print(f"     ✅ Field '{field}' corrected by {c['corrected_by']}")
        print(f"        From: {c['original_value']}")
        print(f"        To: {c['value']}")
        print(f"        When: {c['corrected_at']}")
        print(f"        Why: {c['reason']}")

    print_section("✅ Demo Complete!")
    print("\nEnhanced data lifecycle tracking is now operational.")
    print("All specimen corrections, exports, and modifications are fully auditable.")


if __name__ == "__main__":
    main()

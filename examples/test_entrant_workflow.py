#!/usr/bin/env python3
"""
Test script for entrant approval workflow.

Demonstrates the complete multi-stage review process:
1. Curator corrections
2. Submit for entrant review
3. Entrant approval/rejection
4. Supervisor final approval
5. Export readiness
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from review.engine import SpecimenReview, ReviewStatus, ReviewPriority


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_status(review: SpecimenReview):
    """Print current workflow status."""
    print(f"\n   Status: {review.status.name}")
    print(f"   Assigned to: {review.assigned_to or 'Not assigned'}")
    print(f"   Reviewed by: {review.reviewed_by or 'Not reviewed'}")
    print(f"   Entrant approved: {review.entrant_approved}")
    print(f"   Can export: {review.can_export()}")


def main():
    print_section("Entrant Approval Workflow Demo")

    # Create specimen with initial AI extraction
    print("\n1. Creating specimen with raw AI extraction...")

    raw_data = {
        "catalogNumber": "AAFC-12345",
        "scientificName": "Setaria Viridis",  # Wrong capitalization
        "eventDate": "1988",
        "country": "Canada",
        "stateProvince": "Saskatchewan",
        "locality": "iield Habitat",  # OCR error
    }

    review = SpecimenReview(
        specimen_id="specimen_001",
        dwc_fields=raw_data.copy(),
        raw_extraction=raw_data.copy(),
        extraction_timestamp="2025-12-03T10:00:00Z",
        model="gpt-4o-mini",
        provider="openai",
        status=ReviewStatus.PENDING,
    )

    print_status(review)

    # Curator starts review
    print_section("2. Curator Review & Corrections")

    print("\n   Curator 'alice' starts reviewing...")
    review.status = ReviewStatus.IN_REVIEW
    review.reviewed_by = "curator_alice"

    print("\n   Making corrections...")
    review.apply_correction(
        field="scientificName",
        new_value="Setaria viridis",
        corrected_by="curator_alice",
        reason="Fixed capitalization"
    )

    review.apply_correction(
        field="locality",
        new_value="Field Habitat",
        corrected_by="curator_alice",
        reason="Fixed OCR error: iield -> Field"
    )

    print(f"   ✅ Corrected {len(review.get_corrected_fields())} fields")
    print_status(review)

    # Submit for entrant review
    print_section("3. Submit for Entrant Review")

    print("\n   Curator submits corrected draft...")
    review.submit_for_entrant_review(curator_username="curator_alice")

    print(f"   ✅ Status changed to: {review.status.name}")
    print_status(review)

    # Assign to entrant
    print_section("4. Assign to Data Entrant")

    print("\n   Supervisor assigns to entrant 'bob'...")
    review.assign_to_entrant(
        entrant_username="entrant_bob",
        assigned_by="supervisor_charlie"
    )

    print(f"   ✅ Assigned to: {review.assigned_to}")
    print(f"   ✅ Status changed to: {review.status.name}")
    print_status(review)

    # Scenario A: Entrant Approval Path
    print_section("5a. Entrant Approval (Happy Path)")

    review_approved = SpecimenReview(
        specimen_id="specimen_002",
        dwc_fields=raw_data.copy(),
        raw_extraction=raw_data.copy(),
        status=ReviewStatus.ENTRANT_REVIEW,
        assigned_to="entrant_bob",
    )

    print("\n   Entrant 'bob' reviews and approves...")
    review_approved.entrant_approve(
        entrant_username="entrant_bob",
        notes="Corrections look good, approved!"
    )

    print(f"   ✅ Status: {review_approved.status.name}")
    print(f"   ✅ Approved by: {review_approved.entrant_reviewed_by}")
    print(f"   ✅ Notes: {review_approved.entrant_notes}")
    print_status(review_approved)

    # Scenario B: Entrant Rejection Path
    print_section("5b. Entrant Rejection (Needs Correction)")

    review_rejected = SpecimenReview(
        specimen_id="specimen_003",
        dwc_fields=raw_data.copy(),
        raw_extraction=raw_data.copy(),
        status=ReviewStatus.ENTRANT_REVIEW,
        assigned_to="entrant_bob",
    )

    print("\n   Entrant 'bob' finds issues and rejects...")
    review_rejected.entrant_reject(
        entrant_username="entrant_bob",
        notes="Scientific name needs authority, locality is vague"
    )

    print(f"   ❌ Status: {review_rejected.status.name}")
    print(f"   ❌ Rejected by: {review_rejected.entrant_reviewed_by}")
    print(f"   ❌ Reason: {review_rejected.entrant_notes}")
    print_status(review_rejected)

    # Rework after rejection
    print_section("6. Rework After Rejection")

    print("\n   Curator 'alice' addresses entrant feedback...")
    review_rejected.apply_correction(
        field="scientificName",
        new_value="Setaria viridis (L.) Beauv.",
        corrected_by="curator_alice",
        reason="Added authority per entrant feedback"
    )

    review_rejected.apply_correction(
        field="locality",
        new_value="Field Habitat, 18NW-17-18W",
        corrected_by="curator_alice",
        reason="Added specific location per entrant feedback"
    )

    print(f"   ✅ Made {len(review_rejected.get_corrected_fields())} corrections")

    print("\n   Resubmitting for entrant review...")
    review_rejected.submit_for_entrant_review(curator_username="curator_alice")
    review_rejected.assign_to_entrant(
        entrant_username="entrant_bob",
        assigned_by="curator_alice"
    )

    print(f"   ✅ Status: {review_rejected.status.name}")
    print_status(review_rejected)

    # Final supervisor approval
    print_section("7. Supervisor Final Approval")

    print("\n   Continuing with approved specimen...")
    print(f"   Current status: {review_approved.status.name}")

    print("\n   Supervisor 'charlie' performs final approval...")
    review_approved.supervisor_approve(supervisor_username="supervisor_charlie")

    print(f"   ✅ Status: {review_approved.status.name}")
    print(f"   ✅ Approved by: {review_approved.supervisor_approved_by}")
    print(f"   ✅ Can export: {review_approved.can_export()}")
    print_status(review_approved)

    # Export tracking
    print_section("8. Export Process")

    print(f"\n   Before export:")
    print(f"     Can export: {review_approved.can_export()}")
    print(f"     Export status: {review_approved.export_status}")

    print("\n   Exporting to GBIF...")
    review_approved.mark_exported(
        export_format="DwC-A",
        destination="GBIF portal",
        exported_by="export_bot"
    )

    print(f"\n   After export:")
    print(f"     Export status: {review_approved.export_status}")
    print(f"     Export count: {review_approved.export_count}")
    print(f"     Status: {review_approved.status.name}")

    # Complete workflow visualization
    print_section("9. Complete Workflow States")

    print("""
   Workflow State Machine:

   PENDING
      ↓ (curator starts review)
   IN_REVIEW
      ↓ (curator makes corrections)
   DRAFT_CORRECTED
      ↓ (assign to entrant)
   ENTRANT_REVIEW
      ↓ (entrant reviews)
      ├─→ ENTRANT_APPROVED (if approved)
      │      ↓ (supervisor approves)
      │   READY_FOR_EXPORT
      │      ↓ (export process)
      │   EXPORTED
      │
      └─→ NEEDS_CORRECTION (if rejected)
             ↓ (curator fixes)
          DRAFT_CORRECTED (cycle back)
   """)

    # Show complete data structure
    print_section("10. Complete Workflow Data")

    workflow_data = review_approved.to_dict()["entrant_workflow"]

    print(f"\n   Workflow tracking:")
    print(f"     Assigned to: {workflow_data['assigned_to']}")
    print(f"     Entrant reviewed by: {workflow_data['entrant_reviewed_by']}")
    print(f"     Entrant approved: {workflow_data['entrant_approved']}")
    print(f"     Entrant notes: {workflow_data['entrant_notes']}")
    print(f"     Supervisor approved by: {workflow_data['supervisor_approved_by']}")
    print(f"     Can export: {workflow_data['can_export']}")

    # Query examples
    print_section("11. Workflow Query Examples")

    print("\n   Q: Which specimens are assigned to entrant 'bob'?")
    # In real usage: engine.get_assigned_specimens("entrant_bob")
    if review.assigned_to == "entrant_bob":
        print(f"     ✅ {review.specimen_id} is assigned to entrant_bob")

    print("\n   Q: Which specimens are ready for export?")
    if review_approved.can_export():
        print(f"     ✅ {review_approved.specimen_id} is ready for export")

    print("\n   Q: Has the entrant approved this specimen?")
    if review_approved.entrant_approved:
        print(f"     ✅ Yes, approved by {review_approved.entrant_reviewed_by}")
        print(f"        on {review_approved.entrant_reviewed_at}")

    print("\n   Q: What was the entrant's feedback?")
    if review_rejected.entrant_notes:
        print(f"     ✅ Entrant notes: {review_rejected.entrant_notes}")

    print("\n   Q: Who gave final approval?")
    if review_approved.supervisor_approved_by:
        print(f"     ✅ Supervisor: {review_approved.supervisor_approved_by}")
        print(f"        on {review_approved.supervisor_approved_at}")

    # Role-based access examples
    print_section("12. Role-Based Workflow")

    print("""
   Roles and Permissions:

   CURATOR (alice):
     - Review specimens (IN_REVIEW)
     - Make corrections (apply_correction)
     - Submit for entrant review (DRAFT_CORRECTED)
     - Cannot approve for export

   DATA ENTRANT (bob):
     - Review assigned specimens (ENTRANT_REVIEW)
     - Approve corrections (ENTRANT_APPROVED)
     - Reject and request changes (NEEDS_CORRECTION)
     - Cannot make corrections themselves

   SUPERVISOR (charlie):
     - Assign specimens to entrants
     - Final approval for export (READY_FOR_EXPORT)
     - Can override decisions

   EXPORT BOT:
     - Only exports READY_FOR_EXPORT specimens
     - Records export history
    """)

    print_section("✅ Demo Complete!")
    print("\nEntrant approval workflow is now fully operational.")
    print("Multi-stage collaborative review process implemented successfully.")


if __name__ == "__main__":
    main()

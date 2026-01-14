"""
Review Engine for Extracted Specimen Data

Loads extraction results, applies GBIF validation, and provides
prioritized review queue for manual curation.

Features:
- Load results from raw.jsonl
- Apply GBIF taxonomy + locality validation
- Calculate quality scores per specimen
- Prioritize review queue (lowest quality first)
- Track review/approval status
"""

import json
import logging
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review status for specimens (mutually exclusive lifecycle)."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    NEEDS_CORRECTION = "needs_correction"
    DRAFT_CORRECTED = "draft_corrected"        # Curator corrected, ready for entrant
    ENTRANT_REVIEW = "entrant_review"          # Assigned to data entrant
    ENTRANT_APPROVED = "entrant_approved"      # Entrant approved corrections
    READY_FOR_EXPORT = "ready_for_export"      # Final pre-export state
    EXPORTED = "exported"                      # Successfully exported
    APPROVED = "approved"                      # Legacy/generic approval
    REJECTED = "rejected"


class ReviewPriority(Enum):
    """Priority levels for review queue."""

    CRITICAL = 1  # Major issues, requires immediate attention
    HIGH = 2  # Multiple issues or low confidence
    MEDIUM = 3  # Some issues but mostly complete
    LOW = 4  # Minor issues only
    MINIMAL = 5  # High quality, minimal review needed


@dataclass
class SpecimenReview:
    """Complete review record for a single specimen."""

    # Identity
    specimen_id: str
    sha256_hash: str | None = None

    # Extraction data
    dwc_fields: dict = dataclass_field(default_factory=dict)
    extraction_timestamp: str | None = None
    model: str | None = None
    provider: str | None = None
    extraction_method: str | None = None
    ocr_engine: str | None = None
    converted_from_csv: bool = False
    provenance_history: list[dict] = dataclass_field(default_factory=list)

    # Raw extraction (immutable original AI output)
    raw_extraction: dict | None = None  # Set once at creation, never modified

    # GBIF validation
    gbif_taxonomy_verified: bool = False
    gbif_taxonomy_confidence: float = 0.0
    gbif_taxonomy_issues: list[str] = dataclass_field(default_factory=list)
    gbif_locality_verified: bool = False
    gbif_locality_issues: list[str] = dataclass_field(default_factory=list)

    # Quality metrics
    completeness_score: float = 0.0  # 0-100%
    confidence_score: float = 0.0  # 0-100%
    quality_score: float = 0.0  # Combined metric
    priority: ReviewPriority = ReviewPriority.MEDIUM

    # Review tracking
    status: ReviewStatus = ReviewStatus.PENDING
    flagged: bool = False  # Independent attention marker
    reextraction_requested: bool = False  # Request re-extraction with different params
    reextraction_regions: list[dict] = dataclass_field(default_factory=list)  # Specific regions to re-extract
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    corrections: dict = dataclass_field(default_factory=dict)
    notes: str | None = None  # General notes (exported with DwC data)
    review_notes: str | None = None  # Workflow feedback (not exported)

    # Entrant workflow tracking
    assigned_to: str | None = None  # Data entrant assigned to review
    entrant_reviewed_by: str | None = None  # Who performed entrant review
    entrant_reviewed_at: str | None = None
    entrant_approved: bool = False  # Did entrant approve?
    entrant_notes: str | None = None
    supervisor_approved_by: str | None = None  # Final supervisor approval
    supervisor_approved_at: str | None = None

    # Issues
    critical_issues: list[str] = dataclass_field(default_factory=list)
    warnings: list[str] = dataclass_field(default_factory=list)

    # Export tracking
    export_status: str = "not_exported"  # "not_exported", "exported", "modified_after_export"
    last_export_timestamp: str | None = None
    export_count: int = 0
    export_history: list[dict] = dataclass_field(default_factory=list)

    def calculate_quality_score(self):
        """Calculate overall quality score from components."""
        # Weighted combination of completeness and confidence
        self.quality_score = (self.completeness_score * 0.6) + (self.confidence_score * 0.4)

    def determine_priority(self):
        """Determine review priority based on quality and issues."""
        # Critical priority if major issues
        if self.critical_issues or not self.dwc_fields:
            self.priority = ReviewPriority.CRITICAL
        # High priority if low quality or GBIF issues
        elif self.quality_score < 50 or self.gbif_taxonomy_issues or self.gbif_locality_issues:
            self.priority = ReviewPriority.HIGH
        # Medium priority if moderate quality
        elif self.quality_score < 75:
            self.priority = ReviewPriority.MEDIUM
        # Low priority if good quality but some warnings
        elif self.warnings:
            self.priority = ReviewPriority.LOW
        # Minimal priority if excellent quality
        else:
            self.priority = ReviewPriority.MINIMAL

    def apply_correction(
        self, field: str, new_value: str, corrected_by: str, reason: str | None = None
    ):
        """
        Apply a correction to a field with full audit trail.

        Args:
            field: Darwin Core field name
            new_value: Corrected value
            corrected_by: Username of person making correction
            reason: Optional reason for correction
        """
        # Store correction with metadata
        self.corrections[field] = {
            "value": new_value,
            "corrected_by": corrected_by,
            "corrected_at": datetime.utcnow().isoformat() + "Z",
            "original_value": self.dwc_fields.get(field),
            "was_ai_extracted": (
                field in self.raw_extraction if self.raw_extraction else False
            ),
            "reason": reason,
        }

        # Update main fields
        self.dwc_fields[field] = new_value

        # Mark as needing re-export if previously exported
        if self.export_status == "exported":
            self.export_status = "modified_after_export"

    def mark_exported(self, export_format: str, destination: str, exported_by: str):
        """
        Mark specimen as exported and record export metadata.

        Args:
            export_format: Export format (e.g., "DwC-A", "CSV", "GBIF")
            destination: Export destination (e.g., "S3", "local", "GBIF portal")
            exported_by: Username of person performing export
        """
        export_record = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "export_format": export_format,
            "destination": destination,
            "exported_by": exported_by,
            "data_snapshot": self.dwc_fields.copy(),
            "corrections_count": len(self.corrections),
        }

        self.export_history.append(export_record)
        self.export_status = "exported"
        self.last_export_timestamp = export_record["export_timestamp"]
        self.export_count += 1

    def get_corrected_fields(self) -> list[str]:
        """Get list of field names that have been corrected."""
        return list(self.corrections.keys())

    def get_uncorrected_fields(self) -> list[str]:
        """Get list of field names that are still raw AI output."""
        if not self.raw_extraction:
            return []
        return [f for f in self.raw_extraction.keys() if f not in self.corrections]

    def has_corrections(self) -> bool:
        """Check if any fields have been corrected."""
        return len(self.corrections) > 0

    def needs_export(self) -> bool:
        """Check if specimen needs to be exported."""
        return self.export_status in ["not_exported", "modified_after_export"]

    def assign_to_entrant(self, entrant_username: str, assigned_by: str):
        """
        Assign specimen to data entrant for review.

        Args:
            entrant_username: Username of data entrant
            assigned_by: Username of curator/supervisor making assignment
        """
        self.assigned_to = entrant_username
        self.status = ReviewStatus.ENTRANT_REVIEW
        self.reviewed_by = assigned_by
        self.reviewed_at = datetime.utcnow().isoformat() + "Z"

    def entrant_approve(self, entrant_username: str, notes: str | None = None):
        """
        Mark specimen as approved by data entrant.

        Args:
            entrant_username: Username of approving entrant
            notes: Optional approval notes
        """
        self.entrant_reviewed_by = entrant_username
        self.entrant_reviewed_at = datetime.utcnow().isoformat() + "Z"
        self.entrant_approved = True
        self.entrant_notes = notes
        self.status = ReviewStatus.ENTRANT_APPROVED

    def entrant_reject(self, entrant_username: str, notes: str):
        """
        Mark specimen as rejected by data entrant.

        Args:
            entrant_username: Username of rejecting entrant
            notes: Required rejection reason
        """
        self.entrant_reviewed_by = entrant_username
        self.entrant_reviewed_at = datetime.utcnow().isoformat() + "Z"
        self.entrant_approved = False
        self.entrant_notes = notes
        self.status = ReviewStatus.NEEDS_CORRECTION

    def supervisor_approve(self, supervisor_username: str):
        """
        Final supervisor approval - mark as ready for export.

        Args:
            supervisor_username: Username of approving supervisor
        """
        self.supervisor_approved_by = supervisor_username
        self.supervisor_approved_at = datetime.utcnow().isoformat() + "Z"
        self.status = ReviewStatus.READY_FOR_EXPORT

    def submit_for_entrant_review(self, curator_username: str):
        """
        Submit corrected draft for entrant review.

        Args:
            curator_username: Username of curator submitting
        """
        self.reviewed_by = curator_username
        self.reviewed_at = datetime.utcnow().isoformat() + "Z"
        self.status = ReviewStatus.DRAFT_CORRECTED

    def can_export(self) -> bool:
        """Check if specimen is ready for export."""
        return self.status == ReviewStatus.READY_FOR_EXPORT

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "specimen_id": self.specimen_id,
            "sha256_hash": self.sha256_hash,
            "dwc_fields": self.dwc_fields,
            "extraction_timestamp": self.extraction_timestamp,
            "model": self.model,
            "provider": self.provider,
            "extraction_method": self.extraction_method,
            "ocr_engine": self.ocr_engine,
            "converted_from_csv": self.converted_from_csv,
            "provenance_history": self.provenance_history,
            "provenance": {
                "model": self.model,
                "provider": self.provider,
                "extraction_timestamp": self.extraction_timestamp,
                "extraction_method": self.extraction_method,
                "ocr_engine": self.ocr_engine,
                "converted_from_csv": self.converted_from_csv,
                "history": self.provenance_history,
                "sha256": self.sha256_hash,
            },
            "gbif_validation": {
                "taxonomy_verified": self.gbif_taxonomy_verified,
                "taxonomy_confidence": self.gbif_taxonomy_confidence,
                "taxonomy_issues": self.gbif_taxonomy_issues,
                "locality_verified": self.gbif_locality_verified,
                "locality_issues": self.gbif_locality_issues,
            },
            "quality": {
                "completeness_score": self.completeness_score,
                "confidence_score": self.confidence_score,
                "quality_score": self.quality_score,
                "priority": self.priority.name,
            },
            "review": {
                "status": self.status.name,
                "flagged": self.flagged,
                "reviewed_by": self.reviewed_by,
                "reviewed_at": self.reviewed_at,
                "corrections": self.corrections,
                "notes": self.notes,
            },
            "entrant_workflow": {
                "assigned_to": self.assigned_to,
                "entrant_reviewed_by": self.entrant_reviewed_by,
                "entrant_reviewed_at": self.entrant_reviewed_at,
                "entrant_approved": self.entrant_approved,
                "entrant_notes": self.entrant_notes,
                "supervisor_approved_by": self.supervisor_approved_by,
                "supervisor_approved_at": self.supervisor_approved_at,
                "can_export": self.can_export(),
            },
            "issues": {
                "critical": self.critical_issues,
                "warnings": self.warnings,
            },
            "lifecycle": {
                "raw_extraction": self.raw_extraction,
                "has_corrections": self.has_corrections(),
                "corrected_fields": self.get_corrected_fields(),
                "uncorrected_fields": self.get_uncorrected_fields(),
                "export_status": self.export_status,
                "last_export_timestamp": self.last_export_timestamp,
                "export_count": self.export_count,
                "export_history": self.export_history,
                "needs_export": self.needs_export(),
            },
        }


class ReviewEngine:
    """
    Engine for managing specimen review workflow.

    Loads extraction results, validates with GBIF, and provides
    prioritized review queue.
    """

    # Required Darwin Core fields for GBIF publication
    REQUIRED_FIELDS = [
        "catalogNumber",
        "scientificName",
        "eventDate",
        "recordedBy",
        "country",
        "stateProvince",
        "locality",
    ]

    def __init__(self, gbif_validator=None):
        """
        Initialize review engine.

        Args:
            gbif_validator: Optional GBIFValidator instance
        """
        self.gbif_validator = gbif_validator
        self.reviews: dict[str, SpecimenReview] = {}

        logger.info("Review engine initialized")

    def load_extraction_results(self, results_file: Path) -> int:
        """
        Load extraction results from raw.jsonl file.

        Args:
            results_file: Path to raw.jsonl

        Returns:
            Number of specimens loaded
        """
        logger.info(f"Loading extraction results from {results_file}")

        count = 0
        with open(results_file) as f:
            for line in f:
                result = json.loads(line)

                # Extract specimen info
                specimen_id = result.get("image", "unknown")
                dwc_fields = result.get("dwc", {})

                if not dwc_fields:
                    # Failed extraction
                    review = SpecimenReview(
                        specimen_id=specimen_id,
                        extraction_timestamp=result.get("timestamp"),
                        model=result.get("model"),
                        provider=result.get("provider"),
                        extraction_method=result.get("extraction_method"),
                        ocr_engine=result.get("ocr_engine"),
                        converted_from_csv=bool(result.get("converted_from_csv", False)),
                        provenance_history=result.get(
                            "provenance_history", result.get("lineage", [])
                        ),
                        critical_issues=[result.get("error", "No data extracted")],
                    )
                else:
                    review = SpecimenReview(
                        specimen_id=specimen_id,
                        dwc_fields=dwc_fields,
                        extraction_timestamp=result.get("timestamp"),
                        model=result.get("model"),
                        provider=result.get("provider"),
                        extraction_method=result.get("extraction_method"),
                        ocr_engine=result.get("ocr_engine"),
                        converted_from_csv=bool(result.get("converted_from_csv", False)),
                        provenance_history=result.get(
                            "provenance_history", result.get("lineage", [])
                        ),
                        raw_extraction=dwc_fields.copy(),  # Store immutable copy of original
                    )

                    # Calculate metrics
                    self._calculate_completeness(review)
                    self._calculate_confidence(review)
                    self._identify_issues(review)

                    # Apply GBIF validation if available
                    if self.gbif_validator:
                        self._apply_gbif_validation(review)

                    # Calculate overall quality and priority
                    review.calculate_quality_score()
                    review.determine_priority()

                self.reviews[specimen_id] = review
                count += 1

        logger.info(f"Loaded {count} specimens for review")
        return count

    def _calculate_completeness(self, review: SpecimenReview):
        """Calculate completeness score based on required fields."""
        present = 0
        for field in self.REQUIRED_FIELDS:
            field_data = review.dwc_fields.get(field, {})
            if isinstance(field_data, dict):
                value = field_data.get("value")
            else:
                value = field_data

            if value and str(value).strip():
                present += 1

        review.completeness_score = (present / len(self.REQUIRED_FIELDS)) * 100

    def _calculate_confidence(self, review: SpecimenReview):
        """Calculate average confidence across all fields."""
        confidences = []

        for _field, field_data in review.dwc_fields.items():
            if isinstance(field_data, dict):
                conf = field_data.get("confidence", 0.0)
                if conf > 0:
                    confidences.append(conf)

        if confidences:
            review.confidence_score = sum(confidences) / len(confidences)
        else:
            review.confidence_score = 0.0

    def _identify_issues(self, review: SpecimenReview):
        """Identify critical issues and warnings."""
        # Check for missing required fields
        for field in self.REQUIRED_FIELDS:
            field_data = review.dwc_fields.get(field, {})
            if isinstance(field_data, dict):
                value = field_data.get("value")
            else:
                value = field_data

            if not value or not str(value).strip():
                review.critical_issues.append(f"Missing required field: {field}")

        # Check for low confidence fields
        for field, field_data in review.dwc_fields.items():
            if isinstance(field_data, dict):
                conf = field_data.get("confidence", 0.0)
                value = field_data.get("value")

                if value and conf < 0.5:  # Confidence threshold
                    review.warnings.append(f"Low confidence for {field}: {conf:.2f}")

    def _apply_gbif_validation(self, review: SpecimenReview):
        """Apply GBIF validation to specimen record."""
        if not self.gbif_validator:
            return

        # Prepare record for GBIF validation
        dwc_record = {}
        for field, field_data in review.dwc_fields.items():
            if isinstance(field_data, dict):
                dwc_record[field] = field_data.get("value", "")
            else:
                dwc_record[field] = field_data

        try:
            # Validate taxonomy
            if dwc_record.get("scientificName"):
                _, tax_metadata = self.gbif_validator.verify_taxonomy(dwc_record)
                review.gbif_taxonomy_verified = tax_metadata.get("gbif_taxonomy_verified", False)
                review.gbif_taxonomy_confidence = tax_metadata.get("gbif_confidence", 0.0)
                review.gbif_taxonomy_issues = tax_metadata.get("gbif_issues", [])

            # Validate locality
            if dwc_record.get("decimalLatitude") and dwc_record.get("decimalLongitude"):
                _, loc_metadata = self.gbif_validator.verify_locality(dwc_record)
                review.gbif_locality_verified = loc_metadata.get("gbif_locality_verified", False)
                review.gbif_locality_issues = loc_metadata.get("gbif_issues", [])

        except Exception as e:
            logger.warning(f"GBIF validation error for {review.specimen_id}: {e}")
            review.warnings.append(f"GBIF validation error: {str(e)}")

    def get_review_queue(
        self,
        status: ReviewStatus | None = None,
        priority: ReviewPriority | None = None,
        flagged_only: bool = False,
        sort_by: str = "priority",
    ) -> list[SpecimenReview]:
        """
        Get prioritized review queue with orthogonal filtering.

        Args:
            status: Filter by review status (mutually exclusive lifecycle)
            priority: Filter by priority level (independent quality metric)
            flagged_only: Show only flagged specimens (independent attention marker)
            sort_by: Sort field ("priority", "quality", "completeness")

        Returns:
            Sorted list of SpecimenReview objects
        """
        reviews = list(self.reviews.values())

        # Apply orthogonal filters
        if status:
            reviews = [r for r in reviews if r.status == status]

        if priority:
            reviews = [r for r in reviews if r.priority == priority]

        if flagged_only:
            reviews = [r for r in reviews if r.flagged]

        # Sort
        if sort_by == "priority":
            reviews.sort(key=lambda r: r.priority.value)
        elif sort_by == "quality":
            reviews.sort(key=lambda r: r.quality_score)
        elif sort_by == "completeness":
            reviews.sort(key=lambda r: r.completeness_score)

        return reviews

    def get_review(self, specimen_id: str) -> SpecimenReview | None:
        """Get review record for a specific specimen."""
        return self.reviews.get(specimen_id)

    def update_review(
        self,
        specimen_id: str,
        corrections: dict | None = None,
        status: ReviewStatus | None = None,
        flagged: bool | None = None,
        reviewed_by: str | None = None,
        notes: str | None = None,
    ):
        """
        Update review record.

        Args:
            specimen_id: Specimen identifier
            corrections: Field corrections
            status: New review status
            flagged: Flag for curator attention
            reviewed_by: Reviewer identifier
            notes: Review notes
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        if corrections:
            # Apply corrections with full audit trail
            for field, value in corrections.items():
                # Handle both simple string values and correction metadata
                if isinstance(value, dict) and "value" in value:
                    review.apply_correction(
                        field=field,
                        new_value=value["value"],
                        corrected_by=reviewed_by or "unknown",
                        reason=value.get("reason")
                    )
                else:
                    review.apply_correction(
                        field=field,
                        new_value=value,
                        corrected_by=reviewed_by or "unknown"
                    )

        if status:
            review.status = status

        if flagged is not None:
            review.flagged = flagged

        if reviewed_by:
            review.reviewed_by = reviewed_by

        if notes:
            review.notes = notes

        review.reviewed_at = datetime.now().isoformat()

        logger.info(
            f"Updated review: {specimen_id} (status: {review.status.name}, flagged: {review.flagged})"
        )

    def assign_to_entrant(self, specimen_id: str, entrant_username: str, assigned_by: str):
        """
        Assign specimen to data entrant for review.

        Args:
            specimen_id: Specimen identifier
            entrant_username: Username of data entrant
            assigned_by: Username of curator making assignment
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        review.assign_to_entrant(entrant_username, assigned_by)
        logger.info(f"Assigned {specimen_id} to entrant {entrant_username} by {assigned_by}")

    def entrant_approve(self, specimen_id: str, entrant_username: str, notes: str | None = None):
        """
        Mark specimen as approved by data entrant.

        Args:
            specimen_id: Specimen identifier
            entrant_username: Username of approving entrant
            notes: Optional approval notes
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        review.entrant_approve(entrant_username, notes)
        logger.info(f"Specimen {specimen_id} approved by entrant {entrant_username}")

    def entrant_reject(self, specimen_id: str, entrant_username: str, notes: str):
        """
        Mark specimen as rejected by data entrant.

        Args:
            specimen_id: Specimen identifier
            entrant_username: Username of rejecting entrant
            notes: Required rejection reason
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        review.entrant_reject(entrant_username, notes)
        logger.info(f"Specimen {specimen_id} rejected by entrant {entrant_username}: {notes}")

    def supervisor_approve(self, specimen_id: str, supervisor_username: str):
        """
        Final supervisor approval - mark as ready for export.

        Args:
            specimen_id: Specimen identifier
            supervisor_username: Username of approving supervisor
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        review.supervisor_approve(supervisor_username)
        logger.info(f"Specimen {specimen_id} approved by supervisor {supervisor_username}, ready for export")

    def submit_for_entrant_review(self, specimen_id: str, curator_username: str):
        """
        Submit corrected draft for entrant review.

        Args:
            specimen_id: Specimen identifier
            curator_username: Username of curator submitting
        """
        review = self.reviews.get(specimen_id)
        if not review:
            logger.warning(f"Review not found: {specimen_id}")
            return

        review.submit_for_entrant_review(curator_username)
        logger.info(f"Specimen {specimen_id} submitted for entrant review by {curator_username}")

    def get_assigned_specimens(self, entrant_username: str) -> list[SpecimenReview]:
        """Get all specimens assigned to a specific entrant."""
        return [
            review for review in self.reviews.values()
            if review.assigned_to == entrant_username
        ]

    def get_ready_for_export(self) -> list[SpecimenReview]:
        """Get all specimens ready for export."""
        return [
            review for review in self.reviews.values()
            if review.status == ReviewStatus.READY_FOR_EXPORT
        ]

    def get_statistics(self) -> dict:
        """Get review statistics with orthogonal dimensions."""
        total = len(self.reviews)

        return {
            "total_specimens": total,
            "status_counts": {
                status.name: sum(1 for r in self.reviews.values() if r.status == status)
                for status in ReviewStatus
            },
            "priority_counts": {
                priority.name: sum(1 for r in self.reviews.values() if r.priority == priority)
                for priority in ReviewPriority
            },
            "flagged_count": sum(1 for r in self.reviews.values() if r.flagged),
            "avg_quality_score": (
                sum(r.quality_score for r in self.reviews.values()) / total if total > 0 else 0.0
            ),
            "avg_completeness": (
                sum(r.completeness_score for r in self.reviews.values()) / total
                if total > 0
                else 0.0
            ),
            "gbif_validated": sum(1 for r in self.reviews.values() if r.gbif_taxonomy_verified),
        }

    def export_reviews(self, output_path: Path):
        """Export all reviews to JSON file."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_specimens": len(self.reviews),
            "reviews": [review.to_dict() for review in self.reviews.values()],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(self.reviews)} reviews to {output_path}")

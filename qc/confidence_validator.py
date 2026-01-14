"""Confidence-based quality control for Darwin Core extractions.

This module implements per-field confidence thresholds to automatically flag
specimens that need human review or additional extraction passes. It supports:

- Per-field confidence thresholds (critical vs optional fields)
- Specimen-level quality scoring
- Automatic routing for low-confidence specimens
- Selective field extraction (high-value fields vs comprehensive)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FieldPriority(str, Enum):
    """Field priority levels for extraction and review."""

    CRITICAL = "critical"  # Must be present and high confidence
    HIGH_VALUE = "high_value"  # Important for GBIF publication
    OPTIONAL = "optional"  # Nice to have but not required
    SUPPLEMENTAL = "supplemental"  # Additional context


class ConfidenceLevel(str, Enum):
    """Overall specimen confidence classification."""

    HIGH = "high"  # >=0.9 avg confidence on critical fields
    MEDIUM = "medium"  # 0.7-0.9 avg confidence
    LOW = "low"  # 0.5-0.7 avg confidence
    VERY_LOW = "very_low"  # <0.5 avg confidence


@dataclass
class FieldThreshold:
    """Confidence threshold configuration for a single field."""

    field_name: str
    priority: FieldPriority
    min_confidence: float = 0.7  # Minimum acceptable confidence
    recommended_confidence: float = 0.9  # Target for publication
    required: bool = False  # Must be present
    description: str = ""


@dataclass
class ValidationResult:
    """Result of confidence validation for a specimen."""

    specimen_id: str
    overall_confidence: ConfidenceLevel = ConfidenceLevel.LOW  # Default, will be updated
    flags: List[str] = field(default_factory=list)
    field_scores: Dict[str, float] = field(default_factory=dict)
    critical_fields_ok: bool = True
    needs_review: bool = False
    suggested_action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "specimen_id": self.specimen_id,
            "overall_confidence": self.overall_confidence.value,
            "flags": self.flags,
            "field_scores": self.field_scores,
            "critical_fields_ok": self.critical_fields_ok,
            "needs_review": self.needs_review,
            "suggested_action": self.suggested_action,
            "metadata": self.metadata,
        }


# Darwin Core field priorities based on GBIF requirements and stakeholder needs
FIELD_THRESHOLDS = {
    # Critical fields - must be present and accurate for GBIF
    "scientificName": FieldThreshold(
        field_name="scientificName",
        priority=FieldPriority.CRITICAL,
        min_confidence=0.8,
        recommended_confidence=0.95,
        required=True,
        description="Species identification - highest priority for publication",
    ),
    "catalogNumber": FieldThreshold(
        field_name="catalogNumber",
        priority=FieldPriority.CRITICAL,
        min_confidence=0.8,
        recommended_confidence=0.95,
        required=True,
        description="Unique specimen identifier - required for tracking",
    ),
    # High-value fields - important for biodiversity data
    "eventDate": FieldThreshold(
        field_name="eventDate",
        priority=FieldPriority.HIGH_VALUE,
        min_confidence=0.7,
        recommended_confidence=0.9,
        required=False,
        description="Collection date - valuable for temporal analysis",
    ),
    "recordedBy": FieldThreshold(
        field_name="recordedBy",
        priority=FieldPriority.HIGH_VALUE,
        min_confidence=0.7,
        recommended_confidence=0.85,
        required=False,
        description="Collector name - important for provenance",
    ),
    "country": FieldThreshold(
        field_name="country",
        priority=FieldPriority.HIGH_VALUE,
        min_confidence=0.8,
        recommended_confidence=0.95,
        required=False,
        description="Country code - essential for geographic filtering",
    ),
    "stateProvince": FieldThreshold(
        field_name="stateProvince",
        priority=FieldPriority.HIGH_VALUE,
        min_confidence=0.7,
        recommended_confidence=0.9,
        required=False,
        description="Province/state - refines geographic location",
    ),
    "locality": FieldThreshold(
        field_name="locality",
        priority=FieldPriority.HIGH_VALUE,
        min_confidence=0.6,
        recommended_confidence=0.8,
        required=False,
        description="Specific collection location - often handwritten/difficult",
    ),
    # Optional fields - nice to have
    "institutionCode": FieldThreshold(
        field_name="institutionCode",
        priority=FieldPriority.OPTIONAL,
        min_confidence=0.6,
        recommended_confidence=0.8,
        required=False,
        description="Owning institution - usually consistent",
    ),
    "collectionCode": FieldThreshold(
        field_name="collectionCode",
        priority=FieldPriority.OPTIONAL,
        min_confidence=0.6,
        recommended_confidence=0.8,
        required=False,
        description="Collection within institution",
    ),
    "habitat": FieldThreshold(
        field_name="habitat",
        priority=FieldPriority.OPTIONAL,
        min_confidence=0.5,
        recommended_confidence=0.7,
        required=False,
        description="Habitat description - variable format",
    ),
    "recordNumber": FieldThreshold(
        field_name="recordNumber",
        priority=FieldPriority.OPTIONAL,
        min_confidence=0.7,
        recommended_confidence=0.85,
        required=False,
        description="Collector's field number",
    ),
    # Supplemental fields
    "identifiedBy": FieldThreshold(
        field_name="identifiedBy",
        priority=FieldPriority.SUPPLEMENTAL,
        min_confidence=0.5,
        recommended_confidence=0.7,
        required=False,
        description="Who identified the specimen",
    ),
    "dateIdentified": FieldThreshold(
        field_name="dateIdentified",
        priority=FieldPriority.SUPPLEMENTAL,
        min_confidence=0.5,
        recommended_confidence=0.7,
        required=False,
        description="When identification was made",
    ),
}


class ConfidenceValidator:
    """Validates specimen extractions against confidence thresholds."""

    def __init__(
        self,
        thresholds: Optional[Dict[str, FieldThreshold]] = None,
        strict_mode: bool = False,
        require_critical_fields: bool = True,
    ):
        """Initialize validator with threshold configuration.

        Parameters
        ----------
        thresholds : dict, optional
            Custom field thresholds. Defaults to FIELD_THRESHOLDS.
        strict_mode : bool, default False
            If True, use recommended_confidence instead of min_confidence.
        require_critical_fields : bool, default True
            If True, flag specimens missing required critical fields.
        """
        self.thresholds = thresholds or FIELD_THRESHOLDS
        self.strict_mode = strict_mode
        self.require_critical_fields = require_critical_fields

    def validate_specimen(
        self, specimen_id: str, extraction_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a specimen's extraction against confidence thresholds.

        Parameters
        ----------
        specimen_id : str
            Unique specimen identifier
        extraction_data : dict
            Extracted Darwin Core fields with confidence scores.
            Expected format:
            {
                "dwc": {
                    "scientificName": {"value": "...", "confidence": 0.95},
                    ...
                }
            }

        Returns
        -------
        ValidationResult
            Validation result with flags and suggested actions.
        """
        result = ValidationResult(specimen_id=specimen_id)

        # Extract DWC fields
        dwc_fields = extraction_data.get("dwc", {})

        # Validate each field
        critical_confidences = []
        all_confidences = []

        for field_name, threshold in self.thresholds.items():
            field_data = dwc_fields.get(field_name, {})
            value = field_data.get("value", "")
            confidence = field_data.get("confidence", 0.0)

            result.field_scores[field_name] = confidence

            # Check if required field is missing
            if threshold.required and not value:
                result.flags.append(f"missing_required_{field_name}")
                result.critical_fields_ok = False
                continue

            # Skip empty optional fields
            if not value:
                continue

            # Determine applicable threshold
            min_conf = (
                threshold.recommended_confidence if self.strict_mode else threshold.min_confidence
            )

            # Check confidence level
            if confidence < min_conf:
                result.flags.append(f"low_confidence_{field_name}_{confidence:.2f}")

                if threshold.priority == FieldPriority.CRITICAL:
                    result.critical_fields_ok = False

            # Track confidences for overall scoring
            if threshold.priority == FieldPriority.CRITICAL:
                critical_confidences.append(confidence)
            if value:  # Only count non-empty fields
                all_confidences.append(confidence)

        # Calculate overall confidence level
        if critical_confidences:
            avg_critical = sum(critical_confidences) / len(critical_confidences)
        else:
            avg_critical = 0.0

        if all_confidences:
            avg_all = sum(all_confidences) / len(all_confidences)
        else:
            avg_all = 0.0

        # Classify overall confidence
        if avg_critical >= 0.9 and result.critical_fields_ok:
            result.overall_confidence = ConfidenceLevel.HIGH
            result.suggested_action = "approve_for_publication"
        elif avg_critical >= 0.7 and result.critical_fields_ok:
            result.overall_confidence = ConfidenceLevel.MEDIUM
            result.suggested_action = "light_review_recommended"
            result.needs_review = True
        elif avg_critical >= 0.5:
            result.overall_confidence = ConfidenceLevel.LOW
            result.suggested_action = "manual_review_required"
            result.needs_review = True
        else:
            result.overall_confidence = ConfidenceLevel.VERY_LOW
            result.suggested_action = "re_extract_with_better_model"
            result.needs_review = True

        # Add metadata
        result.metadata["avg_critical_confidence"] = round(avg_critical, 3)
        result.metadata["avg_all_confidence"] = round(avg_all, 3)
        result.metadata["fields_extracted"] = len(
            [f for f in dwc_fields.values() if f.get("value")]
        )
        result.metadata["total_fields"] = len(self.thresholds)

        return result

    def get_critical_fields(self) -> List[str]:
        """Return list of critical field names."""
        return [
            name
            for name, threshold in self.thresholds.items()
            if threshold.priority == FieldPriority.CRITICAL
        ]

    def get_high_value_fields(self) -> List[str]:
        """Return list of high-value field names for selective extraction."""
        return [
            name
            for name, threshold in self.thresholds.items()
            if threshold.priority in [FieldPriority.CRITICAL, FieldPriority.HIGH_VALUE]
        ]

    def should_re_extract(self, validation_result: ValidationResult) -> Tuple[bool, str]:
        """Determine if specimen should be re-extracted with a better model.

        Parameters
        ----------
        validation_result : ValidationResult
            Previous validation result

        Returns
        -------
        Tuple[bool, str]
            (should_re_extract, reason)
        """
        # Re-extract if critical fields failed
        if not validation_result.critical_fields_ok:
            return True, "critical_fields_failed"

        # Re-extract if overall confidence is very low
        if validation_result.overall_confidence == ConfidenceLevel.VERY_LOW:
            return True, "very_low_confidence"

        # Re-extract if multiple high-value fields have low confidence
        low_conf_high_value = [
            flag
            for flag in validation_result.flags
            if "low_confidence" in flag
            and any(field in flag for field in self.get_high_value_fields())
        ]

        if len(low_conf_high_value) >= 3:
            return True, "multiple_high_value_fields_low_confidence"

        return False, ""


def batch_validate(
    specimens: List[Dict[str, Any]],
    validator: Optional[ConfidenceValidator] = None,
) -> Dict[str, ValidationResult]:
    """Validate multiple specimens and return results.

    Parameters
    ----------
    specimens : list
        List of specimen records with extraction data
    validator : ConfidenceValidator, optional
        Validator instance. Creates default if not provided.

    Returns
    -------
    dict
        Mapping of specimen_id to ValidationResult
    """
    if validator is None:
        validator = ConfidenceValidator()

    results = {}
    for specimen in specimens:
        specimen_id = specimen.get("specimen_id", "unknown")
        results[specimen_id] = validator.validate_specimen(specimen_id, specimen)

    return results


def generate_review_queue(
    validation_results: Dict[str, ValidationResult],
    priority_order: Optional[List[ConfidenceLevel]] = None,
) -> List[str]:
    """Generate prioritized review queue based on validation results.

    Parameters
    ----------
    validation_results : dict
        Mapping of specimen_id to ValidationResult
    priority_order : list, optional
        Order to prioritize confidence levels. Defaults to VERY_LOW, LOW, MEDIUM.

    Returns
    -------
    list
        Specimen IDs in priority order for review
    """
    if priority_order is None:
        priority_order = [
            ConfidenceLevel.VERY_LOW,
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
        ]

    queue = []
    for conf_level in priority_order:
        specimens = [
            spec_id
            for spec_id, result in validation_results.items()
            if result.overall_confidence == conf_level and result.needs_review
        ]
        queue.extend(sorted(specimens))  # Sort for consistency

    return queue


__all__ = [
    "FieldPriority",
    "ConfidenceLevel",
    "FieldThreshold",
    "ValidationResult",
    "ConfidenceValidator",
    "FIELD_THRESHOLDS",
    "batch_validate",
    "generate_review_queue",
]

"""Review queue generator for human-in-the-loop correction workflow.

This module classifies specimens into review tiers based on confidence scores
and generates review queues for mobile interface.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ReviewTier(str, Enum):
    """Review tier classification."""

    AUTO_ACCEPT = "auto_accept"  # High confidence, no review needed
    CONFIRM = "confirm"  # Medium confidence, confirm suggestions
    CORRECT = "correct"  # Low confidence, manual correction needed


class FieldStatus(str, Enum):
    """Status of a field correction."""

    GOOD = "good"  # High confidence, accepted as-is
    SUGGESTED = "suggested"  # Has auto-correction suggestion
    MISSING = "missing"  # Empty or failed extraction
    ERROR = "error"  # Extraction error or very low confidence


@dataclass
class FieldReview:
    """Review item for a single field."""

    field_name: str
    status: FieldStatus
    original_value: str | None
    confidence: float
    suggested_value: str | None = None
    suggestion_confidence: float | None = None
    reason: str | None = None  # Why this needs review


@dataclass
class SpecimenReview:
    """Review item for a complete specimen."""

    specimen_id: str
    image_filename: str
    tier: ReviewTier
    fields: list[FieldReview]
    overall_confidence: float
    review_priority: int  # 1 = highest priority
    metadata: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "specimen_id": self.specimen_id,
            "image_filename": self.image_filename,
            "tier": self.tier.value,
            "fields": [asdict(f) for f in self.fields],
            "overall_confidence": self.overall_confidence,
            "review_priority": self.review_priority,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ReviewQueue:
    """Complete review queue with statistics."""

    specimens: list[SpecimenReview]
    statistics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "specimens": [s.to_dict() for s in self.specimens],
            "statistics": self.statistics,
        }

    def save(self, output_path: Path) -> None:
        """Save review queue to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class ReviewQueueGenerator:
    """Generate review queues from corrected specimen data."""

    def __init__(
        self,
        auto_accept_threshold: float = 0.85,
        suggestion_threshold: float = 0.60,
        critical_fields: list[str] | None = None,
    ):
        """Initialize review queue generator.

        Args:
            auto_accept_threshold: Minimum confidence for auto-accept (Tier 1)
            suggestion_threshold: Minimum confidence for suggestions (Tier 2)
            critical_fields: List of field names that require review if low confidence
        """
        self.auto_accept_threshold = auto_accept_threshold
        self.suggestion_threshold = suggestion_threshold
        self.critical_fields = critical_fields or [
            "scientificName",
            "recordedBy",
            "eventDate",
            "locality",
            "country",
            "stateProvince",
        ]

    def classify_field(
        self,
        field_name: str,
        value: str | None,
        confidence: float,
        suggested_value: str | None = None,
        suggestion_confidence: float | None = None,
    ) -> FieldReview:
        """Classify a single field for review.

        Args:
            field_name: Darwin Core field name
            value: Extracted value
            confidence: Extraction confidence (0.0-1.0)
            suggested_value: Auto-correction suggestion
            suggestion_confidence: Confidence in suggestion

        Returns:
            FieldReview with classification
        """
        # Empty or missing value
        if not value:
            return FieldReview(
                field_name=field_name,
                status=FieldStatus.MISSING,
                original_value=None,
                confidence=0.0,
                reason="Field is empty or not extracted",
            )

        # High confidence - good as-is
        if confidence >= self.auto_accept_threshold:
            return FieldReview(
                field_name=field_name,
                status=FieldStatus.GOOD,
                original_value=value,
                confidence=confidence,
            )

        # Has suggestion with good confidence
        if suggested_value and (suggestion_confidence or 0) >= self.auto_accept_threshold:
            return FieldReview(
                field_name=field_name,
                status=FieldStatus.SUGGESTED,
                original_value=value,
                confidence=confidence,
                suggested_value=suggested_value,
                suggestion_confidence=suggestion_confidence,
                reason=f"Auto-correction suggested (confidence: {suggestion_confidence:.2f})",
            )

        # Low confidence - needs review
        if confidence < self.suggestion_threshold:
            return FieldReview(
                field_name=field_name,
                status=FieldStatus.ERROR,
                original_value=value,
                confidence=confidence,
                suggested_value=suggested_value,
                suggestion_confidence=suggestion_confidence,
                reason=f"Low extraction confidence ({confidence:.2f})",
            )

        # Medium confidence - could use confirmation
        return FieldReview(
            field_name=field_name,
            status=FieldStatus.SUGGESTED,
            original_value=value,
            confidence=confidence,
            suggested_value=suggested_value,
            suggestion_confidence=suggestion_confidence,
            reason=f"Medium confidence ({confidence:.2f}), review recommended",
        )

    def classify_specimen(
        self,
        specimen_data: dict[str, Any],
        corrected_data: dict[str, Any] | None = None,
    ) -> SpecimenReview:
        """Classify a specimen for review.

        Args:
            specimen_data: Original specimen record from raw.jsonl
            corrected_data: Corrected data from field parser (optional)

        Returns:
            SpecimenReview with tier classification
        """
        specimen_id = specimen_data.get("image", "unknown").replace(".jpg", "")
        image_filename = specimen_data.get("image", "unknown")

        # Get extracted DwC data and confidence scores
        dwc = specimen_data.get("dwc", {})
        dwc_conf = specimen_data.get("dwc_confidence", {})

        # Apply corrections if available
        if corrected_data:
            dwc.update(corrected_data)

        # Review each critical field
        field_reviews = []
        confidence_scores = []

        for field_name in self.critical_fields:
            value = dwc.get(field_name)
            confidence = dwc_conf.get(field_name, 0.0)

            # Check if we have a suggested correction
            # (In future: this would come from name_matcher, date_parser, etc.)
            suggested_value = None
            suggestion_confidence = None

            field_review = self.classify_field(
                field_name=field_name,
                value=value,
                confidence=confidence,
                suggested_value=suggested_value,
                suggestion_confidence=suggestion_confidence,
            )

            field_reviews.append(field_review)

            # Track confidence for overall scoring
            if field_review.confidence > 0:
                confidence_scores.append(field_review.confidence)

        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        )

        # Determine review tier
        needs_review_fields = [
            f for f in field_reviews if f.status in [FieldStatus.MISSING, FieldStatus.ERROR]
        ]
        has_suggestions = [f for f in field_reviews if f.status == FieldStatus.SUGGESTED]

        if not needs_review_fields and not has_suggestions:
            tier = ReviewTier.AUTO_ACCEPT
            priority = 99  # Lowest priority
        elif has_suggestions and not needs_review_fields:
            tier = ReviewTier.CONFIRM
            priority = 50  # Medium priority
        else:
            tier = ReviewTier.CORRECT
            # Higher priority for more missing fields
            priority = len(needs_review_fields)

        return SpecimenReview(
            specimen_id=specimen_id,
            image_filename=image_filename,
            tier=tier,
            fields=field_reviews,
            overall_confidence=overall_confidence,
            review_priority=priority,
            metadata={
                "needs_review_count": len(needs_review_fields),
                "suggestions_count": len(has_suggestions),
                "flags": specimen_data.get("flags", []),
            },
        )

    def generate_queue(
        self,
        specimens: list[dict[str, Any]],
        corrected_data: dict[str, dict[str, Any]] | None = None,
    ) -> ReviewQueue:
        """Generate review queue from specimen data.

        Args:
            specimens: List of specimen records from raw.jsonl
            corrected_data: Optional dict of {specimen_id: corrected_dwc_fields}

        Returns:
            ReviewQueue with classified specimens and statistics
        """
        reviews = []

        for specimen in specimens:
            specimen_id = specimen.get("image", "").replace(".jpg", "")
            corrections = corrected_data.get(specimen_id) if corrected_data else None

            review = self.classify_specimen(specimen, corrections)
            reviews.append(review)

        # Sort by priority (most urgent first)
        reviews.sort(key=lambda r: (r.review_priority, -r.overall_confidence))

        # Calculate statistics
        tier_counts = defaultdict(int)
        field_status_counts = defaultdict(lambda: defaultdict(int))

        for review in reviews:
            tier_counts[review.tier.value] += 1

            for field in review.fields:
                field_status_counts[field.field_name][field.status.value] += 1

        total = len(reviews)
        statistics = {
            "total_specimens": total,
            "by_tier": dict(tier_counts),
            "by_field": dict(field_status_counts),
            "review_needed": tier_counts[ReviewTier.CONFIRM.value]
            + tier_counts[ReviewTier.CORRECT.value],
            "estimated_review_time_minutes": self._estimate_review_time(reviews),
        }

        return ReviewQueue(specimens=reviews, statistics=statistics)

    def _estimate_review_time(self, reviews: list[SpecimenReview]) -> int:
        """Estimate review time in minutes.

        Args:
            reviews: List of specimen reviews

        Returns:
            Estimated time in minutes
        """
        time_estimate = 0

        for review in reviews:
            if review.tier == ReviewTier.AUTO_ACCEPT:
                continue  # No review time
            elif review.tier == ReviewTier.CONFIRM:
                # ~30 seconds per confirmation
                time_estimate += 0.5
            else:  # ReviewTier.CORRECT
                # ~90 seconds per manual correction
                time_estimate += 1.5

        return int(time_estimate)


def load_specimens_from_jsonl(jsonl_path: Path) -> list[dict[str, Any]]:
    """Load specimen records from JSONL file.

    Args:
        jsonl_path: Path to raw.jsonl file

    Returns:
        List of specimen dictionaries
    """
    specimens = []
    with open(jsonl_path) as f:
        for line in f:
            if line.strip():
                specimens.append(json.loads(line))
    return specimens


__all__ = [
    "ReviewTier",
    "FieldStatus",
    "FieldReview",
    "SpecimenReview",
    "ReviewQueue",
    "ReviewQueueGenerator",
    "load_specimens_from_jsonl",
]

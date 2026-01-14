"""
Tests for ReviewEngine - Specimen review workflow management

Tests cover:
- Loading extraction results from JSONL
- Quality score calculations
- Priority determination
- Issue identification
- Review queue filtering and sorting
- Review updates
- Statistics generation
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.review.engine import (
    ReviewEngine,
    ReviewPriority,
    ReviewStatus,
    SpecimenReview,
)


@pytest.fixture
def sample_extraction_data():
    """Sample extraction data for testing."""
    return [
        {
            "image": "TEST-001",
            "timestamp": "2025-01-15T10:30:00Z",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "extraction_method": "gpt-4o-mini",
            "ocr_engine": "apple_vision",
            "dwc": {
                "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
                "scientificName": {"value": "Artemisia frigida Willd.", "confidence": 0.95},
                "eventDate": {"value": "1969-08-14", "confidence": 0.92},
                "recordedBy": {"value": "J. Tester", "confidence": 0.90},
                "locality": {"value": "Test Location", "confidence": 0.88},
                "stateProvince": {"value": "Test State", "confidence": 0.95},
                "country": {"value": "Test Country", "confidence": 0.98},
            },
        },
        {
            "image": "TEST-002",
            "timestamp": "2025-01-15T10:31:00Z",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "extraction_method": "gpt-4o-mini",
            "ocr_engine": "apple_vision",
            "dwc": {
                "catalogNumber": {"value": "TEST-002", "confidence": 0.90},
                "scientificName": {"value": "Test species", "confidence": 0.45},
                "eventDate": {"value": "1970-07-22", "confidence": 0.50},
                "recordedBy": {"value": "A. Tester", "confidence": 0.85},
                "locality": {"value": "Test Hills", "confidence": 0.40},
                "stateProvince": {"value": "Test State", "confidence": 0.95},
                "country": {"value": "Test Country", "confidence": 0.98},
            },
        },
        {
            "image": "TEST-003",
            "timestamp": "2025-01-15T10:32:00Z",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "extraction_method": "gpt-4o-mini",
            "ocr_engine": "apple_vision",
            "dwc": {
                "catalogNumber": {"value": "TEST-003", "confidence": 0.93},
                # Missing required fields - should be CRITICAL priority
            },
        },
    ]


@pytest.fixture
def temp_jsonl_file(sample_extraction_data):
    """Create temporary JSONL file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for record in sample_extraction_data:
            f.write(json.dumps(record) + "\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink()


@pytest.fixture
def engine():
    """Create ReviewEngine instance."""
    return ReviewEngine(gbif_validator=None)


class TestSpecimenReview:
    """Tests for SpecimenReview dataclass."""

    def test_calculate_quality_score(self):
        """Test quality score calculation (60% completeness + 40% confidence).

        Note: confidence_score is stored as 0-1, converted to 0-100 in calculation.
        """
        review = SpecimenReview(
            specimen_id="TEST-001",
            completeness_score=80.0,
            confidence_score=0.90,  # 0-1 scale
        )

        review.calculate_quality_score()

        # Expected: (80 * 0.6) + (90 * 0.4) = 48 + 36 = 84
        assert review.quality_score == pytest.approx(84.0)

    def test_determine_priority_critical(self):
        """Test CRITICAL priority for specimens with major issues."""
        # Case 1: Critical issues present
        review = SpecimenReview(
            specimen_id="TEST-001",
            critical_issues=["Missing required field: scientificName"],
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.CRITICAL

        # Case 2: No DWC fields
        review = SpecimenReview(specimen_id="TEST-002", dwc_fields={})
        review.determine_priority()
        assert review.priority == ReviewPriority.CRITICAL

    def test_determine_priority_high(self):
        """Test HIGH priority for low quality or GBIF issues."""
        # Case 1: Low quality score
        review = SpecimenReview(
            specimen_id="TEST-001",
            quality_score=40.0,
            dwc_fields={"catalogNumber": {"value": "TEST-001"}},
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.HIGH

        # Case 2: GBIF taxonomy issues
        review = SpecimenReview(
            specimen_id="TEST-002",
            quality_score=80.0,
            gbif_taxonomy_issues=["fuzzy_match"],
            dwc_fields={"catalogNumber": {"value": "TEST-002"}},
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.HIGH

    def test_determine_priority_medium(self):
        """Test MEDIUM priority for moderate quality."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            quality_score=65.0,
            dwc_fields={"catalogNumber": {"value": "TEST-001"}},
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.MEDIUM

    def test_determine_priority_low(self):
        """Test LOW priority for good quality with warnings."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            quality_score=80.0,
            warnings=["Low confidence for eventDate: 0.45"],
            dwc_fields={"catalogNumber": {"value": "TEST-001"}},
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.LOW

    def test_determine_priority_minimal(self):
        """Test MINIMAL priority for excellent quality."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            quality_score=90.0,
            dwc_fields={"catalogNumber": {"value": "TEST-001"}},
        )
        review.determine_priority()
        assert review.priority == ReviewPriority.MINIMAL

    def test_to_dict(self):
        """Test conversion to dictionary for JSON serialization."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            sha256_hash="abc123",
            dwc_fields={"catalogNumber": {"value": "TEST-001"}},
            extraction_timestamp="2025-01-15T10:30:00Z",
            quality_score=85.0,
            status=ReviewStatus.PENDING,
            priority=ReviewPriority.HIGH,
        )

        result = review.to_dict()

        assert result["specimen_id"] == "TEST-001"
        assert result["sha256_hash"] == "abc123"
        assert result["quality"]["quality_score"] == 85.0
        assert result["review"]["status"] == "PENDING"
        assert result["quality"]["priority"] == "HIGH"
        assert result["provenance"]["sha256"] == "abc123"


class TestReviewEngine:
    """Tests for ReviewEngine workflow management."""

    def test_initialization(self):
        """Test ReviewEngine initialization."""
        engine = ReviewEngine()

        assert engine.gbif_validator is None
        assert engine.reviews == {}
        assert engine.REQUIRED_FIELDS == [
            "catalogNumber",
            "scientificName",
            "eventDate",
            "recordedBy",
            "country",
            "stateProvince",
            "locality",
        ]

    def test_load_extraction_results(self, engine, temp_jsonl_file):
        """Test loading extraction results from JSONL file."""
        count = engine.load_extraction_results(temp_jsonl_file)

        assert count == 3
        assert len(engine.reviews) == 3
        assert "TEST-001" in engine.reviews
        assert "TEST-002" in engine.reviews
        assert "TEST-003" in engine.reviews

    def test_calculate_completeness(self, engine):
        """Test completeness score calculation based on required fields."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            dwc_fields={
                "catalogNumber": {"value": "TEST-001"},
                "scientificName": {"value": "Test species"},
                "eventDate": {"value": "2025-01-15"},
                "recordedBy": {"value": "Tester"},
                "country": {"value": "Test Country"},
                # Missing stateProvince and locality (5/7 = 71.4%)
            },
        )

        engine._calculate_completeness(review)

        # 5 out of 7 required fields present
        assert review.completeness_score == pytest.approx(71.43, rel=0.01)

    def test_calculate_confidence(self, engine):
        """Test confidence score calculation (average of field confidences)."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            dwc_fields={
                "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
                "scientificName": {"value": "Test species", "confidence": 0.85},
                "eventDate": {"value": "2025-01-15", "confidence": 0.90},
            },
        )

        engine._calculate_confidence(review)

        # Average: (0.95 + 0.85 + 0.90) / 3 = 0.9
        assert review.confidence_score == pytest.approx(0.9)

    def test_identify_issues(self, engine):
        """Test issue identification (missing fields and low confidence)."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            dwc_fields={
                "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
                "scientificName": {"value": "Test species", "confidence": 0.30},
                # Missing other required fields
            },
        )

        engine._identify_issues(review)

        # Should have critical issues for missing fields
        assert len(review.critical_issues) == 5  # Missing 5 of 7 required fields
        assert any("eventDate" in issue for issue in review.critical_issues)

        # Should have warning for low confidence scientificName
        assert len(review.warnings) == 1
        assert "scientificName" in review.warnings[0]

    def test_get_review_queue_no_filters(self, engine, temp_jsonl_file):
        """Test getting review queue without filters."""
        engine.load_extraction_results(temp_jsonl_file)

        queue = engine.get_review_queue()

        assert len(queue) == 3
        # Should be sorted by priority (CRITICAL first)
        assert queue[0].priority == ReviewPriority.CRITICAL

    def test_get_review_queue_status_filter(self, engine, temp_jsonl_file):
        """Test filtering review queue by status."""
        engine.load_extraction_results(temp_jsonl_file)

        # All should be PENDING initially
        queue = engine.get_review_queue(status=ReviewStatus.PENDING)
        assert len(queue) == 3

        # Update one to APPROVED
        engine.update_review("TEST-001", status=ReviewStatus.APPROVED)

        queue = engine.get_review_queue(status=ReviewStatus.APPROVED)
        assert len(queue) == 1
        assert queue[0].specimen_id == "TEST-001"

    def test_get_review_queue_priority_filter(self, engine, temp_jsonl_file):
        """Test filtering review queue by priority."""
        engine.load_extraction_results(temp_jsonl_file)

        # Filter for CRITICAL priority
        queue = engine.get_review_queue(priority=ReviewPriority.CRITICAL)

        # TEST-003 has missing fields, should be CRITICAL
        assert len(queue) >= 1
        assert all(r.priority == ReviewPriority.CRITICAL for r in queue)

    def test_get_review_queue_flagged_filter(self, engine, temp_jsonl_file):
        """Test filtering review queue by flagged status."""
        engine.load_extraction_results(temp_jsonl_file)

        # Flag one specimen
        engine.update_review("TEST-002", flagged=True)

        queue = engine.get_review_queue(flagged_only=True)

        assert len(queue) == 1
        assert queue[0].specimen_id == "TEST-002"
        assert queue[0].flagged is True

    def test_get_review_queue_sorting(self, engine, temp_jsonl_file):
        """Test sorting review queue by different fields."""
        engine.load_extraction_results(temp_jsonl_file)

        # Sort by priority (default)
        queue = engine.get_review_queue(sort_by="priority")
        priorities = [r.priority.value for r in queue]
        assert priorities == sorted(priorities)

        # Sort by quality
        queue = engine.get_review_queue(sort_by="quality")
        qualities = [r.quality_score for r in queue]
        assert qualities == sorted(qualities)

    def test_get_review(self, engine, temp_jsonl_file):
        """Test getting a specific review record."""
        engine.load_extraction_results(temp_jsonl_file)

        review = engine.get_review("TEST-001")

        assert review is not None
        assert review.specimen_id == "TEST-001"

        # Non-existent specimen
        review = engine.get_review("NONEXISTENT")
        assert review is None

    def test_update_review(self, engine, temp_jsonl_file):
        """Test updating review record."""
        engine.load_extraction_results(temp_jsonl_file)

        # Update with corrections
        corrections = {"scientificName": "Corrected name"}
        engine.update_review(
            specimen_id="TEST-001",
            corrections=corrections,
            status=ReviewStatus.APPROVED,
            flagged=True,
            reviewed_by="test_user",
            notes="Test notes",
        )

        review = engine.get_review("TEST-001")
        # Corrections are stored with full metadata, check the value
        assert "scientificName" in review.corrections
        assert review.corrections["scientificName"]["value"] == "Corrected name"
        assert review.status == ReviewStatus.APPROVED
        assert review.flagged is True
        assert review.reviewed_by == "test_user"
        assert review.notes == "Test notes"
        assert review.reviewed_at is not None

    def test_get_statistics(self, engine, temp_jsonl_file):
        """Test getting review statistics."""
        engine.load_extraction_results(temp_jsonl_file)

        # Update some reviews
        engine.update_review("TEST-001", status=ReviewStatus.APPROVED, flagged=True)
        engine.update_review("TEST-002", status=ReviewStatus.REJECTED)

        stats = engine.get_statistics()

        assert stats["total_specimens"] == 3
        assert stats["status_counts"]["PENDING"] == 1
        assert stats["status_counts"]["APPROVED"] == 1
        assert stats["status_counts"]["REJECTED"] == 1
        assert stats["flagged_count"] == 1
        assert "avg_quality_score" in stats
        assert "avg_completeness" in stats

    def test_export_reviews(self, engine, temp_jsonl_file):
        """Test exporting reviews to JSON file."""
        engine.load_extraction_results(temp_jsonl_file)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            engine.export_reviews(output_path)

            # Verify file was created
            assert output_path.exists()

            # Verify content
            with open(output_path) as f:
                data = json.load(f)

            assert data["total_specimens"] == 3
            assert len(data["reviews"]) == 3
            assert "exported_at" in data

        finally:
            # Cleanup
            output_path.unlink()


class TestQualityScoring:
    """Tests for quality scoring algorithm."""

    def test_high_quality_specimen(self, engine):
        """Test quality scoring for high-quality specimen."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            dwc_fields={
                "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
                "scientificName": {"value": "Test species", "confidence": 0.95},
                "eventDate": {"value": "2025-01-15", "confidence": 0.92},
                "recordedBy": {"value": "Tester", "confidence": 0.90},
                "locality": {"value": "Test Location", "confidence": 0.88},
                "stateProvince": {"value": "Test State", "confidence": 0.95},
                "country": {"value": "Test Country", "confidence": 0.98},
            },
        )

        engine._calculate_completeness(review)
        engine._calculate_confidence(review)
        review.calculate_quality_score()
        review.determine_priority()

        # All fields present, high confidence
        assert review.completeness_score == 100.0
        assert review.confidence_score > 0.85
        assert review.quality_score > 90.0
        assert review.priority == ReviewPriority.MINIMAL

    def test_low_quality_specimen(self, engine):
        """Test quality scoring for low-quality specimen."""
        review = SpecimenReview(
            specimen_id="TEST-001",
            dwc_fields={
                "catalogNumber": {"value": "TEST-001", "confidence": 0.50},
                "scientificName": {"value": "Test species", "confidence": 0.40},
                # Missing most required fields
            },
        )

        engine._calculate_completeness(review)
        engine._calculate_confidence(review)
        engine._identify_issues(review)
        review.calculate_quality_score()
        review.determine_priority()

        # Poor completeness and confidence
        assert review.completeness_score < 50.0
        assert review.confidence_score < 0.5
        assert review.quality_score < 50.0
        assert len(review.critical_issues) > 0
        # CRITICAL priority because of missing required fields (critical issues)
        assert review.priority == ReviewPriority.CRITICAL

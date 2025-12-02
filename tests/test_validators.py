"""
Tests for GBIF Validators - Taxonomy and locality validation

Tests cover:
- GBIF taxonomy validation with pygbif
- Fuzzy name matching
- Confidence scoring
- Locality validation
- Name suggestions
- Error handling

Note: These tests use mock responses to avoid hitting GBIF API during testing.
For integration tests with real GBIF API, see tests/integration/.
"""

from unittest.mock import Mock, patch

import pytest

from src.review.validators import GBIFValidator, create_gbif_validator


@pytest.fixture
def validator():
    """Create GBIFValidator instance with default settings."""
    return GBIFValidator(
        min_confidence_score=0.80,
        enable_fuzzy_matching=True,
        enable_occurrence_validation=False,
    )


@pytest.fixture
def validator_with_occurrence():
    """Create GBIFValidator instance with occurrence validation enabled."""
    return GBIFValidator(
        min_confidence_score=0.80,
        enable_fuzzy_matching=True,
        enable_occurrence_validation=True,
    )


class TestGBIFValidatorInit:
    """Tests for GBIFValidator initialization."""

    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        validator = GBIFValidator()

        assert validator.min_confidence_score == 0.80
        assert validator.enable_fuzzy_matching is True
        assert validator.enable_occurrence_validation is False

    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        validator = GBIFValidator(
            min_confidence_score=0.90,
            enable_fuzzy_matching=False,
            enable_occurrence_validation=True,
        )

        assert validator.min_confidence_score == 0.90
        assert validator.enable_fuzzy_matching is False
        assert validator.enable_occurrence_validation is True


class TestVerifyTaxonomy:
    """Tests for taxonomy verification."""

    @patch("src.review.validators.species")
    def test_verify_taxonomy_exact_match(self, mock_species, validator):
        """Test taxonomy verification with exact match."""
        # Mock GBIF response for exact match
        mock_species.name_backbone.return_value = {
            "usageKey": 123456,
            "scientificName": "Artemisia frigida Willd.",
            "canonicalName": "Artemisia frigida",
            "rank": "SPECIES",
            "status": "ACCEPTED",
            "confidence": 95,
            "matchType": "EXACT",
            "kingdom": "Plantae",
            "family": "Asteraceae",
        }

        record = {"scientificName": "Artemisia frigida Willd."}

        updated_record, metadata = validator.verify_taxonomy(record)

        # Verify metadata
        assert metadata["gbif_taxonomy_verified"] is True
        assert metadata["gbif_match_type"] == "EXACT"
        assert metadata["gbif_confidence"] == 0.95
        assert metadata["gbif_canonical_name"] == "Artemisia frigida"
        assert metadata["gbif_issues"] == []

        # Verify updated record
        assert updated_record["gbif_accepted_name"] == "Artemisia frigida"
        assert updated_record["gbif_kingdom"] == "Plantae"
        assert updated_record["gbif_family"] == "Asteraceae"

    @patch("src.review.validators.species")
    def test_verify_taxonomy_fuzzy_match(self, mock_species, validator):
        """Test taxonomy verification with fuzzy match."""
        # Mock GBIF response for fuzzy match
        mock_species.name_backbone.return_value = {
            "usageKey": 123456,
            "scientificName": "Artemisia frigida Willd.",
            "canonicalName": "Artemisia frigida",
            "rank": "SPECIES",
            "status": "ACCEPTED",
            "confidence": 85,
            "matchType": "FUZZY",
            "kingdom": "Plantae",
            "family": "Asteraceae",
        }

        record = {"scientificName": "Artemisia frigida"}  # Missing authority

        updated_record, metadata = validator.verify_taxonomy(record)

        # Fuzzy match should still verify if confidence meets threshold
        assert metadata["gbif_taxonomy_verified"] is True
        assert metadata["gbif_match_type"] == "FUZZY"
        assert metadata["gbif_confidence"] == 0.85
        assert len(metadata["gbif_issues"]) == 1
        assert "fuzzy_match" in metadata["gbif_issues"][0]

    @patch("src.review.validators.species")
    def test_verify_taxonomy_low_confidence(self, mock_species, validator):
        """Test taxonomy verification with low confidence."""
        # Mock GBIF response with low confidence
        mock_species.name_backbone.return_value = {
            "usageKey": 123456,
            "scientificName": "Unknown species",
            "canonicalName": "Unknown species",
            "rank": "SPECIES",
            "status": "DOUBTFUL",
            "confidence": 30,  # Below 80% threshold
            "matchType": "FUZZY",
        }

        record = {"scientificName": "Unknown speces"}  # Typo

        updated_record, metadata = validator.verify_taxonomy(record)

        # Low confidence should not verify
        assert metadata["gbif_taxonomy_verified"] is False
        assert metadata["gbif_confidence"] == 0.30
        assert any("low_confidence" in issue for issue in metadata["gbif_issues"])

    @patch("src.review.validators.species")
    def test_verify_taxonomy_higher_rank_match(self, mock_species, validator):
        """Test taxonomy verification with higher rank match."""
        # Mock GBIF response for genus-level match
        mock_species.name_backbone.return_value = {
            "usageKey": 123456,
            "scientificName": "Artemisia",
            "canonicalName": "Artemisia",
            "rank": "GENUS",
            "status": "ACCEPTED",
            "confidence": 90,
            "matchType": "HIGHERRANK",
            "kingdom": "Plantae",
            "family": "Asteraceae",
        }

        record = {"scientificName": "Artemisia unknown-species"}

        updated_record, metadata = validator.verify_taxonomy(record)

        # Higher rank match should verify
        assert metadata["gbif_taxonomy_verified"] is True
        assert metadata["gbif_match_type"] == "HIGHERRANK"
        assert metadata["gbif_rank"] == "GENUS"
        assert any("higher_rank_match" in issue for issue in metadata["gbif_issues"])

    @patch("src.review.validators.species")
    def test_verify_taxonomy_no_match(self, mock_species, validator):
        """Test taxonomy verification with no match."""
        # Mock GBIF response for no match
        mock_species.name_backbone.return_value = None

        record = {"scientificName": "Completely Invalid Name"}

        updated_record, metadata = validator.verify_taxonomy(record)

        assert metadata["gbif_taxonomy_verified"] is False
        assert metadata["gbif_match_type"] is None
        assert metadata["gbif_confidence"] == 0.0
        assert "no_match_found" in metadata["gbif_issues"]

    def test_verify_taxonomy_missing_name(self, validator):
        """Test taxonomy verification with missing scientific name."""
        record = {}  # No scientificName

        updated_record, metadata = validator.verify_taxonomy(record)

        assert metadata["gbif_taxonomy_verified"] is False
        assert "missing_scientific_name" in metadata["gbif_issues"]

    @patch("src.review.validators.species")
    def test_verify_taxonomy_error_handling(self, mock_species, validator):
        """Test error handling during taxonomy verification."""
        # Mock GBIF to raise exception
        mock_species.name_backbone.side_effect = Exception("API error")

        record = {"scientificName": "Test species"}

        updated_record, metadata = validator.verify_taxonomy(record)

        assert metadata["gbif_taxonomy_verified"] is False
        assert any("validation_error" in issue for issue in metadata["gbif_issues"])


class TestVerifyLocality:
    """Tests for locality verification."""

    def test_verify_locality_valid_coordinates(self, validator):
        """Test locality verification with valid coordinates."""
        record = {
            "decimalLatitude": 50.0,
            "decimalLongitude": -105.0,
        }

        updated_record, metadata = validator.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is True
        assert metadata["gbif_locality_verified"] is True
        assert metadata["gbif_issues"] == []

    def test_verify_locality_invalid_latitude(self, validator):
        """Test locality verification with invalid latitude."""
        record = {
            "decimalLatitude": 95.0,  # > 90
            "decimalLongitude": -105.0,
        }

        updated_record, metadata = validator.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is False
        assert metadata["gbif_locality_verified"] is False
        assert any("invalid_latitude" in issue for issue in metadata["gbif_issues"])

    def test_verify_locality_invalid_longitude(self, validator):
        """Test locality verification with invalid longitude."""
        record = {
            "decimalLatitude": 50.0,
            "decimalLongitude": 200.0,  # > 180
        }

        updated_record, metadata = validator.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is False
        assert metadata["gbif_locality_verified"] is False
        assert any("invalid_longitude" in issue for issue in metadata["gbif_issues"])

    def test_verify_locality_missing_coordinates(self, validator):
        """Test locality verification with missing coordinates."""
        record = {}  # No coordinates

        updated_record, metadata = validator.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is False
        assert metadata["gbif_locality_verified"] is False
        assert "missing_coordinates" in metadata["gbif_issues"]

    @patch("src.review.validators.occurrences")
    def test_verify_locality_with_occurrence_validation(
        self, mock_occurrences, validator_with_occurrence
    ):
        """Test locality verification with occurrence validation enabled."""
        # Mock GBIF occurrence search
        mock_occurrences.search.return_value = {
            "count": 5,
            "results": [{"key": 123, "scientificName": "Test species"}],
        }

        record = {
            "decimalLatitude": 50.0,
            "decimalLongitude": -105.0,
            "scientificName": "Test species",
        }

        updated_record, metadata = validator_with_occurrence.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is True
        assert metadata["gbif_occurrence_validated"] is True
        assert metadata["gbif_locality_verified"] is True

    @patch("src.review.validators.occurrences")
    def test_verify_locality_no_nearby_occurrences(
        self, mock_occurrences, validator_with_occurrence
    ):
        """Test locality verification with no nearby occurrences."""
        # Mock GBIF occurrence search with no results
        mock_occurrences.search.return_value = {"count": 0, "results": []}

        record = {
            "decimalLatitude": 50.0,
            "decimalLongitude": -105.0,
            "scientificName": "Test species",
        }

        updated_record, metadata = validator_with_occurrence.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is True
        assert metadata["gbif_occurrence_validated"] is False
        assert metadata["gbif_locality_verified"] is False
        assert any(
            "no_nearby_occurrences" in issue for issue in metadata["gbif_issues"]
        )

    def test_verify_locality_error_handling(self, validator):
        """Test error handling during locality verification."""
        record = {
            "decimalLatitude": "invalid",  # Not a number
            "decimalLongitude": -105.0,
        }

        updated_record, metadata = validator.verify_locality(record)

        assert metadata["gbif_coordinate_valid"] is False
        assert any("validation_error" in issue for issue in metadata["gbif_issues"])


class TestGetSuggestions:
    """Tests for taxonomic name suggestions."""

    @patch("src.review.validators.species")
    def test_get_suggestions_success(self, mock_species, validator):
        """Test getting taxonomic name suggestions."""
        # Mock GBIF suggest response
        mock_species.name_suggest.return_value = [
            {
                "key": 123,
                "canonicalName": "Artemisia frigida",
                "rank": "SPECIES",
                "kingdom": "Plantae",
                "family": "Asteraceae",
            },
            {
                "key": 124,
                "canonicalName": "Artemisia tridentata",
                "rank": "SPECIES",
                "kingdom": "Plantae",
                "family": "Asteraceae",
            },
        ]

        suggestions = validator.get_suggestions("Artemisia", limit=10)

        assert len(suggestions) == 2
        assert suggestions[0]["scientificName"] == "Artemisia frigida"
        assert suggestions[0]["rank"] == "SPECIES"
        assert suggestions[0]["kingdom"] == "Plantae"
        assert suggestions[0]["usageKey"] == 123

    @patch("src.review.validators.species")
    def test_get_suggestions_error_handling(self, mock_species, validator):
        """Test error handling during suggestion lookup."""
        # Mock GBIF to raise exception
        mock_species.name_suggest.side_effect = Exception("API error")

        suggestions = validator.get_suggestions("Test")

        assert suggestions == []


class TestCreateGBIFValidator:
    """Tests for validator factory function."""

    def test_create_gbif_validator_defaults(self):
        """Test creating validator with default config."""
        validator = create_gbif_validator()

        assert validator.min_confidence_score == 0.80
        assert validator.enable_fuzzy_matching is True
        assert validator.enable_occurrence_validation is False

    def test_create_gbif_validator_custom_config(self):
        """Test creating validator with custom config."""
        config = {
            "min_confidence_score": 0.90,
            "enable_fuzzy_matching": False,
            "enable_occurrence_validation": True,
        }

        validator = create_gbif_validator(config)

        assert validator.min_confidence_score == 0.90
        assert validator.enable_fuzzy_matching is False
        assert validator.enable_occurrence_validation is True


class TestValidatorIntegration:
    """Integration tests for validator with multiple operations."""

    @patch("src.review.validators.species")
    def test_validate_complete_record(self, mock_species, validator):
        """Test validating a complete specimen record."""
        # Mock GBIF taxonomy response
        mock_species.name_backbone.return_value = {
            "usageKey": 123456,
            "scientificName": "Artemisia frigida Willd.",
            "canonicalName": "Artemisia frigida",
            "rank": "SPECIES",
            "status": "ACCEPTED",
            "confidence": 95,
            "matchType": "EXACT",
            "kingdom": "Plantae",
            "family": "Asteraceae",
        }

        record = {
            "scientificName": "Artemisia frigida Willd.",
            "decimalLatitude": 50.0,
            "decimalLongitude": -105.0,
        }

        # Verify taxonomy
        updated_record, tax_metadata = validator.verify_taxonomy(record)
        assert tax_metadata["gbif_taxonomy_verified"] is True

        # Verify locality
        updated_record, loc_metadata = validator.verify_locality(updated_record)
        assert loc_metadata["gbif_locality_verified"] is True

        # Both validations should pass
        assert updated_record["gbif_accepted_name"] == "Artemisia frigida"

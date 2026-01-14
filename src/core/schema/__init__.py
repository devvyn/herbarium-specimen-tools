"""
Darwin Core schema definitions for herbarium specimens.

Based on TDWG Darwin Core standard with herbarium-specific extensions.
These definitions are shared across extraction and review workflows.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Required fields for specimen completeness scoring
DWC_REQUIRED_FIELDS = [
    "catalogNumber",
    "scientificName",
    "eventDate",
    "recordedBy",
    "country",
    "stateProvince",
    "locality",
]

# All Darwin Core fields tracked by herbarium digitization projects
DWC_ALL_FIELDS = [
    # Core identification
    "occurrenceID",
    "catalogNumber",
    "otherCatalogNumbers",
    "institutionCode",
    "collectionCode",
    # Collection event
    "recordedBy",
    "recordNumber",
    "eventDate",
    "verbatimEventDate",
    # Location
    "country",
    "stateProvince",
    "county",
    "municipality",
    "locality",
    "verbatimLocality",
    "habitat",
    "decimalLatitude",
    "decimalLongitude",
    "minimumElevationInMeters",
    "maximumElevationInMeters",
    # Taxonomy
    "scientificName",
    "scientificNameAuthorship",
    "family",
    "genus",
    "specificEpithet",
    "infraspecificEpithet",
    "taxonRank",
    # Identification
    "identifiedBy",
    "dateIdentified",
    "identificationRemarks",
    "typeStatus",
    # Additional
    "basisOfRecord",
    "preparations",
    "associatedTaxa",
    "occurrenceRemarks",
]


@dataclass
class DwcRecord:
    """
    Darwin Core record for a herbarium specimen.

    All fields are optional strings with confidence scores.
    Provides methods for completeness calculation and serialization.
    """

    # Core identification
    occurrenceID: str | None = None
    catalogNumber: str | None = None
    otherCatalogNumbers: str | None = None
    institutionCode: str | None = None
    collectionCode: str | None = None

    # Collection event
    recordedBy: str | None = None
    recordNumber: str | None = None
    eventDate: str | None = None
    verbatimEventDate: str | None = None

    # Location
    country: str | None = None
    stateProvince: str | None = None
    county: str | None = None
    municipality: str | None = None
    locality: str | None = None
    verbatimLocality: str | None = None
    habitat: str | None = None
    decimalLatitude: str | None = None
    decimalLongitude: str | None = None
    minimumElevationInMeters: str | None = None
    maximumElevationInMeters: str | None = None

    # Taxonomy
    scientificName: str | None = None
    scientificNameAuthorship: str | None = None
    family: str | None = None
    genus: str | None = None
    specificEpithet: str | None = None
    infraspecificEpithet: str | None = None
    taxonRank: str | None = None

    # Identification
    identifiedBy: str | None = None
    dateIdentified: str | None = None
    identificationRemarks: str | None = None
    typeStatus: str | None = None

    # Additional
    basisOfRecord: str | None = None
    preparations: str | None = None
    associatedTaxa: str | None = None
    occurrenceRemarks: str | None = None

    # Confidence scores per field (not part of DwC standard)
    _confidence: dict[str, float] = field(default_factory=dict)

    # Validation flags
    _flags: list[str] = field(default_factory=list)

    def set_field(self, field_name: str, value: str, confidence: float = 1.0):
        """Set a field value with confidence score."""
        if hasattr(self, field_name):
            setattr(self, field_name, value)
            self._confidence[field_name] = confidence

    def get_confidence(self, field_name: str) -> float:
        """Get confidence score for a field."""
        return self._confidence.get(field_name, 0.0)

    def get_completeness(self, required_fields: list[str] | None = None) -> float:
        """Calculate completeness as percentage of required fields present."""
        fields = required_fields or DWC_REQUIRED_FIELDS
        present = sum(1 for f in fields if getattr(self, f, None))
        return (present / len(fields)) * 100 if fields else 0.0

    def get_average_confidence(self) -> float:
        """Calculate average confidence across all fields with values."""
        if not self._confidence:
            return 0.0
        return sum(self._confidence.values()) / len(self._confidence)

    def to_dict(self, include_empty: bool = False) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        for field_name in DWC_ALL_FIELDS:
            value = getattr(self, field_name, None)
            if include_empty or value:
                result[field_name] = value or ""
        return result

    def to_dict_with_confidence(self) -> dict[str, dict[str, Any]]:
        """Convert to dictionary with confidence scores (for mobile API)."""
        result = {}
        for field_name in DWC_ALL_FIELDS:
            value = getattr(self, field_name, None)
            if value:
                result[field_name] = {
                    "value": value,
                    "confidence": self._confidence.get(field_name, 0.0),
                }
        return result

    @classmethod
    def from_extraction(cls, data: dict[str, Any]) -> "DwcRecord":
        """Create from extraction output (with confidence scores).

        Handles both formats:
        - Simple: {"catalogNumber": "12345", ...}
        - With confidence: {"catalogNumber": {"value": "12345", "confidence": 0.9}, ...}
        """
        record = cls()

        for field_name, field_data in data.items():
            if not hasattr(record, field_name):
                continue

            if isinstance(field_data, dict):
                # Format with confidence
                value = field_data.get("value", "")
                confidence = field_data.get("confidence", 0.0)
            else:
                # Simple format
                value = str(field_data) if field_data else ""
                confidence = 0.5  # Default confidence for legacy data

            if value:
                record.set_field(field_name, value, confidence)

        return record

    def add_flag(self, flag: str):
        """Add a validation flag."""
        if flag not in self._flags:
            self._flags.append(flag)

    @property
    def flags(self) -> str:
        """Get flags as semicolon-separated string."""
        return ";".join(self._flags)


__all__ = [
    "DWC_REQUIRED_FIELDS",
    "DWC_ALL_FIELDS",
    "DwcRecord",
]

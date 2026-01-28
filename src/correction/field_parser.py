"""Field parser for herbarium specimen labels - Version 2.

Improved parsing with better pattern matching and span-based extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LocalityData:
    """Structured data extracted from locality field."""

    locality: str | None = None
    recorded_by: str | None = None
    record_number: str | None = None
    catalog_number: str | None = None
    event_date_raw: str | None = None
    elevation_raw: str | None = None
    habitat: str | None = None
    event_remarks: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


def clean_text(text: str) -> str:
    """Clean OCR artifacts from text."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    text = text.replace("·", ".")
    text = text.replace("•", ".")
    return text


def parse_locality_field(locality_text: str) -> LocalityData:
    """Parse compound locality field into structured components.

    Uses span-based extraction to properly remove matched patterns.
    """
    if not locality_text:
        return LocalityData()

    result = LocalityData()
    extracted_spans = []  # (start, end, field_name)

    # Habitat pattern (do first - at end)
    match = re.search(r"HABITAT:\s*(.+?)$", locality_text, re.IGNORECASE)
    if match:
        result.habitat = clean_text(match.group(1))
        extracted_spans.append((match.start(), match.end()))

    # Elevation pattern
    match = re.search(r"(?:ELEVATION|ELEV)[:\.]?\s*([^H]+?)(?=\s+(?:HABITAT|$))", locality_text, re.IGNORECASE)
    if match:
        result.elevation_raw = clean_text(match.group(1))
        extracted_spans.append((match.start(), match.end()))

    # Date pattern - match until ELEVATION/HABITAT keywords or end of string
    match = re.search(r"DATE:\s*([^\n]+?)(?:\s+(?:ELEVATION|ELEV|HABITAT)|$)", locality_text, re.IGNORECASE)
    if match:
        # Extract just the date part (group 1)
        result.event_date_raw = clean_text(match.group(1))
        extracted_spans.append((match.start(), match.end()))

    # Catalog number pattern - match "Nº:" or "No:" with optional "COLL." prefix
    match = re.search(r"(?:COLL\.|Coll\.)?\s*(?:Nº|No\.?|NO):\s*(\w+)", locality_text, re.IGNORECASE)
    if match:
        result.catalog_number = clean_text(match.group(1))
        extracted_spans.append((match.start(), match.end()))

    # Collector pattern
    match = re.search(r"(?:COLL|Collector):\s*([A-Z][^\n:]+?)(?=\s+(?:COLL\.|Nº|No\.|DATE|ELEVATION|HABITAT|$))", locality_text, re.IGNORECASE)
    if match:
        result.recorded_by = clean_text(match.group(1))
        extracted_spans.append((match.start(), match.end()))

    # Remove extracted spans to get locality
    if extracted_spans:
        # Sort by position (reverse to avoid index shifting)
        extracted_spans.sort(reverse=True)

        result_chars = list(locality_text)
        for start, end in extracted_spans:
            result_chars[start:end] = [' '] * (end - start)  # Replace with spaces

        result.locality = clean_text(''.join(result_chars))
    else:
        result.locality = clean_text(locality_text)

    # If locality extraction failed, try from beginning
    if not result.locality or len(result.locality) < 3:
        match = re.match(r"^([^C]+?)(?=\s+(?:COLL|Nº))", locality_text, re.IGNORECASE)
        if match:
            result.locality = clean_text(match.group(1))

    return result


def parse_recorded_by_field(recorded_by_text: str) -> LocalityData:
    """Parse recordedBy field that may contain non-collector data."""
    if not recorded_by_text:
        return LocalityData()

    # If it looks like a proper name, return as-is
    if re.match(r"^[A-Z]\.\s+[A-Z][a-z]+$", recorded_by_text):
        return LocalityData(recorded_by=recorded_by_text)

    # Otherwise parse as compound field
    return parse_locality_field(recorded_by_text)


def merge_locality_data(primary: LocalityData, secondary: LocalityData) -> LocalityData:
    """Merge two LocalityData objects, preferring non-None values from primary."""
    merged = LocalityData()

    for field in [
        "locality",
        "recorded_by",
        "record_number",
        "catalog_number",
        "event_date_raw",
        "elevation_raw",
        "habitat",
        "event_remarks",
    ]:
        primary_val = getattr(primary, field)
        secondary_val = getattr(secondary, field)
        setattr(merged, field, primary_val if primary_val else secondary_val)

    return merged


__all__ = [
    "LocalityData",
    "parse_locality_field",
    "parse_recorded_by_field",
    "merge_locality_data",
    "clean_text",
]

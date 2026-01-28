"""Herbarium data correction tools.

This module provides tools for correcting OCR errors and field misidentification
in Darwin Core specimen records.

Components:
- field_parser: Re-parse compound fields (locality → locality + collector + date)
- name_matcher: Fuzzy match scientific names against GBIF
- date_parser: Parse dates with OCR error tolerance
- collector_normalizer: Normalize collector name variants
- pipeline: Orchestrate all corrections
"""

from .field_parser import (
    LocalityData,
    parse_locality_field,
)

__all__ = [
    "parse_locality_field",
    "LocalityData",
]

__version__ = "0.1.0"

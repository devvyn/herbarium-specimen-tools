"""
Darwin Core (DwC) module for herbarium specimen data.

Provides standardized field handling, normalization, and validation
based on Darwin Core and TDWG standards.
"""

from .normalize import normalize_country, normalize_institution, normalize_province
from .schema import DWC_ALL_FIELDS, DWC_REQUIRED_FIELDS, DwcRecord

__all__ = [
    "DwcRecord",
    "DWC_REQUIRED_FIELDS",
    "DWC_ALL_FIELDS",
    "normalize_institution",
    "normalize_province",
    "normalize_country",
]

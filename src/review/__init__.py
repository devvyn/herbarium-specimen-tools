"""
Review Module - Specimen Review Engine and Mobile API

Provides review engine for quality control and mobile-optimized API
for field curation workflows.
"""

from .engine import ReviewEngine, ReviewStatus, ReviewPriority, SpecimenReview
from .validators import GBIFValidator, create_gbif_validator

# Lazy import to avoid JWT requirement when only using engine classes
def create_mobile_app(*args, **kwargs):
    """Lazy loader for mobile_api to defer JWT requirement."""
    from .mobile_api import create_mobile_app as _create_mobile_app
    return _create_mobile_app(*args, **kwargs)

__all__ = [
    "ReviewEngine",
    "ReviewStatus",
    "ReviewPriority",
    "SpecimenReview",
    "GBIFValidator",
    "create_gbif_validator",
    "create_mobile_app",
]

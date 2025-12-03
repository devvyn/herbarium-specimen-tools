"""
Extraction module for herbarium specimen data.

Provides confidence-based routing for optimal accuracy/cost balance.
"""

from .confidence_router import ConfidenceRouter

__all__ = ["ConfidenceRouter"]

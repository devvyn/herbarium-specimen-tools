"""
Rules-based field extraction from OCR text.

Uses regex patterns and heuristics to extract Darwin Core fields
from plain text without AI.
"""

import re
from datetime import datetime


class RulesEngine:
    """
    Extract Darwin Core fields using pattern matching rules.

    Fast, deterministic, and free - but less intelligent than AI.
    """

    # Canadian provinces (for AAFC specimens)
    PROVINCES = {
        "SK": "Saskatchewan",
        "AB": "Alberta",
        "MB": "Manitoba",
        "BC": "British Columbia",
        "SASK": "Saskatchewan",
        "ALTA": "Alberta",
        "MAN": "Manitoba",
        "SASKATCHEWAN": "Saskatchewan",
        "ALBERTA": "Alberta",
        "MANITOBA": "Manitoba",
    }

    # Common institutional codes
    INSTITUTIONS = {
        "AAFC": "Agriculture and Agri-Food Canada",
        "REGINA": "Regina Research Station",
    }

    def __init__(self):
        """Initialize rules engine."""
        self.stats = {"extractions": 0, "fields_extracted": 0}

    def extract_fields(self, ocr_text: str) -> tuple[dict[str, str], dict[str, float]]:
        """
        Extract Darwin Core fields from OCR text using rules.

        Args:
            ocr_text: Plain text from OCR

        Returns:
            Tuple of (dwc_fields, confidence_scores)
        """
        self.stats["extractions"] += 1

        dwc_fields = {}
        confidences = {}

        # Clean text
        text = self._clean_text(ocr_text)

        # Extract each field type
        extractors = [
            ("catalogNumber", self._extract_catalog_number),
            ("scientificName", self._extract_scientific_name),
            ("eventDate", self._extract_date),
            ("recordedBy", self._extract_collector),
            ("country", self._extract_country),
            ("stateProvince", self._extract_province),
            ("locality", self._extract_locality),
            ("institutionCode", self._extract_institution),
            ("collectionCode", self._extract_collection),
            ("habitat", self._extract_habitat),
        ]

        for field_name, extractor in extractors:
            value, confidence = extractor(text)
            if value:
                dwc_fields[field_name] = value
                confidences[field_name] = confidence
                self.stats["fields_extracted"] += 1

        return dwc_fields, confidences

    def _clean_text(self, text: str) -> str:
        """Clean and normalize OCR text."""
        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)
        # Remove multiple newlines
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    def _extract_catalog_number(self, text: str) -> tuple[str, float]:
        """Extract catalog/accession number."""
        # Pattern: 3-6 digits, possibly with leading zeros
        patterns = [
            (r"\b(\d{3,6})\b", 0.80),  # Simple digits
            (r"No\.?\s*(\d{3,6})", 0.85),  # "No. 12345"
            (r"Cat\.?\s*(?:No\.?)?\s*(\d{3,6})", 0.90),  # "Cat. No. 12345"
            (r"Accession\s*(?:No\.?)?\s*(\d{3,6})", 0.90),
        ]

        for pattern, confidence in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1), confidence

        return "", 0.0

    def _extract_scientific_name(self, text: str) -> tuple[str, float]:
        """Extract scientific name (genus + species + authority)."""
        # Pattern: Capitalized word + lowercase word(s) + optional authority
        # Example: "Artemisia frigida Willd."

        pattern = r"\b([A-Z][a-z]+\s+[a-z]+(?:\s+[a-z]+)?(?:\s+[A-Z][a-z]*\.?)?)(?:\s|$)"

        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            # Simple validation: must have at least genus + species
            parts = name.split()
            if len(parts) >= 2:
                return name, 0.75  # Moderate confidence for pattern match
        return "", 0.0

    def _extract_date(self, text: str) -> tuple[str, float]:
        """Extract collection date."""
        # Multiple date formats
        patterns = [
            # ISO format: 1975-07-15
            (r"(\d{4}-\d{2}-\d{2})", 0.95, lambda m: m.group(1)),
            # Month DD, YYYY: July 15, 1975 or Jul. 15, 1975
            (
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
                0.85,
                lambda m: self._normalize_date(m.group(1)),
            ),
            # DD Mon YYYY: 15 Jul 1975
            (
                r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})",
                0.85,
                lambda m: self._normalize_date(m.group(1)),
            ),
            # Just year: 1975
            (r"\b(19\d{2}|20\d{2})\b", 0.70, lambda m: m.group(1)),
        ]

        for pattern, confidence, normalizer in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return normalizer(match), confidence
                except Exception:
                    continue

        return "", 0.0

    def _normalize_date(self, date_str: str) -> str:
        """Normalize various date formats to ISO 8601."""
        # Try to parse and convert to ISO format
        try:
            # Try common formats
            for fmt in [
                "%B %d, %Y",
                "%b. %d, %Y",
                "%b %d, %Y",
                "%d %B %Y",
                "%d %b %Y",
            ]:
                try:
                    dt = datetime.strptime(date_str.replace(",", "").strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        except Exception:
            pass

        return date_str  # Return original if parsing fails

    def _extract_collector(self, text: str) -> tuple[str, float]:
        """Extract collector name."""
        # Patterns for collector names
        patterns = [
            (r"Collected\s+by\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)(?:\s+[A-Z][a-z]+)?)", 0.85),
            (r"Collector:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)(?:\s+[A-Z][a-z]+)?)", 0.85),
            (r"Leg\.?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?))", 0.80),
        ]

        for pattern, confidence in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip(), confidence

        return "", 0.0

    def _extract_country(self, text: str) -> tuple[str, float]:
        """Extract country."""
        if re.search(r"\bCanada\b", text, re.IGNORECASE):
            return "Canada", 0.95
        return "", 0.0

    def _extract_province(self, text: str) -> tuple[str, float]:
        """Extract Canadian province."""
        for abbrev, full_name in self.PROVINCES.items():
            if re.search(rf"\b{abbrev}\b", text, re.IGNORECASE):
                return full_name, 0.90
        return "", 0.0

    def _extract_locality(self, text: str) -> tuple[str, float]:
        """Extract locality/location description."""
        # Look for common locality patterns
        patterns = [
            (r"(?:Near|At|From)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})", 0.70),
            (r"Locality:?\s+(.+?)(?:\n|$)", 0.75),
        ]

        for pattern, confidence in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                locality = match.group(1).strip()
                if len(locality) > 5:  # Minimum reasonable length
                    return locality, confidence

        return "", 0.0

    def _extract_institution(self, text: str) -> tuple[str, float]:
        """Extract institution code."""
        for code in self.INSTITUTIONS.keys():
            if re.search(rf"\b{code}\b", text, re.IGNORECASE):
                return code, 0.90
        return "", 0.0

    def _extract_collection(self, text: str) -> tuple[str, float]:
        """Extract collection code."""
        # REGINA is common for AAFC
        if re.search(r"\bREGINA\b", text, re.IGNORECASE):
            return "REGINA", 0.90
        return "", 0.0

    def _extract_habitat(self, text: str) -> tuple[str, float]:
        """Extract habitat description."""
        # Look for habitat keywords
        habitat_keywords = [
            "prairie",
            "roadside",
            "ditch",
            "field",
            "forest",
            "meadow",
            "wetland",
        ]

        for keyword in habitat_keywords:
            if keyword in text.lower():
                # Try to extract sentence containing habitat
                pattern = rf"([^.]*{keyword}[^.]*)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip(), 0.65

        return "", 0.0

    def get_stats(self) -> dict:
        """Get extraction statistics."""
        avg_fields = (
            self.stats["fields_extracted"] / self.stats["extractions"]
            if self.stats["extractions"] > 0
            else 0
        )

        return {
            **self.stats,
            "avg_fields_per_extraction": round(avg_fields, 1),
            "cost_per_extraction": 0.0,  # Free!
        }

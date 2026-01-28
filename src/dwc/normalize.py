"""
Field normalization utilities for Darwin Core records.

Standardizes institution codes, geographic names, and vocabulary terms
to canonical forms for consistency and GBIF compatibility.
"""


# Canadian province/territory normalization
PROVINCE_ALIASES = {
    # Full names
    "alberta": "Alberta",
    "british columbia": "British Columbia",
    "manitoba": "Manitoba",
    "new brunswick": "New Brunswick",
    "newfoundland": "Newfoundland and Labrador",
    "newfoundland and labrador": "Newfoundland and Labrador",
    "northwest territories": "Northwest Territories",
    "nova scotia": "Nova Scotia",
    "nunavut": "Nunavut",
    "ontario": "Ontario",
    "prince edward island": "Prince Edward Island",
    "quebec": "Quebec",
    "québec": "Quebec",
    "saskatchewan": "Saskatchewan",
    "yukon": "Yukon",
    "yukon territory": "Yukon",

    # Abbreviations
    "ab": "Alberta",
    "bc": "British Columbia",
    "mb": "Manitoba",
    "nb": "New Brunswick",
    "nl": "Newfoundland and Labrador",
    "nfld": "Newfoundland and Labrador",
    "nt": "Northwest Territories",
    "nwt": "Northwest Territories",
    "ns": "Nova Scotia",
    "nu": "Nunavut",
    "on": "Ontario",
    "ont": "Ontario",
    "pe": "Prince Edward Island",
    "pei": "Prince Edward Island",
    "qc": "Quebec",
    "que": "Quebec",
    "sk": "Saskatchewan",
    "sask": "Saskatchewan",
    "yt": "Yukon",

    # Common OCR errors
    "saskatchevan": "Saskatchewan",
    "saskatchwan": "Saskatchewan",
    "albertà": "Alberta",
    "ontarìo": "Ontario",
}

# Country normalization
COUNTRY_ALIASES = {
    "canada": "Canada",
    "can": "Canada",
    "ca": "Canada",
    "united states": "United States",
    "united states of america": "United States",
    "usa": "United States",
    "us": "United States",
    "u.s.a.": "United States",
    "u.s.": "United States",
    "mexico": "Mexico",
    "mex": "Mexico",
    "mx": "Mexico",
}

# Institution code normalization (AAFC and related)
INSTITUTION_ALIASES = {
    # Agriculture and Agri-Food Canada
    "aafc": "AAFC",
    "agriculture and agri-food canada": "AAFC",
    "agriculture canada": "AAFC",
    "agr. canada": "AAFC",

    # Specific AAFC collections
    "dao": "DAO",  # National Collection of Vascular Plants
    "daom": "DAOM",  # National Mycological Herbarium
    "daomc": "DAOMC",  # Mycological collection

    # Other Canadian institutions
    "can": "CAN",  # Canadian Museum of Nature
    "canm": "CANM",
    "mt": "MT",  # Université de Montréal
    "qfa": "QFA",  # Université Laval
    "ubc": "UBC",  # University of British Columbia
    "v": "V",  # Royal BC Museum
    "win": "WIN",  # University of Manitoba

    # Common variations
    "a.a.f.c.": "AAFC",
    "d.a.o.": "DAO",
}


def normalize_province(value: str | None) -> str:
    """
    Normalize a province/state name to standard form.

    Handles abbreviations, full names, and common OCR errors.

    Args:
        value: Raw province string from extraction

    Returns:
        Normalized province name, or original if no match
    """
    if not value:
        return ""

    # Clean and lowercase for lookup
    cleaned = value.strip().lower()

    # Remove common prefixes/suffixes
    cleaned = cleaned.replace("province of ", "")
    cleaned = cleaned.replace(", canada", "")

    return PROVINCE_ALIASES.get(cleaned, value.strip())


def normalize_country(value: str | None) -> str:
    """
    Normalize a country name to standard form.

    Args:
        value: Raw country string from extraction

    Returns:
        Normalized country name, or original if no match
    """
    if not value:
        return ""

    cleaned = value.strip().lower()
    return COUNTRY_ALIASES.get(cleaned, value.strip())


def normalize_institution(value: str | None) -> str:
    """
    Normalize an institution code to standard form.

    Args:
        value: Raw institution code from extraction

    Returns:
        Normalized institution code, or original if no match
    """
    if not value:
        return ""

    cleaned = value.strip().lower()
    return INSTITUTION_ALIASES.get(cleaned, value.strip().upper())


def normalize_date(value: str | None) -> str:
    """
    Normalize a date string to ISO 8601 format (YYYY-MM-DD).

    Handles common date formats found on herbarium labels.

    Args:
        value: Raw date string from extraction

    Returns:
        ISO 8601 date string, or original if parsing fails
    """
    if not value:
        return ""

    import re
    from datetime import datetime

    value = value.strip()

    # Already ISO format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value

    # Common formats to try
    formats = [
        "%d %B %Y",      # "15 July 1969"
        "%d %b %Y",      # "15 Jul 1969"
        "%B %d, %Y",     # "July 15, 1969"
        "%b %d, %Y",     # "Jul 15, 1969"
        "%d/%m/%Y",      # "15/07/1969"
        "%m/%d/%Y",      # "07/15/1969"
        "%Y/%m/%d",      # "1969/07/15"
        "%d-%m-%Y",      # "15-07-1969"
        "%Y",            # "1969" (year only)
        "%B %Y",         # "July 1969"
        "%b %Y",         # "Jul 1969"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            # Return appropriate precision
            if fmt in ["%Y"]:
                return dt.strftime("%Y")
            elif fmt in ["%B %Y", "%b %Y"]:
                return dt.strftime("%Y-%m")
            else:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Return original if no format matches
    return value


def normalize_elevation(value: str | None) -> int | None:
    """
    Extract elevation in meters from a string.

    Handles various formats: "500m", "500 m", "1500 ft", etc.

    Args:
        value: Raw elevation string

    Returns:
        Elevation in meters as integer, or None if parsing fails
    """
    if not value:
        return None

    import re

    value = value.strip().lower()

    # Extract number and unit
    match = re.search(r"(\d+(?:\.\d+)?)\s*(m|meters?|ft|feet|')?", value)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2) or "m"

    # Convert to meters if needed
    if unit in ["ft", "feet", "'"]:
        number = number * 0.3048

    return int(round(number))


def normalize_catalog_number(value: str | None) -> str:
    """
    Clean and normalize a catalog/collection number.

    Removes common prefixes and standardizes format.

    Args:
        value: Raw catalog number from extraction

    Returns:
        Cleaned catalog number
    """
    if not value:
        return ""

    import re

    value = value.strip()

    # Remove common prefixes
    prefixes = [
        r"^(no\.?|n[°º]\.?|coll\.?\s*n[°º]?\.?|cat\.?\s*n[°º]?\.?)\s*:?\s*",
        r"^#\s*",
    ]

    for prefix in prefixes:
        value = re.sub(prefix, "", value, flags=re.IGNORECASE)

    # Remove leading zeros if purely numeric
    if value.isdigit():
        value = value.lstrip("0") or "0"

    return value.strip()

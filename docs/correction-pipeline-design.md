# Herbarium Data Correction Pipeline - Architecture Design

**Created:** 2025-12-03
**Status:** Design Phase
**Purpose:** Correct OCR errors and field misidentification in Darwin Core extractions

---

## Problem Analysis

### Current Data Quality (40 AAFC Specimens Analyzed)

**Critical Fields - Accuracy:**
- ✅ **Catalog Number**: 72% confidence, 90% complete (best field)
- ⚠️ **Scientific Name**: 38% confidence, 47% complete, significant OCR errors
- ❌ **Event Date**: 0% confidence, 0% complete (total failure)
- ❌ **Recorded By**: 26% confidence, 32% complete, wrong data (contains catalog numbers, not names)
- ⚠️ **Locality**: 36% confidence, 45% complete, contains mixed data

### Root Cause: Field Misidentification

The extraction pipeline (OCR → Darwin Core mapping) is placing text fragments in incorrect fields:

**Example Specimen:**
```
recordedBy: "Nº:13259 DATE: 111 kugust 1969 ELEVATION"  ← NOT A COLLECTOR NAME
locality: "Saskatchehan Landing COLL: J. Looten COLL.Nº:13259 DATE: 111 kugust 1969..."
                                      ↑ ACTUAL COLLECTOR    ↑ ACTUAL DATE
```

**Key Findings:**
1. Collector names and dates are in the `locality` field, not their proper fields
2. `recordedBy` contains catalog metadata instead of collector names
3. Scientific names have OCR errors: "denecio canua" → "Senecio canus"
4. Dates not extracted: "111 kugust 1969" → should be "1969-08-11"

---

## Correction Pipeline Architecture

### Phase 1: Field Re-parsing (CRITICAL)

**Input:** Darwin Core records with `locality` field containing mixed data
**Output:** Properly separated fields (locality, recordedBy, eventDate, habitat, elevation)

**Strategy:**
```python
# Locality field typically contains:
# "[Location] COLL: [Collector] COLL.Nº:[Number] DATE: [Date] ELEVATION: [Elev] HABITAT: [Habitat]"

def parse_locality_field(locality_text):
    """Extract structured data from compound locality field."""
    # Pattern matching for common label structures
    patterns = {
        'collector': r'COLL:\s*([A-Z][^C]+?)(?:COLL\.|DATE|ELEVATION|HABITAT|$)',
        'date': r'DATE:\s*([^E]+?)(?:ELEVATION|HABITAT|$)',
        'elevation': r'ELEVATION:\s*([^H]+?)(?:HABITAT|$)',
        'habitat': r'HABITAT:\s*(.+?)$',
        'catalog': r'COLL\.Nº:\s*(\w+)',
    }
    # Return separated fields
```

### Phase 2: OCR Error Correction

#### 2.1 Scientific Name Fuzzy Matching

**Strategy:** Fuzzy match against GBIF Taxonomic Backbone

```python
from pygbif import species

def correct_scientific_name(raw_name, confidence_threshold=0.7):
    """
    Fuzzy match scientific name against GBIF.

    Examples:
    - "denecio canua" → "Senecio canus" (Levenshtein distance)
    - "Stipe viridula" → "Stipa viridula" (single char missing)
    - "lahlonbergla cuspi" → "Muhlenbergia cuspidata" (more complex)
    """
    # Use GBIF species name matching API
    # Return: (corrected_name, gbif_key, match_confidence, taxonomy_metadata)
```

**GBIF API:**
- Endpoint: `https://api.gbif.org/v1/species/match`
- Supports fuzzy matching with confidence scores
- Returns full taxonomy hierarchy

#### 2.2 Date Parsing

**Strategy:** Parse various date formats with OCR error tolerance

```python
import dateparser
from datetime import datetime

def parse_herbarium_date(date_text):
    """
    Parse dates from OCR text with common errors.

    Examples:
    - "111 kugust 1969" → "1969-08-11" (OCR: "kugust"="August", "111"="11")
    - "June 1969" → "1969-06"
    - "15/7/1965" → "1965-07-15"
    - "July-August 1970" → "1970-07" (midpoint or range)
    """
    # Month name OCR corrections
    month_corrections = {
        'kugust': 'august',
        'jume': 'june',
        'septeber': 'september',
        # ... more OCR variants
    }
    # Day number OCR corrections
    # Return ISO 8601 format: YYYY-MM-DD or YYYY-MM or YYYY
```

#### 2.3 Collector Name Normalization

**Strategy:** Deduplicate collector name variants

```python
from difflib import SequenceMatcher

def normalize_collector_name(raw_collector, known_collectors_db):
    """
    Normalize collector names with OCR variants.

    Examples:
    - "J. Looten" → "J. Looman"
    - "J. Loonan" → "J. Looman"
    - "J.Looman" → "J. Looman" (spacing)
    """
    # Fuzzy match against known collector database
    # Return: (normalized_name, confidence)
```

### Phase 3: Validation & Quality Metrics

**Use existing AAFC QC infrastructure:**
- `qc.confidence_validator.ConfidenceValidator` - per-field thresholds
- `qc.GbifLookup` - taxonomy/locality validation
- Generate review queue for low-confidence corrections

```python
from qc import ConfidenceValidator, batch_validate

def validate_corrections(original_record, corrected_record):
    """
    Compare original vs corrected data.
    Track which fields were corrected and confidence improvement.
    """
    validator = ConfidenceValidator()
    # Return ValidationResult with improvement metrics
```

---

## Implementation Plan

### Module Structure

```
herbarium-specimen-tools/
├── src/
│   └── correction/
│       ├── __init__.py
│       ├── field_parser.py          # Phase 1: Locality re-parsing
│       ├── name_matcher.py          # Phase 2.1: Scientific name fuzzy match
│       ├── date_parser.py           # Phase 2.2: Date parsing
│       ├── collector_normalizer.py  # Phase 2.3: Collector name normalization
│       ├── pipeline.py              # Orchestrate all corrections
│       └── validation.py            # Quality metrics
├── tests/
│   └── correction/
│       ├── test_field_parser.py
│       ├── test_name_matcher.py
│       ├── test_date_parser.py
│       └── test_pipeline.py
└── examples/
    └── correction_workflow.py       # End-to-end example
```

### CLI Interface

```bash
# Run correction pipeline on AAFC data
python -m correction.pipeline \
  --input ~/path/to/aafc/production_run_*/raw.jsonl \
  --output ~/path/to/corrected/ \
  --enable-gbif-validation \
  --generate-report

# Options:
#   --dry-run: Show proposed corrections without applying
#   --fields: Specify which corrections to apply (default: all)
#   --confidence-threshold: Minimum confidence for auto-correction (default: 0.7)
```

### Integration with AAFC Pipeline

The corrected data should be exported as:
1. **Corrected raw.jsonl** - Full provenance of corrections
2. **Corrected occurrence.csv** - Darwin Core compliant
3. **Correction report** - Per-specimen changes and confidence improvements
4. **DwC-A export** - Ready for Excel review by office workers

---

## Testing Strategy

### Unit Tests

Each module has comprehensive unit tests:

```python
# test_field_parser.py
def test_parse_locality_with_collector_and_date():
    locality = "Saskatchewan Landing COLL: J. Looman DATE: 11 August 1969"
    result = parse_locality_field(locality)
    assert result['recordedBy'] == "J. Looman"
    assert result['eventDate'] == "1969-08-11"
    assert result['locality'] == "Saskatchewan Landing"
```

### Integration Tests

Test with actual AAFC specimen data:
- 40 specimens from Dec 2 processing runs
- Known error patterns from analysis
- Expected corrections validated manually

### Regression Tests

Ensure corrections don't introduce new errors:
- Original correct data preserved
- Only low-confidence fields corrected
- High-confidence data left unchanged

---

## Success Metrics

### Quantitative Goals

**Before Correction (Current State):**
- Scientific Name: 47% complete, 38% confidence
- Event Date: 0% complete, 0% confidence
- Recorded By: 32% complete, 26% confidence
- Locality: 45% complete, 36% confidence

**After Correction (Target):**
- Scientific Name: 90%+ complete, 80%+ confidence
- Event Date: 85%+ complete, 70%+ confidence
- Recorded By: 90%+ complete, 85%+ confidence
- Locality: 90%+ complete, 80%+ confidence

### Qualitative Goals

- Excel-reviewable DwC-A export with clear field labels
- Office workers can validate catalog numbers and handwritten labels
- Provenance tracking: which fields were corrected and why
- Human review queue: specimens requiring manual validation

---

## Dependencies

### Required Libraries

```python
# Scientific name matching
pygbif>=0.6.0              # GBIF API client
fuzzywuzzy>=0.18.0         # Fuzzy string matching
python-Levenshtein>=0.12.0 # Fast string distance

# Date parsing
dateparser>=1.1.0          # Parse dates from natural language
python-dateutil>=2.8.0     # Date utilities

# Data processing
pandas>=2.0.0              # DataFrame operations
numpy>=1.24.0              # Numerical operations

# Validation
requests>=2.31.0           # HTTP requests for GBIF API
```

### AAFC Pipeline Integration

Leverage existing QC infrastructure:
- `qc.confidence_validator` - Field confidence thresholds
- `qc.GbifLookup` - GBIF validation
- `dwc.archive` - DwC-A export
- `cli.py export` - Archive generation

---

## Open Questions

1. **Collector Database**: Where to source known collector name variations?
   - Option A: Build from AAFC historical data
   - Option B: Use GBIF contributor database
   - Option C: Manual curation + fuzzy matching

2. **Correction Confidence**: When to auto-correct vs queue for human review?
   - High confidence (>0.8): Auto-correct
   - Medium confidence (0.5-0.8): Auto-correct + flag for review
   - Low confidence (<0.5): Queue for human review only

3. **Scientific Name Authority**: Which taxonomic backbone?
   - Primary: GBIF Backbone Taxonomy
   - Fallback: Plants of the World Online (POWO)
   - User-configurable per institution

4. **Date Uncertainty**: How to represent partial dates?
   - "June 1969" → eventDate="1969-06", eventDateUncertaintyInDays=15
   - "Summer 1970" → eventDate="1970-07-15", eventDateUncertaintyInDays=45

---

## Next Steps

1. ✅ **Completed**: Analyze 40 specimens, identify error patterns
2. ✅ **Completed**: Design correction pipeline architecture (this document)
3. **Next**: Implement `field_parser.py` - locality field re-parsing
4. **Next**: Implement `name_matcher.py` - GBIF fuzzy matching
5. **Next**: Implement `date_parser.py` - date parsing with OCR error tolerance
6. **Next**: Build `pipeline.py` - orchestrate corrections
7. **Next**: Test with 40 AAFC specimens
8. **Next**: Generate corrected DwC-A for Excel review

---

## References

- [Darwin Core Standard](https://dwc.tdwg.org/)
- [GBIF Species Matching API](https://www.gbif.org/developer/species)
- [GBIF Backbone Taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c)
- AAFC Herbarium QC Infrastructure: `~/Documents/pinned/active-projects/aafc-herbarium-dwc-extraction-2025/qc/`

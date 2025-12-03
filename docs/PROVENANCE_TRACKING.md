# Provenance Tracking Documentation

## Overview

Comprehensive provenance tracking ensures scientific reproducibility and quality control for herbarium specimen extractions. Every extraction decision is documented with full context.

---

## Current State (AAFC Extractions)

### What's Tracked Now

```json
{
  "image": "specimen_001.jpg",
  "specimen_id": "sha256_hash",
  "model": "vision-api",
  "provider": "apple",
  "extraction_method": "simple",
  "ocr_engine": "vision",
  "timestamp": "2025-10-31T21:56:16.591399+00:00",
  "dwc": {
    "scientificName": {
      "value": "Artemisia frigida",
      "confidence": 0.963
    }
  }
}
```

**Good**: Basic model tracking, timestamp, per-field confidence
**Missing**: Field-level provenance, re-extraction tracking, validation sources, costs, versions

---

## Enhanced Provenance System

### What We Track Now

#### Specimen-Level Provenance

```json
{
  "specimen_id": "SPECIMEN-001",
  "image_path": "SPECIMEN-001.jpg",
  "timestamp": "2025-12-03T04:55:00Z",
  "extraction_strategy": "confidence_routing",

  "total_processing_time_ms": 3500,
  "total_estimated_cost_usd": 0.001350,

  "models_used": ["gpt-4o-mini", "gpt-4o"],
  "api_calls_made": 2,
  "cache_hits": 0,

  "code_version": "d69923e",
  "python_version": "3.11.5",
  "platform": "Darwin"
}
```

#### Field-Level Provenance

**Every field tracks:**

```json
{
  "scientificName": {
    "value": "Artemisia frigida Willd.",
    "confidence": 0.89,

    "model": "gpt-4o",
    "provider": "openai",
    "extraction_method": "confidence_routing_reextraction",
    "timestamp": "2025-12-03T04:55:03Z",
    "processing_time_ms": 2000,
    "estimated_cost_usd": 0.001125,

    "original_confidence": 0.65,
    "original_model": "gpt-4o-mini",
    "improvement": 0.24,

    "gbif_validated": true,
    "gbif_cache_hit": false,
    "gbif_timestamp": "2025-12-03T04:55:05Z",

    "code_version": "d69923e",
    "prompt_version": "a7f3b2c"
  }
}
```

---

## Scientific Value

### 1. Reproducibility

**Question**: "How was scientificName extracted?"
**Answer**:
- Initial extraction: gpt-4o-mini at 0.65 confidence
- Re-extracted with gpt-4o → 0.89 confidence
- Validated against GBIF API (not cache)
- Code version d69923e, prompt version a7f3b2c

**Can reproduce exact extraction** by:
1. Checkout code version d69923e
2. Use gpt-4o-mini for initial pass
3. Re-extract with gpt-4o if <0.70 confidence
4. Validate with GBIF

### 2. Quality Tracking

**Questions:**
- Which fields needed re-extraction? → `original_confidence != null`
- What was the accuracy improvement? → `improvement` field
- Which model works best for which fields? → Group by `field_name` + `model`
- What's the average confidence by extraction method? → Aggregate `confidence` by `extraction_method`

**Analysis Example**:
```python
# Find fields that improved most from re-extraction
re_extracted = [f for f in fields.values() if f.original_confidence]
avg_improvement = sum(f.improvement for f in re_extracted) / len(re_extracted)
# Result: +0.24 average improvement
```

### 3. Cost Accountability

**Questions:**
- How much did this specimen cost to extract? → `total_estimated_cost_usd`
- Which fields were most expensive? → `field.estimated_cost_usd`
- What's the ROI for confidence routing? → Compare `base_cost` vs `routed_cost + accuracy_gain`

**Grant Reporting Example**:
```python
# Total processing costs for 1,000 specimens
specimens = load_provenance_data()
total_cost = sum(s.total_estimated_cost_usd for s in specimens)
total_time_hours = sum(s.total_processing_time_ms for s in specimens) / 3600000

print(f"Processed 1,000 specimens:")
print(f"  Cost: ${total_cost:.2f}")
print(f"  Time: {total_time_hours:.1f} hours")
print(f"  Avg quality: {avg(s.summary.avg_confidence for s in specimens):.2f}")
```

### 4. Validation Auditing

**Questions:**
- How many GBIF validations hit cache? → `validation_cache_hit`
- Which fields required API lookups? → `gbif_cache_hit == false`
- What's the cache hit rate? → `cache_hits / api_calls_made`

**Optimization Example**:
```python
# Identify expensive validation patterns
expensive_lookups = [
    f for f in fields.values()
    if f.gbif_validated and not f.gbif_cache_hit
]

# These scientific names need caching
names_to_cache = [f.value for f in expensive_lookups]
```

### 5. Model Performance Analysis

**Questions:**
- Which model is best for handwritten vs printed text?
- Does gpt-4o always improve over gpt-4o-mini?
- What's the cost-benefit of Apple Vision preprocessing?

**Analysis Example**:
```python
# Compare models by field type
from collections import defaultdict

model_performance = defaultdict(lambda: {"count": 0, "avg_conf": 0.0})

for field_name, field in provenance.fields.items():
    key = (field.model, field_name)
    model_performance[key]["count"] += 1
    model_performance[key]["avg_conf"] += field.confidence

# Results:
# gpt-4o-mini + scientificName: 0.72 avg confidence
# gpt-4o + scientificName: 0.89 avg confidence
# Improvement: +0.17 for 5x cost increase
```

---

## Provenance Queries

### Example 1: Find All Re-Extracted Fields

```python
from extraction.provenance import load_provenance

prov = load_provenance("SPECIMEN-001.jsonl")

re_extracted = {
    name: field
    for name, field in prov.fields.items()
    if field.original_confidence is not None
}

for name, field in re_extracted.items():
    print(f"{name}: {field.original_confidence:.2f} → {field.confidence:.2f} (+{field.improvement:.2f})")
```

### Example 2: Cost Analysis by Extraction Strategy

```python
specimens = load_all_provenance()

by_strategy = defaultdict(list)
for spec in specimens:
    by_strategy[spec.extraction_strategy].append(spec)

for strategy, specs in by_strategy.items():
    avg_cost = sum(s.total_estimated_cost_usd for s in specs) / len(specs)
    avg_conf = sum(s.summary["avg_confidence"] for s in specs) / len(specs)
    print(f"{strategy}: ${avg_cost:.4f}, {avg_conf:.2f} confidence")

# Results:
# direct: $0.0004, 0.75 confidence
# confidence_routing: $0.0006, 0.87 confidence
# hybrid_cascade: $0.0002, 0.85 confidence
```

### Example 3: Identify GBIF Cache Opportunities

```python
cache_misses = []

for prov in load_all_provenance():
    for name, field in prov.fields.items():
        if field.gbif_validated and not field.gbif_cache_hit:
            cache_misses.append(field.value)

# Count most frequent cache misses
from collections import Counter
frequent_misses = Counter(cache_misses).most_common(20)

print("Most frequently validated (not cached) scientific names:")
for name, count in frequent_misses:
    print(f"  {name}: {count} validations")

# → Pre-populate cache with these names
```

---

## Integration with Review Engine

### ReviewEngine with Provenance

```python
from extraction.provenance import create_provenance, estimate_extraction_cost
from extraction.confidence_router import ConfidenceRouter

# Create provenance tracker
prov = create_provenance(
    image_path="specimen.jpg",
    specimen_id="SPEC-001",
    extraction_strategy="confidence_routing"
)

# Extract with provenance tracking
router = ConfidenceRouter()
dwc_fields, confidences = router.extract_with_routing(image_path)

# Record each field
for field_name, value in dwc_fields.items():
    prov.add_field(
        field_name=field_name,
        value=value,
        confidence=confidences[field_name],
        model=router.base_model,
        provider="openai",
        extraction_method="confidence_routing",
        processing_time_ms=processing_time,
        estimated_cost_usd=estimate_extraction_cost(router.base_model)
    )

# Save provenance with extraction
output = {
    "specimen_id": "SPEC-001",
    "dwc": dwc_fields,
    "provenance": prov.to_dict()
}
```

### Query Provenance in Review UI

```python
# In mobile review interface
def get_specimen_provenance(specimen_id):
    """Get human-readable provenance summary for review UI."""
    prov = load_provenance(specimen_id)

    return {
        "extraction_date": prov.timestamp,
        "models_used": ", ".join(prov.models_used),
        "total_cost": f"${prov.total_estimated_cost_usd:.4f}",
        "processing_time": f"{prov.total_processing_time_ms/1000:.1f}s",
        "re_extracted_fields": [
            name for name, f in prov.fields.items()
            if f.original_confidence is not None
        ],
        "code_version": prov.code_version,
    }
```

---

## Storage Format

### JSONL with Provenance

```jsonl
{"specimen_id": "SPEC-001", "dwc": {...}, "provenance": {...}}
{"specimen_id": "SPEC-002", "dwc": {...}, "provenance": {...}}
```

### Separate Provenance File (Optional)

```
extractions/
├── raw.jsonl (Darwin Core data)
└── provenance.jsonl (Full provenance records)
```

---

## Provenance Standards

### Darwin Core Provenance Terms

We map to existing Darwin Core terms where applicable:

- `dcterms:modified` → `timestamp`
- `dwc:dataGeneralizations` → `extraction_method`
- `dwc:informationWithheld` → (none - we expose everything)

### Custom Extensions

Additional provenance beyond Darwin Core:

- `confidence` - AI confidence scores
- `model` - Which AI model
- `processing_time_ms` - Performance tracking
- `estimated_cost_usd` - Cost tracking
- `original_confidence` - Re-extraction tracking

---

## Privacy & Security

### What's Safe to Share

✅ **Public repositories**:
- Model names (gpt-4o-mini, apple-vision)
- Extraction methods (confidence_routing)
- Processing times
- Confidence scores
- Code versions

❌ **Never include**:
- API keys
- Raw API responses (may contain PII)
- Absolute file paths (use relative)
- Infrastructure details (server IPs, etc.)

### Redacted Example

```json
{
  "model": "gpt-4o-mini",
  "provider": "openai",
  "image_path": "SPECIMEN-001.jpg",  // Relative path only
  "code_version": "d69923e"
}
```

---

## Future Enhancements

### Version 2.0 Features

- **Chain-of-thought logging**: Record reasoning steps
- **Human review provenance**: Who approved/rejected
- **Batch processing metadata**: Parallel vs sequential
- **Error provenance**: Track failures and retries
- **Model comparison**: A/B test different models

### Integration with Standards

- **PROV-O**: W3C provenance ontology
- **Darwin Core Archive**: Include provenance in DwC-A metadata
- **GBIF publishing**: Submit provenance with occurrence data

---

## Demo

Run provenance demonstration:

```bash
python examples/provenance_demo.py
```

Outputs complete provenance record with explanations.

---

## Summary

**Provenance tracking ensures:**

1. ✅ **Scientific reproducibility** - Exact extraction conditions documented
2. ✅ **Quality transparency** - Confidence scores and improvements visible
3. ✅ **Cost accountability** - Per-field and total costs tracked
4. ✅ **Performance monitoring** - Processing times recorded
5. ✅ **Validation auditing** - GBIF cache hits vs API calls
6. ✅ **Model evaluation** - Compare performance across models/methods
7. ✅ **Version control** - Code and prompt versions tracked

**Every extraction decision is documented with full context for scientific rigor.**

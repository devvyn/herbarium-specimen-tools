# Full Dataset Run: AAFC Herbarium Collection

**Date**: 2026-01-14
**Dataset**: AAFC Herbarium Specimen Collection
**Total Specimens**: 2,885

## Extraction Pipeline

| Metric | Value |
|--------|-------|
| Model | qwen/qwen-2.5-vl-72b-instruct:free |
| Provider | OpenRouter (free tier) |
| Fields Extracted | 8 Darwin Core fields per specimen |
| API Cost | $0.00 (free tier model) |

## Review System Metrics

### Quality Distribution

| Metric | Value |
|--------|-------|
| Average Quality Score | 57.9% |
| Average Completeness | 58.1% |
| GBIF Validated | 0 (validation disabled) |

### Priority Classification

| Priority | Count | Percentage | Criteria |
|----------|-------|------------|----------|
| CRITICAL | 236 | 8.2% | Missing required fields (catalogNumber, scientificName) |
| HIGH | 0 | 0% | Confidence < 0.5 on key fields |
| MEDIUM | 1,017 | 35.2% | Some fields need attention |
| LOW | 50 | 1.7% | Minor issues |
| MINIMAL | 1,582 | 54.8% | High quality, ready for quick approval |

### Review Status (Initial Load)

All 2,885 specimens loaded as **PENDING** - ready for human review.

## Sample Critical Issues

Specimens flagged as CRITICAL typically have:
- Missing `catalogNumber` (empty string or null)
- Low completeness (~42.9%)
- Example: DSC_0486.JPG - "Avena fatua L." with no catalog number

## Lessons Learned

### What Worked Well

1. **Free-tier model viability**: Qwen 2.5 VL 72B produced usable extractions at zero cost
2. **Review queue loading**: 2,885 specimens loaded in seconds
3. **Priority routing**: Automatic classification by quality metrics
4. **Quality scoring formula**: 60% completeness + 40% confidence provides useful ranking

### Areas for Improvement

1. **Completeness scores**: 58% average suggests many optional fields empty
2. **GBIF validation**: Not run (would add ~3 seconds per specimen without caching)
3. **Missing catalog numbers**: 8% of specimens missing this critical identifier

### Architecture Observations

- **Two-codebase merge**: Extraction pipeline + review system now unified
- **bcrypt migration**: Replaced passlib due to Python 3.14 compatibility
- **Confidence scaling**: Fixed 0-1 to 0-100 conversion in quality scoring

## API Endpoints Verified

```
GET  /api/v1/health          - 200 OK
POST /api/v1/auth/login      - 200 OK (testuser/testpass123)
GET  /api/v1/statistics      - 200 OK (full metrics)
GET  /api/v1/queue           - 200 OK (paginated specimens)
```

## Next Steps

1. **Mobile Interface Demo**: Serve PWA frontend for curator workflow
2. **GBIF Validation**: Enable for subset to measure accuracy
3. **Export Pipeline**: Generate Darwin Core Archive from approved specimens
4. **Catalog Number Recovery**: Re-run extraction on CRITICAL specimens with focused prompt

## Files

- Extraction data: `openrouter_full_2885/raw.jsonl`
- Review server: `start_review_server.sh`
- Test suite: 52 tests passing

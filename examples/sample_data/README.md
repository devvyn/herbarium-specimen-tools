# Sample Data

**Purpose**: Anonymized specimen data for testing the mobile interface

## Files

### raw.jsonl

Sample extraction results in JSONL format (5 specimens).

**Format**: Each line is a JSON object with the following structure:
```json
{
  "image": "EXAMPLE-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "extraction_method": "gpt-4o-mini",
  "ocr_engine": "apple_vision",
  "dwc": {
    "catalogNumber": {"value": "EXAMPLE-001", "confidence": 0.95},
    "scientificName": {"value": "Artemisia frigida Willd.", "confidence": 0.95},
    "eventDate": {"value": "1969-08-14", "confidence": 0.92},
    ...
  }
}
```

**Top-level fields**:
- `image` - Specimen identifier (matches image filename)
- `timestamp` - Extraction timestamp (ISO 8601)
- `model` - AI model used for extraction
- `provider` - AI provider (e.g., openai, anthropic)
- `extraction_method` - Method used (OCR + AI)
- `ocr_engine` - OCR engine used (e.g., apple_vision, tesseract)

**Darwin Core fields** (in `dwc` object):
Each field has `value` and `confidence` (0.0-1.0):
- `catalogNumber` - Specimen catalog ID
- `scientificName` - Species scientific name
- `eventDate` - Collection date
- `recordedBy` - Collector name
- `locality` - Collection location
- `stateProvince` - State/province
- `country` - Country
- `habitat` - Habitat description
- `minimumElevationInMeters` - Elevation

**Specimens**:
- EXAMPLE-001: High quality (all fields complete, high confidence)
- EXAMPLE-002: Good quality (slightly lower confidence on some fields)
- EXAMPLE-003: High quality (well-preserved data)
- EXAMPLE-004: Lower quality (low confidence on date - only month/year)
- EXAMPLE-005: Excellent quality (high confidence across all fields)

## Images

**Note**: This repository does not include actual specimen images due to licensing.

**For testing**, you can:
1. Use your own public domain herbarium images
2. Create placeholder images
3. Use images from Biodiversity Heritage Library (CC0 licensed)

**Image naming**: Should match catalog numbers (e.g., `EXAMPLE-001.jpg`)

**Recommended sources**:
- [Biodiversity Heritage Library](https://www.biodiversitylibrary.org/) - Public domain
- [iDigBio](https://www.idigbio.org/) - CC0 licensed specimens
- [GBIF](https://www.gbif.org/) - Filter for CC0 images

## Testing the Mobile Interface

```bash
# Create images directory
mkdir -p examples/sample_data/images

# Add sample images (your own or from public domain sources)
# cp your-images/* examples/sample_data/images/

# Start mobile server with sample data
python mobile/run_mobile_server.py \
  --extraction-dir examples/sample_data \
  --image-dir examples/sample_data/images \
  --port 8000

# Access from mobile device
# http://YOUR_IP:8000
```

## License

Sample data is provided as examples under CC0 (public domain).

**Species used** (all common North American plants):
- *Artemisia frigida* - Fringed sagewort
- *Bouteloua gracilis* - Blue grama
- *Astragalus canadensis* - Canada milk-vetch
- *Symphoricarpos occidentalis* - Western snowberry
- *Elymus canadensis* - Canada wild rye

All specimen data is fictional and anonymized.

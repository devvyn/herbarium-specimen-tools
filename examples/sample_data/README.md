# Sample Data

**Purpose**: Anonymized specimen data for testing the mobile interface

## Files

### raw.jsonl

Sample extraction results in JSONL format (5 specimens).

**Fields**:
- `catalog_number` - Specimen catalog ID (EXAMPLE-001, etc.)
- `scientific_name` - Species scientific name
- `confidence` - AI confidence score (0.0-1.0)
- `event_date` - Collection date
- `recorded_by` - Collector name (anonymized)
- `locality` - Collection location (generic)
- `state_province` - State/province (generic)
- `country` - Country (generic)
- `habitat` - Habitat description
- `minimum_elevation_in_meters` - Elevation
- `coordinates` - Lat/lon (approximate)
- `image_sha256` - Image hash (placeholder)
- `extraction_method` - OCR/AI method used
- `extraction_timestamp` - When extracted
- `status` - Review status (PENDING/IN_REVIEW/APPROVED/REJECTED)
- `priority` - Priority level (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
- `issues` - Optional validation issues

**Statuses**:
- EXAMPLE-001: PENDING (not yet reviewed)
- EXAMPLE-002: PENDING (high priority)
- EXAMPLE-003: PENDING (low priority)
- EXAMPLE-004: IN_REVIEW (has issues - low confidence date)
- EXAMPLE-005: APPROVED (completed review)

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

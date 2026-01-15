#!/bin/bash
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
export ENVIRONMENT=development

# Use the existing extraction data and image directory
uv run python -c "
import uvicorn
from pathlib import Path
from src.review.mobile_api import create_mobile_app

# Paths
extraction_file = Path('/Users/devvynmurphy/Documents/pinned/active-projects/aafc-herbarium-dwc-extraction-2025/openrouter_full_2885/raw.jsonl')
image_dir = Path('/Users/devvynmurphy/Documents/projects/AAFC/pyproj/resized')
static_dir = Path('/Users/devvynmurphy/Documents/Code/herbarium-specimen-tools/mobile')

app = create_mobile_app(
    extraction_dir=extraction_file.parent,
    image_dir=image_dir,
    enable_gbif=False,  # No API calls
    static_dir=static_dir,  # Serve mobile PWA
)

print(f'Starting review server...')
print(f'  Extraction: {extraction_file}')
print(f'  Images: {image_dir}')
print(f'  API docs: http://localhost:8080/docs')

uvicorn.run(app, host='0.0.0.0', port=8080, log_level='info')
"

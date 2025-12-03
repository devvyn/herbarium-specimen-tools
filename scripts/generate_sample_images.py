#!/usr/bin/env python3
"""Generate synthetic herbarium specimen images for demo/testing.

This script creates placeholder specimen images for the sample data,
allowing users to test the mobile interface without needing real specimen images.
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def generate_specimen_image(catalog_number: str, scientific_name: str, output_path: Path):
    """Generate a synthetic herbarium sheet image.

    Args:
        catalog_number: Specimen catalog/accession number
        scientific_name: Scientific name of the species
        output_path: Path where image should be saved
    """
    # Create beige background (herbarium sheet color)
    width, height = 2000, 3000
    img = Image.new('RGB', (width, height), color='#f5f5dc')
    draw = ImageDraw.Draw(img)

    # Draw simple plant silhouette (stylized)
    # Stem
    stem_x = width // 2
    draw.line([(stem_x, height * 0.3), (stem_x, height * 0.8)],
              fill='#4a5520', width=8)

    # Leaves (simple ovals)
    for i in range(4):
        y = int(height * (0.35 + i * 0.1))
        leaf_left = (stem_x - 150, y - 40, stem_x - 20, y + 40)
        leaf_right = (stem_x + 20, y - 40, stem_x + 150, y + 40)
        draw.ellipse(leaf_left, fill='#6b7c3a')
        draw.ellipse(leaf_right, fill='#6b7c3a')

    # Flower cluster at top
    for i in range(3):
        for j in range(2):
            flower_x = stem_x - 30 + i * 30
            flower_y = int(height * 0.25 + j * 25)
            draw.ellipse([flower_x - 10, flower_y - 10,
                         flower_x + 10, flower_y + 10],
                        fill='#e8d5b7')

    # Draw specimen label
    label_x, label_y = 100, 2600
    label_width, label_height = 800, 300

    # Label background (white with border)
    draw.rectangle([label_x, label_y,
                   label_x + label_width, label_y + label_height],
                   fill='white', outline='black', width=3)

    # Try to use a decent font, fall back to default if not available
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # Label text
    text_x = label_x + 30
    draw.text((text_x, label_y + 30),
              f"Catalog: {catalog_number}",
              fill='black', font=font_large)
    draw.text((text_x, label_y + 100),
              f"Species: {scientific_name}",
              fill='black', font=font_medium)
    draw.text((text_x, label_y + 180),
              "Sample Herbarium Image",
              fill='#666666', font=font_medium)

    # Save image
    img.save(output_path, 'JPEG', quality=85)


def main():
    """Generate images for all specimens in sample data."""
    # Find project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    sample_data_dir = project_root / 'examples' / 'sample_data'
    images_dir = sample_data_dir / 'images'
    images_dir.mkdir(exist_ok=True)

    # Read sample JSONL
    raw_jsonl = sample_data_dir / 'raw.jsonl'

    if not raw_jsonl.exists():
        print(f"❌ Sample data not found: {raw_jsonl}")
        print("   Make sure you're running this from the project root")
        return 1

    print("🖼️  Generating sample specimen images...")
    print(f"   Output directory: {images_dir}")
    print()

    count = 0
    with open(raw_jsonl) as f:
        for line in f:
            specimen = json.loads(line)
            catalog = specimen['image']
            sci_name = specimen['dwc']['scientificName']['value']

            output_path = images_dir / f"{catalog}.jpg"
            print(f"   Creating {output_path.name}... ", end='', flush=True)
            generate_specimen_image(catalog, sci_name, output_path)
            print("✓")
            count += 1

    print()
    print(f"✅ Generated {count} specimen images in {images_dir}")
    print()
    print("You can now run:")
    print("  python mobile/run_mobile_server.py --dev")

    return 0


if __name__ == '__main__':
    exit(main())

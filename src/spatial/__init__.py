"""Spatial zone analysis for herbarium specimen labels.

Provides 9-zone grid classification for mapping text field locations.
Based on AAFC herbarium digitization standards.

Usage:
    from src.spatial import ZoneTemplateCache, classify_zone, BoundingBox

    # Create zone classification
    box = BoundingBox(x=0.2, y=0.7, width=0.3, height=0.1)
    zone = classify_zone(box)
    print(zone)  # "top-left"

    # Load cached zone templates
    cache = ZoneTemplateCache()
    cache.load_from_file(Path("spatial_zones.jsonl"))
    template = cache.get("specimen_abc123")
"""

from .image_annotator import (
    ZONE_COLORS,
    annotate_specimen_image,
    draw_text_boxes,
    draw_zone_grid,
)
from .zone_detector import (
    DWC_ZONE_HINTS,
    BoundingBox,
    HorizontalZone,
    SpatialTemplate,
    TextBlock,
    VerticalZone,
    ZoneInfo,
    analyze_text_zones,
    classify_zone,
    create_template,
    get_zone_statistics,
)
from .zone_loader import (
    ZoneTemplateCache,
    get_zones_file_path,
    load_zone_template,
)

__all__ = [
    # Zone detection
    "VerticalZone",
    "HorizontalZone",
    "BoundingBox",
    "TextBlock",
    "ZoneInfo",
    "SpatialTemplate",
    "classify_zone",
    "analyze_text_zones",
    "create_template",
    "get_zone_statistics",
    "DWC_ZONE_HINTS",
    # Zone loading
    "ZoneTemplateCache",
    "get_zones_file_path",
    "load_zone_template",
    # Image annotation
    "ZONE_COLORS",
    "draw_zone_grid",
    "draw_text_boxes",
    "annotate_specimen_image",
]

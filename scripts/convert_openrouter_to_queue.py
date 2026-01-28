#!/usr/bin/env python3
"""
Convert OpenRouter extraction raw.jsonl to review_queue.json format.

Usage:
    python scripts/convert_openrouter_to_queue.py \
        --input path/to/raw.jsonl \
        --output review_queue.json \
        --limit 100  # optional: limit for testing
"""

import argparse
import hashlib
import json
from pathlib import Path


# Core Darwin Core fields for review (ordered by importance)
REVIEW_FIELDS = [
    "catalogNumber",
    "scientificName",
    "eventDate",
    "recordedBy",
    "locality",
    "stateProvince",
    "country",
    "habitat",
    "recordNumber",
    "minimumElevationInMeters",
]


def classify_field_status(value: str | None, confidence: float) -> tuple[str, str]:
    """Determine field status and reason based on value and confidence."""
    if not value or value.strip() == "":
        return "missing", "Field is empty or not extracted"
    elif confidence >= 0.95:
        return "verified", f"High confidence ({confidence:.2f})"
    elif confidence >= 0.85:
        return "suggested", f"Good confidence ({confidence:.2f}), quick review recommended"
    elif confidence >= 0.70:
        return "suggested", f"Medium confidence ({confidence:.2f}), review recommended"
    else:
        return "needs_review", f"Low confidence ({confidence:.2f}), careful review needed"


def calculate_priority(fields: list[dict], overall_confidence: float) -> int:
    """Calculate review priority (1=highest, 5=lowest)."""
    missing_count = sum(1 for f in fields if f["status"] == "missing")
    needs_review_count = sum(1 for f in fields if f["status"] == "needs_review")

    # Critical fields missing = highest priority
    critical_fields = {"scientificName", "catalogNumber", "eventDate"}
    critical_missing = sum(
        1 for f in fields
        if f["field_name"] in critical_fields and f["status"] == "missing"
    )

    if critical_missing > 0:
        return 1  # Critical
    elif needs_review_count > 2 or missing_count > 3:
        return 2  # High
    elif needs_review_count > 0 or missing_count > 1:
        return 3  # Medium
    elif overall_confidence < 0.9:
        return 4  # Low
    else:
        return 5  # Minimal - likely auto-approvable


def convert_specimen(record: dict) -> dict | None:
    """Convert a single OpenRouter record to review queue format."""
    # Skip records with errors
    if "error" in record:
        return None

    dwc = record.get("dwc", {})
    if not dwc:
        return None

    image_filename = record.get("image", "")

    # Generate specimen_id from image filename (consistent hashing)
    specimen_id = hashlib.sha256(image_filename.encode()).hexdigest()

    # Convert DwC fields to review format
    fields = []
    confidence_sum = 0
    confidence_count = 0

    for field_name in REVIEW_FIELDS:
        field_data = dwc.get(field_name, {})

        # Handle both nested {"value": ..., "confidence": ...} and flat formats
        if isinstance(field_data, dict):
            value = field_data.get("value")
            confidence = field_data.get("confidence", 0.0)
        else:
            value = field_data if field_data else None
            confidence = 0.8  # Default for flat format

        status, reason = classify_field_status(value, confidence)

        fields.append({
            "field_name": field_name,
            "status": status,
            "original_value": value,
            "confidence": confidence,
            "suggested_value": None,
            "suggestion_confidence": None,
            "reason": reason,
        })

        if value:
            confidence_sum += confidence
            confidence_count += 1

    overall_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
    priority = calculate_priority(fields, overall_confidence)

    # Count statistics
    needs_review = sum(1 for f in fields if f["status"] == "needs_review")
    suggestions = sum(1 for f in fields if f["status"] == "suggested")
    missing = sum(1 for f in fields if f["status"] == "missing")

    # Determine tier based on overall quality
    if overall_confidence >= 0.95 and missing == 0:
        tier = "verified"
    elif overall_confidence >= 0.85:
        tier = "correct"
    elif overall_confidence >= 0.70:
        tier = "review"
    else:
        tier = "problematic"

    return {
        "specimen_id": specimen_id,
        "image_filename": image_filename,
        "tier": tier,
        "fields": fields,
        "overall_confidence": round(overall_confidence, 3),
        "review_priority": priority,
        "metadata": {
            "needs_review_count": needs_review,
            "suggestions_count": suggestions,
            "missing_count": missing,
            "flags": [],
            "model": record.get("model", "unknown"),
            "provider": record.get("provider", "unknown"),
            "extraction_timestamp": record.get("timestamp", ""),
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Convert OpenRouter extraction to review queue")
    parser.add_argument("--input", "-i", required=True, help="Input raw.jsonl file")
    parser.add_argument("--output", "-o", required=True, help="Output review_queue.json file")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit number of specimens (for testing)")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    specimens = []
    errors = 0
    skipped = 0

    print(f"Reading from: {input_path}")

    with open(input_path) as f:
        for i, line in enumerate(f):
            if args.limit and len(specimens) >= args.limit:
                break

            try:
                record = json.loads(line.strip())
                specimen = convert_specimen(record)
                if specimen:
                    specimens.append(specimen)
                else:
                    skipped += 1
            except json.JSONDecodeError as e:
                errors += 1
                if errors <= 5:
                    print(f"  JSON error on line {i+1}: {e}")

    # Sort by priority (highest first)
    specimens.sort(key=lambda s: (s["review_priority"], -s["overall_confidence"]))

    # Write output
    output_data = {"specimens": specimens}

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    # Summary statistics
    print(f"\n{'='*50}")
    print(f"Conversion complete!")
    print(f"{'='*50}")
    print(f"Total specimens: {len(specimens)}")
    print(f"Skipped (errors): {skipped}")
    print(f"JSON parse errors: {errors}")
    print(f"\nBy tier:")
    tiers = {}
    for s in specimens:
        tiers[s["tier"]] = tiers.get(s["tier"], 0) + 1
    for tier, count in sorted(tiers.items()):
        print(f"  {tier}: {count}")

    print(f"\nBy priority:")
    priorities = {}
    for s in specimens:
        priorities[s["review_priority"]] = priorities.get(s["review_priority"], 0) + 1
    priority_labels = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Minimal"}
    for p in sorted(priorities.keys()):
        print(f"  {p} ({priority_labels.get(p, '?')}): {priorities[p]}")

    print(f"\nOutput written to: {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())

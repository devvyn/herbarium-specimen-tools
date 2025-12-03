"""
Confidence-based extraction routing for improved accuracy.

Routes low-confidence fields to more powerful models for re-extraction,
balancing cost and accuracy.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)


class ConfidenceRouter:
    """
    Routes extraction based on confidence scores.

    Strategy:
    1. Extract all fields with base model (gpt-4o-mini)
    2. Identify fields with confidence < threshold
    3. Re-extract low-confidence fields with premium model (gpt-4o)
    4. Merge results (use higher confidence version)
    """

    def __init__(
        self,
        base_model: str = "gpt-4o-mini",
        premium_model: str = "gpt-4o",
        confidence_threshold: float = 0.70,
        enable_routing: bool = True,
    ):
        """
        Initialize confidence router.

        Args:
            base_model: Fast, cheap model for initial extraction
            premium_model: Accurate, expensive model for re-extraction
            confidence_threshold: Re-extract fields below this confidence
            enable_routing: Enable routing (disable for pure base model)
        """
        if OpenAI is None:
            raise ImportError("OpenAI SDK required for extraction")

        self.base_model = base_model
        self.premium_model = premium_model
        self.confidence_threshold = confidence_threshold
        self.enable_routing = enable_routing
        self.client = OpenAI()

        self.stats = {
            "total_extractions": 0,
            "fields_re_extracted": 0,
            "premium_api_calls": 0,
        }

        logger.info(
            f"ConfidenceRouter initialized: {base_model} → {premium_model} "
            f"(threshold: {confidence_threshold}, routing: {enable_routing})"
        )

    def extract_with_routing(
        self,
        image_path: Path,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Dict[str, float]]:
        """
        Extract Darwin Core fields with confidence-based routing.

        Args:
            image_path: Path to specimen image
            system_prompt: Optional system prompt (uses default if None)
            user_prompt: Optional user prompt (uses default if None)

        Returns:
            Tuple of (dwc_fields, confidence_scores)
        """
        self.stats["total_extractions"] += 1

        # Step 1: Base extraction with fast model
        logger.info(f"Base extraction with {self.base_model}: {image_path.name}")
        dwc_fields, confidences = self._extract_with_model(
            image_path, self.base_model, system_prompt, user_prompt
        )

        if not self.enable_routing:
            return dwc_fields, confidences

        # Step 2: Identify low-confidence fields
        low_confidence_fields = {
            field: conf
            for field, conf in confidences.items()
            if conf < self.confidence_threshold
        }

        if not low_confidence_fields:
            logger.info(f"All fields above {self.confidence_threshold} confidence - no re-extraction needed")
            return dwc_fields, confidences

        logger.info(
            f"Re-extracting {len(low_confidence_fields)} low-confidence fields: "
            f"{list(low_confidence_fields.keys())}"
        )

        # Step 3: Re-extract low-confidence fields with premium model
        improved_fields, improved_confidences = self._extract_specific_fields(
            image_path,
            list(low_confidence_fields.keys()),
            system_prompt,
            user_prompt,
        )

        self.stats["fields_re_extracted"] += len(improved_fields)
        self.stats["premium_api_calls"] += 1

        # Step 4: Merge results (use improved if better confidence)
        for field in low_confidence_fields:
            if field in improved_fields:
                improved_conf = improved_confidences.get(field, 0.0)
                original_conf = confidences[field]

                if improved_conf > original_conf:
                    logger.debug(
                        f"Field '{field}': {original_conf:.2f} → {improved_conf:.2f} "
                        f"(improved by {improved_conf - original_conf:.2f})"
                    )
                    dwc_fields[field] = improved_fields[field]
                    confidences[field] = improved_conf
                else:
                    logger.debug(
                        f"Field '{field}': Premium model didn't improve confidence, keeping original"
                    )

        return dwc_fields, confidences

    def _extract_with_model(
        self,
        image_path: Path,
        model: str,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract Darwin Core fields using specified model."""
        # Default prompts
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        if user_prompt is None:
            user_prompt = self._get_default_user_prompt()

        # Encode image
        with open(image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            },
        ]

        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,  # Deterministic for extractions
            )
        except Exception as e:
            logger.error(f"OpenAI API error with {model}: {e}")
            return {}, {}

        # Parse response
        content = response.choices[0].message.content
        if not content:
            return {}, {}

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {}, {}

        # Extract fields and confidences
        dwc_fields = {}
        confidences = {}

        for field, field_data in data.items():
            if isinstance(field_data, dict):
                dwc_fields[field] = field_data.get("value", "")
                confidences[field] = float(field_data.get("confidence", 0.0))

        return dwc_fields, confidences

    def _extract_specific_fields(
        self,
        image_path: Path,
        target_fields: list,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Dict[str, float]]:
        """
        Re-extract specific fields with premium model and focused prompt.

        Args:
            image_path: Path to specimen image
            target_fields: List of field names to re-extract
            system_prompt: Optional base system prompt
            user_prompt: Optional base user prompt

        Returns:
            Tuple of (dwc_fields, confidence_scores) for target fields only
        """
        # Build focused prompt for target fields
        if user_prompt is None:
            user_prompt = self._get_default_user_prompt()

        focused_prompt = (
            f"{user_prompt}\n\n"
            f"IMPORTANT: Focus specifically on extracting these fields with high accuracy:\n"
            f"{', '.join(target_fields)}\n\n"
            f"Take extra care with these fields, as they had low confidence in initial extraction."
        )

        # Extract with premium model
        return self._extract_with_model(
            image_path, self.premium_model, system_prompt, focused_prompt
        )

    def _get_default_system_prompt(self) -> str:
        """Default system prompt for Darwin Core extraction."""
        return """You are an expert botanical data extraction system.

Extract Darwin Core fields from herbarium specimen images with high accuracy.

Return JSON where each field maps to {"value": "...", "confidence": 0.0-1.0}.

Confidence scoring:
- 1.0: Clearly legible, no ambiguity
- 0.9: Minor uncertainty (e.g., one character unclear)
- 0.8: Moderate uncertainty (partial illegibility)
- 0.7: Significant uncertainty (multiple unclear characters)
- <0.7: High uncertainty or illegible"""

    def _get_default_user_prompt(self) -> str:
        """Default user prompt for Darwin Core extraction."""
        return """Extract all Darwin Core fields visible in this herbarium specimen image.

Focus on:
- catalogNumber (specimen ID)
- scientificName (with authority if present)
- recordedBy (collector name)
- recordNumber (collector number)
- eventDate (collection date)
- country, stateProvince, locality
- habitat
- coordinates (if present)

Return JSON with value and confidence for each field."""

    def get_stats(self) -> Dict:
        """Get extraction statistics."""
        total = self.stats["total_extractions"]
        fields_re_extracted = self.stats["fields_re_extracted"]
        premium_calls = self.stats["premium_api_calls"]

        return {
            **self.stats,
            "avg_fields_per_re_extraction": (
                fields_re_extracted / premium_calls if premium_calls > 0 else 0
            ),
            "premium_call_rate": (
                f"{premium_calls / total * 100:.1f}%" if total > 0 else "0%"
            ),
        }

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_extractions": 0,
            "fields_re_extracted": 0,
            "premium_api_calls": 0,
        }

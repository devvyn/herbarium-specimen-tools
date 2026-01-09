"""
Tests for engine adapters and protocol conformance.

Verifies that engine adapters properly implement the OCREngine
and FieldExtractor protocols.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.protocols import (
    OCREngine,
    FieldExtractor,
    OCRResult,
    ExtractionResult,
)
from src.core.engines import (
    AppleVisionAdapter,
    RulesEngineAdapter,
    EngineRegistry,
    get_engine_registry,
)


class TestAppleVisionAdapter:
    """Tests for Apple Vision OCR adapter."""

    def test_implements_protocol(self):
        """Verify adapter implements OCREngine protocol."""
        adapter = AppleVisionAdapter()
        assert isinstance(adapter, OCREngine)

    def test_has_name_property(self):
        """Verify name property returns expected value."""
        adapter = AppleVisionAdapter()
        assert adapter.name == "apple-vision"

    def test_has_is_available_property(self):
        """Verify is_available property exists."""
        adapter = AppleVisionAdapter()
        # Should be bool regardless of platform
        assert isinstance(adapter.is_available, bool)

    def test_extract_text_returns_ocr_result(self, tmp_path):
        """Verify extract_text returns OCRResult."""
        adapter = AppleVisionAdapter()

        # Create a dummy image file
        image_path = tmp_path / "test.jpg"
        image_path.touch()

        result = adapter.extract_text(image_path)

        # Should return OCRResult regardless of availability
        assert isinstance(result, OCRResult)
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.regions, list)
        assert isinstance(result.metadata, dict)

    def test_extract_text_missing_file(self, tmp_path):
        """Verify graceful handling of missing file."""
        adapter = AppleVisionAdapter()

        result = adapter.extract_text(tmp_path / "nonexistent.jpg")

        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0
        assert "error" in result.metadata

    @patch("src.ocr.apple_vision.AppleVisionOCR.extract_text")
    def test_extract_text_with_results(self, mock_extract, tmp_path):
        """Verify correct processing of OCR results."""
        # Mock successful extraction
        mock_extract.return_value = (
            [
                {"text": "Line 1", "confidence": 0.95, "bounds": {"x": 0, "y": 0, "width": 100, "height": 20}},
                {"text": "Line 2", "confidence": 0.90, "bounds": {"x": 0, "y": 25, "width": 100, "height": 20}},
            ],
            None,  # No error
        )

        adapter = AppleVisionAdapter()
        image_path = tmp_path / "test.jpg"
        image_path.touch()

        result = adapter.extract_text(image_path)

        assert "Line 1" in result.text
        assert "Line 2" in result.text
        assert result.confidence == pytest.approx(0.925, rel=0.01)
        assert len(result.regions) == 2
        assert result.metadata["block_count"] == 2
        assert result.metadata["cost_usd"] == 0.0


class TestRulesEngineAdapter:
    """Tests for rules-based field extractor adapter."""

    def test_implements_protocol(self):
        """Verify adapter implements FieldExtractor protocol."""
        adapter = RulesEngineAdapter()
        assert isinstance(adapter, FieldExtractor)

    def test_has_name_property(self):
        """Verify name property returns expected value."""
        adapter = RulesEngineAdapter()
        assert adapter.name == "rules-engine"

    def test_has_model_property(self):
        """Verify model property returns expected value."""
        adapter = RulesEngineAdapter()
        assert adapter.model == "regex-patterns-v1"

    def test_has_provider_property(self):
        """Verify provider property returns expected value."""
        adapter = RulesEngineAdapter()
        assert adapter.provider == "local"

    def test_extract_fields_returns_extraction_result(self, tmp_path):
        """Verify extract_fields returns ExtractionResult."""
        adapter = RulesEngineAdapter()
        image_path = tmp_path / "test.jpg"

        result = adapter.extract_fields(image_path, ocr_text="Sample text")

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.fields, dict)
        assert result.model == "regex-patterns-v1"
        assert result.provider == "local"
        assert result.cost_usd == 0.0

    def test_extract_fields_without_ocr_text(self, tmp_path):
        """Verify graceful handling when no OCR text provided."""
        adapter = RulesEngineAdapter()
        image_path = tmp_path / "test.jpg"

        result = adapter.extract_fields(image_path)

        assert isinstance(result, ExtractionResult)
        assert result.fields == {}

    def test_extract_fields_extracts_specimen_data(self, tmp_path):
        """Verify fields are extracted from OCR text."""
        adapter = RulesEngineAdapter()
        image_path = tmp_path / "test.jpg"

        ocr_text = """
        AAFC REGINA
        Artemisia frigida Willd.
        Saskatchewan, Canada
        Near Swift Current
        July 15, 1975
        Cat. No. 12345
        """

        result = adapter.extract_fields(image_path, ocr_text=ocr_text)

        # Should extract multiple fields
        assert len(result.fields) > 0

        # Verify scientificName extraction (reliable pattern)
        assert "scientificName" in result.fields
        assert "Artemisia" in result.fields["scientificName"]["value"]

        # Verify country extraction
        assert "country" in result.fields
        assert result.fields["country"]["value"] == "Canada"

        # Verify province extraction
        assert "stateProvince" in result.fields
        assert result.fields["stateProvince"]["value"] == "Saskatchewan"

        # Verify institution code extraction
        assert "institutionCode" in result.fields
        assert result.fields["institutionCode"]["value"] == "AAFC"

        # Verify all fields have confidence scores
        for field_name, field_data in result.fields.items():
            assert "value" in field_data
            assert "confidence" in field_data
            assert field_data["confidence"] > 0.0


class TestEngineRegistry:
    """Tests for engine registry."""

    def test_list_ocr_engines(self):
        """Verify listing registered OCR engines."""
        registry = EngineRegistry()
        engines = registry.list_ocr_engines()

        assert isinstance(engines, list)
        assert "apple-vision" in engines

    def test_list_field_extractors(self):
        """Verify listing registered field extractors."""
        registry = EngineRegistry()
        extractors = registry.list_field_extractors()

        assert isinstance(extractors, list)
        assert "rules" in extractors

    def test_get_ocr_engine(self):
        """Verify getting OCR engine by name."""
        registry = EngineRegistry()
        engine = registry.get_ocr_engine("apple-vision")

        assert engine is not None
        assert isinstance(engine, OCREngine)
        assert engine.name == "apple-vision"

    def test_get_ocr_engine_not_found(self):
        """Verify None returned for unknown engine."""
        registry = EngineRegistry()
        engine = registry.get_ocr_engine("unknown-engine")

        assert engine is None

    def test_get_field_extractor(self):
        """Verify getting field extractor by name."""
        registry = EngineRegistry()
        extractor = registry.get_field_extractor("rules")

        assert extractor is not None
        assert isinstance(extractor, FieldExtractor)
        assert extractor.name == "rules-engine"

    def test_get_field_extractor_not_found(self):
        """Verify None returned for unknown extractor."""
        registry = EngineRegistry()
        extractor = registry.get_field_extractor("unknown-extractor")

        assert extractor is None

    def test_lazy_initialization(self):
        """Verify engines are initialized lazily."""
        registry = EngineRegistry()

        # Before access, no instances created
        assert len(registry._ocr_instances) == 0

        # First access creates instance
        engine1 = registry.get_ocr_engine("apple-vision")
        assert len(registry._ocr_instances) == 1

        # Second access returns same instance
        engine2 = registry.get_ocr_engine("apple-vision")
        assert engine1 is engine2
        assert len(registry._ocr_instances) == 1

    def test_register_custom_ocr_engine(self):
        """Verify registering custom OCR engine."""
        registry = EngineRegistry()

        # Create a simple mock engine class
        class MockEngine:
            @property
            def name(self) -> str:
                return "mock-engine"

            @property
            def is_available(self) -> bool:
                return True

            def extract_text(self, image_path: Path) -> OCRResult:
                return OCRResult(text="mock", confidence=1.0, regions=[], metadata={})

        registry.register_ocr_engine("mock", MockEngine)

        assert "mock" in registry.list_ocr_engines()
        engine = registry.get_ocr_engine("mock")
        assert engine is not None
        assert engine.name == "mock-engine"

    def test_get_available_ocr_engines(self):
        """Verify listing available engines."""
        registry = EngineRegistry()
        available = registry.get_available_ocr_engines()

        # Should be a list (may be empty on non-macOS)
        assert isinstance(available, list)

    def test_get_fallback_chain(self):
        """Verify fallback chain returns available engines in order."""
        registry = EngineRegistry()

        # Request chain with mix of known and unknown engines
        chain = registry.get_fallback_chain(["unknown", "apple-vision", "also-unknown"])

        # Should return only available engines
        for engine in chain:
            assert isinstance(engine, OCREngine)


class TestGlobalRegistry:
    """Tests for global registry singleton."""

    def test_get_engine_registry_returns_same_instance(self):
        """Verify singleton behavior."""
        registry1 = get_engine_registry()
        registry2 = get_engine_registry()

        assert registry1 is registry2

    def test_get_engine_registry_has_builtin_engines(self):
        """Verify global registry has built-in engines."""
        registry = get_engine_registry()

        assert "apple-vision" in registry.list_ocr_engines()
        assert "rules" in registry.list_field_extractors()

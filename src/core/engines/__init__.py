"""
Engine registry for OCR and field extraction plugins.

Provides:
- EngineRegistry: Plugin discovery and management
- Protocol-conforming adapters for existing implementations
- Factory functions for creating engines by name

Usage:
    from src.core.engines import get_engine_registry, OCREngineAdapter

    registry = get_engine_registry()
    engine = registry.get_ocr_engine("apple-vision")
    result = engine.extract_text(image_path)
"""

from pathlib import Path
from typing import Dict, List, Optional, Type

from src.core.protocols import (
    ExtractionResult,
    FieldExtractor,
    OCREngine,
    OCRResult,
)

# Adapters
from .apple_vision_adapter import AppleVisionAdapter
from .rules_adapter import RulesEngineAdapter

__all__ = [
    "AppleVisionAdapter",
    "RulesEngineAdapter",
    "EngineRegistry",
    "get_engine_registry",
]


class EngineRegistry:
    """
    Registry for OCR engines and field extractors.

    Supports plugin discovery, fallback policies, and lazy initialization.
    """

    def __init__(self):
        """Initialize engine registry."""
        self._ocr_engines: Dict[str, Type[OCREngine]] = {}
        self._field_extractors: Dict[str, Type[FieldExtractor]] = {}
        self._ocr_instances: Dict[str, OCREngine] = {}
        self._extractor_instances: Dict[str, FieldExtractor] = {}

        # Register built-in engines
        self._register_builtin_engines()

    def _register_builtin_engines(self) -> None:
        """Register built-in OCR engines and extractors."""
        # OCR Engines
        self.register_ocr_engine("apple-vision", AppleVisionAdapter)

        # Field Extractors
        self.register_field_extractor("rules", RulesEngineAdapter)

    def register_ocr_engine(
        self,
        name: str,
        engine_class: Type[OCREngine],
    ) -> None:
        """Register an OCR engine class.

        Args:
            name: Engine name for lookup
            engine_class: Class implementing OCREngine protocol
        """
        self._ocr_engines[name] = engine_class

    def register_field_extractor(
        self,
        name: str,
        extractor_class: Type[FieldExtractor],
    ) -> None:
        """Register a field extractor class.

        Args:
            name: Extractor name for lookup
            extractor_class: Class implementing FieldExtractor protocol
        """
        self._field_extractors[name] = extractor_class

    def get_ocr_engine(self, name: str) -> Optional[OCREngine]:
        """Get OCR engine instance by name.

        Creates instance on first access (lazy initialization).

        Args:
            name: Engine name

        Returns:
            OCREngine instance or None if not found
        """
        if name not in self._ocr_engines:
            return None

        if name not in self._ocr_instances:
            self._ocr_instances[name] = self._ocr_engines[name]()

        return self._ocr_instances[name]

    def get_field_extractor(self, name: str) -> Optional[FieldExtractor]:
        """Get field extractor instance by name.

        Creates instance on first access (lazy initialization).

        Args:
            name: Extractor name

        Returns:
            FieldExtractor instance or None if not found
        """
        if name not in self._field_extractors:
            return None

        if name not in self._extractor_instances:
            self._extractor_instances[name] = self._field_extractors[name]()

        return self._extractor_instances[name]

    def list_ocr_engines(self) -> List[str]:
        """List registered OCR engine names."""
        return list(self._ocr_engines.keys())

    def list_field_extractors(self) -> List[str]:
        """List registered field extractor names."""
        return list(self._field_extractors.keys())

    def get_available_ocr_engines(self) -> List[str]:
        """List OCR engines available on this system."""
        available = []
        for name in self._ocr_engines:
            engine = self.get_ocr_engine(name)
            if engine and engine.is_available:
                available.append(name)
        return available

    def get_fallback_chain(
        self,
        preferred: List[str],
    ) -> List[OCREngine]:
        """Get ordered list of available engines from preference list.

        Args:
            preferred: Ordered list of preferred engine names

        Returns:
            List of available OCREngine instances in preference order
        """
        engines = []
        for name in preferred:
            engine = self.get_ocr_engine(name)
            if engine and engine.is_available:
                engines.append(engine)
        return engines


# Module-level singleton
_registry: Optional[EngineRegistry] = None


def get_engine_registry() -> EngineRegistry:
    """Get the global engine registry singleton."""
    global _registry
    if _registry is None:
        _registry = EngineRegistry()
    return _registry

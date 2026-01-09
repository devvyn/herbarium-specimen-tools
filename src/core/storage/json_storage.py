"""
JSON file-based storage backend.

Stores specimen data in JSON files:
- Extraction data: Loaded from raw.jsonl (immutable source)
- Review state: Persisted to review_state.json (mutable)

Suitable for development and single-user scenarios.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.protocols import SpecimenData

logger = logging.getLogger(__name__)


class JSONStorage:
    """JSON file-based storage for specimen data.

    Implements the SpecimenStorage protocol using JSON files.

    The storage separates concerns:
    - Extraction data is loaded from external sources (raw.jsonl)
    - Review state is managed internally (review_state.json)

    This mirrors the current run_server.py pattern but provides
    a clean interface for future migration to other backends.
    """

    def __init__(
        self,
        data_dir: Path,
        state_file: Optional[Path] = None,
    ):
        """Initialize JSON storage.

        Args:
            data_dir: Directory for data files
            state_file: Path to review state JSON (default: data_dir/review_state.json)
        """
        self.data_dir = Path(data_dir)
        self.state_file = state_file or (self.data_dir / "review_state.json")

        # In-memory cache of specimens
        self._specimens: Dict[str, SpecimenData] = {}

        # Track which specimens have been modified
        self._dirty: set = set()

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get(self, specimen_id: str) -> Optional[SpecimenData]:
        """Get specimen by ID."""
        return self._specimens.get(specimen_id)

    def put(self, specimen: SpecimenData) -> None:
        """Store or update specimen."""
        self._specimens[specimen.specimen_id] = specimen
        self._dirty.add(specimen.specimen_id)
        self._save_state()

    def delete(self, specimen_id: str) -> bool:
        """Delete specimen. Returns True if existed."""
        if specimen_id in self._specimens:
            del self._specimens[specimen_id]
            self._dirty.discard(specimen_id)
            self._save_state()
            return True
        return False

    def list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SpecimenData]:
        """List specimens with optional filters."""
        results = list(self._specimens.values())

        # Apply filters
        if status:
            results = [s for s in results if s.status == status]
        if priority:
            results = [s for s in results if s.priority == priority]

        # Sort by priority (assuming priority values are comparable)
        results.sort(key=lambda s: s.priority)

        # Paginate
        return results[offset : offset + limit]

    def count(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> int:
        """Count specimens matching filters."""
        if not status and not priority:
            return len(self._specimens)

        count = 0
        for s in self._specimens.values():
            if status and s.status != status:
                continue
            if priority and s.priority != priority:
                continue
            count += 1
        return count

    def load_from_jsonl(self, jsonl_path: Path) -> int:
        """Load specimens from JSONL extraction file.

        Args:
            jsonl_path: Path to raw.jsonl file

        Returns:
            Number of specimens loaded
        """
        count = 0
        with open(jsonl_path) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    specimen = self._record_to_specimen(record)
                    self._specimens[specimen.specimen_id] = specimen
                    count += 1
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse record: {e}")

        logger.info(f"Loaded {count} specimens from {jsonl_path}")

        # Apply any saved review state
        self._load_state()

        return count

    def _record_to_specimen(self, record: Dict[str, Any]) -> SpecimenData:
        """Convert extraction record to SpecimenData."""
        specimen_id = record.get("image", record.get("specimen_id", "unknown"))

        # Extract DwC fields
        dwc_fields = record.get("dwc", {})

        # Default status and priority
        status = "pending"
        priority = "MEDIUM"

        # Build metadata from extraction info
        metadata = {
            "model": record.get("model"),
            "provider": record.get("provider"),
            "extraction_method": record.get("extraction_method"),
            "ocr_engine": record.get("ocr_engine"),
            "timestamp": record.get("timestamp"),
        }

        return SpecimenData(
            specimen_id=specimen_id,
            dwc_fields=dwc_fields,
            status=status,
            priority=priority,
            metadata=metadata,
        )

    def _load_state(self) -> None:
        """Load review state from JSON file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                state = json.load(f)

            for specimen_id, data in state.items():
                if specimen_id in self._specimens:
                    specimen = self._specimens[specimen_id]
                    # Update mutable fields from saved state
                    if "status" in data:
                        specimen.status = data["status"]
                    if "priority" in data:
                        specimen.priority = data["priority"]
                    # Store review-specific fields in metadata
                    specimen.metadata["notes"] = data.get("notes")
                    specimen.metadata["review_notes"] = data.get("review_notes")
                    specimen.metadata["flagged"] = data.get("flagged", False)
                    specimen.metadata["reextraction_requested"] = data.get(
                        "reextraction_requested", False
                    )
                    specimen.metadata["corrections"] = data.get("corrections", {})

            logger.info(f"Applied review state for {len(state)} specimens")

        except Exception as e:
            logger.warning(f"Failed to load review state: {e}")

    def _save_state(self) -> None:
        """Save review state to JSON file."""
        state = {}

        for specimen_id, specimen in self._specimens.items():
            # Only save specimens with review activity
            meta = specimen.metadata
            has_activity = (
                meta.get("notes")
                or meta.get("review_notes")
                or specimen.status != "pending"
                or meta.get("flagged")
                or meta.get("reextraction_requested")
            )

            if has_activity:
                state[specimen_id] = {
                    "notes": meta.get("notes"),
                    "review_notes": meta.get("review_notes"),
                    "status": specimen.status,
                    "priority": specimen.priority,
                    "flagged": meta.get("flagged", False),
                    "reextraction_requested": meta.get("reextraction_requested", False),
                    "corrections": meta.get("corrections", {}),
                }

        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Saved review state for {len(state)} specimens")
        except Exception as e:
            logger.error(f"Failed to save review state: {e}")

    def sync(self) -> None:
        """Force sync of all dirty specimens to disk."""
        self._save_state()
        self._dirty.clear()

    def close(self) -> None:
        """Close storage and ensure all data is persisted."""
        self.sync()

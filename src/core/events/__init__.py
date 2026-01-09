"""
Event sourcing for herbarium specimen workflows.

Provides an append-only event log for tracking all state changes:
- Complete audit trail for scientific reproducibility
- Event replay for debugging and recovery
- Decoupled event handlers for extensibility

Event Types:
- SpecimenCreated: New specimen added to system
- SpecimenUpdated: Specimen data modified
- StatusChanged: Review status transition
- FieldCorrected: Manual field correction by reviewer
- ExtractionCompleted: OCR/AI extraction finished
- ValidationCompleted: GBIF/IPNI validation finished
- SpecimenExported: Specimen exported to DwC-A

Usage:
    from src.core.events import EventStore, SpecimenCreated

    store = EventStore(Path("./events.jsonl"))
    store.append(SpecimenCreated(
        specimen_id="SPEC-001",
        source="jsonl_import",
        metadata={"file": "raw.jsonl"}
    ))

    # Replay events
    for event in store.replay():
        print(f"{event.timestamp}: {event.event_type}")
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Type
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events in the specimen workflow."""

    SPECIMEN_CREATED = "specimen_created"
    SPECIMEN_UPDATED = "specimen_updated"
    SPECIMEN_DELETED = "specimen_deleted"
    STATUS_CHANGED = "status_changed"
    FIELD_CORRECTED = "field_corrected"
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    SPECIMEN_EXPORTED = "specimen_exported"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"


@dataclass
class Event:
    """Base event class with common fields."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_type: str = field(default="")
    specimen_id: Optional[str] = None
    actor: str = "system"  # User or system that caused the event
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        event_type = data.get("event_type", "")

        # Route to specific event class
        event_class = EVENT_REGISTRY.get(event_type, Event)
        return event_class(**{k: v for k, v in data.items() if k in event_class.__dataclass_fields__})


@dataclass
class SpecimenCreated(Event):
    """Event: New specimen added to the system."""

    event_type: str = field(default=EventType.SPECIMEN_CREATED.value)
    source: str = ""  # "jsonl_import", "manual_entry", "api"
    initial_status: str = "pending"
    field_count: int = 0


@dataclass
class SpecimenUpdated(Event):
    """Event: Specimen data modified."""

    event_type: str = field(default=EventType.SPECIMEN_UPDATED.value)
    changed_fields: List[str] = field(default_factory=list)
    reason: str = ""  # "correction", "re-extraction", "merge"


@dataclass
class SpecimenDeleted(Event):
    """Event: Specimen removed from system."""

    event_type: str = field(default=EventType.SPECIMEN_DELETED.value)
    reason: str = ""


@dataclass
class StatusChanged(Event):
    """Event: Review status transition."""

    event_type: str = field(default=EventType.STATUS_CHANGED.value)
    old_status: str = ""
    new_status: str = ""
    reason: str = ""  # "approved", "rejected", "needs_review"


@dataclass
class FieldCorrected(Event):
    """Event: Manual field correction by reviewer."""

    event_type: str = field(default=EventType.FIELD_CORRECTED.value)
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""
    correction_type: str = ""  # "typo", "ocr_error", "missing_data"
    confidence_before: float = 0.0
    confidence_after: float = 1.0  # Manual corrections are high confidence


@dataclass
class ExtractionCompleted(Event):
    """Event: OCR/AI extraction finished."""

    event_type: str = field(default=EventType.EXTRACTION_COMPLETED.value)
    engine: str = ""  # "apple-vision", "gpt-4o", "claude-sonnet"
    provider: str = ""  # "local", "openai", "anthropic"
    field_count: int = 0
    avg_confidence: float = 0.0
    processing_time_ms: float = 0.0
    cost_usd: float = 0.0


@dataclass
class ValidationCompleted(Event):
    """Event: GBIF/IPNI validation finished."""

    event_type: str = field(default=EventType.VALIDATION_COMPLETED.value)
    validator: str = ""  # "gbif", "ipni"
    field_name: str = ""
    is_valid: bool = False
    matched_name: Optional[str] = None
    cache_hit: bool = False


@dataclass
class SpecimenExported(Event):
    """Event: Specimen exported to DwC-A or other format."""

    event_type: str = field(default=EventType.SPECIMEN_EXPORTED.value)
    export_format: str = ""  # "dwc-a", "csv", "json"
    destination: str = ""  # File path or URL
    record_count: int = 1


@dataclass
class BatchStarted(Event):
    """Event: Batch processing started."""

    event_type: str = field(default=EventType.BATCH_STARTED.value)
    batch_id: str = ""
    specimen_count: int = 0
    operation: str = ""  # "extraction", "validation", "export"


@dataclass
class BatchCompleted(Event):
    """Event: Batch processing completed."""

    event_type: str = field(default=EventType.BATCH_COMPLETED.value)
    batch_id: str = ""
    success_count: int = 0
    failure_count: int = 0
    total_time_ms: float = 0.0


# Registry mapping event type strings to classes
EVENT_REGISTRY: Dict[str, Type[Event]] = {
    EventType.SPECIMEN_CREATED.value: SpecimenCreated,
    EventType.SPECIMEN_UPDATED.value: SpecimenUpdated,
    EventType.SPECIMEN_DELETED.value: SpecimenDeleted,
    EventType.STATUS_CHANGED.value: StatusChanged,
    EventType.FIELD_CORRECTED.value: FieldCorrected,
    EventType.EXTRACTION_COMPLETED.value: ExtractionCompleted,
    EventType.VALIDATION_COMPLETED.value: ValidationCompleted,
    EventType.SPECIMEN_EXPORTED.value: SpecimenExported,
    EventType.BATCH_STARTED.value: BatchStarted,
    EventType.BATCH_COMPLETED.value: BatchCompleted,
}


class EventStore:
    """
    Append-only event log with JSON Lines storage.

    Features:
    - Durable append-only storage
    - Event replay by specimen, time range, or type
    - Pluggable event handlers for side effects
    """

    def __init__(self, log_path: Path):
        """Initialize event store.

        Args:
            log_path: Path to JSONL event log file
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def append(self, event: Event) -> None:
        """Append event to log and notify handlers.

        Args:
            event: Event to append
        """
        # Write to log file
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        logger.debug(f"Event appended: {event.event_type} for {event.specimen_id}")

        # Notify handlers
        self._notify_handlers(event)

    def replay(
        self,
        specimen_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Iterator[Event]:
        """Replay events with optional filters.

        Args:
            specimen_id: Filter by specimen ID
            event_type: Filter by event type
            since: Filter events after this time
            until: Filter events before this time

        Yields:
            Matching events in chronological order
        """
        if not self.log_path.exists():
            return

        with open(self.log_path) as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    event = Event.from_dict(data)

                    # Apply filters
                    if specimen_id and event.specimen_id != specimen_id:
                        continue
                    if event_type and event.event_type != event_type:
                        continue
                    if since or until:
                        event_time = datetime.fromisoformat(event.timestamp)
                        if since and event_time < since:
                            continue
                        if until and event_time > until:
                            continue

                    yield event

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse event: {e}")

    def get_specimen_history(self, specimen_id: str) -> List[Event]:
        """Get complete event history for a specimen.

        Args:
            specimen_id: Specimen to get history for

        Returns:
            List of events in chronological order
        """
        return list(self.replay(specimen_id=specimen_id))

    def get_latest_status(self, specimen_id: str) -> Optional[str]:
        """Get current status by replaying status changes.

        Args:
            specimen_id: Specimen to check

        Returns:
            Current status or None if no status events
        """
        status = None
        for event in self.replay(
            specimen_id=specimen_id,
            event_type=EventType.STATUS_CHANGED.value,
        ):
            if isinstance(event, StatusChanged):
                status = event.new_status
        return status

    def count_events(
        self,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Count events matching filters.

        Args:
            event_type: Filter by event type
            since: Count events after this time

        Returns:
            Number of matching events
        """
        return sum(1 for _ in self.replay(event_type=event_type, since=since))

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Event], None],
    ) -> None:
        """Register handler for event type.

        Args:
            event_type: Event type to handle
            handler: Callback function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def _notify_handlers(self, event: Event) -> None:
        """Notify registered handlers of event."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


class EventSourcedStorage:
    """
    Storage wrapper that emits events for all operations.

    Wraps any SpecimenStorage implementation and adds event sourcing.
    """

    def __init__(self, storage: Any, event_store: EventStore, actor: str = "system"):
        """Initialize event-sourced storage.

        Args:
            storage: Underlying SpecimenStorage implementation
            event_store: EventStore for recording events
            actor: Default actor for events
        """
        self._storage = storage
        self._event_store = event_store
        self._actor = actor

    def get(self, specimen_id: str) -> Any:
        """Get specimen (passthrough, no event)."""
        return self._storage.get(specimen_id)

    def put(self, specimen: Any, reason: str = "") -> None:
        """Store specimen and emit event."""
        existing = self._storage.get(specimen.specimen_id)

        self._storage.put(specimen)

        if existing is None:
            # New specimen
            self._event_store.append(
                SpecimenCreated(
                    specimen_id=specimen.specimen_id,
                    actor=self._actor,
                    source="storage_put",
                    initial_status=specimen.status,
                    field_count=len(specimen.dwc_fields),
                )
            )
        else:
            # Updated specimen
            changed_fields = self._detect_changes(existing, specimen)
            if changed_fields:
                self._event_store.append(
                    SpecimenUpdated(
                        specimen_id=specimen.specimen_id,
                        actor=self._actor,
                        changed_fields=changed_fields,
                        reason=reason,
                    )
                )

            # Check for status change
            if existing.status != specimen.status:
                self._event_store.append(
                    StatusChanged(
                        specimen_id=specimen.specimen_id,
                        actor=self._actor,
                        old_status=existing.status,
                        new_status=specimen.status,
                        reason=reason,
                    )
                )

    def delete(self, specimen_id: str, reason: str = "") -> bool:
        """Delete specimen and emit event."""
        result = self._storage.delete(specimen_id)

        if result:
            self._event_store.append(
                SpecimenDeleted(
                    specimen_id=specimen_id,
                    actor=self._actor,
                    reason=reason,
                )
            )

        return result

    def list(self, **kwargs: Any) -> List[Any]:
        """List specimens (passthrough)."""
        return self._storage.list(**kwargs)

    def count(self, **kwargs: Any) -> int:
        """Count specimens (passthrough)."""
        return self._storage.count(**kwargs)

    def record_field_correction(
        self,
        specimen_id: str,
        field_name: str,
        old_value: str,
        new_value: str,
        correction_type: str = "manual",
    ) -> None:
        """Record a field correction event."""
        self._event_store.append(
            FieldCorrected(
                specimen_id=specimen_id,
                actor=self._actor,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                correction_type=correction_type,
            )
        )

    def record_extraction(
        self,
        specimen_id: str,
        engine: str,
        provider: str,
        field_count: int,
        avg_confidence: float,
        processing_time_ms: float,
        cost_usd: float = 0.0,
    ) -> None:
        """Record an extraction completion event."""
        self._event_store.append(
            ExtractionCompleted(
                specimen_id=specimen_id,
                actor=self._actor,
                engine=engine,
                provider=provider,
                field_count=field_count,
                avg_confidence=avg_confidence,
                processing_time_ms=processing_time_ms,
                cost_usd=cost_usd,
            )
        )

    def record_validation(
        self,
        specimen_id: str,
        validator: str,
        field_name: str,
        is_valid: bool,
        matched_name: Optional[str] = None,
        cache_hit: bool = False,
    ) -> None:
        """Record a validation completion event."""
        self._event_store.append(
            ValidationCompleted(
                specimen_id=specimen_id,
                actor=self._actor,
                validator=validator,
                field_name=field_name,
                is_valid=is_valid,
                matched_name=matched_name,
                cache_hit=cache_hit,
            )
        )

    def _detect_changes(self, old: Any, new: Any) -> List[str]:
        """Detect which fields changed between specimens."""
        changed = []

        # Compare DwC fields
        old_fields = old.dwc_fields or {}
        new_fields = new.dwc_fields or {}

        all_keys = set(old_fields.keys()) | set(new_fields.keys())
        for key in all_keys:
            old_val = old_fields.get(key, {}).get("value")
            new_val = new_fields.get(key, {}).get("value")
            if old_val != new_val:
                changed.append(key)

        # Compare metadata
        if old.metadata != new.metadata:
            changed.append("metadata")

        if old.priority != new.priority:
            changed.append("priority")

        return changed


__all__ = [
    # Event types
    "Event",
    "EventType",
    "SpecimenCreated",
    "SpecimenUpdated",
    "SpecimenDeleted",
    "StatusChanged",
    "FieldCorrected",
    "ExtractionCompleted",
    "ValidationCompleted",
    "SpecimenExported",
    "BatchStarted",
    "BatchCompleted",
    # Store
    "EventStore",
    "EventSourcedStorage",
    "EVENT_REGISTRY",
]

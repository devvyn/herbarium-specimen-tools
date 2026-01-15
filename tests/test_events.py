"""
Tests for event sourcing module.

Tests event types, EventStore, and EventSourcedStorage wrapper.
"""

from datetime import UTC, datetime

import pytest

from src.core.events import (
    EVENT_REGISTRY,
    Event,
    EventSourcedStorage,
    EventStore,
    EventType,
    ExtractionCompleted,
    FieldCorrected,
    SpecimenCreated,
    StatusChanged,
)
from src.core.protocols import SpecimenData


class TestEventTypes:
    """Tests for event dataclasses."""

    def test_event_has_required_fields(self):
        """Verify base Event has required fields."""
        event = Event()

        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.actor == "system"

    def test_event_to_dict(self):
        """Verify event serialization."""
        event = SpecimenCreated(
            specimen_id="TEST-001",
            source="test",
            initial_status="pending",
            field_count=5,
        )

        data = event.to_dict()

        assert data["specimen_id"] == "TEST-001"
        assert data["event_type"] == "specimen_created"
        assert data["source"] == "test"
        assert data["field_count"] == 5

    def test_event_from_dict(self):
        """Verify event deserialization."""
        data = {
            "event_id": "test-123",
            "timestamp": "2025-01-01T00:00:00+00:00",
            "event_type": "specimen_created",
            "specimen_id": "TEST-001",
            "source": "test",
            "initial_status": "pending",
            "field_count": 5,
        }

        event = Event.from_dict(data)

        assert isinstance(event, SpecimenCreated)
        assert event.specimen_id == "TEST-001"
        assert event.source == "test"

    def test_status_changed_event(self):
        """Verify StatusChanged event."""
        event = StatusChanged(
            specimen_id="TEST-001",
            old_status="pending",
            new_status="approved",
            reason="Verified by curator",
        )

        assert event.event_type == "status_changed"
        assert event.old_status == "pending"
        assert event.new_status == "approved"

    def test_field_corrected_event(self):
        """Verify FieldCorrected event."""
        event = FieldCorrected(
            specimen_id="TEST-001",
            field_name="scientificName",
            old_value="Artemisia frigida",
            new_value="Artemisia frigida Willd.",
            correction_type="authority_added",
        )

        assert event.event_type == "field_corrected"
        assert event.field_name == "scientificName"
        assert event.confidence_after == 1.0  # Manual corrections

    def test_extraction_completed_event(self):
        """Verify ExtractionCompleted event."""
        event = ExtractionCompleted(
            specimen_id="TEST-001",
            engine="apple-vision",
            provider="local",
            field_count=12,
            avg_confidence=0.85,
            processing_time_ms=1500.0,
            cost_usd=0.0,
        )

        assert event.event_type == "extraction_completed"
        assert event.cost_usd == 0.0

    def test_all_event_types_in_registry(self):
        """Verify all event types are registered."""
        for event_type in EventType:
            assert event_type.value in EVENT_REGISTRY


class TestEventStore:
    """Tests for EventStore."""

    @pytest.fixture
    def event_store(self, tmp_path):
        """Create EventStore with temp file."""
        return EventStore(log_path=tmp_path / "events.jsonl")

    def test_append_event(self, event_store):
        """Verify event is appended to log."""
        event = SpecimenCreated(
            specimen_id="TEST-001",
            source="test",
        )

        event_store.append(event)

        assert event_store.log_path.exists()
        with open(event_store.log_path) as f:
            lines = f.readlines()
        assert len(lines) == 1

    def test_append_multiple_events(self, event_store):
        """Verify multiple events are appended."""
        for i in range(5):
            event_store.append(
                SpecimenCreated(specimen_id=f"TEST-{i:03d}", source="test")
            )

        with open(event_store.log_path) as f:
            lines = f.readlines()
        assert len(lines) == 5

    def test_replay_all_events(self, event_store):
        """Verify replay returns all events."""
        for i in range(3):
            event_store.append(
                SpecimenCreated(specimen_id=f"TEST-{i:03d}", source="test")
            )

        events = list(event_store.replay())

        assert len(events) == 3

    def test_replay_filter_by_specimen(self, event_store):
        """Verify replay filters by specimen ID."""
        event_store.append(SpecimenCreated(specimen_id="A", source="test"))
        event_store.append(SpecimenCreated(specimen_id="B", source="test"))
        event_store.append(StatusChanged(specimen_id="A", old_status="pending", new_status="approved"))

        events = list(event_store.replay(specimen_id="A"))

        assert len(events) == 2
        assert all(e.specimen_id == "A" for e in events)

    def test_replay_filter_by_event_type(self, event_store):
        """Verify replay filters by event type."""
        event_store.append(SpecimenCreated(specimen_id="A", source="test"))
        event_store.append(StatusChanged(specimen_id="A", old_status="pending", new_status="approved"))
        event_store.append(SpecimenCreated(specimen_id="B", source="test"))

        events = list(event_store.replay(event_type="specimen_created"))

        assert len(events) == 2
        assert all(e.event_type == "specimen_created" for e in events)

    def test_replay_filter_by_time(self, event_store, tmp_path):
        """Verify replay filters by time range."""
        # Create events with specific timestamps
        old_event = SpecimenCreated(specimen_id="OLD", source="test")
        old_event.timestamp = "2024-01-01T00:00:00+00:00"

        new_event = SpecimenCreated(specimen_id="NEW", source="test")
        new_event.timestamp = "2025-06-01T00:00:00+00:00"

        event_store.append(old_event)
        event_store.append(new_event)

        # Filter since 2025
        since = datetime(2025, 1, 1, tzinfo=UTC)
        events = list(event_store.replay(since=since))

        assert len(events) == 1
        assert events[0].specimen_id == "NEW"

    def test_get_specimen_history(self, event_store):
        """Verify getting complete specimen history."""
        event_store.append(SpecimenCreated(specimen_id="TEST-001", source="test"))
        event_store.append(StatusChanged(specimen_id="TEST-001", old_status="pending", new_status="in_review"))
        event_store.append(FieldCorrected(specimen_id="TEST-001", field_name="scientificName", old_value="x", new_value="y"))
        event_store.append(StatusChanged(specimen_id="TEST-001", old_status="in_review", new_status="approved"))

        history = event_store.get_specimen_history("TEST-001")

        assert len(history) == 4
        assert history[0].event_type == "specimen_created"
        assert history[-1].event_type == "status_changed"

    def test_get_latest_status(self, event_store):
        """Verify getting current status from event history."""
        event_store.append(SpecimenCreated(specimen_id="TEST-001", source="test"))
        event_store.append(StatusChanged(specimen_id="TEST-001", old_status="pending", new_status="in_review"))
        event_store.append(StatusChanged(specimen_id="TEST-001", old_status="in_review", new_status="approved"))

        status = event_store.get_latest_status("TEST-001")

        assert status == "approved"

    def test_get_latest_status_no_events(self, event_store):
        """Verify None returned when no status events."""
        status = event_store.get_latest_status("NONEXISTENT")
        assert status is None

    def test_count_events(self, event_store):
        """Verify event counting."""
        event_store.append(SpecimenCreated(specimen_id="A", source="test"))
        event_store.append(SpecimenCreated(specimen_id="B", source="test"))
        event_store.append(StatusChanged(specimen_id="A", old_status="x", new_status="y"))

        assert event_store.count_events() == 3
        assert event_store.count_events(event_type="specimen_created") == 2

    def test_event_handler_registration(self, event_store):
        """Verify event handlers are called."""
        received_events = []

        def handler(event):
            received_events.append(event)

        event_store.register_handler("specimen_created", handler)
        event_store.append(SpecimenCreated(specimen_id="TEST", source="test"))

        assert len(received_events) == 1
        assert received_events[0].specimen_id == "TEST"

    def test_handler_not_called_for_other_types(self, event_store):
        """Verify handlers only called for registered types."""
        received_events = []

        def handler(event):
            received_events.append(event)

        event_store.register_handler("specimen_created", handler)
        event_store.append(StatusChanged(specimen_id="TEST", old_status="x", new_status="y"))

        assert len(received_events) == 0


class TestEventSourcedStorage:
    """Tests for EventSourcedStorage wrapper."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        class MockStorage:
            def __init__(self):
                self._data = {}

            def get(self, specimen_id):
                return self._data.get(specimen_id)

            def put(self, specimen):
                self._data[specimen.specimen_id] = specimen

            def delete(self, specimen_id):
                if specimen_id in self._data:
                    del self._data[specimen_id]
                    return True
                return False

            def list(self, **kwargs):
                return list(self._data.values())

            def count(self, **kwargs):
                return len(self._data)

        return MockStorage()

    @pytest.fixture
    def event_sourced_storage(self, mock_storage, tmp_path):
        """Create EventSourcedStorage with mock storage."""
        event_store = EventStore(log_path=tmp_path / "events.jsonl")
        return EventSourcedStorage(mock_storage, event_store, actor="test-user")

    def test_put_new_specimen_emits_created(self, event_sourced_storage):
        """Verify SpecimenCreated event on new specimen."""
        specimen = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={"scientificName": {"value": "Test", "confidence": 0.9}},
            status="pending",
            priority="MEDIUM",
            metadata={},
        )

        event_sourced_storage.put(specimen)

        events = list(event_sourced_storage._event_store.replay())
        assert len(events) == 1
        assert events[0].event_type == "specimen_created"
        assert events[0].actor == "test-user"

    def test_put_existing_specimen_emits_updated(self, event_sourced_storage):
        """Verify SpecimenUpdated event on update."""
        specimen = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={"scientificName": {"value": "Test", "confidence": 0.9}},
            status="pending",
            priority="MEDIUM",
            metadata={},
        )
        event_sourced_storage.put(specimen)

        # Update the specimen
        updated = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={"scientificName": {"value": "Updated", "confidence": 0.95}},
            status="pending",
            priority="MEDIUM",
            metadata={},
        )
        event_sourced_storage.put(updated, reason="correction")

        events = list(event_sourced_storage._event_store.replay())
        assert len(events) == 2
        assert events[1].event_type == "specimen_updated"
        assert "scientificName" in events[1].changed_fields

    def test_status_change_emits_status_changed(self, event_sourced_storage):
        """Verify StatusChanged event on status update."""
        specimen = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={},
            status="pending",
            priority="MEDIUM",
            metadata={},
        )
        event_sourced_storage.put(specimen)

        # Change status
        updated = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={},
            status="approved",
            priority="MEDIUM",
            metadata={},
        )
        event_sourced_storage.put(updated)

        events = list(event_sourced_storage._event_store.replay(
            event_type="status_changed"
        ))
        assert len(events) == 1
        assert events[0].old_status == "pending"
        assert events[0].new_status == "approved"

    def test_delete_emits_deleted(self, event_sourced_storage):
        """Verify SpecimenDeleted event on delete."""
        specimen = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields={},
            status="pending",
            priority="MEDIUM",
            metadata={},
        )
        event_sourced_storage.put(specimen)
        event_sourced_storage.delete("TEST-001", reason="duplicate")

        events = list(event_sourced_storage._event_store.replay(
            event_type="specimen_deleted"
        ))
        assert len(events) == 1
        assert events[0].reason == "duplicate"

    def test_record_field_correction(self, event_sourced_storage):
        """Verify FieldCorrected event recording."""
        event_sourced_storage.record_field_correction(
            specimen_id="TEST-001",
            field_name="scientificName",
            old_value="Artemisia frigida",
            new_value="Artemisia frigida Willd.",
            correction_type="authority_added",
        )

        events = list(event_sourced_storage._event_store.replay(
            event_type="field_corrected"
        ))
        assert len(events) == 1
        assert events[0].field_name == "scientificName"

    def test_record_extraction(self, event_sourced_storage):
        """Verify ExtractionCompleted event recording."""
        event_sourced_storage.record_extraction(
            specimen_id="TEST-001",
            engine="apple-vision",
            provider="local",
            field_count=10,
            avg_confidence=0.85,
            processing_time_ms=1200.0,
        )

        events = list(event_sourced_storage._event_store.replay(
            event_type="extraction_completed"
        ))
        assert len(events) == 1
        assert events[0].engine == "apple-vision"

    def test_record_validation(self, event_sourced_storage):
        """Verify ValidationCompleted event recording."""
        event_sourced_storage.record_validation(
            specimen_id="TEST-001",
            validator="gbif",
            field_name="scientificName",
            is_valid=True,
            matched_name="Artemisia frigida Willd.",
            cache_hit=True,
        )

        events = list(event_sourced_storage._event_store.replay(
            event_type="validation_completed"
        ))
        assert len(events) == 1
        assert events[0].is_valid is True
        assert events[0].cache_hit is True

    def test_passthrough_get(self, event_sourced_storage):
        """Verify get passes through without event."""
        result = event_sourced_storage.get("NONEXISTENT")
        assert result is None

        events = list(event_sourced_storage._event_store.replay())
        assert len(events) == 0

    def test_passthrough_list(self, event_sourced_storage):
        """Verify list passes through without event."""
        result = event_sourced_storage.list()
        assert result == []

    def test_passthrough_count(self, event_sourced_storage):
        """Verify count passes through without event."""
        result = event_sourced_storage.count()
        assert result == 0

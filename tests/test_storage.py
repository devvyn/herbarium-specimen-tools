"""
Tests for storage backends.

Tests both JSONStorage and SQLiteStorage implementations.
"""

import json

import pytest

from src.core.protocols import SpecimenData
from src.core.storage import JSONStorage, SQLiteStorage, create_storage

# Sample test data
SAMPLE_SPECIMEN = SpecimenData(
    specimen_id="TEST-001",
    dwc_fields={
        "scientificName": {"value": "Artemisia frigida", "confidence": 0.95},
        "catalogNumber": {"value": "TEST-001", "confidence": 0.98},
    },
    status="pending",
    priority="MEDIUM",
    metadata={"model": "gpt-4o-mini", "provider": "openai"},
)

SAMPLE_JSONL = [
    {
        "image": "SPEC-001",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "timestamp": "2025-01-01T00:00:00Z",
        "dwc": {
            "scientificName": {"value": "Artemisia frigida", "confidence": 0.95},
            "catalogNumber": {"value": "SPEC-001", "confidence": 0.98},
        },
    },
    {
        "image": "SPEC-002",
        "model": "gpt-4o",
        "provider": "openai",
        "timestamp": "2025-01-01T00:01:00Z",
        "dwc": {
            "scientificName": {"value": "Rosa acicularis", "confidence": 0.90},
            "catalogNumber": {"value": "SPEC-002", "confidence": 0.99},
        },
    },
]


@pytest.fixture
def json_storage(tmp_path):
    """Create a JSONStorage instance with temp directory."""
    return JSONStorage(data_dir=tmp_path)


@pytest.fixture
def sqlite_storage(tmp_path):
    """Create a SQLiteStorage instance with temp database."""
    storage = SQLiteStorage(db_path=tmp_path / "test.db")
    yield storage
    storage.close()


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create a sample JSONL file for testing."""
    jsonl_path = tmp_path / "raw.jsonl"
    with open(jsonl_path, "w") as f:
        for record in SAMPLE_JSONL:
            f.write(json.dumps(record) + "\n")
    return jsonl_path


class TestJSONStorage:
    """Tests for JSONStorage backend."""

    def test_put_and_get(self, json_storage):
        """Test storing and retrieving a specimen."""
        json_storage.put(SAMPLE_SPECIMEN)
        retrieved = json_storage.get("TEST-001")

        assert retrieved is not None
        assert retrieved.specimen_id == "TEST-001"
        assert retrieved.dwc_fields["scientificName"]["value"] == "Artemisia frigida"

    def test_get_nonexistent(self, json_storage):
        """Test getting a specimen that doesn't exist."""
        assert json_storage.get("NONEXISTENT") is None

    def test_delete(self, json_storage):
        """Test deleting a specimen."""
        json_storage.put(SAMPLE_SPECIMEN)
        assert json_storage.delete("TEST-001") is True
        assert json_storage.get("TEST-001") is None

    def test_delete_nonexistent(self, json_storage):
        """Test deleting a specimen that doesn't exist."""
        assert json_storage.delete("NONEXISTENT") is False

    def test_list_all(self, json_storage):
        """Test listing all specimens."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        json_storage.put(spec1)
        json_storage.put(spec2)

        results = json_storage.list()
        assert len(results) == 2

    def test_list_filter_status(self, json_storage):
        """Test listing with status filter."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        json_storage.put(spec1)
        json_storage.put(spec2)

        results = json_storage.list(status="pending")
        assert len(results) == 1
        assert results[0].specimen_id == "A"

    def test_list_filter_priority(self, json_storage):
        """Test listing with priority filter."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "pending", "LOW", {})
        json_storage.put(spec1)
        json_storage.put(spec2)

        results = json_storage.list(priority="HIGH")
        assert len(results) == 1
        assert results[0].specimen_id == "A"

    def test_list_pagination(self, json_storage):
        """Test listing with pagination."""
        for i in range(10):
            json_storage.put(SpecimenData(f"SPEC-{i:03d}", {}, "pending", "MEDIUM", {}))

        page1 = json_storage.list(limit=5, offset=0)
        page2 = json_storage.list(limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].specimen_id != page2[0].specimen_id

    def test_count(self, json_storage):
        """Test counting specimens."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        json_storage.put(spec1)
        json_storage.put(spec2)

        assert json_storage.count() == 2
        assert json_storage.count(status="pending") == 1
        assert json_storage.count(priority="HIGH") == 1

    def test_load_from_jsonl(self, json_storage, sample_jsonl):
        """Test loading specimens from JSONL file."""
        count = json_storage.load_from_jsonl(sample_jsonl)

        assert count == 2
        spec = json_storage.get("SPEC-001")
        assert spec is not None
        assert spec.dwc_fields["scientificName"]["value"] == "Artemisia frigida"

    def test_state_persistence(self, tmp_path, sample_jsonl):
        """Test that review state persists across storage instances."""
        # First instance: load and modify
        storage1 = JSONStorage(data_dir=tmp_path)
        storage1.load_from_jsonl(sample_jsonl)

        spec = storage1.get("SPEC-001")
        spec.status = "approved"
        spec.metadata["review_notes"] = "Looks good"
        storage1.put(spec)
        storage1.close()

        # Second instance: verify state persisted
        storage2 = JSONStorage(data_dir=tmp_path)
        storage2.load_from_jsonl(sample_jsonl)

        spec2 = storage2.get("SPEC-001")
        assert spec2.status == "approved"
        assert spec2.metadata.get("review_notes") == "Looks good"


class TestSQLiteStorage:
    """Tests for SQLiteStorage backend."""

    def test_put_and_get(self, sqlite_storage):
        """Test storing and retrieving a specimen."""
        sqlite_storage.put(SAMPLE_SPECIMEN)
        retrieved = sqlite_storage.get("TEST-001")

        assert retrieved is not None
        assert retrieved.specimen_id == "TEST-001"
        assert retrieved.dwc_fields["scientificName"]["value"] == "Artemisia frigida"

    def test_get_nonexistent(self, sqlite_storage):
        """Test getting a specimen that doesn't exist."""
        assert sqlite_storage.get("NONEXISTENT") is None

    def test_delete(self, sqlite_storage):
        """Test deleting a specimen."""
        sqlite_storage.put(SAMPLE_SPECIMEN)
        assert sqlite_storage.delete("TEST-001") is True
        assert sqlite_storage.get("TEST-001") is None

    def test_delete_nonexistent(self, sqlite_storage):
        """Test deleting a specimen that doesn't exist."""
        assert sqlite_storage.delete("NONEXISTENT") is False

    def test_list_all(self, sqlite_storage):
        """Test listing all specimens."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        sqlite_storage.put(spec1)
        sqlite_storage.put(spec2)

        results = sqlite_storage.list()
        assert len(results) == 2

    def test_list_filter_status(self, sqlite_storage):
        """Test listing with status filter."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        sqlite_storage.put(spec1)
        sqlite_storage.put(spec2)

        results = sqlite_storage.list(status="pending")
        assert len(results) == 1
        assert results[0].specimen_id == "A"

    def test_list_filter_priority(self, sqlite_storage):
        """Test listing with priority filter."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "pending", "LOW", {})
        sqlite_storage.put(spec1)
        sqlite_storage.put(spec2)

        results = sqlite_storage.list(priority="HIGH")
        assert len(results) == 1
        assert results[0].specimen_id == "A"

    def test_list_pagination(self, sqlite_storage):
        """Test listing with pagination."""
        for i in range(10):
            sqlite_storage.put(
                SpecimenData(f"SPEC-{i:03d}", {}, "pending", "MEDIUM", {})
            )

        page1 = sqlite_storage.list(limit=5, offset=0)
        page2 = sqlite_storage.list(limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5

    def test_count(self, sqlite_storage):
        """Test counting specimens."""
        spec1 = SpecimenData("A", {}, "pending", "HIGH", {})
        spec2 = SpecimenData("B", {}, "approved", "LOW", {})
        sqlite_storage.put(spec1)
        sqlite_storage.put(spec2)

        assert sqlite_storage.count() == 2
        assert sqlite_storage.count(status="pending") == 1
        assert sqlite_storage.count(priority="HIGH") == 1

    def test_load_from_jsonl(self, sqlite_storage, sample_jsonl):
        """Test loading specimens from JSONL file."""
        count = sqlite_storage.load_from_jsonl(sample_jsonl)

        assert count == 2
        spec = sqlite_storage.get("SPEC-001")
        assert spec is not None
        assert spec.dwc_fields["scientificName"]["value"] == "Artemisia frigida"

    def test_update_existing(self, sqlite_storage):
        """Test updating an existing specimen."""
        sqlite_storage.put(SAMPLE_SPECIMEN)

        # Update status
        updated = SpecimenData(
            specimen_id="TEST-001",
            dwc_fields=SAMPLE_SPECIMEN.dwc_fields,
            status="approved",
            priority="LOW",
            metadata={"review_notes": "Updated"},
        )
        sqlite_storage.put(updated)

        retrieved = sqlite_storage.get("TEST-001")
        assert retrieved.status == "approved"
        assert retrieved.priority == "LOW"


class TestStorageFactory:
    """Tests for storage factory function."""

    def test_create_json_storage(self, tmp_path):
        """Test creating JSON storage via factory."""
        storage = create_storage("json", {"path": str(tmp_path)})
        assert isinstance(storage, JSONStorage)

    def test_create_sqlite_storage(self, tmp_path):
        """Test creating SQLite storage via factory."""
        storage = create_storage("sqlite", {"path": str(tmp_path / "test.db")})
        assert isinstance(storage, SQLiteStorage)

    def test_create_unknown_backend(self):
        """Test that unknown backend raises error."""
        with pytest.raises(ValueError, match="Unknown storage backend"):
            create_storage("postgres", {})

"""
Tests for Local Development Server

Tests cover:
- Review state persistence (notes, review_notes, status)
- Quick actions (approve, reject, flag, reextract)
- Persistence across server restarts (simulated)
- All review metadata fields

Uses FastAPI TestClient and simulates the full persistence cycle.
"""

import json

import pytest
from fastapi.testclient import TestClient

# Sample extraction data for testing
SAMPLE_RECORDS = [
    {
        "image": "TEST-001",
        "timestamp": "2025-01-15T10:30:00Z",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "extraction_method": "gpt-4o-mini",
        "ocr_engine": "apple_vision",
        "dwc": {
            "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
            "scientificName": {"value": "Artemisia frigida Willd.", "confidence": 0.95},
            "eventDate": {"value": "1969-08-14", "confidence": 0.92},
            "recordedBy": {"value": "J. Tester", "confidence": 0.90},
            "locality": {"value": "Test Location", "confidence": 0.88},
            "stateProvince": {"value": "Test State", "confidence": 0.95},
            "country": {"value": "Test Country", "confidence": 0.98},
        },
    },
    {
        "image": "TEST-002",
        "timestamp": "2025-01-15T10:31:00Z",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "extraction_method": "gpt-4o-mini",
        "ocr_engine": "apple_vision",
        "dwc": {
            "catalogNumber": {"value": "TEST-002", "confidence": 0.90},
            "scientificName": {"value": "Test species", "confidence": 0.45},
            "eventDate": {"value": "1970-07-22", "confidence": 0.50},
            "recordedBy": {"value": "A. Tester", "confidence": 0.85},
            "locality": {"value": "Test Hills", "confidence": 0.40},
            "stateProvince": {"value": "Test State", "confidence": 0.95},
            "country": {"value": "Test Country", "confidence": 0.98},
        },
    },
]


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary directory with sample extraction data."""
    # Create the data directory structure
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create raw.jsonl with sample records
    raw_file = data_dir / "raw.jsonl"
    with open(raw_file, "w") as f:
        for record in SAMPLE_RECORDS:
            f.write(json.dumps(record) + "\n")

    # Create empty images directory
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    return tmp_path, data_dir, images_dir


@pytest.fixture
def app_and_state_file(test_data_dir, monkeypatch):
    """Create FastAPI app with controlled state file location."""
    tmp_path, data_dir, images_dir = test_data_dir

    # Patch the REVIEW_STATE_FILE to use temp directory
    state_file = tmp_path / "review_state.json"

    # Import after patching
    import mobile.run_server as server_module
    monkeypatch.setattr(server_module, "REVIEW_STATE_FILE", state_file)
    monkeypatch.setattr(server_module, "DEFAULT_AAFC_OUTPUT", data_dir.parent)

    # Mock the find_latest_extraction to return our test file
    from src.data import loader
    monkeypatch.setattr(loader, "DEFAULT_AAFC_OUTPUT", data_dir)

    # Create the app
    app = server_module.create_app(
        data_path=data_dir / "raw.jsonl",
        images_path=images_dir
    )

    return app, state_file, server_module


@pytest.fixture
def client(app_and_state_file):
    """Create test client."""
    app, state_file, server_module = app_and_state_file
    return TestClient(app)


class TestLocalServerBasics:
    """Basic endpoint tests for local server."""

    def test_root_redirects_to_index(self, client):
        """Test root redirects to index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/index.html" in response.headers.get("location", "")

    def test_get_queue_no_auth_required(self, client):
        """Test queue access without authentication."""
        response = client.get("/api/v1/queue")
        assert response.status_code == 200
        data = response.json()
        assert "specimens" in data
        assert len(data["specimens"]) == 2

    def test_get_specimen_no_auth_required(self, client):
        """Test specimen access without authentication."""
        response = client.get("/api/v1/specimen/TEST-001")
        assert response.status_code == 200
        data = response.json()
        assert data["specimen"]["id"] == "TEST-001"

    def test_get_statistics_no_auth_required(self, client):
        """Test statistics access without authentication."""
        response = client.get("/api/v1/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_specimens"] == 2


class TestQuickActions:
    """Tests for quick action endpoints."""

    def test_approve_specimen(self, client):
        """Test approving a specimen."""
        response = client.post("/api/v1/specimen/TEST-001/approve")
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

        # Verify status changed
        response = client.get("/api/v1/specimen/TEST-001")
        assert response.json()["specimen"]["review"]["status"] == "APPROVED"

    def test_reject_specimen(self, client):
        """Test rejecting a specimen."""
        response = client.post("/api/v1/specimen/TEST-001/reject?notes=Quality%20too%20low")
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

        # Verify status changed
        response = client.get("/api/v1/specimen/TEST-001")
        assert response.json()["specimen"]["review"]["status"] == "REJECTED"

    def test_flag_specimen(self, client):
        """Test flagging a specimen."""
        response = client.post("/api/v1/specimen/TEST-001/flag?notes=Needs%20expert")
        assert response.status_code == 200
        assert response.json()["status"] == "flagged"

        # Verify flagged
        response = client.get("/api/v1/specimen/TEST-001")
        assert response.json()["specimen"]["review"]["flagged"] is True

    def test_request_reextraction(self, client):
        """Test requesting re-extraction."""
        response = client.post(
            "/api/v1/specimen/TEST-001/request-reextraction?notes=OCR%20failed"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "reextraction_requested"

        # Verify reextraction_requested flag
        response = client.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["reextraction_requested"] is True
        # Note: review_notes should be set via request-reextraction
        assert review["review_notes"] == "OCR failed"


class TestNotesPersistence:
    """Tests for notes persistence."""

    def test_save_dwc_notes(self, client):
        """Test saving DwC notes via PUT."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={"notes": "This is a canonical DwC note"}
        )
        assert response.status_code == 200

        # Verify notes saved
        response = client.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["notes"] == "This is a canonical DwC note"

    def test_save_review_notes(self, client):
        """Test saving review feedback notes via PUT."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={"review_notes": "Workflow feedback for re-extraction"}
        )
        assert response.status_code == 200

        # Verify review_notes saved
        response = client.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["review_notes"] == "Workflow feedback for re-extraction"

    def test_save_both_notes_types(self, client):
        """Test saving both note types simultaneously."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={
                "notes": "DwC note for export",
                "review_notes": "Internal workflow feedback"
            }
        )
        assert response.status_code == 200

        # Verify both notes saved
        response = client.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["notes"] == "DwC note for export"
        assert review["review_notes"] == "Internal workflow feedback"

    def test_update_priority(self, client):
        """Test updating specimen priority."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={"priority": "CRITICAL"}
        )
        assert response.status_code == 200

        # Verify priority changed
        response = client.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["priority"] == "CRITICAL"


class TestStatePersistence:
    """Tests for review state persistence across server restarts."""

    def test_state_file_created_on_save(self, app_and_state_file, client):
        """Test that state file is created when saving."""
        app, state_file, server_module = app_and_state_file

        # Initially state file may not exist or be empty
        if state_file.exists():
            state_file.unlink()

        # Save some review data
        client.put(
            "/api/v1/specimen/TEST-001",
            json={"notes": "Test note", "review_notes": "Test review note"}
        )

        # Verify state file was created
        assert state_file.exists()

        # Verify content
        with open(state_file) as f:
            state = json.load(f)

        assert "TEST-001" in state
        assert state["TEST-001"]["notes"] == "Test note"
        assert state["TEST-001"]["review_notes"] == "Test review note"

    def test_state_persists_across_restart(self, test_data_dir, monkeypatch):
        """Test that state persists when creating a new app instance."""
        tmp_path, data_dir, images_dir = test_data_dir
        state_file = tmp_path / "review_state.json"

        import mobile.run_server as server_module
        monkeypatch.setattr(server_module, "REVIEW_STATE_FILE", state_file)

        from src.data import loader
        monkeypatch.setattr(loader, "DEFAULT_AAFC_OUTPUT", data_dir)

        # Create first app instance
        app1 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client1 = TestClient(app1)

        # Save review data
        client1.put(
            "/api/v1/specimen/TEST-001",
            json={
                "notes": "Persisted DwC note",
                "review_notes": "Persisted review feedback"
            }
        )
        client1.post("/api/v1/specimen/TEST-001/approve")

        # Verify saved in first instance
        response = client1.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]
        assert review["notes"] == "Persisted DwC note"
        assert review["review_notes"] == "Persisted review feedback"
        assert review["status"] == "APPROVED"

        # Clear in-memory state to simulate restart
        server_module.specimens.clear()

        # Create second app instance (simulating restart)
        app2 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client2 = TestClient(app2)

        # Verify state was loaded from disk
        response = client2.get("/api/v1/specimen/TEST-001")
        review = response.json()["specimen"]["review"]

        assert review["notes"] == "Persisted DwC note", \
            f"Expected 'Persisted DwC note', got '{review['notes']}'"
        assert review["review_notes"] == "Persisted review feedback", \
            f"Expected 'Persisted review feedback', got '{review['review_notes']}'"
        assert review["status"] == "APPROVED", \
            f"Expected 'APPROVED', got '{review['status']}'"

    def test_review_notes_persist_specifically(self, test_data_dir, monkeypatch):
        """
        Specific test for the reported bug: review_notes not persisting.

        This test isolates the exact issue:
        1. Save review_notes
        2. Restart server
        3. Verify review_notes is returned in API response
        """
        tmp_path, data_dir, images_dir = test_data_dir
        state_file = tmp_path / "review_state.json"

        import mobile.run_server as server_module
        monkeypatch.setattr(server_module, "REVIEW_STATE_FILE", state_file)

        from src.data import loader
        monkeypatch.setattr(loader, "DEFAULT_AAFC_OUTPUT", data_dir)

        # === Session 1: Save review_notes ===
        app1 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client1 = TestClient(app1)

        # Save ONLY review_notes (the reported bug scenario)
        response = client1.put(
            "/api/v1/specimen/TEST-001",
            json={"review_notes": "Image is not a specimen, it's a photo marker"}
        )
        assert response.status_code == 200

        # Verify saved in session 1
        response = client1.get("/api/v1/specimen/TEST-001")
        review1 = response.json()["specimen"]["review"]
        assert review1["review_notes"] == "Image is not a specimen, it's a photo marker"

        # Verify state file contains review_notes
        with open(state_file) as f:
            state = json.load(f)
        assert state["TEST-001"]["review_notes"] == "Image is not a specimen, it's a photo marker"

        # === Session 2: Restart and verify ===
        server_module.specimens.clear()

        app2 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client2 = TestClient(app2)

        # Get specimen in new session
        response = client2.get("/api/v1/specimen/TEST-001")
        review2 = response.json()["specimen"]["review"]

        # THIS IS THE BUG: review_notes should persist
        assert review2["review_notes"] == "Image is not a specimen, it's a photo marker", \
            f"review_notes did not persist! Got: '{review2.get('review_notes', '')}'"

    def test_all_review_fields_persist(self, test_data_dir, monkeypatch):
        """Test that all review fields persist correctly."""
        tmp_path, data_dir, images_dir = test_data_dir
        state_file = tmp_path / "review_state.json"

        import mobile.run_server as server_module
        monkeypatch.setattr(server_module, "REVIEW_STATE_FILE", state_file)

        from src.data import loader
        monkeypatch.setattr(loader, "DEFAULT_AAFC_OUTPUT", data_dir)

        # Session 1: Set all fields
        app1 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client1 = TestClient(app1)

        # Set notes and review_notes
        client1.put(
            "/api/v1/specimen/TEST-001",
            json={
                "notes": "DwC note",
                "review_notes": "Review feedback",
                "priority": "CRITICAL"
            }
        )

        # Flag and reject
        client1.post("/api/v1/specimen/TEST-001/flag")
        client1.post("/api/v1/specimen/TEST-001/reject")

        # Request re-extraction on TEST-002
        client1.post("/api/v1/specimen/TEST-002/request-reextraction?notes=OCR%20error")

        # Session 2: Verify all fields
        server_module.specimens.clear()
        app2 = server_module.create_app(
            data_path=data_dir / "raw.jsonl",
            images_path=images_dir
        )
        client2 = TestClient(app2)

        # Check TEST-001
        response = client2.get("/api/v1/specimen/TEST-001")
        review1 = response.json()["specimen"]["review"]
        assert review1["notes"] == "DwC note"
        assert review1["review_notes"] == "Review feedback"
        assert review1["priority"] == "CRITICAL"
        assert review1["flagged"] is True
        assert review1["status"] == "REJECTED"

        # Check TEST-002
        response = client2.get("/api/v1/specimen/TEST-002")
        review2 = response.json()["specimen"]["review"]
        assert review2["reextraction_requested"] is True
        assert review2["review_notes"] == "OCR error"


class TestErrorHandling:
    """Tests for error handling."""

    def test_specimen_not_found(self, client):
        """Test 404 for nonexistent specimen."""
        response = client.get("/api/v1/specimen/NONEXISTENT")
        assert response.status_code == 404

    def test_invalid_priority(self, client):
        """Test handling of invalid priority value."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={"priority": "INVALID"}
        )
        # Should return 500 (KeyError) or 422 (validation error)
        assert response.status_code in [422, 500]

    def test_empty_update_body(self, client):
        """Test handling of empty update body."""
        response = client.put(
            "/api/v1/specimen/TEST-001",
            json={}
        )
        # Should succeed but not change anything
        assert response.status_code == 200


class TestQueueFiltering:
    """Tests for queue filtering and pagination."""

    def test_filter_by_status(self, client):
        """Test filtering queue by status."""
        # Approve one specimen
        client.post("/api/v1/specimen/TEST-001/approve")

        # Filter for approved only
        response = client.get("/api/v1/queue?status=approved")
        data = response.json()
        assert len(data["specimens"]) == 1
        assert data["specimens"][0]["id"] == "TEST-001"

    def test_filter_by_priority(self, client):
        """Test filtering queue by priority."""
        # Set one to critical
        client.put("/api/v1/specimen/TEST-001", json={"priority": "CRITICAL"})

        # Filter for critical only
        response = client.get("/api/v1/queue?priority=CRITICAL")
        data = response.json()
        assert len(data["specimens"]) == 1
        assert data["specimens"][0]["id"] == "TEST-001"

    def test_pagination(self, client):
        """Test queue pagination."""
        response = client.get("/api/v1/queue?limit=1&offset=0")
        data = response.json()

        assert len(data["specimens"]) == 1
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["has_more"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

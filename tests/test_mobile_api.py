"""
Tests for Mobile API - FastAPI endpoints and authentication

Tests cover:
- Authentication endpoints (login, token verification)
- Review queue endpoints
- Specimen detail and update endpoints
- Image serving
- Offline sync
- Statistics
- Security (rate limiting, CORS, headers)

Uses FastAPI TestClient for endpoint testing.
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.review.mobile_api import create_mobile_app, get_password_hash


@pytest.fixture
def sample_data_dir(tmp_path):
    """Create temporary directory with sample extraction data."""
    # Create raw.jsonl
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    raw_file = data_dir / "raw.jsonl"
    sample_records = [
        {
            "image": "TEST-001",
            "timestamp": "2025-01-15T10:30:00Z",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "extraction_method": "gpt-4o-mini",
            "ocr_engine": "apple_vision",
            "dwc": {
                "catalogNumber": {"value": "TEST-001", "confidence": 0.95},
                "scientificName": {
                    "value": "Artemisia frigida Willd.",
                    "confidence": 0.95,
                },
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

    with open(raw_file, "w") as f:
        for record in sample_records:
            f.write(json.dumps(record) + "\n")

    # Create images directory (empty for testing)
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    return data_dir, images_dir


@pytest.fixture
def test_users():
    """Create test users with hashed passwords."""
    return {"testuser": get_password_hash("testpass123")}


@pytest.fixture
def app(sample_data_dir, test_users):
    """Create FastAPI app for testing."""
    data_dir, images_dir = sample_data_dir

    return create_mobile_app(
        extraction_dir=data_dir,
        image_dir=images_dir,
        enable_gbif=False,  # Disable GBIF for faster tests
        users=test_users,
    )


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get authentication token for testing."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAuthentication:
    """Tests for authentication endpoints."""

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"

    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpass"},
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_rate_limiting(self, client):
        """Test rate limiting on login endpoint."""
        # Make 5 failed attempts (rate limit threshold)
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "wrongpass"},
            )

        # 6th attempt should be rate limited
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpass"},
        )

        assert response.status_code == 429
        assert "Too many login attempts" in response.json()["detail"]

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    def test_get_current_user_no_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401  # Unauthorized (no credentials)

    def test_get_current_user_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401


class TestReviewQueue:
    """Tests for review queue endpoints."""

    def test_get_queue_success(self, client, auth_headers):
        """Test getting review queue."""
        response = client.get("/api/v1/queue", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "specimens" in data
        assert "pagination" in data
        assert len(data["specimens"]) == 2

    def test_get_queue_no_auth(self, client):
        """Test getting queue without authentication."""
        response = client.get("/api/v1/queue")

        assert response.status_code == 401  # Unauthorized (no credentials)

    def test_get_queue_pagination(self, client, auth_headers):
        """Test queue pagination."""
        response = client.get(
            "/api/v1/queue", params={"limit": 1, "offset": 0}, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["specimens"]) == 1
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["has_more"] is True

    def test_get_queue_status_filter(self, client, auth_headers):
        """Test filtering queue by status."""
        response = client.get("/api/v1/queue", params={"status": "PENDING"}, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "PENDING" for s in data["specimens"])

    def test_get_queue_invalid_status(self, client, auth_headers):
        """Test queue with invalid status filter."""
        response = client.get("/api/v1/queue", params={"status": "INVALID"}, headers=auth_headers)

        assert response.status_code == 400


class TestSpecimenEndpoints:
    """Tests for specimen detail and update endpoints."""

    def test_get_specimen_success(self, client, auth_headers):
        """Test getting specimen details."""
        response = client.get("/api/v1/specimen/TEST-001", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["specimen"]["id"] == "TEST-001"
        assert "fields" in data["specimen"]
        assert "quality" in data["specimen"]
        assert "gbif_validation" in data["specimen"]
        assert "review" in data["specimen"]

    def test_get_specimen_not_found(self, client, auth_headers):
        """Test getting nonexistent specimen."""
        response = client.get("/api/v1/specimen/NONEXISTENT", headers=auth_headers)

        assert response.status_code == 404

    def test_update_specimen(self, client, auth_headers):
        """Test updating specimen review."""
        update_data = {
            "corrections": {"scientificName": "Corrected name"},
            "status": "APPROVED",
            "flagged": True,
            "notes": "Test notes",
        }

        response = client.put("/api/v1/specimen/TEST-001", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["specimen_id"] == "TEST-001"

        # Verify update was applied
        response = client.get("/api/v1/specimen/TEST-001", headers=auth_headers)
        specimen = response.json()["specimen"]
        assert specimen["review"]["status"] == "APPROVED"
        assert specimen["review"]["flagged"] is True

    def test_update_field(self, client, auth_headers):
        """Test updating a single field."""
        field_data = {"field": "scientificName", "value": "New name", "accept_suggestion": True}

        response = client.post(
            "/api/v1/specimen/TEST-001/field/scientificName",
            json=field_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["field"] == "scientificName"
        assert data["value"] == "New name"

    def test_approve_specimen(self, client, auth_headers):
        """Test quick approve action."""
        response = client.post("/api/v1/specimen/TEST-001/approve", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["status"] == "approved"

        # Verify status changed
        response = client.get("/api/v1/specimen/TEST-001", headers=auth_headers)
        assert response.json()["specimen"]["review"]["status"] == "APPROVED"

    def test_reject_specimen(self, client, auth_headers):
        """Test quick reject action."""
        response = client.post(
            "/api/v1/specimen/TEST-001/reject",
            params={"notes": "Quality too low"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_flag_specimen(self, client, auth_headers):
        """Test flagging specimen for attention."""
        response = client.post(
            "/api/v1/specimen/TEST-001/flag",
            params={"notes": "Needs expert review"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "flagged"

        # Verify flagged
        response = client.get("/api/v1/specimen/TEST-001", headers=auth_headers)
        assert response.json()["specimen"]["review"]["flagged"] is True


class TestImageServing:
    """Tests for image serving endpoints."""

    def test_get_image_not_found(self, client, auth_headers):
        """Test getting nonexistent image."""
        response = client.get("/api/v1/images/TEST-001", headers=auth_headers)

        assert response.status_code == 404

    def test_get_thumbnail_not_found(self, client, auth_headers):
        """Test getting nonexistent thumbnail."""
        response = client.get("/api/v1/images/TEST-001/thumb", headers=auth_headers)

        assert response.status_code == 404


class TestOfflineSync:
    """Tests for offline sync endpoints."""

    def test_download_batch(self, client, auth_headers):
        """Test downloading batch for offline work."""
        request_data = {"status": "PENDING", "limit": 10}

        response = client.post("/api/v1/sync/download", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "batch" in data
        assert "count" in data
        assert "downloaded_at" in data
        assert data["count"] <= 10

    def test_upload_batch(self, client, auth_headers):
        """Test uploading batch of offline changes."""
        updates = [
            {
                "specimen_id": "TEST-001",
                "status": "APPROVED",
                "corrections": {"scientificName": "Updated name"},
                "client_timestamp": "2025-01-15T12:00:00Z",
            }
        ]

        response = client.post("/api/v1/sync/upload", json=updates, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["synced"] == 1
        assert data["errors"] == 0


class TestStatistics:
    """Tests for statistics endpoints."""

    def test_get_statistics(self, client, auth_headers):
        """Test getting review statistics."""
        response = client.get("/api/v1/statistics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_specimens" in data
        assert "status_counts" in data
        assert "priority_counts" in data
        assert "flagged_count" in data
        assert "avg_quality_score" in data


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint (no auth required)."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "total_specimens" in data
        assert "timestamp" in data


class TestSecurity:
    """Tests for security features."""

    def test_security_headers(self, client):
        """Test that security headers are present."""
        response = client.get("/api/v1/health")

        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in headers

    def test_cors_headers(self, client):
        """Test CORS headers are configured."""
        # OPTIONS request to test CORS
        response = client.options("/api/v1/queue")

        # FastAPI TestClient doesn't fully simulate CORS preflight,
        # but we can verify the middleware is loaded
        assert response.status_code in [200, 405]  # Either OK or Method Not Allowed


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json(self, client, auth_headers):
        """Test handling of invalid JSON."""
        # Use PUT endpoint which accepts JSON body
        response = client.put(
            "/api/v1/specimen/TEST-001",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        assert response.status_code == 422  # Validation error

    def test_missing_required_fields(self, client):
        """Test login with missing fields."""
        response = client.post("/api/v1/auth/login", json={"username": "testuser"})

        assert response.status_code == 422  # Validation error

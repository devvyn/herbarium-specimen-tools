# API Reference

Complete reference for the Mobile Review API endpoints.

**Base URL**: `http://localhost:8000/api/v1`

**Authentication**: Bearer token (JWT)

---

## Authentication

### POST /auth/login

Authenticate user and receive JWT token.

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "username": "string",
    "display_name": "string"
  }
}
```

**Errors**:
- `401 Unauthorized` - Invalid credentials
- `429 Too Many Requests` - Rate limit exceeded (5 attempts per 15 minutes)

**Rate Limiting**: 5 attempts per 15 minutes per IP address

---

### GET /auth/me

Get current authenticated user information.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "username": "string",
  "display_name": "string"
}
```

**Errors**:
- `401 Unauthorized` - Invalid or expired token

---

## Review Queue

### GET /queue

Get prioritized review queue with filtering and pagination.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `status` (optional): Filter by status (`PENDING`, `IN_REVIEW`, `APPROVED`, `REJECTED`)
- `priority` (optional): Filter by priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `MINIMAL`)
- `flagged_only` (boolean, optional): Show only flagged specimens
- `limit` (integer, default: 50): Number of results per page
- `offset` (integer, default: 0): Pagination offset

**Response** (200 OK):
```json
{
  "specimens": [
    {
      "id": "EXAMPLE-001",
      "thumbnail_url": "/api/v1/images/EXAMPLE-001/thumb",
      "priority": "HIGH",
      "status": "PENDING",
      "flagged": false,
      "quality_score": 85.5,
      "completeness": 92.3,
      "critical_issues": 0,
      "warnings": 2,
      "scientific_name": "Artemisia frigida Willd.",
      "catalog_number": "EXAMPLE-001"
    }
  ],
  "pagination": {
    "total": 150,
    "offset": 0,
    "limit": 50,
    "has_more": true
  }
}
```

**Errors**:
- `400 Bad Request` - Invalid filter parameters
- `401 Unauthorized` - Missing or invalid token

---

## Specimen Management

### GET /specimen/{specimen_id}

Get complete specimen details including all fields, metadata, and validation.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "specimen": {
    "id": "EXAMPLE-001",
    "image_url": "/api/v1/images/EXAMPLE-001",
    "thumbnail_url": "/api/v1/images/EXAMPLE-001/thumb",
    "fields": {
      "catalogNumber": {
        "value": "EXAMPLE-001",
        "confidence": 0.95,
        "is_suggestion": true,
        "corrected_value": null
      },
      "scientificName": {
        "value": "Artemisia frigida Willd.",
        "confidence": 0.95,
        "is_suggestion": true,
        "corrected_value": "Artemisia frigida"
      }
    },
    "metadata": {
      "extraction_timestamp": "2025-01-15T10:30:00Z",
      "model": "gpt-4o-mini",
      "provider": "openai"
    },
    "quality": {
      "completeness_score": 100.0,
      "confidence_score": 0.93,
      "quality_score": 91.2
    },
    "gbif_validation": {
      "taxonomy_verified": true,
      "taxonomy_confidence": 0.95,
      "taxonomy_issues": [],
      "locality_verified": false,
      "locality_issues": ["missing_coordinates"]
    },
    "review": {
      "status": "PENDING",
      "priority": "MEDIUM",
      "flagged": false,
      "reviewed_by": null,
      "reviewed_at": null,
      "notes": null
    },
    "issues": {
      "critical": [],
      "warnings": ["Low confidence for eventDate: 0.45"]
    }
  }
}
```

**Errors**:
- `404 Not Found` - Specimen not found
- `401 Unauthorized` - Missing or invalid token

---

### PUT /specimen/{specimen_id}

Update specimen review status, corrections, flags, or notes.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "corrections": {
    "scientificName": "Corrected value"
  },
  "status": "APPROVED",
  "priority": "HIGH",
  "flagged": true,
  "notes": "Review notes"
}
```

All fields are optional.

**Response** (200 OK):
```json
{
  "status": "updated",
  "specimen_id": "EXAMPLE-001"
}
```

**Errors**:
- `400 Bad Request` - Invalid status or priority value
- `401 Unauthorized` - Missing or invalid token

---

### POST /specimen/{specimen_id}/field/{field_name}

Update a single field with suggestion acceptance tracking.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "field": "scientificName",
  "value": "Updated value",
  "accept_suggestion": true
}
```

**Response** (200 OK):
```json
{
  "status": "updated",
  "field": "scientificName",
  "value": "Updated value",
  "accepted_suggestion": true
}
```

**Errors**:
- `404 Not Found` - Specimen not found
- `401 Unauthorized` - Missing or invalid token

---

### POST /specimen/{specimen_id}/approve

Quick approve action (mobile shortcut).

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "status": "approved",
  "specimen_id": "EXAMPLE-001"
}
```

---

### POST /specimen/{specimen_id}/reject

Quick reject action (mobile shortcut).

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `notes` (optional): Rejection reason

**Response** (200 OK):
```json
{
  "status": "rejected",
  "specimen_id": "EXAMPLE-001"
}
```

---

### POST /specimen/{specimen_id}/flag

Flag specimen for expert attention.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `notes` (optional): Flagging reason

**Response** (200 OK):
```json
{
  "status": "flagged",
  "specimen_id": "EXAMPLE-001"
}
```

---

## Image Serving

### GET /images/{specimen_id}

Serve full-resolution specimen image.

**Headers**: `Authorization: Bearer <token>`

**Response**: Image file (JPEG, PNG, or TIFF)

**Errors**:
- `404 Not Found` - Image not found
- `401 Unauthorized` - Missing or invalid token

---

### GET /images/{specimen_id}/thumb

Serve thumbnail image (currently returns full image with client-side resize).

**Headers**: `Authorization: Bearer <token>`

**Response**: Image file

---

## Offline Sync

### POST /sync/download

Download batch of specimens for offline review.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
{
  "status": "PENDING",
  "priority": "HIGH",
  "limit": 50
}
```

**Response** (200 OK):
```json
{
  "batch": [
    {
      "id": "EXAMPLE-001",
      "image_url": "/api/v1/images/EXAMPLE-001",
      "data": { /* full specimen data */ }
    }
  ],
  "count": 50,
  "downloaded_at": "2025-01-15T12:00:00Z"
}
```

---

### POST /sync/upload

Upload batch of offline changes.

**Headers**: `Authorization: Bearer <token>`

**Request Body**:
```json
[
  {
    "specimen_id": "EXAMPLE-001",
    "corrections": { "scientificName": "Updated" },
    "status": "APPROVED",
    "client_timestamp": "2025-01-15T12:30:00Z"
  }
]
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "specimen_id": "EXAMPLE-001",
      "status": "synced"
    }
  ],
  "synced": 1,
  "errors": 0
}
```

---

## Statistics

### GET /statistics

Get review statistics and progress.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "total_specimens": 150,
  "status_counts": {
    "PENDING": 100,
    "IN_REVIEW": 20,
    "APPROVED": 25,
    "REJECTED": 5
  },
  "priority_counts": {
    "CRITICAL": 10,
    "HIGH": 30,
    "MEDIUM": 80,
    "LOW": 25,
    "MINIMAL": 5
  },
  "flagged_count": 8,
  "avg_quality_score": 78.5,
  "avg_completeness": 85.2,
  "gbif_validated": 120
}
```

---

## Health Check

### GET /health

Health check endpoint (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "total_specimens": 150,
  "timestamp": "2025-01-15T12:00:00Z"
}
```

---

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400  | Bad Request | Invalid parameters, malformed JSON |
| 401  | Unauthorized | Missing/invalid token, expired token |
| 403  | Forbidden | Missing Authorization header |
| 404  | Not Found | Specimen/resource doesn't exist |
| 422  | Validation Error | Request body doesn't match schema |
| 429  | Too Many Requests | Rate limit exceeded |
| 500  | Internal Server Error | Server-side error |

---

## Rate Limiting

**Login Endpoint**: 5 attempts per 15 minutes per IP address

After exceeding the rate limit, clients must wait 15 minutes before attempting again.

---

## Security

All endpoints (except `/health`) require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

Tokens expire after 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable).

---

## Interactive Documentation

When running in development mode, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These are disabled in production for security.

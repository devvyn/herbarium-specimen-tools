# API Endpoints

REST API structure for the Herbarium Mobile Review system, including authentication flow and HTMX partials.

## API Structure

```mermaid
graph TD
    subgraph "Public Endpoints"
        HEALTH["/api/v1/health<br/>Health Check"]
        ROOT["/<br/>Redirect to UI"]
    end

    subgraph "Authentication"
        LOGIN["/api/v1/auth/login<br/>POST: Issue JWT"]
        ME["/api/v1/auth/me<br/>GET: Current User"]
    end

    subgraph "Review Queue"
        QUEUE["/api/v1/queue<br/>GET: Paginated Queue"]
        STATS["/api/v1/statistics<br/>GET: Queue Stats"]
    end

    subgraph "Specimen Operations"
        GET_SPEC["/api/v1/specimen/{id}<br/>GET: Full Details"]
        PUT_SPEC["/api/v1/specimen/{id}<br/>PUT: Update Review"]
        FIELD["/api/v1/specimen/{id}/field/{name}<br/>POST: Update Field"]
    end

    subgraph "Quick Actions"
        APPROVE["/api/v1/specimen/{id}/approve<br/>POST: Quick Approve"]
        REJECT["/api/v1/specimen/{id}/reject<br/>POST: Quick Reject"]
        FLAG["/api/v1/specimen/{id}/flag<br/>POST: Flag for Expert"]
        REEXTRACT["/api/v1/specimen/{id}/request-reextraction<br/>POST: Request Re-extraction"]
    end

    subgraph "Images"
        IMAGE["/api/v1/images/{id}<br/>GET: Full Image"]
        THUMB["/api/v1/images/{id}/thumb<br/>GET: Thumbnail"]
    end

    subgraph "Offline Sync"
        DOWNLOAD["/api/v1/sync/download<br/>POST: Batch Download"]
        UPLOAD["/api/v1/sync/upload<br/>POST: Batch Upload"]
    end

    subgraph "HTMX Partials"
        P_STATS["/partials/stats<br/>GET: Stats HTML"]
        P_QUEUE["/partials/queue<br/>GET: Queue HTML"]
        P_SPEC["/partials/specimen/{id}<br/>GET: Detail HTML"]
    end

    subgraph "Page Routes"
        LOGIN_PAGE["/<br/>Login Page"]
        QUEUE_PAGE["/queue<br/>Queue Page"]
        SPEC_PAGE["/specimen/{id}<br/>Specimen Page"]
    end
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant PWA as Mobile PWA
    participant API as FastAPI
    participant JWT as JWT Service

    U->>PWA: Enter username
    PWA->>API: POST /api/v1/auth/login
    Note over API: Username-only auth<br/>(network trust model)
    API->>JWT: Create token (24h expiry)
    JWT-->>API: JWT token
    API-->>PWA: {access_token, user}
    PWA->>PWA: Store token in localStorage

    Note over PWA: Subsequent requests
    PWA->>API: GET /api/v1/queue<br/>Authorization: Bearer {token}
    API->>JWT: Verify token
    JWT-->>API: Valid + username
    API-->>PWA: Queue data
```

## Request/Response Flow

```mermaid
sequenceDiagram
    participant PWA as Mobile PWA
    participant MW as Middleware
    participant API as FastAPI
    participant ENGINE as Review Engine
    participant DATA as Data Layer

    PWA->>MW: HTTP Request
    MW->>MW: Add Security Headers
    MW->>MW: CORS Validation
    MW->>API: Forward Request

    alt Authenticated Endpoint
        API->>API: Verify JWT
        API->>ENGINE: Process Request
        ENGINE->>DATA: Read/Write Data
        DATA-->>ENGINE: Result
        ENGINE-->>API: Processed Data
    else Public Endpoint
        API->>ENGINE: Process Request
        ENGINE-->>API: Data
    end

    API-->>MW: Response
    MW-->>PWA: HTTP Response
```

## Endpoints Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login` | No | Issue JWT token for username |
| GET | `/api/v1/auth/me` | Yes | Get current user info |

### Queue Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/queue` | Yes | Get paginated review queue |
| GET | `/api/v1/statistics` | Yes | Get queue statistics |

### Specimen Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/specimen/{id}` | Yes | Get full specimen details |
| PUT | `/api/v1/specimen/{id}` | Yes | Update specimen review data |
| POST | `/api/v1/specimen/{id}/field/{name}` | Yes | Update single DwC field |
| POST | `/api/v1/specimen/{id}/approve` | Yes | Quick approve |
| POST | `/api/v1/specimen/{id}/reject` | Yes | Quick reject |
| POST | `/api/v1/specimen/{id}/flag` | Yes | Flag for expert review |
| POST | `/api/v1/specimen/{id}/request-reextraction` | Yes | Request re-extraction |
| POST | `/api/v1/specimen/{id}/request-region-reextraction` | Yes | Request region re-extraction |
| DELETE | `/api/v1/specimen/{id}/reextraction-regions` | Yes | Clear pending re-extractions |
| GET | `/api/v1/specimen/{id}/corrections` | Yes | Get correction history |
| POST | `/api/v1/specimen/{id}/annotation` | Yes | Save manual annotation |

### Images

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/images/{id}` | No | Serve specimen image |
| GET | `/api/v1/images/{id}/thumb` | No | Serve thumbnail |

### Offline Sync

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/sync/download` | Yes | Download batch for offline |
| POST | `/api/v1/sync/upload` | Yes | Upload offline changes |

### Feedback Export

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/feedback/export` | Yes | Export corrections for ML training |

### HTMX Partials

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/partials/stats` | Yes | Statistics HTML partial |
| GET | `/partials/queue` | Yes | Queue list HTML partial |
| GET | `/partials/specimen/{id}` | Yes | Specimen detail HTML partial |

## Components Table

| Component | Location | Description |
|-----------|----------|-------------|
| Mobile API | `/src/review/mobile_api.py` | FastAPI application factory and endpoints |
| Run Server | `/mobile/run_server.py` | Alternative server with simpler setup |
| Auth Utils | `/src/review/mobile_api.py` | JWT creation and verification functions |
| Pydantic Models | `/src/review/mobile_api.py` | Request/response validation models |
| Templates | `/templates/` | Jinja2 HTMX partials |

## See Also

- [System Overview](system-overview.md) - High-level architecture
- [Review Workflow](../modules/review-workflow.md) - Status transitions
- [Mobile PWA](../modules/mobile-pwa.md) - Client-side architecture

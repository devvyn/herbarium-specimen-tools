# Mobile PWA Architecture

Progressive Web App architecture for the Herbarium Review mobile interface, including Vue.js components, Service Worker caching, and offline sync.

## PWA Architecture

```mermaid
graph TD
    subgraph "Browser"
        APP[Vue.js 3 App<br/>index.html]
        STORE[localStorage<br/>JWT Token + State]
        SW[Service Worker<br/>sw.js]
        CACHE[(Browser Cache<br/>Static Assets)]
        RUNTIME[(Runtime Cache<br/>API Responses)]
    end

    subgraph "Network"
        API[FastAPI Backend<br/>REST API]
        S3[S3/iCloud<br/>Images]
    end

    APP --> STORE
    APP --> SW
    SW --> CACHE
    SW --> RUNTIME
    SW <-->|Network First| API
    SW <-->|Cache First| S3
```

## Vue.js Application Structure

```mermaid
graph TD
    subgraph "App Component"
        ROOT[Root App<br/>v-if routing]
    end

    subgraph "Views"
        LOGIN[Login Screen<br/>Username input]
        QUEUE[Queue View<br/>Specimen list]
        DETAIL[Detail View<br/>Field editing]
        STATS[Stats Banner<br/>Progress metrics]
    end

    subgraph "Components"
        HEADER[Header<br/>Navigation]
        FILTERS[Queue Filters<br/>Status/Priority]
        CARD[Specimen Card<br/>List item]
        IMAGE[Image Viewer<br/>Fit/1:1/Fullscreen]
        FIELD[Field Editor<br/>Accept/Edit/Clear]
        ACTIONS[Quick Actions<br/>Approve/Reject/Flag]
    end

    ROOT --> LOGIN
    ROOT --> QUEUE
    ROOT --> DETAIL
    QUEUE --> HEADER
    QUEUE --> FILTERS
    QUEUE --> CARD
    QUEUE --> STATS
    DETAIL --> IMAGE
    DETAIL --> FIELD
    DETAIL --> ACTIONS
```

## Service Worker Caching Strategy

```mermaid
graph TD
    subgraph "Cache Strategy Selection"
        REQ[Incoming Request]
        CHECK{URL Pattern}
    end

    subgraph "Network First"
        NF_NET[Try Network]
        NF_CACHE[Fallback to Cache]
        NF_STORE[Update Cache]
    end

    subgraph "Cache First"
        CF_CACHE[Try Cache]
        CF_NET[Fallback to Network]
        CF_STORE[Update Cache]
    end

    subgraph "Cache Types"
        STATIC[herbarium-v1<br/>Static Assets]
        RUNTIME[herbarium-runtime<br/>API + Images]
    end

    REQ --> CHECK
    CHECK -->|/api/*| NF_NET
    NF_NET -->|Success| NF_STORE
    NF_NET -->|Fail| NF_CACHE

    CHECK -->|/api/v1/images/*| CF_CACHE
    CHECK -->|Static Assets| CF_CACHE
    CF_CACHE -->|Miss| CF_NET
    CF_NET --> CF_STORE

    NF_STORE --> RUNTIME
    CF_STORE --> RUNTIME
    CF_STORE --> STATIC
```

## Offline Sync Flow

```mermaid
sequenceDiagram
    participant USER as User
    participant APP as Vue App
    participant SW as Service Worker
    participant STORE as localStorage
    participant API as Backend API

    Note over USER,API: Online Mode
    USER->>APP: Review Specimen
    APP->>API: PUT /api/v1/specimen/{id}
    API-->>APP: Success
    APP->>STORE: Update local state

    Note over USER,API: Going Offline
    APP->>SW: Detect offline
    SW->>STORE: Queue pending changes
    USER->>APP: Continue reviewing
    APP->>STORE: Store changes locally

    Note over USER,API: Coming Online
    SW->>SW: Detect online
    SW->>STORE: Get pending changes
    SW->>API: POST /api/v1/sync/upload
    API-->>SW: Sync results
    SW->>STORE: Clear synced items
    SW->>APP: Notify user
```

## Image Viewer States

```mermaid
stateDiagram-v2
    [*] --> FIT: Image Loaded

    FIT --> ACTUAL: Tap "1:1"
    ACTUAL --> FIT: Tap "Fit"

    FIT --> FULLSCREEN: Tap Fullscreen
    ACTUAL --> FULLSCREEN: Tap Fullscreen
    FULLSCREEN --> FIT: Exit Fullscreen

    state FIT {
        [*] --> contain
        note right of contain: Image fits container
    }

    state ACTUAL {
        [*] --> scroll
        note right of scroll: Native scroll for 1:1 view
    }

    state FULLSCREEN {
        [*] --> native_zoom
        note right of native_zoom: iOS pinch-zoom fallback
    }
```

## Authentication State

```mermaid
stateDiagram-v2
    [*] --> CheckToken: App Load

    CheckToken --> Authenticated: Valid Token
    CheckToken --> LoginScreen: No Token/Expired

    LoginScreen --> Authenticated: Login Success

    Authenticated --> Queue: Show Queue
    Queue --> Detail: Select Specimen
    Detail --> Queue: Back

    Authenticated --> LoginScreen: Token Expired
    Authenticated --> LoginScreen: Logout
```

## Components Table

| Component | Location | Description |
|-----------|----------|-------------|
| index.html | `/mobile/index.html` | Main HTML with Vue app template |
| app.js | `/mobile/js/app.js` | Vue.js application logic |
| api.js | `/mobile/js/api.js` | API client with auth handling |
| error-tracker.js | `/mobile/js/error-tracker.js` | Client-side error tracking |
| app.css | `/mobile/css/app.css` | Mobile-optimized styles |
| sw.js | `/mobile/sw.js` | Service Worker for offline support |
| manifest.json | `/mobile/manifest.json` | PWA manifest for installability |
| icons/ | `/mobile/icons/` | App icons (192x192, 512x512) |

## Static Assets (Cached on Install)

| Asset | Purpose |
|-------|---------|
| `/` | Root redirect |
| `/index.html` | Main application |
| `/css/app.css` | Application styles |
| `/js/api.js` | API client |
| `/js/app.js` | Vue application |
| `/manifest.json` | PWA configuration |
| Vue.js 3 CDN | Framework |

## PWA Features

| Feature | Implementation |
|---------|----------------|
| Installable | manifest.json with icons |
| Offline Support | Service Worker caching |
| iOS Optimized | apple-mobile-web-app-capable |
| Touch Optimized | Touch-friendly UI components |
| Responsive | Mobile-first CSS |
| Sync | Batch download/upload endpoints |

## Browser Compatibility

| Feature | Chrome | Safari iOS | Firefox |
|---------|--------|------------|---------|
| Service Worker | Full | Full | Full |
| Cache API | Full | Full | Full |
| PWA Install | Full | Add to Home | Limited |
| Fullscreen API | Full | Limited* | Full |

*iOS Safari uses pinch-zoom fallback for fullscreen image viewing.

## See Also

- [System Overview](../architecture/system-overview.md) - High-level architecture
- [API Endpoints](../architecture/api-endpoints.md) - Backend API structure
- [Review Workflow](review-workflow.md) - Status state machine
- [Mobile README](/mobile/README.md) - Setup and usage guide

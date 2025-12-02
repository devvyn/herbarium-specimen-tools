# Mobile Review Interface

Progressive Web App (PWA) for mobile-based specimen curation and data refining.

## Overview

This mobile interface reduces friction in herbarium data extraction workflows by providing:

- **Mobile-First Design**: Optimized for mobile Safari and Chrome with touch gestures
- **Offline Support**: Service worker caching for working without constant internet
- **Staged Workflow**: Progressive review from initial assessment to approval
- **Field-Level Editing**: Accept/reject AI suggestions with easy corrections
- **Priority Management**: Upgrade/downgrade specimen priorities
- **Image Viewer**: Full-screen pinch-zoom for detailed inspection

## Architecture

```
┌─────────────────────────────────────┐
│     Mobile Browser                  │
│  Progressive Web App (PWA)          │
│  - Vue.js 3                         │
│  - Service Worker                   │
│  - Add to Home Screen               │
└──────────────┬──────────────────────┘
               │ HTTPS/REST API
┌──────────────▼──────────────────────┐
│  FastAPI Backend                    │
│  - JWT Authentication               │
│  - Review Engine Integration        │
│  - GBIF Validation                  │
│  - Image Serving                    │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn python-jose[cryptography] python-multipart
```

### 2. Prepare Data

Ensure you have extraction results and images:

```bash
# Extraction results (JSONL format)
ls data/extractions/raw.jsonl

# Specimen images
ls data/images/
```

### 3. Start Server

```bash
python mobile/run_mobile_server.py \
  --extraction-dir data/extractions \
  --image-dir data/images \
  --host 0.0.0.0 \
  --port 8000
```

### 4. Access on Mobile Device

**Option A: Development (Same WiFi)**
1. Find your computer's IP address: `ifconfig` or `ipconfig`
2. On mobile browser, navigate to: `http://YOUR_IP:8000`

**Option B: Production (Internet Access)**
1. Deploy to internet-accessible server (see Deployment section)
2. Access via domain: `https://your-domain.com`

### 5. Add to Home Screen (iOS/Android)

**iOS (Safari)**:
1. Open in Safari
2. Tap Share button
3. Tap "Add to Home Screen"
4. App now appears on home screen like native app

**Android (Chrome)**:
1. Open in Chrome
2. Tap menu (⋮)
3. Tap "Add to Home Screen"

## Features

### Review Queue

- **Filtering**: By status (PENDING/IN_REVIEW/APPROVED/REJECTED) and priority
- **Sorting**: Automatic priority-first ordering (CRITICAL → MINIMAL)
- **Quick Info**: Catalog number, scientific name, quality scores at a glance
- **Visual Indicators**: Color-coded priority badges, issue counts, flags

### Specimen Detail View

**Image Viewer:**
- Full-screen display
- Tap to zoom (pinch-zoom supported)
- Swipe navigation

**Quick Actions:**
- ✓ Approve - Mark specimen as approved
- ✗ Reject - Mark for rejection with optional notes
- 🚩 Flag - Flag for expert attention

**Field Editor:**
- View all Darwin Core fields
- Confidence scores shown for each field
- Accept AI suggestions with one tap
- Edit values directly with mobile keyboard
- Auto-save on blur

**Priority Control:**
- Upgrade/downgrade priority level
- CRITICAL → HIGH → MEDIUM → LOW → MINIMAL

**GBIF Validation:**
- Taxonomy verification status
- Locality verification status
- Issues and warnings displayed

**Notes:**
- Add review notes
- Track correction rationale

### Workflow Stages

**Suggested workflow:**

1. **Initial Review** (status: PENDING → IN_REVIEW)
   - Open specimen from queue
   - View image and extracted fields
   - Identify issues

2. **Correction** (status: IN_REVIEW)
   - Accept correct AI suggestions (tap ✓)
   - Edit incorrect fields
   - Add notes for problematic specimens
   - Flag for expert if uncertain

3. **Priority Adjustment**
   - Upgrade critical issues
   - Downgrade high-quality specimens

4. **Final Decision** (status: APPROVED or REJECTED)
   - Approve if all fields correct
   - Reject if specimen unusable
   - Flag if needs expert consultation

## API Endpoints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

### Authentication

**POST** `/api/v1/auth/login`
```json
{
  "username": "curator",
  "password": "your-password"
}
```

Returns:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {"username": "curator"}
}
```

### Review Queue

**GET** `/api/v1/queue?status=PENDING&priority=CRITICAL&limit=50`

Returns paginated specimen list with filters.

### Specimen Details

**GET** `/api/v1/specimen/{specimen_id}`

Returns full specimen data including fields, validation, issues.

### Update Specimen

**PUT** `/api/v1/specimen/{specimen_id}`
```json
{
  "corrections": {"scientificName": "Corrected Name"},
  "status": "APPROVED",
  "priority": "HIGH",
  "flagged": false,
  "notes": "Review notes"
}
```

### Field Update

**POST** `/api/v1/specimen/{specimen_id}/field/{field_name}`
```json
{
  "field": "scientificName",
  "value": "Artemisia frigida Willd.",
  "accept_suggestion": true
}
```

### Quick Actions

- **POST** `/api/v1/specimen/{specimen_id}/approve`
- **POST** `/api/v1/specimen/{specimen_id}/reject?notes=...`
- **POST** `/api/v1/specimen/{specimen_id}/flag?notes=...`

### Statistics

**GET** `/api/v1/statistics`

Returns review progress statistics.

## Deployment

### Development (Local Network)

```bash
# Start server accessible on local network
python mobile/run_mobile_server.py --host 0.0.0.0 --port 8000

# Find your IP
ifconfig | grep "inet "

# Access from mobile device
# http://YOUR_IP:8000
```

### Production (Traditional Server)

**Requirements:**
- Internet-accessible server (VPS, cloud instance, etc.)
- Domain name (optional but recommended)
- HTTPS certificate (required for PWA features)

**Option 1: Nginx + Uvicorn**

1. Install Nginx:
```bash
sudo apt install nginx certbot python3-certbot-nginx
```

2. Create systemd service (`/etc/systemd/system/herbarium-mobile.service`):
```ini
[Unit]
Description=Herbarium Mobile Review API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/herbarium-specimen-tools
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python mobile/run_mobile_server.py \
  --host 127.0.0.1 \
  --port 8000 \
  --extraction-dir /path/to/data/extractions \
  --image-dir /path/to/images
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Configure Nginx (`/etc/nginx/sites-available/herbarium-mobile`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. Enable HTTPS:
```bash
sudo certbot --nginx -d your-domain.com
```

5. Start service:
```bash
sudo systemctl enable herbarium-mobile
sudo systemctl start herbarium-mobile
```

**Option 2: Docker**

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "mobile/run_mobile_server.py", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t herbarium-mobile .
docker run -p 8000:8000 \
  -v /path/to/data:/app/data \
  -v /path/to/images:/app/images \
  herbarium-mobile
```

## Security

**Production Checklist:**

- [ ] Change JWT secret key (set environment variable `JWT_SECRET_KEY`)
- [ ] Use strong passwords for user accounts
- [ ] Enable HTTPS (required for PWA)
- [ ] Configure CORS to restrict origins
- [ ] Set up proper user authentication (database, OAuth, etc.)
- [ ] Enable rate limiting
- [ ] Set up logging and monitoring
- [ ] Regular security updates

**Update authentication in production:**

Edit the server configuration to use proper user management instead of hardcoded credentials.

## Troubleshooting

**Issue: Cannot access from mobile device**
- Ensure server is bound to `0.0.0.0` not `127.0.0.1`
- Check firewall allows port 8000
- Ensure device and server on same WiFi (for local development)

**Issue: Images not loading**
- Verify image directory path is correct
- Check image files exist with correct extensions (.jpg, .png, etc.)
- Check file permissions

**Issue: PWA not installing**
- PWA requires HTTPS (except localhost)
- Check manifest.json is accessible
- Check service worker is registered
- Try clearing browser cache

**Issue: Authentication failing**
- Check JWT token in localStorage
- Token expires after 30 days (configurable)
- Check server logs for auth errors

**Issue: Offline mode not working**
- Service worker only works over HTTPS
- Check browser console for SW errors
- Try unregistering and re-registering SW

## Development

**File Structure:**
```
mobile/
├── index.html          # Main PWA entry point
├── manifest.json       # PWA manifest
├── sw.js              # Service worker
├── css/
│   └── app.css        # Mobile-first styles
├── js/
│   ├── api.js         # API client
│   └── app.js         # Vue.js app
└── run_mobile_server.py  # Server launcher
```

**Enable dev mode:**
```bash
python mobile/run_mobile_server.py --reload
```

**Test API:**
```bash
# Get health check
curl http://localhost:8000/api/v1/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "curator", "password": "changeme123"}'

# Get queue (with token)
curl http://localhost:8000/api/v1/queue \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Future Enhancements

- [ ] Thumbnail generation for faster loading
- [ ] Batch operations (approve multiple)
- [ ] Voice input for notes
- [ ] Bluetooth barcode scanner integration
- [ ] True offline sync (IndexedDB storage)
- [ ] Dark mode
- [ ] Multi-user collaboration
- [ ] Real-time updates (WebSocket)
- [ ] Advanced search/filtering
- [ ] Export reviewed specimens

## Contributing

Contributions welcome! See [../CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [../LICENSE](../LICENSE) for details.

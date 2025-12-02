# Deployment Guide

Production deployment guide for the Herbarium Mobile Review API.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Deployment Options](#deployment-options)
  - [Traditional Server](#traditional-server)
  - [Docker](#docker)
  - [AWS Lambda (Serverless)](#aws-lambda-serverless)
- [Security Checklist](#security-checklist)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11 or higher
- Specimen extraction data (raw.jsonl format)
- Specimen images directory
- SSL/TLS certificate for HTTPS (required for PWA features)

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file (never commit this to git):

```bash
# Environment
ENVIRONMENT=production

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here  # Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# User Authentication
# Format: username:hashed_password,username2:hashed_password2
AUTH_USERS=curator:$2b$12$abc...,reviewer:$2b$12$xyz...

# CORS (comma-separated origins)
ALLOWED_ORIGINS=https://yourdomain.com,https://mobile.yourdomain.com

# Trusted Hosts (production only, comma-separated)
ALLOWED_HOSTS=yourdomain.com,mobile.yourdomain.com

# GBIF Configuration
GBIF_MIN_CONFIDENCE=0.80
GBIF_FUZZY_MATCHING=true
GBIF_OCCURRENCE_VALIDATION=false

# Data Directories
EXTRACTION_DIR=/path/to/extractions
IMAGE_DIR=/path/to/images

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

### Generating User Passwords

```bash
# Generate hashed password
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('your-password-here'))"
```

Add the resulting hash to `AUTH_USERS` environment variable.

---

## Deployment Options

### Traditional Server

Best for: Small to medium deployments, full control, simple setup

#### 1. Install Dependencies

```bash
# Clone repository
git clone https://github.com/devvyn/herbarium-specimen-tools.git
cd herbarium-specimen-tools

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit with your configuration
nano .env
```

#### 3. Set Up Systemd Service

Create `/etc/systemd/system/herbarium-api.service`:

```ini
[Unit]
Description=Herbarium Mobile Review API
After=network.target

[Service]
Type=simple
User=herbarium
WorkingDirectory=/opt/herbarium-specimen-tools
Environment="PATH=/opt/herbarium-specimen-tools/venv/bin"
EnvironmentFile=/opt/herbarium-specimen-tools/.env
ExecStart=/opt/herbarium-specimen-tools/venv/bin/python mobile/run_mobile_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable herbarium-api
sudo systemctl start herbarium-api
sudo systemctl status herbarium-api
```

#### 4. Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/herbarium-api`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/herbarium-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Docker

Best for: Containerized deployments, consistent environments

#### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 herbarium && \
    chown -R herbarium:herbarium /app
USER herbarium

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "mobile/run_mobile_server.py"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - AUTH_USERS=${AUTH_USERS}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - EXTRACTION_DIR=/data/extractions
      - IMAGE_DIR=/data/images
    volumes:
      - ./data:/data:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 3. Deploy

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

### AWS Lambda (Serverless)

Best for: Scalable deployments, pay-per-use, minimal infrastructure

#### 1. Install Mangum (ASGI adapter)

```bash
pip install mangum
```

#### 2. Create Lambda Handler

Create `lambda_handler.py`:

```python
from mangum import Mangum
from mobile.run_mobile_server import create_app

app = create_app()
handler = Mangum(app)
```

#### 3. Package for Lambda

```bash
# Create deployment package
pip install -r requirements.txt -t package/
cp -r src mobile lambda_handler.py package/
cd package && zip -r ../lambda.zip . && cd ..
```

#### 4. Deploy with AWS CLI

```bash
# Create Lambda function
aws lambda create-function \
  --function-name herbarium-api \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler lambda_handler.handler \
  --zip-file fileb://lambda.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{ENVIRONMENT=production,JWT_SECRET_KEY=your-key,...}"

# Configure API Gateway (or use AWS Console)
```

---

## Security Checklist

Before deploying to production:

- [ ] **HTTPS Only**: SSL/TLS certificate configured
- [ ] **JWT Secret**: Strong secret key (32+ characters, randomly generated)
- [ ] **User Passwords**: Bcrypt hashed, stored securely
- [ ] **Environment Variables**: All secrets in environment (not code)
- [ ] **CORS**: Restricted to specific origins
- [ ] **Trusted Hosts**: Limited to your domains
- [ ] **API Docs**: Disabled in production (check ENVIRONMENT=production)
- [ ] **Rate Limiting**: Login endpoint protected
- [ ] **Firewall**: Only necessary ports open
- [ ] **Updates**: All dependencies up to date
- [ ] **Backups**: Data backup strategy in place
- [ ] **Monitoring**: Error tracking and logging configured

---

## Monitoring

### Health Check

```bash
curl https://yourdomain.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "total_specimens": 150,
  "timestamp": "2025-01-15T12:00:00Z"
}
```

### Logging

View application logs:

```bash
# Systemd
sudo journalctl -u herbarium-api -f

# Docker
docker-compose logs -f api

# Lambda
aws logs tail /aws/lambda/herbarium-api --follow
```

### Monitoring Tools

Recommended:
- **Sentry**: Error tracking
- **Prometheus + Grafana**: Metrics and dashboards
- **CloudWatch**: AWS-specific monitoring
- **UptimeRobot**: Uptime monitoring

---

## Troubleshooting

### Server Won't Start

**Check logs**:
```bash
sudo journalctl -u herbarium-api -n 50
```

**Common issues**:
- Missing `JWT_SECRET_KEY` environment variable
- Missing `AUTH_USERS` environment variable
- Invalid paths in `EXTRACTION_DIR` or `IMAGE_DIR`
- Port 8000 already in use

### Authentication Fails

**Verify user hash**:
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd_context.verify("your-password", "stored-hash")  # Should return True
```

**Check environment**:
```bash
echo $AUTH_USERS
```

### CORS Errors

**Update CORS origins**:
```bash
export ALLOWED_ORIGINS=https://yourdomain.com,https://mobile.yourdomain.com
```

**Verify in browser console**: Check for CORS-related error messages

### Performance Issues

**Increase workers** (for production servers):
```bash
uvicorn mobile.run_mobile_server:app --workers 4 --host 0.0.0.0 --port 8000
```

**Enable caching**: Consider Redis for rate limiting and session storage

### Image Serving Slow

**Options**:
1. Generate thumbnails (modify `/images/{id}/thumb` endpoint)
2. Use CDN for image delivery
3. Optimize images before deployment
4. Enable Nginx caching

---

## Backup Strategy

### Data to Back Up

1. **Extraction Data**: `EXTRACTION_DIR/raw.jsonl`
2. **Images**: `IMAGE_DIR/` (if not backed up elsewhere)
3. **Review Data**: Export regularly via API
4. **Configuration**: `.env` file (encrypted)

### Backup Script Example

```bash
#!/bin/bash
BACKUP_DIR=/backups/herbarium/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup extraction data
cp $EXTRACTION_DIR/raw.jsonl $BACKUP_DIR/

# Export review data
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://yourdomain.com/api/v1/export > $BACKUP_DIR/reviews.json

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR/
rm -rf $BACKUP_DIR
```

---

## Scaling Considerations

### Horizontal Scaling

- **Load Balancer**: Nginx or AWS ALB
- **Multiple Instances**: Run multiple API instances
- **Shared State**: Use Redis for rate limiting across instances
- **Database**: Consider PostgreSQL for review data persistence

### Vertical Scaling

- Increase memory/CPU for Lambda functions
- Increase worker processes for traditional servers
- Optimize image serving (thumbnails, CDN)

---

## Support

For deployment issues:
- Check [Troubleshooting](#troubleshooting) section
- Review logs for error messages
- Open an issue: https://github.com/devvyn/herbarium-specimen-tools/issues

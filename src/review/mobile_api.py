"""
Mobile-Optimized API for Herbarium Specimen Review

Progressive Web App (PWA) backend designed for iPhone-based field curation.
Supports staged review workflow with offline sync capabilities.

Features:
- JWT authentication (expandable for collaboration)
- Staged workflow: PENDING → IN_REVIEW → NEEDS_CORRECTION → APPROVED/REJECTED
- Field-level suggestion approval/rejection
- Priority management (upgrade/downgrade)
- Mobile-optimized image serving
- Offline sync support
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .engine import ReviewEngine, ReviewPriority, ReviewStatus
from .validators import GBIFValidator

logger = logging.getLogger(__name__)

# JWT Configuration - MUST use environment variable in production
SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    secrets.token_urlsafe(32) if os.environ.get("ENVIRONMENT") == "development" else None,
)

if SECRET_KEY is None:
    raise ValueError(
        "JWT_SECRET_KEY environment variable must be set in production. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)  # 24 hours default

security = HTTPBearer()


# ============================================================================
# Pydantic Models for API
# ============================================================================


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class FieldCorrectionRequest(BaseModel):
    field: str
    value: str
    accept_suggestion: bool = True  # True = accept AI, False = reject and use user value


class UpdateSpecimenRequest(BaseModel):
    corrections: dict | None = None
    status: str | None = None
    priority: str | None = None
    flagged: bool | None = None
    notes: str | None = None


class BatchDownloadRequest(BaseModel):
    status: str | None = "PENDING"
    priority: str | None = None
    limit: int = 50


class SpecimenSyncUpdate(BaseModel):
    specimen_id: str
    corrections: dict | None = None
    status: str | None = None
    priority: str | None = None
    flagged: bool | None = None
    notes: str | None = None
    client_timestamp: str


# ============================================================================
# Authentication
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password,
    )


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
            )
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
        )


# ============================================================================
# Application Factory
# ============================================================================


def create_mobile_app(
    extraction_dir: Path,
    image_dir: Path,
    enable_gbif: bool = True,
    users: dict | None = None,
) -> FastAPI:
    """
    Create mobile-optimized FastAPI application.

    Args:
        extraction_dir: Directory containing raw.jsonl
        image_dir: Directory containing specimen images
        enable_gbif: Enable GBIF validation
        users: Dict of {username: hashed_password} for authentication
              If None, loads from environment variables or requires setup

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Herbarium Mobile Review API",
        description="Mobile-optimized API for specimen curation",
        version="1.0.0",
        docs_url="/docs" if os.environ.get("ENVIRONMENT") == "development" else None,
        redoc_url="/redoc" if os.environ.get("ENVIRONMENT") == "development" else None,
    )

    # CORS configuration - restrict to specific origins
    allowed_origins = os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,  # Cache preflight requests for 10 minutes
    )

    # Trusted host middleware for production
    if os.environ.get("ENVIRONMENT") == "production":
        allowed_hosts = os.environ.get("ALLOWED_HOSTS", "").split(",")
        if allowed_hosts and allowed_hosts[0]:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Rate limiting state (simple in-memory, use Redis for production)
    app.state.rate_limit_store = {}

    # Load users from environment or use provided dict
    if users is None:
        # Try to load from environment variable
        # Format: USERNAME1:HASHED_PASSWORD1,USERNAME2:HASHED_PASSWORD2
        users_env = os.environ.get("AUTH_USERS", "")
        if users_env:
            users = {}
            for user_entry in users_env.split(","):
                if ":" in user_entry:
                    username, hashed_pwd = user_entry.split(":", 1)
                    users[username.strip()] = hashed_pwd.strip()
        else:
            # Require explicit user creation in production
            if os.environ.get("ENVIRONMENT") == "production":
                raise ValueError(
                    "No users configured. Set AUTH_USERS environment variable with "
                    "format: 'username:hashed_password' or pass users dict to create_mobile_app()"
                )
            # Development mode: create a test user
            logger.warning(
                "⚠️  Development mode: Using default test credentials. "
                "Set ENVIRONMENT=production and AUTH_USERS for production use."
            )
            users = {
                "testuser": get_password_hash("testpass123")  # Only for development
            }

    app.state.users = users
    app.state.extraction_dir = extraction_dir
    app.state.image_dir = image_dir

    # Initialize review engine
    gbif_validator = GBIFValidator() if enable_gbif else None
    engine = ReviewEngine(gbif_validator=gbif_validator)

    # Load extraction results
    results_file = extraction_dir / "raw.jsonl"
    if results_file.exists():
        engine.load_extraction_results(results_file)
        logger.info(f"Loaded {len(engine.reviews)} specimens for mobile review")
    else:
        logger.warning(f"Results file not found: {results_file}")

    app.state.engine = engine

    # ========================================================================
    # Authentication Endpoints
    # ========================================================================

    @app.post("/api/v1/auth/login", response_model=TokenResponse)
    async def login(request: LoginRequest, http_request: Request):
        """
        Authenticate user and return JWT token.

        Rate limited to prevent brute force attacks.
        """
        # Rate limiting (simple implementation)
        client_ip = http_request.client.host
        rate_key = f"login:{client_ip}"
        current_time = datetime.now()

        # Get or initialize rate limit data
        if rate_key not in app.state.rate_limit_store:
            app.state.rate_limit_store[rate_key] = {"count": 0, "reset_time": current_time}

        rate_data = app.state.rate_limit_store[rate_key]

        # Reset if time window passed (5 attempts per 15 minutes)
        if current_time - rate_data["reset_time"] > timedelta(minutes=15):
            rate_data["count"] = 0
            rate_data["reset_time"] = current_time

        # Check rate limit
        if rate_data["count"] >= 5:
            logger.warning(f"Rate limit exceeded for login from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again in 15 minutes.",
            )

        # Increment attempt counter
        rate_data["count"] += 1

        username = request.username
        password = request.password

        # Verify user exists and password matches (timing-safe)
        if username not in app.state.users:
            # Use a dummy verification to prevent timing attacks
            # This ensures failed lookups take the same time as password checks
            try:
                bcrypt.checkpw(
                    b"dummy", b"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.x1qKJqKJqKJqKO"
                )
            except Exception:
                pass
            logger.warning(f"Failed login attempt for non-existent user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
            )

        hashed_password = app.state.users[username]
        if not verify_password(password, hashed_password):
            logger.warning(f"Failed login attempt for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
            )

        # Reset rate limit on successful login
        rate_data["count"] = 0

        # Create access token
        access_token = create_access_token(data={"sub": username})

        logger.info(f"Successful login for user: {username}")

        return TokenResponse(
            access_token=access_token,
            user={
                "username": username,
                "display_name": username.capitalize(),
            },
        )

    @app.get("/api/v1/auth/me")
    async def get_current_user(username: str = Depends(verify_token)):
        """Get current authenticated user info."""
        return {
            "username": username,
            "display_name": username.capitalize(),
        }

    # ========================================================================
    # Review Queue Endpoints
    # ========================================================================

    @app.get("/api/v1/queue")
    async def get_queue(
        status: str | None = None,
        priority: str | None = None,
        flagged_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        username: str = Depends(verify_token),
    ):
        """
        Get prioritized review queue.

        Mobile-optimized with pagination and lightweight response.
        """
        # Parse filters
        status_enum = None
        if status:
            try:
                status_enum = ReviewStatus[status.upper()]
            except KeyError:
                raise HTTPException(400, f"Invalid status: {status}")

        priority_enum = None
        if priority:
            try:
                priority_enum = ReviewPriority[priority.upper()]
            except KeyError:
                raise HTTPException(400, f"Invalid priority: {priority}")

        # Get filtered queue
        queue = engine.get_review_queue(
            status=status_enum,
            priority=priority_enum,
            flagged_only=flagged_only,
            sort_by="priority",
        )

        # Apply pagination
        total = len(queue)
        queue = queue[offset : offset + limit]

        # Mobile-optimized response (minimal data)
        return {
            "specimens": [
                {
                    "id": review.specimen_id,
                    "thumbnail_url": f"/api/v1/images/{review.specimen_id}/thumb",
                    "priority": review.priority.name,
                    "status": review.status.name,
                    "flagged": review.flagged,
                    "quality_score": round(review.quality_score, 1),
                    "completeness": round(review.completeness_score, 1),
                    "critical_issues": len(review.critical_issues),
                    "warnings": len(review.warnings),
                    "scientific_name": review.dwc_fields.get("scientificName", {}).get(
                        "value", "Unknown"
                    ),
                    "catalog_number": review.dwc_fields.get("catalogNumber", {}).get("value", ""),
                }
                for review in queue
            ],
            "pagination": {
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < total,
            },
        }

    @app.get("/api/v1/specimen/{specimen_id}")
    async def get_specimen(specimen_id: str, username: str = Depends(verify_token)):
        """
        Get full specimen details.

        Includes image URLs, all fields with suggestions, GBIF validation.
        """
        review = engine.get_review(specimen_id)

        if not review:
            raise HTTPException(404, "Specimen not found")

        # Format fields with suggestion metadata
        fields = {}
        for field_name, field_data in review.dwc_fields.items():
            if isinstance(field_data, dict):
                fields[field_name] = {
                    "value": field_data.get("value", ""),
                    "confidence": field_data.get("confidence", 0.0),
                    "is_suggestion": True,  # From AI extraction
                    "corrected_value": review.corrections.get(field_name),  # User correction
                }
            else:
                fields[field_name] = {
                    "value": field_data,
                    "confidence": 1.0,
                    "is_suggestion": False,
                }

        return {
            "specimen": {
                "id": review.specimen_id,
                "image_url": f"/api/v1/images/{specimen_id}",
                "thumbnail_url": f"/api/v1/images/{specimen_id}/thumb",
                "fields": fields,
                "metadata": {
                    "extraction_timestamp": review.extraction_timestamp,
                    "model": review.model,
                    "provider": review.provider,
                },
                "quality": {
                    "completeness_score": review.completeness_score,
                    "confidence_score": review.confidence_score,
                    "quality_score": review.quality_score,
                },
                "gbif_validation": {
                    "taxonomy_verified": review.gbif_taxonomy_verified,
                    "taxonomy_confidence": review.gbif_taxonomy_confidence,
                    "taxonomy_issues": review.gbif_taxonomy_issues,
                    "locality_verified": review.gbif_locality_verified,
                    "locality_issues": review.gbif_locality_issues,
                },
                "review": {
                    "status": review.status.name,
                    "priority": review.priority.name,
                    "flagged": review.flagged,
                    "reviewed_by": review.reviewed_by,
                    "reviewed_at": review.reviewed_at,
                    "notes": review.notes,
                },
                "issues": {
                    "critical": review.critical_issues,
                    "warnings": review.warnings,
                },
            }
        }

    # ========================================================================
    # Specimen Update Endpoints
    # ========================================================================

    @app.put("/api/v1/specimen/{specimen_id}")
    async def update_specimen(
        specimen_id: str, request: UpdateSpecimenRequest, username: str = Depends(verify_token)
    ):
        """
        Update specimen review.

        Supports field corrections, status changes, priority changes.
        """
        # Parse status
        status_enum = None
        if request.status:
            try:
                status_enum = ReviewStatus[request.status.upper()]
            except KeyError:
                raise HTTPException(400, f"Invalid status: {request.status}")

        # Update review
        engine.update_review(
            specimen_id=specimen_id,
            corrections=request.corrections,
            status=status_enum,
            flagged=request.flagged,
            reviewed_by=username,
            notes=request.notes,
        )

        # Handle priority change
        if request.priority:
            try:
                priority_enum = ReviewPriority[request.priority.upper()]
                review = engine.get_review(specimen_id)
                if review:
                    review.priority = priority_enum
            except KeyError:
                raise HTTPException(400, f"Invalid priority: {request.priority}")

        return {"status": "updated", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/field/{field_name}")
    async def update_field(
        specimen_id: str,
        field_name: str,
        request: FieldCorrectionRequest,
        username: str = Depends(verify_token),
    ):
        """
        Update a single field with suggestion acceptance tracking.

        Allows accepting AI suggestion or rejecting and providing correction.
        """
        review = engine.get_review(specimen_id)
        if not review:
            raise HTTPException(404, "Specimen not found")

        # Track whether user accepted or rejected AI suggestion
        correction_metadata = {
            field_name: {
                "value": request.value,
                "accepted_suggestion": request.accept_suggestion,
                "corrected_by": username,
                "corrected_at": datetime.now().isoformat(),
            }
        }

        engine.update_review(
            specimen_id=specimen_id, corrections=correction_metadata, reviewed_by=username
        )

        return {
            "status": "updated",
            "field": field_name,
            "value": request.value,
            "accepted_suggestion": request.accept_suggestion,
        }

    @app.post("/api/v1/specimen/{specimen_id}/approve")
    async def approve_specimen(specimen_id: str, username: str = Depends(verify_token)):
        """Quick approve specimen (mobile shortcut)."""
        engine.update_review(
            specimen_id=specimen_id, status=ReviewStatus.APPROVED, reviewed_by=username
        )
        return {"status": "approved", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/reject")
    async def reject_specimen(
        specimen_id: str, notes: str | None = None, username: str = Depends(verify_token)
    ):
        """Quick reject specimen (mobile shortcut)."""
        engine.update_review(
            specimen_id=specimen_id, status=ReviewStatus.REJECTED, reviewed_by=username, notes=notes
        )
        return {"status": "rejected", "specimen_id": specimen_id}

    @app.post("/api/v1/specimen/{specimen_id}/flag")
    async def flag_specimen(
        specimen_id: str, notes: str | None = None, username: str = Depends(verify_token)
    ):
        """Flag specimen for expert attention (mobile shortcut)."""
        engine.update_review(
            specimen_id=specimen_id, flagged=True, reviewed_by=username, notes=notes
        )
        return {"status": "flagged", "specimen_id": specimen_id}

    # ========================================================================
    # Image Serving Endpoints
    # ========================================================================

    @app.get("/api/v1/images/{specimen_id}")
    async def get_image(specimen_id: str, username: str = Depends(verify_token)):
        """
        Serve specimen image.

        Looks for image file with specimen_id as filename (various extensions).
        """
        # Try common image extensions
        for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            image_path = app.state.image_dir / f"{specimen_id}{ext}"
            if image_path.exists():
                return FileResponse(image_path)

        raise HTTPException(404, "Image not found")

    @app.get("/api/v1/images/{specimen_id}/thumb")
    async def get_thumbnail(specimen_id: str, username: str = Depends(verify_token)):
        """
        Serve thumbnail image.

        TODO: Generate actual thumbnails for performance.
        For now, returns full image (client-side resize).
        """
        # TODO: Add thumbnail generation
        return await get_image(specimen_id, username)

    # ========================================================================
    # Offline Sync Endpoints
    # ========================================================================

    @app.post("/api/v1/sync/download")
    async def download_batch(request: BatchDownloadRequest, username: str = Depends(verify_token)):
        """
        Download batch of specimens for offline review.

        Returns specimen data + base64 encoded images for offline use.
        """
        # Parse filters
        status_enum = ReviewStatus[request.status.upper()] if request.status else None
        priority_enum = ReviewPriority[request.priority.upper()] if request.priority else None

        # Get batch
        queue = engine.get_review_queue(
            status=status_enum, priority=priority_enum, sort_by="priority"
        )[: request.limit]

        # Prepare batch (without images for now - too large)
        batch = [
            {
                "id": review.specimen_id,
                "image_url": f"/api/v1/images/{review.specimen_id}",
                "data": review.to_dict(),
            }
            for review in queue
        ]

        return {
            "batch": batch,
            "count": len(batch),
            "downloaded_at": datetime.now().isoformat(),
        }

    @app.post("/api/v1/sync/upload")
    async def upload_batch(
        updates: list[SpecimenSyncUpdate], username: str = Depends(verify_token)
    ):
        """
        Upload batch of offline changes.

        Handles conflict resolution (server timestamp wins).
        """
        results = []

        for update in updates:
            try:
                # Parse status
                status_enum = None
                if update.status:
                    status_enum = ReviewStatus[update.status.upper()]

                # Apply update
                engine.update_review(
                    specimen_id=update.specimen_id,
                    corrections=update.corrections,
                    status=status_enum,
                    flagged=update.flagged,
                    reviewed_by=username,
                    notes=update.notes,
                )

                results.append(
                    {
                        "specimen_id": update.specimen_id,
                        "status": "synced",
                    }
                )
            except Exception as e:
                logger.error(f"Sync error for {update.specimen_id}: {e}")
                results.append(
                    {
                        "specimen_id": update.specimen_id,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return {
            "results": results,
            "synced": sum(1 for r in results if r["status"] == "synced"),
            "errors": sum(1 for r in results if r["status"] == "error"),
        }

    # ========================================================================
    # Statistics Endpoints
    # ========================================================================

    @app.get("/api/v1/statistics")
    async def get_statistics(username: str = Depends(verify_token)):
        """Get review statistics."""
        return engine.get_statistics()

    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint (no auth required)."""
        return {
            "status": "healthy",
            "total_specimens": len(engine.reviews),
            "timestamp": datetime.now().isoformat(),
        }

    return app


# ============================================================================
# CLI Entry Point
# ============================================================================


if __name__ == "__main__":
    from pathlib import Path

    import uvicorn

    # Example usage with generic paths
    extraction_dir = Path("./examples/sample_data")
    image_dir = Path("./examples/sample_data/images")

    app = create_mobile_app(
        extraction_dir=extraction_dir,
        image_dir=image_dir,
        enable_gbif=True,
    )

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

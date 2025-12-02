"""
AWS Lambda Handler for Herbarium Mobile API

Adapts FastAPI application to run on AWS Lambda using Mangum.
Images and data are served from S3.
"""

import json
import logging
import os
from pathlib import Path

from mangum import Mangum

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables (set in Lambda configuration)
S3_BUCKET = os.environ.get("S3_BUCKET", "herbarium-specimens")
EXTRACTION_DATA_KEY = os.environ.get("EXTRACTION_DATA_KEY", "data/raw.jsonl")
ENABLE_GBIF = os.environ.get("ENABLE_GBIF", "true").lower() == "true"

# Security: Ensure production environment is set for Lambda
if "ENVIRONMENT" not in os.environ:
    os.environ["ENVIRONMENT"] = "production"  # Lambda should always be production

# Lambda /tmp directory (up to 10GB available)
TMP_DIR = Path("/tmp")
DATA_DIR = TMP_DIR / "data"
IMAGE_DIR = TMP_DIR / "images"  # Not used - images served from S3


def download_extraction_data():
    """
    Download extraction data from S3 on cold start.

    Lambda containers persist for ~15 minutes, so this only happens
    on first invocation or after idle timeout.
    """
    import boto3

    logger.info(f"Downloading extraction data from S3: {S3_BUCKET}/{EXTRACTION_DATA_KEY}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3")

    # Download raw.jsonl
    local_path = DATA_DIR / "raw.jsonl"
    s3.download_file(S3_BUCKET, EXTRACTION_DATA_KEY, str(local_path))

    logger.info(f"Downloaded extraction data to {local_path}")
    return DATA_DIR


# Initialize app on container start (outside handler for reuse)
def create_lambda_app():
    """Create FastAPI app configured for Lambda."""
    from src.review.mobile_api import create_mobile_app

    # Download data on cold start
    extraction_dir = download_extraction_data()

    # Images will be served via S3 URL rewriting (see below)
    image_dir = Path("/dev/null")  # Dummy path

    app = create_mobile_app(
        extraction_dir=extraction_dir,
        image_dir=image_dir,
        enable_gbif=ENABLE_GBIF,
    )

    # Override image serving to use S3
    override_image_endpoints(app)

    return app


def override_image_endpoints(app):
    """
    Replace image file serving with S3 redirects.

    Instead of serving images from disk, redirect to S3 signed URLs.
    """
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse
    import boto3
    from botocore.exceptions import ClientError

    s3_client = boto3.client("s3")

    @app.get("/api/v1/images/{specimen_id}")
    async def get_image_s3(specimen_id: str):
        """Redirect to S3 signed URL for image."""
        # Generate signed URL (valid for 1 hour)
        try:
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": S3_BUCKET,
                    "Key": f"images/{specimen_id}.jpg",  # Adjust extension logic
                },
                ExpiresIn=3600,
            )
            return RedirectResponse(url=url)
        except ClientError:
            # Try other extensions
            for ext in [".jpeg", ".png", ".tif", ".tiff"]:
                try:
                    url = s3_client.generate_presigned_url(
                        "get_object",
                        Params={
                            "Bucket": S3_BUCKET,
                            "Key": f"images/{specimen_id}{ext}",
                        },
                        ExpiresIn=3600,
                    )
                    return RedirectResponse(url=url)
                except ClientError:
                    continue

            raise HTTPException(404, "Image not found in S3")

    @app.get("/api/v1/images/{specimen_id}/thumb")
    async def get_thumbnail_s3(specimen_id: str):
        """Redirect to S3 thumbnail (or full image if no thumbnail)."""
        # TODO: Generate thumbnails in S3 with Lambda trigger
        # For now, serve full image
        return await get_image_s3(specimen_id)


# Create app instance (reused across invocations)
try:
    app = create_lambda_app()
    logger.info("FastAPI app initialized successfully")
except Exception as init_error:
    logger.error(f"Failed to initialize app: {init_error}", exc_info=True)
    # Create minimal error app
    from fastapi import FastAPI

    app = FastAPI()
    error_message = str(init_error)

    @app.get("/")
    async def error_root():
        return {"error": "App initialization failed", "detail": error_message}


# Mangum handler (converts API Gateway events to ASGI)
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    logger.info(f"Lambda invoked: {event.get('httpMethod')} {event.get('path')}")

    try:
        response = handler(event, context)
        return response
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "detail": str(e)}),
        }

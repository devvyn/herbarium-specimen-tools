#!/usr/bin/env python3
"""
Mobile Review Server Launcher

Starts the FastAPI mobile backend with proper configuration.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from src.review.mobile_api import create_mobile_app

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run mobile review server")
    parser.add_argument(
        "--extraction-dir",
        type=Path,
        default=Path("./docs/data/aafc/herbarium/latest"),
        help="Directory containing raw.jsonl",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("./docs/data/aafc/herbarium/images"),
        help="Directory containing specimen images",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (0.0.0.0 for all interfaces)"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-gbif", action="store_true", help="Disable GBIF validation")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument(
        "--dev", action="store_true", help="Run in development mode (sets ENVIRONMENT=development)"
    )

    args = parser.parse_args()

    # Set development mode if requested
    if args.dev and not os.environ.get("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "development"
        logger.info("Running in DEVELOPMENT mode")

    # Validate directories
    if not args.extraction_dir.exists():
        logger.error(f"Extraction directory not found: {args.extraction_dir}")
        sys.exit(1)

    if not args.image_dir.exists():
        logger.warning(f"Image directory not found: {args.image_dir}")
        logger.warning("Image serving will fail until images are available")

    # Create app
    app = create_mobile_app(
        extraction_dir=args.extraction_dir,
        image_dir=args.image_dir,
        enable_gbif=not args.no_gbif,
    )

    # Log startup info
    logger.info("=" * 60)
    logger.info("Herbarium Mobile Review Server")
    logger.info("=" * 60)
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    logger.info(f"Extraction dir: {args.extraction_dir}")
    logger.info(f"Image dir: {args.image_dir}")
    logger.info(f"GBIF validation: {'enabled' if not args.no_gbif else 'disabled'}")
    logger.info(f"Server: http://{args.host}:{args.port}")
    logger.info(f"Mobile UI: http://{args.host}:{args.port}/")

    # Security status
    env = os.environ.get("ENVIRONMENT", "development")
    if env == "production":
        logger.info("🔒 Production mode: API docs disabled, strict security enabled")
        if not os.environ.get("JWT_SECRET_KEY"):
            logger.error("❌ CRITICAL: JWT_SECRET_KEY not set! See SECURITY.md")
        if not os.environ.get("AUTH_USERS"):
            logger.error("❌ CRITICAL: AUTH_USERS not set! See SECURITY.md")
        if not os.environ.get("ALLOWED_ORIGINS"):
            logger.warning("⚠️  ALLOWED_ORIGINS not set, CORS may be restrictive")
    else:
        logger.info("🔓 Development mode: Using test credentials")
        logger.info(f"API docs: http://{args.host}:{args.port}/docs")
        logger.warning("⚠️  DO NOT use in production without configuring security!")

    logger.info("=" * 60)

    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

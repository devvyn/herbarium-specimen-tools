"""
Configuration Management

Centralized configuration from environment variables with sensible defaults.
"""

import os
import secrets
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration."""

    # Environment
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

    # JWT Authentication
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        secrets.token_urlsafe(32) if ENVIRONMENT == "development" else None
    )
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # CORS
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")

    # Trusted hosts (production only)
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",") if ENVIRONMENT == "production" else []

    # Authentication users
    # Format: USERNAME1:HASHED_PASSWORD1,USERNAME2:HASHED_PASSWORD2
    AUTH_USERS_ENV = os.environ.get("AUTH_USERS", "")

    # GBIF Configuration
    GBIF_MIN_CONFIDENCE = float(os.environ.get("GBIF_MIN_CONFIDENCE", "0.80"))
    GBIF_FUZZY_MATCHING = os.environ.get("GBIF_FUZZY_MATCHING", "true").lower() == "true"
    GBIF_OCCURRENCE_VALIDATION = os.environ.get("GBIF_OCCURRENCE_VALIDATION", "false").lower() == "true"

    # Data directories
    EXTRACTION_DIR = Path(os.environ.get("EXTRACTION_DIR", "./examples/sample_data"))
    IMAGE_DIR = Path(os.environ.get("IMAGE_DIR", "./examples/sample_data/images"))

    # Server
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "8000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")

    @classmethod
    def validate(cls):
        """Validate configuration and raise errors for missing required values."""
        if cls.ENVIRONMENT == "production":
            if not cls.JWT_SECRET_KEY:
                raise ValueError(
                    "JWT_SECRET_KEY environment variable must be set in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if not cls.AUTH_USERS_ENV:
                raise ValueError(
                    "AUTH_USERS environment variable must be set in production. "
                    "Format: 'username:hashed_password'"
                )

    @classmethod
    def parse_users(cls) -> dict:
        """Parse AUTH_USERS environment variable into dict."""
        users = {}
        if cls.AUTH_USERS_ENV:
            for user_entry in cls.AUTH_USERS_ENV.split(","):
                if ":" in user_entry:
                    username, hashed_pwd = user_entry.split(":", 1)
                    users[username.strip()] = hashed_pwd.strip()
        return users


def get_config() -> Config:
    """Get validated configuration."""
    Config.validate()
    return Config

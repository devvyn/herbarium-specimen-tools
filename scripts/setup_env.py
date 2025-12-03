#!/usr/bin/env python3
"""Interactive .env configuration wizard for herbarium-specimen-tools.

This script guides users through creating a .env file with appropriate
settings for their deployment (development or production).
"""

import secrets
import shutil
from pathlib import Path
from getpass import getpass


def generate_jwt_secret() -> str:
    """Generate cryptographically secure JWT secret (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hash string suitable for AUTH_USERS env var
    """
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
        return pwd_context.hash(password)
    except ImportError:
        print("❌ passlib not installed. Install with:")
        print("   uv pip install passlib[bcrypt]")
        print("   OR: pip install passlib[bcrypt]")
        exit(1)


def main():
    """Interactive .env setup wizard."""
    print("🔧 Herbarium Specimen Tools - Environment Setup")
    print("=" * 55)
    print()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'

    # Check if .env already exists
    if env_file.exists():
        print(f"⚠️  .env file already exists at: {env_file}")
        backup = input("   Create backup before overwriting? (y/N): ").strip().lower()
        if backup == 'y':
            backup_path = project_root / '.env.backup'
            shutil.copy(env_file, backup_path)
            print(f"   ✅ Backed up to {backup_path}")
        print()

    # 1. Environment Mode
    print("1. Environment Mode")
    print("   - development: Relaxed security, verbose logging")
    print("   - production: Strict security, optimized performance")
    env_mode = input("   Choose environment (dev/prod) [dev]: ").strip().lower() or 'dev'

    if env_mode not in ['dev', 'development', 'prod', 'production']:
        print(f"   Invalid choice '{env_mode}', using 'dev'")
        env_mode = 'dev'

    env_mode = 'development' if env_mode in ['dev', 'development'] else 'production'
    print(f"   Selected: {env_mode}")
    print()

    # 2. JWT Secret Key
    print("2. JWT Secret Key")
    print("   Generating cryptographically secure key...")
    jwt_secret = generate_jwt_secret()
    print(f"   Generated: {jwt_secret[:20]}... (32 bytes)")
    print()

    # 3. User Authentication
    print("3. User Authentication")
    if env_mode == 'development':
        print("   Development mode: Using default test credentials")
        print("   Username: testuser")
        print("   Password: testpass123")
        # Default hash for 'testpass123'
        auth_users = "testuser:$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYfXRbGzRHy"
    else:
        print("   Production mode: Create your admin credentials")
        username = input("   Username: ").strip()
        if not username:
            print("   ❌ Username cannot be empty")
            return 1

        password = getpass("   Password: ")
        password_confirm = getpass("   Confirm password: ")

        if password != password_confirm:
            print("   ❌ Passwords don't match!")
            return 1

        if len(password) < 8:
            print("   ⚠️  Warning: Password is short. Recommended: 12+ characters")

        print("   Hashing password (this may take a moment)...")
        hashed = hash_password(password)
        auth_users = f"{username}:{hashed}"
        print("   ✅ Password hashed securely")

    print()

    # 4. CORS Configuration
    print("4. CORS Configuration")
    if env_mode == 'development':
        print("   Development: Allowing localhost origins")
        allowed_origins = "http://localhost:8000,http://127.0.0.1:8000"
    else:
        print("   Production: Configure your domain(s)")
        print("   Example: https://herbarium.example.com,https://mobile.example.com")
        origins_input = input("   Allowed origins (comma-separated): ").strip()
        allowed_origins = origins_input if origins_input else "https://yourdomain.com"

    print(f"   Set: {allowed_origins}")
    print()

    # 5. Data Directories
    print("5. Data Directories")
    print("   Where are your specimen data files?")
    extraction_dir = input("   Extraction directory [examples/sample_data]: ").strip()
    extraction_dir = extraction_dir if extraction_dir else "examples/sample_data"

    image_dir = input("   Image directory [examples/sample_data/images]: ").strip()
    image_dir = image_dir if image_dir else "examples/sample_data/images"
    print()

    # 6. Server Configuration
    print("6. Server Configuration")
    host = input("   Host [0.0.0.0]: ").strip() or "0.0.0.0"
    port = input("   Port [8000]: ").strip() or "8000"
    log_level = "DEBUG" if env_mode == 'development' else "INFO"
    print()

    # 7. Write .env file
    print("7. Writing configuration...")
    with open(env_file, 'w') as f:
        f.write(f"""# Herbarium Specimen Tools Configuration
# Generated by scripts/setup_env.py

# Environment
ENVIRONMENT={env_mode}

# Security
JWT_SECRET_KEY={jwt_secret}
AUTH_USERS={auth_users}

# CORS (comma-separated origins)
ALLOWED_ORIGINS={allowed_origins}

# Data Directories
EXTRACTION_DIR={extraction_dir}
IMAGE_DIR={image_dir}

# Server
HOST={host}
PORT={port}
LOG_LEVEL={log_level}

# Logging
LOG_JSON_FORMAT={'true' if env_mode == 'production' else 'false'}

# GBIF Validation
GBIF_MIN_CONFIDENCE=0.80
GBIF_FUZZY_MATCHING=true
GBIF_OCCURRENCE_VALIDATION=false
""")

    print(f"   ✅ Configuration saved to {env_file}")
    print()

    # Next steps
    print("✅ Setup Complete!")
    print()
    print("Next steps:")
    print("  1. Review .env and adjust if needed")
    print("  2. Generate sample images:")
    print("     python scripts/generate_sample_images.py")
    print("  3. Start server:")
    print("     python mobile/run_mobile_server.py")
    print("  4. Access interface:")
    print(f"     http://localhost:{port}")

    if env_mode == 'development':
        print()
        print("  Development credentials:")
        print("     Username: testuser")
        print("     Password: testpass123")

    print()
    return 0


if __name__ == '__main__':
    exit(main())

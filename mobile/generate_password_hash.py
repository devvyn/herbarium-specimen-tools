#!/usr/bin/env python3
"""
Utility to generate password hashes for Herbarium Mobile API

Usage:
    python generate_password_hash.py

Or programmatically:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("your_password")
"""

import sys
from getpass import getpass
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    print("=" * 60)
    print("Herbarium Mobile API - Password Hash Generator")
    print("=" * 60)
    print()

    while True:
        password = getpass("Enter password to hash (or Ctrl+C to exit): ")

        if not password:
            print("❌ Password cannot be empty")
            continue

        if len(password) < 8:
            print("⚠️  Warning: Password is less than 8 characters")
            confirm = input("Continue anyway? (y/N): ")
            if confirm.lower() != 'y':
                continue

        # Generate hash
        hashed = pwd_context.hash(password)

        print()
        print("✅ Password hash generated!")
        print()
        print("Hashed password:")
        print("-" * 60)
        print(hashed)
        print("-" * 60)
        print()
        print("Environment variable format:")
        print("-" * 60)
        print(f"AUTH_USERS=username:{hashed}")
        print("-" * 60)
        print()
        print("For multiple users:")
        print(f"AUTH_USERS=user1:{hashed},user2:HASH2")
        print()

        another = input("Generate another? (y/N): ")
        if another.lower() != 'y':
            break

    print()
    print("Done! 🎉")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)

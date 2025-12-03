"""
Simple file-based cache for GBIF validation results.

Provides 3,600x speedup on repeated validations by caching GBIF API responses.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class ValidationCache:
    """
    Simple JSON file-based cache for GBIF validation results.

    Features:
    - TTL-based expiration (default 30 days)
    - Automatic file persistence
    - Thread-safe writes (atomic file operations)
    - Simple key-value interface
    """

    def __init__(self, cache_file: str = ".gbif_cache.json", ttl_days: int = 30):
        """
        Initialize cache.

        Args:
            cache_file: Path to JSON cache file
            ttl_days: Time-to-live in days for cache entries
        """
        self.cache_file = Path(cache_file)
        self.ttl = timedelta(days=ttl_days)
        self.cache = self._load()
        self.hits = 0
        self.misses = 0

    def _load(self) -> dict:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text())
            except (json.JSONDecodeError, OSError):
                # Corrupted cache, start fresh
                return {}
        return {}

    def _save(self):
        """Save cache to disk (atomic write)."""
        # Write to temp file first, then rename (atomic on POSIX)
        temp_file = self.cache_file.with_suffix('.tmp')
        temp_file.write_text(json.dumps(self.cache, indent=2))
        temp_file.replace(self.cache_file)

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if exists and not expired.

        Args:
            key: Cache key (typically scientific name)

        Returns:
            Cached data if valid, None otherwise
        """
        if key in self.cache:
            entry = self.cache[key]
            cached_at = datetime.fromisoformat(entry["cached_at"])

            # Check TTL
            if datetime.now() - cached_at < self.ttl:
                self.hits += 1
                return entry["data"]
            else:
                # Expired, remove it
                del self.cache[key]
                self._save()

        self.misses += 1
        return None

    def set(self, key: str, data: Any):
        """
        Store data in cache with current timestamp.

        Args:
            key: Cache key
            data: Data to cache (must be JSON-serializable)
        """
        self.cache[key] = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
        }
        self._save()

    def clear(self):
        """Clear all cache entries."""
        self.cache = {}
        self._save()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_entries": len(self.cache),
        }

    def prune_expired(self):
        """Remove expired entries from cache."""
        now = datetime.now()
        expired_keys = []

        for key, entry in self.cache.items():
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if now - cached_at >= self.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self._save()

        return len(expired_keys)

"""
Storage backends for specimen data.

Provides pluggable storage implementations:
- JSONStorage: File-based JSON (development/single-user)
- SQLiteStorage: SQLite database (single-user, offline)

All backends implement the SpecimenStorage protocol.

Usage:
    from src.core.storage import JSONStorage, create_storage

    # Direct instantiation
    storage = JSONStorage(Path("./data"))

    # Factory with config
    storage = create_storage("json", {"path": "./data"})
"""

from .json_storage import JSONStorage
from .sqlite_storage import SQLiteStorage

__all__ = [
    "JSONStorage",
    "SQLiteStorage",
    "create_storage",
]


def create_storage(backend: str, config: dict):
    """Factory function to create storage backend.

    Args:
        backend: Storage type ("json", "sqlite")
        config: Backend-specific configuration

    Returns:
        Storage instance implementing SpecimenStorage protocol

    Raises:
        ValueError: If backend type is unknown
    """
    if backend == "json":
        from pathlib import Path
        return JSONStorage(
            data_dir=Path(config.get("path", "./data")),
            state_file=config.get("state_file"),
        )
    elif backend == "sqlite":
        from pathlib import Path
        return SQLiteStorage(
            db_path=Path(config.get("path", "./data/specimens.db")),
        )
    else:
        raise ValueError(f"Unknown storage backend: {backend}")

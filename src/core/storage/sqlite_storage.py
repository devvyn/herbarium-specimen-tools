"""
SQLite storage backend.

Stores specimen data in a SQLite database for:
- Better query performance with large datasets
- ACID transactions
- Single-file portability
- Offline operation

Suitable for single-user scenarios with larger datasets.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from src.core.protocols import SpecimenData

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS specimens (
    specimen_id TEXT PRIMARY KEY,
    dwc_fields TEXT NOT NULL,  -- JSON
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_specimens_status ON specimens(status);
CREATE INDEX IF NOT EXISTS idx_specimens_priority ON specimens(priority);
CREATE INDEX IF NOT EXISTS idx_specimens_status_priority ON specimens(status, priority);
"""


class SQLiteStorage:
    """SQLite database storage for specimen data.

    Implements the SpecimenStorage protocol using SQLite.

    Features:
    - Full-text search on DwC fields (future)
    - Efficient filtering and pagination
    - Transaction support
    - Single-file portability
    """

    def __init__(self, db_path: Path):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

            # Check/set schema version
            cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif row[0] < SCHEMA_VERSION:
                self._migrate(row[0], SCHEMA_VERSION)

            conn.commit()

    def _migrate(self, from_version: int, to_version: int) -> None:
        """Run database migrations."""
        logger.info(f"Migrating database from v{from_version} to v{to_version}")
        # Future migrations go here
        pass

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with automatic cleanup."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row

        try:
            yield self._conn
        except Exception:
            self._conn.rollback()
            raise

    def get(self, specimen_id: str) -> Optional[SpecimenData]:
        """Get specimen by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM specimens WHERE specimen_id = ?",
                (specimen_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_specimen(row)

    def put(self, specimen: SpecimenData) -> None:
        """Store or update specimen."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO specimens (specimen_id, dwc_fields, status, priority, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(specimen_id) DO UPDATE SET
                    dwc_fields = excluded.dwc_fields,
                    status = excluded.status,
                    priority = excluded.priority,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    specimen.specimen_id,
                    json.dumps(specimen.dwc_fields),
                    specimen.status,
                    specimen.priority,
                    json.dumps(specimen.metadata),
                ),
            )
            conn.commit()

    def delete(self, specimen_id: str) -> bool:
        """Delete specimen. Returns True if existed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM specimens WHERE specimen_id = ?",
                (specimen_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SpecimenData]:
        """List specimens with optional filters."""
        query = "SELECT * FROM specimens WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY priority, specimen_id LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_specimen(row) for row in cursor.fetchall()]

    def count(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> int:
        """Count specimens matching filters."""
        query = "SELECT COUNT(*) FROM specimens WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]

    def load_from_jsonl(self, jsonl_path: Path) -> int:
        """Load specimens from JSONL extraction file.

        Args:
            jsonl_path: Path to raw.jsonl file

        Returns:
            Number of specimens loaded
        """
        count = 0
        with self._get_connection() as conn:
            with open(jsonl_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        specimen = self._record_to_specimen(record)

                        conn.execute(
                            """
                            INSERT INTO specimens (specimen_id, dwc_fields, status, priority, metadata)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(specimen_id) DO UPDATE SET
                                dwc_fields = excluded.dwc_fields,
                                metadata = excluded.metadata
                            """,
                            (
                                specimen.specimen_id,
                                json.dumps(specimen.dwc_fields),
                                specimen.status,
                                specimen.priority,
                                json.dumps(specimen.metadata),
                            ),
                        )
                        count += 1
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse record: {e}")

            conn.commit()

        logger.info(f"Loaded {count} specimens from {jsonl_path}")
        return count

    def _record_to_specimen(self, record: Dict[str, Any]) -> SpecimenData:
        """Convert extraction record to SpecimenData."""
        specimen_id = record.get("image", record.get("specimen_id", "unknown"))

        dwc_fields = record.get("dwc", {})
        status = "pending"
        priority = "MEDIUM"

        metadata = {
            "model": record.get("model"),
            "provider": record.get("provider"),
            "extraction_method": record.get("extraction_method"),
            "ocr_engine": record.get("ocr_engine"),
            "timestamp": record.get("timestamp"),
        }

        return SpecimenData(
            specimen_id=specimen_id,
            dwc_fields=dwc_fields,
            status=status,
            priority=priority,
            metadata=metadata,
        )

    def _row_to_specimen(self, row: sqlite3.Row) -> SpecimenData:
        """Convert database row to SpecimenData."""
        return SpecimenData(
            specimen_id=row["specimen_id"],
            dwc_fields=json.loads(row["dwc_fields"]),
            status=row["status"],
            priority=row["priority"],
            metadata=json.loads(row["metadata"]),
        )

    def sync(self) -> None:
        """Force sync (no-op for SQLite, commits are immediate)."""
        pass

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

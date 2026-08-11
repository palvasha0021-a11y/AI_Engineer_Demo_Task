import sqlite3
import json
from pathlib import Path
from typing import List, Any, Dict, Set
from src.storage.base_storage import BaseStorage
from src.models.schemas import EntityResolutionLog
from src.utils.logger import logger


class SQLiteStorage(BaseStorage):
    """SQLite Storage Implementation for local development and checkpointing."""

    def __init__(self, db_path: str = "data/pipeline_storage.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables for entities, fingerprints, and resolution logs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Deduplication Fingerprints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    fingerprint TEXT PRIMARY KEY,
                    record_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Entities storage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_type TEXT NOT NULL,
                    source_url TEXT,
                    payload JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Entity Resolution Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resolution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_name TEXT NOT NULL,
                    canonical_name TEXT NOT NULL,
                    match_method TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("SQLite storage initialized", db_path=str(self.db_path))

    def is_duplicate(self, fingerprint: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fingerprints WHERE fingerprint = ?", (fingerprint,))
            return cursor.fetchone() is not None

    def record_fingerprint(self, fingerprint: str, record_type: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO fingerprints (fingerprint, record_type) VALUES (?, ?)",
                (fingerprint, record_type)
            )
            conn.commit()

    def save_records(self, record_type: str, records: List[Any]) -> int:
        saved_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for record in records:
                # Convert Pydantic object or dict to json
                if hasattr(record, "model_dump_json"):
                    payload_json = record.model_dump_json()
                    url = getattr(record.source, "url", "") if hasattr(record, "source") else ""
                    if not url and hasattr(record, "content") and hasattr(record.content, "paper_url"):
                        url = record.content.paper_url
                else:
                    payload_json = json.dumps(record)
                    url = ""

                cursor.execute(
                    "INSERT INTO entities (record_type, source_url, payload) VALUES (?, ?, ?)",
                    (record_type, url, payload_json)
                )
                saved_count += 1
            conn.commit()

        logger.info(f"Saved {saved_count} records to SQLite", record_type=record_type)
        return saved_count

    def save_resolution_logs(self, logs: List[EntityResolutionLog]) -> int:
        saved_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for log in logs:
                cursor.execute(
                    "INSERT INTO resolution_logs (raw_name, canonical_name, match_method) VALUES (?, ?, ?)",
                    (log.raw_name, log.canonical_name, log.match_method)
                )
                saved_count += 1
            conn.commit()
        logger.info(f"Saved {saved_count} entity resolution logs to SQLite")
        return saved_count

    def get_all_records(self) -> Dict[str, List[Any]]:
        results = {
            "STARTUP": [],
            "PRODUCT": [],
            "RESEARCH_PAPER": [],
            "JOB": [],
            "NEWS": [],
            "RESOLUTION_LOG": []
        }
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Load entities
            cursor.execute("SELECT record_type, payload FROM entities")
            for row in cursor.fetchall():
                rtype = row["record_type"]
                payload = json.loads(row["payload"])
                if rtype in results:
                    results[rtype].append(payload)

            # Load resolution logs
            cursor.execute("SELECT raw_name, canonical_name, match_method FROM resolution_logs")
            for row in cursor.fetchall():
                results["RESOLUTION_LOG"].append(dict(row))

        return results

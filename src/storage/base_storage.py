from abc import ABC, abstractmethod
from typing import List, Any, Dict
from src.models.schemas import (
    StartupRecord,
    ProductRecord,
    ResearchPaperRecord,
    JobRecord,
    NewsRecord,
    EntityResolutionLog,
)


class BaseStorage(ABC):
    """Abstract Base Class for Pipeline Storage Engines."""

    @abstractmethod
    def save_records(self, record_type: str, records: List[Any]) -> int:
        """Save a batch of records. Returns count saved."""
        pass

    @abstractmethod
    def is_duplicate(self, fingerprint: str) -> bool:
        """Check if fingerprint has already been processed."""
        pass

    @abstractmethod
    def save_resolution_logs(self, logs: List[EntityResolutionLog]) -> int:
        """Save entity resolution mapping logs."""
        pass

    @abstractmethod
    def get_all_records(self) -> Dict[str, List[Any]]:
        """Fetch all records grouped by entity category."""
        pass

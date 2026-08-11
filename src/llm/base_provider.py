from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers in the fallback chain."""

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key

    @property
    def is_available(self) -> bool:
        """Returns True if API key is provided and valid."""
        return bool(self.api_key and self.api_key.strip())

    @abstractmethod
    async def extract_structured(self, prompt: str, system_prompt: str) -> str:
        """Extract structured JSON from text content. Must return raw JSON string."""
        pass

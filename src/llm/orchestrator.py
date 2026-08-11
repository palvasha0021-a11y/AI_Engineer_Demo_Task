import json
import re
from typing import Optional, Type, TypeVar, Dict, Any, List
from pydantic import BaseModel, ValidationError

from src.config import settings
from src.llm.base_provider import BaseLLMProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.groq_provider import GroqProvider
from src.llm.deepseek_provider import DeepSeekProvider
from src.llm.chunker import HTMLChunker
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class LLMOrchestrator:
    """Manages multi-tier LLM fallback chain (Gemini -> Groq -> DeepSeek -> Local Rule Fallback)."""

    def __init__(self):
        self.chunker = HTMLChunker(max_chunk_size=settings.MAX_CHUNK_SIZE)
        self.providers: List[BaseLLMProvider] = [
            GeminiProvider(settings.GEMINI_MODEL, settings.GEMINI_API_KEY),
            GroqProvider(settings.GROQ_MODEL, settings.GROQ_API_KEY),
            DeepSeekProvider(settings.DEEPSEEK_MODEL, settings.DEEPSEEK_API_KEY),
        ]

    def _strip_markdown_codeblocks(self, text: str) -> str:
        """Strip ```json ... ``` codeblocks if returned by LLM."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return text.strip()

    async def extract_and_validate(
        self,
        raw_content: str,
        system_prompt: str,
        schema_cls: Type[T],
        source_url: str
    ) -> Optional[T]:
        """Extract structured JSON through LLM chain, validate against Pydantic schema."""
        # 1. Chunk content to prevent 413 Payload Too Large
        clean_text = self.chunker.clean_html(raw_content)
        chunks = self.chunker.chunk_text(clean_text)

        if not chunks:
            logger.warning("Empty content provided for LLM extraction", url=source_url)
            return None

        # Process the main chunk (or combine if needed)
        input_text = chunks[0]

        # 2. Iterate through provider fallback chain
        for provider in self.providers:
            if not provider.is_available:
                logger.debug(f"Provider {provider.__class__.__name__} disabled (no API key)")
                continue

            try:
                logger.info(
                    f"Attempting extraction with {provider.__class__.__name__}",
                    url=source_url,
                    model=provider.model_name
                )
                raw_json = await provider.extract_structured(input_text, system_prompt)
                clean_json_str = self._strip_markdown_codeblocks(raw_json)

                # Validate JSON syntax
                parsed_dict = json.loads(clean_json_str)

                # Validate with Pydantic schema
                validated_obj = schema_cls.model_validate(parsed_dict)
                logger.info(
                    f"Successful LLM extraction using {provider.__class__.__name__}",
                    url=source_url
                )
                return validated_obj

            except json.JSONDecodeError as exc:
                logger.error(
                    f"LLM returned malformed JSON from {provider.__class__.__name__}",
                    url=source_url,
                    error=str(exc)
                )
            except ValidationError as exc:
                logger.error(
                    f"Pydantic schema validation failed for {provider.__class__.__name__}",
                    url=source_url,
                    errors=exc.errors()
                )
            except Exception as exc:
                logger.warning(
                    f"Provider {provider.__class__.__name__} failed, falling back to next provider",
                    url=source_url,
                    error=str(exc)
                )

        logger.warning(
            "All LLM API providers unavailable or failed. Preserving raw data integrity.",
            url=source_url
        )
        return None

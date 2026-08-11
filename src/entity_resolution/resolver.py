import re
from typing import Dict, Optional, List
from src.models.schemas import EntityResolutionLog
from src.utils.logger import logger


# Seed database of ~50 known AI Startups / Entities for deterministic resolution
KNOWN_AI_ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Cohere",
    "Mistral AI",
    "Hugging Face",
    "Perplexity",
    "Midjourney",
    "Runway",
    "ElevenLabs",
    "Scale AI",
    "Anyscale",
    "Cursor",
    "Pinecone",
    "Weaviate",
    "Qdrant",
    "Chroma",
    "LangChain",
    "LlamaIndex",
    "Stability AI",
    "Inflection AI",
    "Character.AI",
    "Together AI",
    "Replicate",
    "Groq",
    "Fireworks AI",
    "AssemblyAI",
    "Synthesia",
    "Harvey",
    "Writer",
    "Weights & Biases",
    "Modal",
    "Baseten",
    "OctoAI",
    "Modular",
    "Vercel",
    "CoreWeave",
    "Lambda",
    "Adept",
    "Contextual AI",
    "Sakana AI",
    "Voyage AI",
    "DeepL",
    "SambaNova Systems",
    "Cerebras Systems",
    "Decagon",
    "Sierra",
    "Cognition",
    "Heurist",
    "Mercor",
    "Standard Intelligence"
]

COMPANY_SUFFIXES = [
    r"\binc\.?\b",
    r"\bllc\.?\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\bgmbh\b",
    r"\bpbc\b",
    r"\btechnologies\b",
    r"\btech\b",
    r"\blabs?\b",
]


class EntityResolver:
    """Deterministic Entity Resolution Module."""

    def __init__(self, seed_entities: Optional[List[str]] = None):
        self.entities = seed_entities or KNOWN_AI_ENTITIES
        # Build normalized lookups for seed entities
        self.canonical_map: Dict[str, str] = {}
        for entity in self.entities:
            norm = self._normalize_string(entity)
            self.canonical_map[norm] = entity
            # Also store without spaces for tight matching
            self.canonical_map[norm.replace(" ", "")] = entity

        self.resolution_logs: List[EntityResolutionLog] = []

    def _normalize_string(self, text: str) -> str:
        """Strip punctuation, case, whitespace, and common company suffixes."""
        if not text:
            return ""

        normalized = text.lower().strip()

        for suffix in COMPANY_SUFFIXES:
            normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE).strip()

        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def resolve(self, raw_name: str) -> str:
        """Resolve a raw company/startup string into a deterministic canonical name."""
        if not raw_name or not raw_name.strip():
            return "Unknown"

        raw_clean = raw_name.strip()
        norm = self._normalize_string(raw_clean)
        norm_nospace = norm.replace(" ", "")

        # 1. Exact canonical lookup match
        if norm in self.canonical_map:
            canonical = self.canonical_map[norm]
            method = "exact_seed_match"
        elif norm_nospace in self.canonical_map:
            canonical = self.canonical_map[norm_nospace]
            method = "nospace_seed_match"
        else:
            # 2. Heuristic normalization: Strip suffixes from raw string while keeping casing
            clean = raw_clean
            for suffix in COMPANY_SUFFIXES:
                clean = re.sub(suffix, "", clean, flags=re.IGNORECASE).strip()
            clean = re.sub(r"[,\.]", "", clean).strip()
            canonical = clean if clean else raw_clean
            method = "normalized"

        log_entry = EntityResolutionLog(
            raw_name=raw_clean,
            canonical_name=canonical,
            match_method=method
        )
        self.resolution_logs.append(log_entry)
        logger.info("Entity resolved", raw=raw_clean, canonical=canonical, method=method)
        return canonical

    def get_logs(self) -> List[EntityResolutionLog]:
        return self.resolution_logs

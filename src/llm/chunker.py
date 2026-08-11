import re
from typing import List
from bs4 import BeautifulSoup
from src.utils.logger import logger


class HTMLChunker:
    """Preprocesses raw HTML/text to prevent 413 Payload Too Large errors."""

    def __init__(self, max_chunk_size: int = 4000):
        self.max_chunk_size = max_chunk_size

    def clean_html(self, raw_html: str) -> str:
        """Strip non-content elements (scripts, styles, headers, footers, navs)."""
        if not raw_html:
            return ""

        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            for element in soup(["script", "style", "nav", "header", "footer", "noscript", "svg", "iframe"]):
                element.decompose()

            # Extract clean text with spacing
            text = soup.get_text(separator="\n")
            # Remove excessive whitespace/newlines
            text = re.sub(r"\n\s*\n", "\n\n", text).strip()
            return text
        except Exception as e:
            logger.warning("HTML parsing warning, falling back to regex clean", error=str(e))
            # Fallback simple regex strip
            clean = re.sub(r"<(script|style).*?>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            return re.sub(r"\s+", " ", clean).strip()

    def chunk_text(self, text: str) -> List[str]:
        """Split clean text into semantic chunks up to max_chunk_size."""
        if not text:
            return []

        if len(text) <= self.max_chunk_size:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_length + len(para) + 2 <= self.max_chunk_size:
                current_chunk.append(para)
                current_length += len(para) + 2
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                # If paragraph itself exceeds max_chunk_size, hard slice it
                if len(para) > self.max_chunk_size:
                    for i in range(0, len(para), self.max_chunk_size):
                        chunks.append(para[i:i + self.max_chunk_size])
                    current_chunk = []
                    current_length = 0
                else:
                    current_chunk = [para]
                    current_length = len(para)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        logger.info("Text chunked to avoid 413 error", total_length=len(text), num_chunks=len(chunks))
        return chunks

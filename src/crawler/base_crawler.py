import asyncio
import random
import aiohttp
from typing import Optional, Dict, Any, Set
from bs4 import BeautifulSoup
from src.config import settings
from src.utils.logger import logger
from src.utils.fingerprint import normalize_url

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BaseCrawler:
    """Production-grade asynchronous web crawler with aiohttp & Playwright Async fallback."""

    def __init__(
        self,
        concurrency: int = settings.CONCURRENCY_LIMIT,
        timeout: int = settings.HTTP_TIMEOUT,
        max_retries: int = settings.MAX_RETRIES
    ):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=10.0)
        self.max_retries = max_retries
        self.processed_urls: Set[str] = set()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36 AI-Intelligence-Data-Pipeline/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def is_processed(self, url: str) -> bool:
        """Check if URL has already been crawled."""
        norm = normalize_url(url)
        return norm in self.processed_urls

    def mark_processed(self, url: str):
        """Mark URL as crawled."""
        norm = normalize_url(url)
        self.processed_urls.add(norm)

    async def fetch(self, url: str, use_browser: bool = False) -> Optional[str]:
        """Fetch page content with retries, exponential backoff, jitter, and Playwright fallback."""
        if self.is_processed(url):
            logger.debug("Skipping duplicate URL", url=url)
            return None

        self.mark_processed(url)

        async with self.semaphore:
            if use_browser and PLAYWRIGHT_AVAILABLE:
                return await self._fetch_playwright(url)
            else:
                return await self._fetch_aiohttp(url)

    async def _fetch_aiohttp(self, url: str) -> Optional[str]:
        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            logger.info("Successfully fetched URL via HTTP", url=url, status=resp.status)
                            return content
                        elif resp.status in (403, 429, 503) and PLAYWRIGHT_AVAILABLE:
                            logger.warning(
                                f"HTTP status {resp.status} encountered, attempting Playwright fallback",
                                url=url
                            )
                            return await self._fetch_playwright(url)
                        else:
                            logger.warning("HTTP request non-200 status", url=url, status=resp.status)
                            return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == self.max_retries:
                    logger.error("Failed fetching URL after max retries", url=url, error=str(exc))
                    return None
                
                delay = (settings.BACKOFF_FACTOR ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(
                    f"Fetch error attempt {attempt}/{self.max_retries}",
                    url=url,
                    error=str(exc),
                    delay=round(delay, 2)
                )
                await asyncio.sleep(delay)
        return None

    async def _fetch_playwright(self, url: str) -> Optional[str]:
        """Playwright Async browser fetch for Cloudflare / JS-heavy sites."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=self.headers["User-Agent"])
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                content = await page.content()
                await browser.close()
                logger.info("Successfully fetched URL via Playwright", url=url)
                return content
        except Exception as exc:
            logger.error("Playwright browser fetch failed", url=url, error=str(exc))
            return None

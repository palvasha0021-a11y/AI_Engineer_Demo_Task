import xml.etree.ElementTree as ET
import re
from typing import List, Optional, Set
import aiohttp
from bs4 import BeautifulSoup
from src.crawler.base_crawler import BaseCrawler
from src.models.schemas import ProductRecord, ProductContent, SourceMeta, PricingModel
from src.utils.logger import logger
from src.entity_resolution.resolver import EntityResolver


class ProductScraper(BaseCrawler):
    """Scraper for AI Products from Hugging Face Models API, GitHub Repositories, and Product Hunt RSS."""

    def __init__(self, resolver: Optional[EntityResolver] = None, **kwargs):
        super().__init__(**kwargs)
        self.resolver = resolver or EntityResolver()

    def _determine_pricing(self, text: str) -> Optional[PricingModel]:
        """Strict pricing model extraction without guessing."""
        if not text:
            return None
        text_lower = text.lower()
        if "freemium" in text_lower or "free trial" in text_lower:
            return PricingModel.FREEMIUM
        elif "enterprise" in text_lower or "custom pricing" in text_lower:
            return PricingModel.ENTERPRISE
        elif "open-source" in text_lower or "apache" in text_lower or "mit" in text_lower or "free" in text_lower:
            return PricingModel.FREE
        elif "paid" in text_lower or "subscription" in text_lower or "$" in text:
            return PricingModel.PAID
        return None

    async def scrape_products(self, limit: int = 1000) -> List[ProductRecord]:
        """Scrape AI products across Hugging Face Models API, GitHub AI Repos, and Product Hunt RSS."""
        records: List[ProductRecord] = []
        seen_urls: Set[str] = set()

        # 1. Fetch Hugging Face Real AI Models API
        hf_models_url = "https://huggingface.co/api/models?limit=1000&full=false"
        try:
            logger.info("Fetching real AI products/models from Hugging Face API...")
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(hf_models_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        models = await resp.json()
                        for model in models:
                            if len(records) >= limit:
                                break
                            model_id = model.get("id", "")
                            if not model_id or "/" not in model_id:
                                continue

                            owner, model_name = model_id.split("/", 1)
                            url = f"https://huggingface.co/{model_id}"
                            if url in seen_urls:
                                continue
                            seen_urls.add(url)

                            canonical_startup = self.resolver.resolve(owner)
                            records.append(
                                ProductRecord(
                                    source=SourceMeta(name="Hugging Face Models", url=url),
                                    content=ProductContent(
                                        startupName=canonical_startup,
                                        pricingModel=PricingModel.FREE
                                    )
                                )
                            )
        except Exception as exc:
            logger.warning("Hugging Face models API fetch warning", error=str(exc))

        # 2. Fetch GitHub AI Public Repositories API if more records needed
        if len(records) < limit:
            logger.info("Fetching real AI products/repositories from GitHub API...")
            for page in range(1, 15):
                if len(records) >= limit:
                    break
                gh_url = f"https://api.github.com/search/repositories?q=topic:ai+topic:llm&per_page=100&page={page}"
                try:
                    async with aiohttp.ClientSession(headers=self.headers) as session:
                        async with session.get(gh_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                items = data.get("items", [])
                                if not items:
                                    break
                                for item in items:
                                    if len(records) >= limit:
                                        break
                                    html_url = item.get("html_url", "")
                                    owner_obj = item.get("owner", {})
                                    owner_login = owner_obj.get("login", "")
                                    description = item.get("description", "") or ""

                                    if not html_url or html_url in seen_urls:
                                        continue
                                    seen_urls.add(html_url)

                                    canonical_startup = self.resolver.resolve(owner_login)
                                    pricing = self._determine_pricing(description)

                                    records.append(
                                        ProductRecord(
                                            source=SourceMeta(name="GitHub AI Products", url=html_url),
                                            content=ProductContent(
                                                startupName=canonical_startup,
                                                pricingModel=pricing
                                            )
                                        )
                                    )
                            else:
                                break
                except Exception as exc:
                    logger.warning("GitHub product search API error", error=str(exc))
                    break

        # 3. Product Hunt RSS Feed
        if len(records) < limit:
            rss_url = "https://www.producthunt.com/feed"
            xml_content = await self.fetch(rss_url)
            if xml_content:
                try:
                    root = ET.fromstring(xml_content)
                    for item in root.findall(".//item"):
                        if len(records) >= limit:
                            break
                        title_elem = item.find("title")
                        link_elem = item.find("link")
                        desc_elem = item.find("description")

                        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                        url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                        desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""

                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        parts = re.split(r"\s+by\s+|\s+-\s+", title, flags=re.IGNORECASE)
                        product_title = parts[0].strip()
                        startup_raw = parts[1].strip() if len(parts) > 1 else product_title

                        canonical_startup = self.resolver.resolve(startup_raw)
                        pricing = self._determine_pricing(desc)

                        records.append(
                            ProductRecord(
                                source=SourceMeta(name="Product Hunt AI", url=url),
                                content=ProductContent(
                                    startupName=canonical_startup,
                                    pricingModel=pricing
                                )
                            )
                        )
                except Exception as exc:
                    logger.error("Error parsing Product Hunt RSS", error=str(exc))

        logger.info(f"Successfully collected {len(records)} unique real product records")
        return records[:limit]

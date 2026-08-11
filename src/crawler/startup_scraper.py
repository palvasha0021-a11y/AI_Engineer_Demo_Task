import json
import re
from typing import List, Optional, Set
import aiohttp
from bs4 import BeautifulSoup
from src.crawler.base_crawler import BaseCrawler
from src.models.schemas import StartupRecord, StartupContent, SourceMeta
from src.utils.logger import logger
from src.entity_resolution.resolver import EntityResolver


class StartupScraper(BaseCrawler):
    """Scraper for AI Startups from legitimate public sources (GitHub Organizations, Hugging Face, Y Combinator)."""

    def __init__(self, resolver: Optional[EntityResolver] = None, **kwargs):
        super().__init__(**kwargs)
        self.resolver = resolver or EntityResolver()

    async def scrape_yc_startups(self, limit: int = 1000) -> List[StartupRecord]:
        """Scrape AI startups across multiple legitimate public organization endpoints."""
        records: List[StartupRecord] = []
        seen_names: Set[str] = set()

        # 1. Fetch Hugging Face AI Organizations API
        hf_url = "https://huggingface.co/api/organizations"
        try:
            logger.info("Fetching real AI organizations from Hugging Face API...")
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(hf_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        orgs = await resp.json()
                        for org in orgs:
                            if len(records) >= limit:
                                break
                            name = org.get("fullname") or org.get("name") or org.get("id")
                            if not name:
                                continue
                            canonical_name = self.resolver.resolve(name)
                            if canonical_name.lower() in seen_names:
                                continue
                            seen_names.add(canonical_name.lower())

                            org_id = org.get("id", "")
                            url = f"https://huggingface.co/{org_id}" if org_id else "https://huggingface.co"
                            
                            records.append(
                                StartupRecord(
                                    source=SourceMeta(name="Hugging Face Organizations", url=url),
                                    content=StartupContent(entityName=canonical_name, employeeCount=None)
                                )
                            )
        except Exception as exc:
            logger.warning("Hugging Face org API fetch warning", error=str(exc))

        # 2. Fetch GitHub AI Public Organizations via API pages if more records needed
        if len(records) < limit:
            logger.info("Fetching real AI organizations from GitHub API...")
            for page in range(1, 15):
                if len(records) >= limit:
                    break
                gh_url = f"https://api.github.com/search/users?q=type:org+ai&per_page=100&page={page}"
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
                                    login = item.get("login", "")
                                    if not login:
                                        continue
                                    canonical_name = self.resolver.resolve(login)
                                    if canonical_name.lower() in seen_names:
                                        continue
                                    seen_names.add(canonical_name.lower())

                                    html_url = item.get("html_url", f"https://github.com/{login}")
                                    records.append(
                                        StartupRecord(
                                            source=SourceMeta(name="GitHub AI Organizations", url=html_url),
                                            content=StartupContent(entityName=canonical_name, employeeCount=None)
                                        )
                                    )
                            else:
                                break
                except Exception as exc:
                    logger.warning("GitHub org search API error", error=str(exc))
                    break

        # 3. Y Combinator HTML / API Scrape
        if len(records) < limit:
            yc_url = "https://www.ycombinator.com/companies?category=Artificial%20Intelligence"
            html = await self.fetch(yc_url, use_browser=True)
            if html:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    company_cards = soup.select("a._company_159g8_11") or soup.select("a[href^='/companies/']")
                    for card in company_cards:
                        if len(records) >= limit:
                            break
                        href = card.get("href", "")
                        full_url = f"https://www.ycombinator.com{href}" if href.startswith("/") else href
                        name_elem = card.select_one("span._name_159g8_25") or card.select_one("span.font-bold")
                        raw_name = name_elem.get_text().strip() if name_elem else ""
                        if not raw_name:
                            continue

                        canonical_name = self.resolver.resolve(raw_name)
                        if canonical_name.lower() in seen_names:
                            continue
                        seen_names.add(canonical_name.lower())

                        card_text = card.get_text()
                        emp_match = re.search(r"(\d+)\s*-\s*(\d+)\s+employees?", card_text, re.IGNORECASE)
                        employee_count = int(emp_match.group(2)) if emp_match else None

                        records.append(
                            StartupRecord(
                                source=SourceMeta(name="Y Combinator Directory", url=full_url),
                                content=StartupContent(entityName=canonical_name, employeeCount=employee_count)
                            )
                        )
                except Exception as exc:
                    logger.error("Error parsing YC startups", error=str(exc))

        logger.info(f"Successfully collected {len(records)} unique real startup records")
        return records[:limit]

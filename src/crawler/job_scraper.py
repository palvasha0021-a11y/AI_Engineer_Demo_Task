import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup
from src.crawler.base_crawler import BaseCrawler
from src.models.schemas import JobRecord, JobContent, SourceMeta
from src.utils.logger import logger
from src.utils.date_parser import parse_date, format_iso, is_within_last_24_hours
from src.entity_resolution.resolver import EntityResolver


class JobScraper(BaseCrawler):
    """Scraper for 5 distinct AI job boards enforcing 24-hour publication freshness."""

    JOB_SOURCES = [
        {"name": "RemoteOK AI", "url": "https://remoteok.com/remote-ai-jobs.rss"},
        {"name": "WeWorkRemotely AI", "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss"},
        {"name": "Jobspresso AI", "url": "https://jobspresso.co/category/remote-software-jobs/feed/"},
        {"name": "Remotive AI Jobs", "url": "https://remotive.com/api/remote-jobs?category=software-dev"},
        {"name": "NoDesk AI", "url": "https://nodesk.co/remote-jobs/engineering/index.xml"},
    ]

    def __init__(self, resolver: Optional[EntityResolver] = None, **kwargs):
        super().__init__(**kwargs)
        self.resolver = resolver or EntityResolver()

    def _infer_role_family(self, title: str) -> str:
        """Categorize job role family from title."""
        title_lower = title.lower()
        if "research" in title_lower or "scientist" in title_lower:
            return "Research & Science"
        elif "product" in title_lower or "pm" in title_lower:
            return "Product Management"
        elif "data" in title_lower or "analyst" in title_lower:
            return "Data & Analytics"
        elif "design" in title_lower or "ui" in title_lower:
            return "Design & UX"
        return "Engineering"

    async def scrape_jobs(self, limit: int = 1000, freshness_hours: int = 24) -> List[JobRecord]:
        """Scrape jobs across 5 job boards, keeping ONLY those published within last 24h."""
        records: List[JobRecord] = []

        for source in self.JOB_SOURCES:
            if len(records) >= limit:
                break

            logger.info(f"Crawling job board: {source['name']}", url=source['url'])

            # Remotive JSON API
            if "remotive.com" in source['url']:
                try:
                    async with aiohttp.ClientSession(headers=self.headers) as session:
                        async with session.get(source['url'], timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                jobs = data.get("jobs", [])
                                for j in jobs:
                                    if len(records) >= limit:
                                        break
                                    title = j.get("title", "")
                                    company = j.get("company_name", "AI Company")
                                    url = j.get("url", source['url'])
                                    date_raw = j.get("publication_date")

                                    parsed_dt = parse_date(date_raw, default_now=True)
                                    if not is_within_last_24_hours(parsed_dt, hours=freshness_hours):
                                        continue

                                    canonical_company = self.resolver.resolve(company)
                                    records.append(
                                        JobRecord(
                                            source=SourceMeta(name=source['name'], url=url),
                                            content=JobContent(
                                                company=canonical_company,
                                                date=format_iso(parsed_dt),
                                                is_remote=True,
                                                role_family=self._infer_role_family(title)
                                            )
                                        )
                                    )
                except Exception as exc:
                    logger.warning(f"Error fetching Remotive API", error=str(exc))
                continue

            # BeautifulSoup XML RSS parsing for robust HTML/XML handling
            xml_raw = await self.fetch(source['url'])
            if not xml_raw:
                continue

            try:
                soup = BeautifulSoup(xml_raw, "xml") or BeautifulSoup(xml_raw, "html.parser")
                items = soup.find_all("item") or soup.find_all("entry")

                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    date_elem = item.find("pubDate") or item.find("published") or item.find("updated")

                    title = title_elem.get_text().strip() if title_elem else ""
                    if link_elem:
                        url = link_elem.get_text().strip() if link_elem.get_text() else link_elem.get("href", source['url'])
                    else:
                        url = source['url']

                    date_raw = date_elem.get_text().strip() if date_elem else None
                    parsed_dt = parse_date(date_raw, default_now=True)

                    if not is_within_last_24_hours(parsed_dt, hours=freshness_hours):
                        continue

                    parts = re.split(r"\s+at\s+|\s+-\s+|\s+:\s+", title, flags=re.IGNORECASE)
                    company_raw = parts[1].strip() if len(parts) > 1 else "AI Tech Company"
                    company_canonical = self.resolver.resolve(company_raw)

                    records.append(
                        JobRecord(
                            source=SourceMeta(name=source['name'], url=url),
                            content=JobContent(
                                company=company_canonical,
                                date=format_iso(parsed_dt),
                                is_remote=True,
                                role_family=self._infer_role_family(title)
                            )
                        )
                    )
                    if len(records) >= limit:
                        break

            except Exception as exc:
                logger.error(f"Error parsing job feed {source['name']}", error=str(exc))

        logger.info(f"Successfully collected {len(records)} 24h-fresh job records")
        return records[:limit]

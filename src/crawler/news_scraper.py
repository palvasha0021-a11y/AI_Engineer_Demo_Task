import html
import re
from datetime import datetime, timezone
from typing import List, Optional
from bs4 import BeautifulSoup
from src.crawler.base_crawler import BaseCrawler
from src.models.schemas import NewsRecord, NewsContent, SourceMeta
from src.utils.logger import logger
from src.utils.date_parser import parse_date, format_iso, is_within_last_24_hours


class NewsScraper(BaseCrawler):
    """Scraper for 5 distinct AI news sources enforcing strict 24-hour publication freshness."""

    NEWS_SOURCES = [
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
        {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
        {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"},
        {"name": "HackerNews AI", "url": "https://news.ycombinator.com/rss"},
        {"name": "AI News Daily", "url": "https://www.artificialintelligence-news.com/feed/"},
    ]

    async def scrape_news(self, limit: int = 1000, freshness_hours: int = 24) -> List[NewsRecord]:
        """Scrape articles across 5 AI news sources, retaining ONLY articles published in last 24h."""
        records: List[NewsRecord] = []

        for source in self.NEWS_SOURCES:
            if len(records) >= limit:
                break

            logger.info(f"Crawling AI news source: {source['name']}", url=source['url'])
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
                    content_elem = item.find("encoded") or item.find("description") or item.find("summary")

                    title = title_elem.get_text().strip() if title_elem else ""
                    if link_elem:
                        url = link_elem.get_text().strip() if link_elem.get_text() else link_elem.get("href", source['url'])
                    else:
                        url = source['url']

                    date_raw = date_elem.get_text().strip() if date_elem else None
                    parsed_dt = parse_date(date_raw, default_now=True)

                    # 24-HOUR FRESHNESS FILTER
                    if not is_within_last_24_hours(parsed_dt, hours=freshness_hours):
                        logger.debug("Bypassing news article older than 24h", url=url, date=date_raw)
                        continue

                    raw_html = content_elem.get_text() if content_elem else title
                    content_soup = BeautifulSoup(raw_html, "html.parser")
                    full_text = content_soup.get_text(separator=" ").strip()

                    records.append(
                        NewsRecord(
                            source=SourceMeta(name=source['name'], url=url),
                            content=NewsContent(
                                title=title,
                                publication_date=format_iso(parsed_dt),
                                full_text=full_text[:2000]
                            )
                        )
                    )
                    if len(records) >= limit:
                        break

            except Exception as exc:
                logger.error(f"Error parsing news feed {source['name']}", error=str(exc))

        logger.info(f"Successfully collected {len(records)} 24h-fresh news records")
        return records[:limit]

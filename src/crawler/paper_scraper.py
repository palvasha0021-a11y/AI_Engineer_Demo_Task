import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Set, Dict, Any
import aiohttp
from src.crawler.base_crawler import BaseCrawler
from src.models.schemas import ResearchPaperRecord, ResearchPaperContent, SourceMeta
from src.config import settings
from src.utils.logger import logger
from src.utils.date_parser import parse_date, format_iso
from src.utils.fingerprint import normalize_url


class ResearchPaperScraper(BaseCrawler):
    """Real arXiv API Scraper and GitHub Repo & Star Enrichment Engine."""

    SEARCH_QUERIES = [
        "cat:cs.AI",
        "cat:cs.CL",
        "cat:cs.CV",
        "cat:cs.LG",
        'all:"large language models"',
        'all:"deep learning"',
        'all:"generative AI"'
    ]

    async def fetch_github_stars(self, repo_url: str) -> Optional[int]:
        """Fetch real-time GitHub stars directly from GitHub REST API."""
        if not repo_url or "github.com" not in repo_url:
            return None

        # Clean trailing slashes, .git extensions, and path fragments
        cleaned_url = re.sub(r"\.git$", "", repo_url.strip().rstrip("/"))
        match = re.search(r"github\.com/([^/#\?]+)/([^/#\?]+)", cleaned_url)
        if not match:
            return None

        owner, repo = match.group(1), match.group(2)
        # Avoid non-repository routes like GitHub organization pages or blog
        if owner.lower() in ("topics", "sponsors", "features", "pricing", "about", "blog"):
            return None

        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Intelligence-Pipeline/1.0"
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        stars = data.get("stargazers_count")
                        logger.info(f"Fetched real GitHub stars for {owner}/{repo}", stars=stars, repo_url=cleaned_url)
                        return stars
                    elif resp.status == 404:
                        logger.warning(f"GitHub repository not found (404)", repo=f"{owner}/{repo}")
                        return None
                    elif resp.status == 403:
                        logger.warning(f"GitHub API rate limit or forbidden (403)", repo=f"{owner}/{repo}")
                        return None
                    else:
                        logger.warning(f"GitHub API HTTP status {resp.status}", repo=f"{owner}/{repo}")
                        return None
        except Exception as exc:
            logger.warning(f"Failed fetching GitHub stars for {repo_url}", error=str(exc))
            return None

    def extract_github_url(self, text: str) -> Optional[str]:
        """Extract legitimate GitHub repository URL from text content."""
        if not text:
            return None

        pattern = r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
        matches = re.findall(pattern, text)
        for owner, repo in matches:
            repo_clean = repo.rstrip(".,;:)>]")
            owner_clean = owner.lstrip("(<[")
            if owner_clean.lower() not in ("topics", "sponsors", "features", "pricing", "about", "blog"):
                full_url = f"https://github.com/{owner_clean}/{repo_clean}"
                return full_url

        return None

    def parse_arxiv_entry(self, entry_elem: ET.Element, namespace: Dict[str, str]) -> Optional[ResearchPaperRecord]:
        """Parse a single Atom entry element from arXiv API."""
        id_elem = entry_elem.find("atom:id", namespace)
        raw_id_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
        if not raw_id_url:
            return None

        # Extract arXiv ID e.g. 2401.12345 or cs/0112017
        arxiv_id = raw_id_url.split("/abs/")[-1]
        paper_url = f"https://arxiv.org/abs/{arxiv_id}"

        title_elem = entry_elem.find("atom:title", namespace)
        title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"
        title = re.sub(r"\s+", " ", title).strip()

        authors = []
        for author in entry_elem.findall("atom:author", namespace):
            name_elem = author.find("atom:name", namespace)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        published_elem = entry_elem.find("atom:published", namespace)
        pub_date_str = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
        parsed_dt = parse_date(pub_date_str, default_now=True)

        summary_elem = entry_elem.find("atom:summary", namespace)
        summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""

        comment_elem = entry_elem.find("arxiv:comment", namespace)
        comment = comment_elem.text if comment_elem is not None and comment_elem.text else ""

        full_text_to_search = f"{summary} {comment}"
        github_url = self.extract_github_url(full_text_to_search)

        # Build initial record (github_stars populated async later)
        return ResearchPaperRecord(
            schemaVersion="1.0",
            recordType="RESEARCH_PAPER",
            content=ResearchPaperContent(
                title=title,
                authors=authors,
                paper_url=paper_url,
                github_url=github_url,
                github_stars=None,
                published_date=format_iso(parsed_dt)
            ),
            source=SourceMeta(
                name="arXiv",
                url=paper_url
            )
        )

    async def scrape_arxiv_papers(self, limit: int = 10, query_category: str = "cat:cs.AI") -> List[ResearchPaperRecord]:
        """Scrape real AI papers from official arXiv API query endpoint."""
        encoded_query = query_category.replace(" ", "%20")
        arxiv_url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&max_results={limit * 2}&sortBy=submittedDate&sortOrder=descending"

        logger.info(f"Executing live arXiv API fetch...", url=arxiv_url)
        xml_content = await self.fetch(arxiv_url)

        if not xml_content:
            logger.error("Failed to retrieve arXiv feed from API")
            return []

        records = []
        seen_ids: Set[str] = set()

        try:
            root = ET.fromstring(xml_content)
            namespace = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom"
            }

            entries = root.findall("atom:entry", namespace)
            logger.info(f"Retrieved {len(entries)} paper entries from arXiv API")

            for entry in entries:
                record = self.parse_arxiv_entry(entry, namespace)
                if not record:
                    continue

                paper_url = record.content.paper_url
                if paper_url in seen_ids:
                    logger.debug("Skipping duplicate arXiv paper", url=paper_url)
                    continue

                seen_ids.add(paper_url)

                # Enrich with real GitHub stars if a real GitHub URL was found
                if record.content.github_url:
                    stars = await self.fetch_github_stars(record.content.github_url)
                    record.content.github_stars = stars
                else:
                    record.content.github_url = None
                    record.content.github_stars = None

                records.append(record)
                if len(records) >= limit:
                    break

        except Exception as exc:
            logger.error("Error parsing arXiv XML feed", error=str(exc))

        logger.info(f"Successfully processed {len(records)} unique real arXiv papers")
        return records

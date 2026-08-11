import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
import asyncio
import json
import time
from pathlib import Path
from src.config import settings
from src.crawler.paper_scraper import ResearchPaperScraper
from src.crawler.startup_scraper import StartupScraper
from src.crawler.product_scraper import ProductScraper
from src.crawler.job_scraper import JobScraper
from src.crawler.news_scraper import NewsScraper
from src.entity_resolution.resolver import EntityResolver
from src.storage.sqlite_storage import SQLiteStorage
from src.storage.sheets_exporter import GoogleSheetsExporter
from src.utils.logger import logger


async def run_paper_pipeline(limit: int = 10):
    """Run real arXiv Research Paper & GitHub Enrichment Pipeline."""
    start_time = time.time()
    logger.info("================================================================")
    logger.info("STARTING REAL ARXIV RESEARCH PAPER + GITHUB ENRICHMENT PIPELINE")
    logger.info(f"Configuration: target_limit={limit} real papers")
    logger.info("================================================================")

    storage = SQLiteStorage(settings.DATABASE_PATH)
    paper_scraper = ResearchPaperScraper(concurrency=settings.CONCURRENCY_LIMIT)

    # Scrape real papers from live arXiv API
    papers = await paper_scraper.scrape_arxiv_papers(limit=limit)

    total_collected = len(papers)
    unique_papers = len({p.content.paper_url for p in papers})
    with_github = sum(1 for p in papers if p.content.github_url is not None)
    without_github = total_collected - with_github

    # Save to SQLite Storage
    storage.save_records("RESEARCH_PAPER", papers)

    # Export to JSON file at data/research_papers.json (Requirement 14)
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "research_papers.json"

    paper_dicts = [p.model_dump() for p in papers]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(paper_dicts, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {total_collected} real paper records to {json_path}")

    # Export to CSV via GoogleSheetsExporter (data/3_research_papers.csv)
    exporter = GoogleSheetsExporter(settings.OUTPUT_DIR)
    all_data = storage.get_all_records()
    exported_files = exporter.export_all(all_data)

    duration = round(time.time() - start_time, 2)

    logger.info("================================================================")
    logger.info("REAL ARXIV RESEARCH PAPER PIPELINE EXECUTION SUMMARY")
    logger.info(f"Execution Duration:            {duration}s")
    logger.info(f"Total Papers Collected:        {total_collected}")
    logger.info(f"Unique Papers:                 {unique_papers}")
    logger.info(f"Papers with GitHub Repos:      {with_github}")
    logger.info(f"Papers without GitHub Repos:   {without_github}")
    logger.info("Local Output Files:")
    logger.info(f" - JSON Output: {json_path}")
    logger.info(f" - CSV Output:  {exported_files.get('Research Papers', 'data/output/3_research_papers.csv')}")
    logger.info("================================================================")

    # Return summary dict for display
    return {
        "duration": duration,
        "total_collected": total_collected,
        "unique_papers": unique_papers,
        "with_github": with_github,
        "without_github": without_github,
        "json_path": str(json_path),
        "csv_path": exported_files.get("Research Papers", "data/output/3_research_papers.csv"),
        "papers": papers
    }


async def run_full_pipeline(limit: int = settings.DEFAULT_RECORD_LIMIT, freshness_hours: int = settings.FRESHNESS_HOURS):
    """Run full pipeline across all 5 entity types."""
    start_time = time.time()
    logger.info("Starting Full Pipeline Execution across 5 entity types...")

    resolver = EntityResolver()
    storage = SQLiteStorage(settings.DATABASE_PATH)
    exporter = GoogleSheetsExporter(settings.OUTPUT_DIR)

    paper_scraper = ResearchPaperScraper(concurrency=settings.CONCURRENCY_LIMIT)
    startup_scraper = StartupScraper(resolver=resolver, concurrency=settings.CONCURRENCY_LIMIT)
    product_scraper = ProductScraper(resolver=resolver, concurrency=settings.CONCURRENCY_LIMIT)
    job_scraper = JobScraper(resolver=resolver, concurrency=settings.CONCURRENCY_LIMIT)
    news_scraper = NewsScraper(concurrency=settings.CONCURRENCY_LIMIT)

    results = await asyncio.gather(
        paper_scraper.scrape_arxiv_papers(limit=limit),
        startup_scraper.scrape_yc_startups(limit=limit),
        product_scraper.scrape_products(limit=limit),
        job_scraper.scrape_jobs(limit=limit, freshness_hours=freshness_hours),
        news_scraper.scrape_news(limit=limit, freshness_hours=freshness_hours),
        return_exceptions=True
    )

    papers = results[0] if not isinstance(results[0], Exception) else []
    startups = results[1] if not isinstance(results[1], Exception) else []
    products = results[2] if not isinstance(results[2], Exception) else []
    jobs = results[3] if not isinstance(results[3], Exception) else []
    news = results[4] if not isinstance(results[4], Exception) else []

    storage.save_records("RESEARCH_PAPER", papers)
    storage.save_records("STARTUP", startups)
    storage.save_records("PRODUCT", products)
    storage.save_records("JOB", jobs)
    storage.save_records("NEWS", news)

    resolution_logs = resolver.get_logs()
    storage.save_resolution_logs(resolution_logs)

    all_data = storage.get_all_records()
    exporter.export_all(all_data)


def main():
    parser = argparse.ArgumentParser(description="AI Intelligence Data Ingestion & Enrichment Pipeline")
    parser.add_argument("--source", type=str, default="all", choices=["all", "papers"], help="Target pipeline source module (papers or all)")
    parser.add_argument("--limit", type=int, default=settings.DEFAULT_RECORD_LIMIT, help="Record limit")
    parser.add_argument("--freshness", type=int, default=settings.FRESHNESS_HOURS, help="Freshness window in hours")
    args = parser.parse_args()

    if args.source == "papers":
        asyncio.run(run_paper_pipeline(limit=args.limit))
    else:
        asyncio.run(run_full_pipeline(limit=args.limit, freshness_hours=args.freshness))


if __name__ == "__main__":
    main()

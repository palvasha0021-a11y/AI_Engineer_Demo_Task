import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from src.config import settings
from src.utils.logger import logger

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


class GoogleSheetsExporter:
    """Exporter producing CSV files locally and publishing to 6 Google Sheets tabs."""

    def __init__(self, output_dir: str = settings.OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, data: Dict[str, List[Any]]) -> Dict[str, str]:
        """Export all 6 tabs to CSV files locally and attempt Google Sheets API sync."""
        exported_files = {}

        # 1. Export Startups
        startups_file = self.output_dir / "1_startups.csv"
        self._write_csv(
            startups_file,
            ["Entity Name", "Employee Count", "Source Name", "Source URL", "Collected At"],
            [
                [
                    item.get("content", {}).get("entityName", ""),
                    item.get("content", {}).get("employeeCount", ""),
                    item.get("source", {}).get("name", ""),
                    item.get("source", {}).get("url", ""),
                    item.get("collectedAt", "")
                ]
                for item in data.get("STARTUP", [])
            ]
        )
        exported_files["Startups"] = str(startups_file)

        # 2. Export Products
        products_file = self.output_dir / "2_products.csv"
        self._write_csv(
            products_file,
            ["Startup Name", "Pricing Model", "Source Name", "Source URL", "Collected At"],
            [
                [
                    item.get("content", {}).get("startupName", ""),
                    item.get("content", {}).get("pricingModel", ""),
                    item.get("source", {}).get("name", ""),
                    item.get("source", {}).get("url", ""),
                    item.get("collectedAt", "")
                ]
                for item in data.get("PRODUCT", [])
            ]
        )
        exported_files["Products"] = str(products_file)

        # 3. Export Research Papers
        papers_file = self.output_dir / "3_research_papers.csv"
        self._write_csv(
            papers_file,
            ["Title", "Authors", "Paper URL", "GitHub URL", "GitHub Stars", "Published Date"],
            [
                [
                    item.get("content", {}).get("title", ""),
                    ", ".join(item.get("content", {}).get("authors", [])),
                    item.get("content", {}).get("paper_url", ""),
                    item.get("content", {}).get("github_url", "") or "",
                    item.get("content", {}).get("github_stars", 0),
                    item.get("content", {}).get("published_date", "")
                ]
                for item in data.get("RESEARCH_PAPER", [])
            ]
        )
        exported_files["Research Papers"] = str(papers_file)

        # 4. Export Jobs
        jobs_file = self.output_dir / "4_jobs.csv"
        self._write_csv(
            jobs_file,
            ["Company", "Date", "Is Remote", "Role Family", "Source Name", "Source URL"],
            [
                [
                    item.get("content", {}).get("company", ""),
                    item.get("content", {}).get("date", ""),
                    item.get("content", {}).get("is_remote", True),
                    item.get("content", {}).get("role_family", ""),
                    item.get("source", {}).get("name", ""),
                    item.get("source", {}).get("url", "")
                ]
                for item in data.get("JOB", [])
            ]
        )
        exported_files["Jobs"] = str(jobs_file)

        # 5. Export News
        news_file = self.output_dir / "5_news.csv"
        self._write_csv(
            news_file,
            ["Title", "Source Name", "URL", "Publication Date", "Text Snippet"],
            [
                [
                    item.get("content", {}).get("title", ""),
                    item.get("source", {}).get("name", ""),
                    item.get("source", {}).get("url", ""),
                    item.get("content", {}).get("publication_date", ""),
                    (item.get("content", {}).get("full_text", "") or "")[:200]
                ]
                for item in data.get("NEWS", [])
            ]
        )
        exported_files["News"] = str(news_file)

        # 6. Export Entity Mapping Log
        mapping_file = self.output_dir / "6_entity_mapping_log.csv"
        self._write_csv(
            mapping_file,
            ["Raw Name", "Canonical Name", "Match Method"],
            [
                [
                    item.get("raw_name", ""),
                    item.get("canonical_name", ""),
                    item.get("match_method", "")
                ]
                for item in data.get("RESOLUTION_LOG", [])
            ]
        )
        exported_files["Entity Mapping Log"] = str(mapping_file)

        logger.info("Successfully exported 6 local CSV files", output_dir=str(self.output_dir))

        # 7. Attempt Google Sheets API Export
        self.sync_to_google_sheets(exported_files)

        return exported_files

    def _write_csv(self, filepath: Path, headers: List[str], rows: List[List[Any]]):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    def sync_to_google_sheets(self, exported_files: Dict[str, str]):
        """Sync CSV data to Google Sheets API if service credentials and SHEET_ID are set."""
        creds_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        sheet_id = settings.GOOGLE_SHEET_ID

        if not GOOGLE_SHEETS_AVAILABLE or not os.path.exists(creds_file) or not sheet_id:
            logger.info(
                "Google Sheets sync bypassed (Credentials or SHEET_ID not configured). "
                "Local CSV output files are ready in data/output/"
            )
            return

        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = service_account.Credentials.from_service_account_file(creds_file, scopes=scopes)
            service = build("sheets", "4", credentials=creds)

            for tab_name, csv_path in exported_files.items():
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    values = list(reader)

                body = {"values": values}
                range_name = f"'{tab_name}'!A1"
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body=body
                ).execute()

            logger.info("Successfully synced all 6 tabs to Google Sheets API", sheet_id=sheet_id)

        except Exception as exc:
            logger.error("Failed Google Sheets API sync", error=str(exc))

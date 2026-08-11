import xml.etree.ElementTree as ET
import pytest
from src.crawler.paper_scraper import ResearchPaperScraper
from src.models.schemas import ResearchPaperRecord, ResearchPaperContent, SourceMeta


SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <published>2024-01-20T18:00:00Z</published>
    <updated>2024-01-21T10:00:00Z</updated>
    <title>Generative AI for Autonomous Agents</title>
    <summary>This paper introduces a novel framework. Code is available at https://github.com/huggingface/transformers.</summary>
    <author>
      <name>Alice Smith</name>
    </author>
    <author>
      <name>Bob Jones</name>
    </author>
    <arxiv:comment>Accepted to NeurIPS 2024</arxiv:comment>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.67890v1</id>
    <published>2024-01-22T14:30:00Z</published>
    <title>Pure Theoretical Deep Learning Bounds</title>
    <summary>We prove fundamental bounds on neural network capacity without code implementations.</summary>
    <author>
      <name>Charlie Brown</name>
    </author>
  </entry>
</feed>
"""


def test_arxiv_xml_entry_parsing():
    scraper = ResearchPaperScraper()
    root = ET.fromstring(SAMPLE_ARXIV_XML)
    namespace = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entries = root.findall("atom:entry", namespace)
    assert len(entries) == 2

    # Test Paper 1 (Has GitHub Repo)
    record1 = scraper.parse_arxiv_entry(entries[0], namespace)
    assert record1 is not None
    assert record1.content.title == "Generative AI for Autonomous Agents"
    assert record1.content.authors == ["Alice Smith", "Bob Jones"]
    assert record1.content.paper_url == "https://arxiv.org/abs/2401.12345v1"
    assert record1.content.github_url == "https://github.com/huggingface/transformers"
    assert record1.source.name == "arXiv"
    assert record1.source.url == "https://arxiv.org/abs/2401.12345v1"

    # Test Paper 2 (No GitHub Repo)
    record2 = scraper.parse_arxiv_entry(entries[1], namespace)
    assert record2 is not None
    assert record2.content.title == "Pure Theoretical Deep Learning Bounds"
    assert record2.content.authors == ["Charlie Brown"]
    assert record2.content.paper_url == "https://arxiv.org/abs/2401.67890v1"
    assert record2.content.github_url is None
    assert record2.content.github_stars is None


def test_github_url_extraction_regex():
    scraper = ResearchPaperScraper()

    # Valid GitHub links
    text1 = "Official implementation: https://github.com/openai/whisper. Check out repo."
    assert scraper.extract_github_url(text1) == "https://github.com/openai/whisper"

    # Invalid / Missing GitHub links
    text2 = "We present a deep learning model. No code released."
    assert scraper.extract_github_url(text2) is None


def test_missing_github_repo_handling_schema():
    content = ResearchPaperContent(
        title="Theoretical Bounds",
        authors=["Author One"],
        paper_url="https://arxiv.org/abs/2401.00000",
        github_url=None,
        github_stars=None,
        published_date="2024-01-01T00:00:00Z"
    )

    record = ResearchPaperRecord(
        schemaVersion="1.0",
        recordType="RESEARCH_PAPER",
        content=content,
        source=SourceMeta(name="arXiv", url="https://arxiv.org/abs/2401.00000")
    )

    assert record.content.github_url is None
    assert record.content.github_stars is None
    assert record.recordType == "RESEARCH_PAPER"
    assert record.source.name == "arXiv"


def test_duplicate_arxiv_id_prevention():
    scraper = ResearchPaperScraper()
    root = ET.fromstring(SAMPLE_ARXIV_XML)
    namespace = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    entries = root.findall("atom:entry", namespace)
    rec1 = scraper.parse_arxiv_entry(entries[0], namespace)
    rec2 = scraper.parse_arxiv_entry(entries[0], namespace)  # Duplicate entry

    seen_urls = set()
    records = []

    for r in [rec1, rec2]:
        if r.content.paper_url not in seen_urls:
            seen_urls.add(r.content.paper_url)
            records.append(r)

    assert len(records) == 1

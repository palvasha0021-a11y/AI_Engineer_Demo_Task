import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    pdf_path = "architecture.pdf"
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=3
    )

    story = []

    # Title Banner
    story.append(Paragraph("AI Intelligence Data Ingestion & Enrichment Pipeline", title_style))
    story.append(Paragraph("System Architecture Blueprint (Designed for 500,000+ Record Horizontal Scale)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    # Section 1: Executive Summary & High-Level Architecture
    story.append(Paragraph("1. Executive Summary & Core System Architecture", h2_style))
    story.append(Paragraph(
        "The AI Intelligence Data Ingestion & Enrichment Pipeline is a high-throughput, fault-tolerant asynchronous system "
        "designed to collect, validate, enrich, and deduplicate AI ecosystem intelligence. The system strictly operates on a "
        "zero-hallucination policy—all data points trace directly to verified source URLs (arXiv, Y Combinator, Product Hunt, "
        "Job Boards, and AI News feeds). Unverified fields default to null/empty values.",
        body_style
    ))

    # Architectural Overview Table
    arch_data = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Technology Stack</b>", body_style), Paragraph("<b>Role / Functionality</b>", body_style)],
        [Paragraph("Async Crawling", body_style), Paragraph("Python asyncio + aiohttp", body_style), Paragraph("Non-blocking network IO with bounded semaphore concurrency.", body_style)],
        [Paragraph("Browser Automation", body_style), Paragraph("Playwright Async", body_style), Paragraph("Headless Chromium fallback for JS-heavy anti-bot targets.", body_style)],
        [Paragraph("LLM Failover Chain", body_style), Paragraph("Gemini Flash → Groq → DeepSeek", body_style), Paragraph("Multi-tier LLM fallback for structured JSON extraction.", body_style)],
        [Paragraph("Data Storage", body_style), Paragraph("SQLite / PostgreSQL + CSV", body_style), Paragraph("Local checkpointing and 6-tab Google Sheets exporting.", body_style)],
    ]
    t = Table(arch_data, colWidths=[110, 150, 270])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Section 2: 500,000+ Record Scaling Strategy
    story.append(Paragraph("2. Scaling Architecture for 500,000+ Records", h2_style))
    story.append(Paragraph("• <b>Distributed Queue Model:</b> Decouples URL scraping from LLM extraction using Kafka / Redis queues.", bullet_style))
    story.append(Paragraph("• <b>Streaming Batch Processing:</b> Records are processed in bounded memory chunks (e.g. 500 items/batch) to prevent OOM errors.", bullet_style))
    story.append(Paragraph("• <b>Distributed Lock Manager:</b> Redis Redlock ensures multiple crawler workers never process the same URL.", bullet_style))
    story.append(Paragraph("• <b>Database Partitioning:</b> PostgreSQL declarative table partitioning by record_type and monthly range.", bullet_style))

    # Section 3 & 4: 413 & 429 Handling
    story.append(Paragraph("3. 413 Payload & 429 Rate Limit Resilience", h2_style))
    story.append(Paragraph("• <b>HTML Cleaning & Chunking (413):</b> BeautifulSoup strips &lt;script&gt;, &lt;style&gt;, &lt;nav&gt;, &lt;header&gt;, &lt;footer&gt;. Documents &gt;4,000 chars are semantically chunked before calling LLMs.", bullet_style))
    story.append(Paragraph("• <b>Exponential Backoff & Jitter (429):</b> Backoff delay calculated as factor^attempt + jitter, dynamically honoring HTTP Retry-After headers.", bullet_style))
    story.append(Paragraph("• <b>Tiered Provider Failover:</b> If Gemini (Tier 1) hits rate limits or fails, execution automatically transfers to Groq Llama (Tier 2), then DeepSeek (Tier 3).", bullet_style))

    story.append(PageBreak())

    # Page 2
    story.append(Paragraph("4. Freshness & Distributed Deduplication Strategy", h2_style))
    story.append(Paragraph("• <b>24-Hour Publication Boundary:</b> All job postings and news articles pass through UTC datetime normalization. Records with publication timestamps &gt;24 hours old are strictly filtered out.", bullet_style))
    story.append(Paragraph("• <b>Canonical Fingerprinting:</b> Unique SHA-256 fingerprint generated from normalized URL, canonical entity name, and publication date:", body_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<i>Fingerprint = SHA256(NormalizedURL || CanonicalName || PubDate)</i>", bullet_style))
    story.append(Paragraph("• <b>Distributed Bloom Filter:</b> A global Redis Bloom filter enables O(1) duplicate URL checks across N concurrent crawler nodes.", bullet_style))

    # Section 5 & 6: Database & Storage Strategy
    story.append(Paragraph("5. Primary Database & Vector/Graph Storage Blueprint", h2_style))
    story.append(Paragraph("• <b>Primary Database (PostgreSQL):</b> Relational storage with JSONB payload indexing and GIN indexes for fast attribute searching.", bullet_style))
    story.append(Paragraph("• <b>Vector Search (PgVector / Qdrant):</b> Dense vector embeddings (text-embedding-004) stored for paper abstracts and news articles to power semantic search and topic clustering.", bullet_style))
    story.append(Paragraph("• <b>Graph Storage (Neo4j):</b> Graph relations modeled across entities:", body_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<b>(STARTUP) -[:LAUNCHED]-&gt; (PRODUCT)</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<b>(STARTUP) -[:POSTED]-&gt; (JOB)</b>", bullet_style))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;<b>(RESEARCH_PAPER) -[:HAS_REPO]-&gt; (GITHUB_REPO)</b>", bullet_style))

    # Section 7: Entity Resolution Architecture
    story.append(Paragraph("6. Deterministic Entity Resolution Engine", h2_style))
    story.append(Paragraph(
        "Entity resolution maps raw company strings (e.g. 'Open AI, Inc.', 'Open AI') to canonical entities ('OpenAI') using "
        "a multi-stage deterministic pipeline:",
        body_style
    ))
    story.append(Paragraph("1. Lowercasing and strip punctuation & whitespace.", bullet_style))
    story.append(Paragraph("2. Strip common corporate legal designators (Inc, LLC, Corp, Ltd, GmbH, Co, PBC).", bullet_style))
    story.append(Paragraph("3. Exact and tight-whitespace match against a 50-item seed AI startup database.", bullet_style))
    story.append(Paragraph("4. Audit log written to <i>6_entity_mapping_log.csv</i>.", bullet_style))

    story.append(Spacer(1, 10))

    # Section 8: Google Sheets & Export Pipeline
    story.append(Paragraph("7. Output & Export Pipeline (6 Google Sheets Tabs)", h2_style))

    tabs_data = [
        [Paragraph("<b>Tab Number</b>", body_style), Paragraph("<b>Tab Name</b>", body_style), Paragraph("<b>Schema Summary</b>", body_style)],
        [Paragraph("Tab 1", body_style), Paragraph("Startups", body_style), Paragraph("Entity Name, Employee Count, Source Name, Source URL, Collected At", body_style)],
        [Paragraph("Tab 2", body_style), Paragraph("Products", body_style), Paragraph("Startup Name, Pricing Model (FREE|FREEMIUM|PAID|ENTERPRISE), Source URL", body_style)],
        [Paragraph("Tab 3", body_style), Paragraph("Research Papers", body_style), Paragraph("Title, Authors, Paper URL, GitHub URL, GitHub Stars, Published Date", body_style)],
        [Paragraph("Tab 4", body_style), Paragraph("Jobs", body_style), Paragraph("Company, Date, Is Remote, Role Family, Source Name, Source URL", body_style)],
        [Paragraph("Tab 5", body_style), Paragraph("News", body_style), Paragraph("Title, Source Name, URL, Publication Date, Text Snippet", body_style)],
        [Paragraph("Tab 6", body_style), Paragraph("Entity Mapping Log", body_style), Paragraph("Raw Name, Canonical Name, Match Method", body_style)],
    ]
    t2 = Table(tabs_data, colWidths=[70, 120, 340])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)

    story.append(PageBreak())

    # Page 3
    story.append(Paragraph("8. Data Verification & Quality Control Summary", h2_style))
    story.append(Paragraph("The pipeline enforces strict automated quality gates prior to export:", body_style))

    qc_data = [
        [Paragraph("<b>Check Category</b>", body_style), Paragraph("<b>Enforcement Mechanism</b>", body_style), Paragraph("<b>Action on Violation</b>", body_style)],
        [Paragraph("Source Traceability", body_style), Paragraph("Mandatory source.url check on every Pydantic record", body_style), Paragraph("Reject record immediately.", body_style)],
        [Paragraph("No Hallucinations", body_style), Paragraph("GitHub stars fetched live via GitHub REST API; no LLM estimation", body_style), Paragraph("Set github_stars = null.", body_style)],
        [Paragraph("Freshness Filter", body_style), Paragraph("UTC cutoff check: (now - pub_date) <= 24 hours", body_style), Paragraph("Discard stale job/news record.", body_style)],
        [Paragraph("Schema Integrity", body_style), Paragraph("Pydantic v2 strict type and enum validation", body_style), Paragraph("Log validation error & failover.", body_style)],
    ]
    t3 = Table(qc_data, colWidths=[120, 230, 180])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)

    story.append(Spacer(1, 15))
    story.append(Paragraph("9. Production Deployment Blueprint", h2_style))
    story.append(Paragraph("• <b>Containerization:</b> Packaged into a lightweight Docker container with Python 3.11-slim and headless Chromium.", bullet_style))
    story.append(Paragraph("• <b>Orchestration:</b> Deployed as Kubernetes CronJobs / Celery Distributed Workers for scheduled ingestion runs.", bullet_style))
    story.append(Paragraph("• <b>Observability:</b> Structured JSON logging with Datadog / Grafana Loki integration tracking fetch durations, HTTP status codes, LLM failovers, and entity resolution rates.", bullet_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10))
    story.append(Paragraph("<i>AI Intelligence Data Ingestion and Enrichment Pipeline — Production Architecture Blueprint</i>", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#718096"), alignment=1)))

    doc.build(story)
    print(f"Successfully generated {pdf_path}")

if __name__ == "__main__":
    generate_pdf()

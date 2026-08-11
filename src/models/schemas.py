from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str
    url: str


# 1. RESEARCH PAPER SCHEMA
class ResearchPaperContent(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    paper_url: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    published_date: str


class ResearchPaperRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "RESEARCH_PAPER"
    content: ResearchPaperContent
    source: SourceMeta
    collectedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 2. STARTUP SCHEMA
class StartupContent(BaseModel):
    entityName: str
    employeeCount: Optional[int] = None


class StartupRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "STARTUP"
    source: SourceMeta
    content: StartupContent
    collectedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 3. PRODUCT SCHEMA
class ProductContent(BaseModel):
    startupName: str
    pricingModel: Optional[PricingModel] = None


class ProductRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "PRODUCT"
    source: SourceMeta
    content: ProductContent
    collectedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 4. JOB SCHEMA
class JobContent(BaseModel):
    company: str
    date: str
    is_remote: bool = True
    role_family: str = "Engineering"


class JobRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "JOB"
    source: SourceMeta
    content: JobContent
    collectedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 5. NEWS SCHEMA
class NewsContent(BaseModel):
    title: str
    publication_date: str
    full_text: str


class NewsRecord(BaseModel):
    schemaVersion: str = "1.0"
    recordType: str = "NEWS"
    source: SourceMeta
    content: NewsContent
    collectedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 6. ENTITY RESOLUTION LOG SCHEMA
class EntityResolutionLog(BaseModel):
    raw_name: str
    canonical_name: str
    match_method: str

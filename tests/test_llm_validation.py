import pytest
from pydantic import ValidationError
from src.models.schemas import ResearchPaperRecord, ResearchPaperContent, PricingModel, ProductContent, SourceMeta


def test_research_paper_schema_validation():
    valid_data = {
        "schemaVersion": "1.0",
        "recordType": "RESEARCH_PAPER",
        "content": {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani et al."],
            "paper_url": "https://arxiv.org/abs/1706.03762",
            "github_url": "https://github.com/tensorflow/tensor2tensor",
            "github_stars": 12500,
            "published_date": "2017-06-12T00:00:00Z"
        },
        "source": {
            "name": "arXiv",
            "url": "https://arxiv.org/abs/1706.03762"
        }
    }
    record = ResearchPaperRecord.model_validate(valid_data)
    assert record.content.title == "Attention Is All You Need"
    assert record.content.github_stars == 12500
    assert record.source.name == "arXiv"


def test_product_schema_enum_rejection():
    invalid_data = {
        "startupName": "OpenAI",
        "pricingModel": "INVALID_PRICING_MODEL"
    }
    with pytest.raises(ValidationError):
        ProductContent.model_validate(invalid_data)

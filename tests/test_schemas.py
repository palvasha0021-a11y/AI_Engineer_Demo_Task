from src.models.schemas import (
    StartupRecord,
    StartupContent,
    ProductRecord,
    ProductContent,
    JobRecord,
    JobContent,
    NewsRecord,
    NewsContent,
    SourceMeta,
    PricingModel,
)


def test_all_entity_schemas_instantiation():
    source = SourceMeta(name="Test Source", url="https://example.com")

    startup = StartupRecord(
        source=source,
        content=StartupContent(entityName="OpenAI", employeeCount=1500)
    )
    assert startup.recordType == "STARTUP"
    assert startup.content.employeeCount == 1500

    product = ProductRecord(
        source=source,
        content=ProductContent(startupName="OpenAI", pricingModel=PricingModel.FREEMIUM)
    )
    assert product.recordType == "PRODUCT"
    assert product.content.pricingModel == PricingModel.FREEMIUM

    job = JobRecord(
        source=source,
        content=JobContent(company="OpenAI", date="2026-08-10T12:00:00Z", is_remote=True, role_family="Engineering")
    )
    assert job.recordType == "JOB"
    assert job.content.company == "OpenAI"

    news = NewsRecord(
        source=source,
        content=NewsContent(title="Breakthrough in AI", publication_date="2026-08-10T12:00:00Z", full_text="Content text")
    )
    assert news.recordType == "NEWS"
    assert news.content.title == "Breakthrough in AI"

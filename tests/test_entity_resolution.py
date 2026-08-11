from src.entity_resolution.resolver import EntityResolver


def test_entity_resolution_known_seed_variations():
    resolver = EntityResolver()

    assert resolver.resolve("Open AI, Inc.") == "OpenAI"
    assert resolver.resolve("Open AI") == "OpenAI"
    assert resolver.resolve("OpenAI Inc.") == "OpenAI"
    assert resolver.resolve("Anthropic, PBC") == "Anthropic"
    assert resolver.resolve("Mistral AI Lab") == "Mistral AI"
    assert resolver.resolve("Stability.AI LLC") == "Stability AI"


def test_entity_resolution_unseen_company_normalization():
    resolver = EntityResolver()

    resolved = resolver.resolve("ThinkingNode Technologies Corp.")
    assert resolved == "ThinkingNode"

    logs = resolver.get_logs()
    assert len(logs) == 1
    assert logs[0].raw_name == "ThinkingNode Technologies Corp."
    assert logs[0].canonical_name == "ThinkingNode"
    assert logs[0].match_method == "normalized"

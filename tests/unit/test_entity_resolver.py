import uuid

from knowledge_core.domain.entity import Entity
from knowledge_workers.ingestion.entity_resolver import EntityResolver


def _make_entity(
    name: str,
    entity_type: str = "company",
    properties: dict | None = None,
    source_count: int = 1,
) -> Entity:
    """Create a test entity with sensible defaults."""
    canonical = name.lower().strip()
    return Entity(
        id=uuid.uuid4(),
        name=name,
        canonical_name=canonical,
        type=entity_type,
        properties=properties or {},
        source_count=source_count,
    )


class TestCanonicalize:
    def test_lowercases_and_strips_whitespace(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("  Apple Inc  ") == "apple"

    def test_collapses_multiple_spaces(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("New   York   Times") == "new york times"

    def test_strips_inc_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Apple Inc") == "apple"

    def test_strips_inc_dot_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Apple Inc.") == "apple"

    def test_strips_llc_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Acme LLC") == "acme"

    def test_strips_ltd_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Barclays Ltd") == "barclays"

    def test_strips_corp_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Microsoft Corp") == "microsoft"

    def test_strips_corp_dot_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Microsoft Corp.") == "microsoft"

    def test_preserves_name_without_corporate_suffix(self):
        resolver = EntityResolver()
        assert resolver._canonicalize("Google") == "google"


class TestExactMatch:
    def test_finds_identical_entity(self):
        resolver = EntityResolver()
        existing = _make_entity("Apple", "company")
        match = resolver._find_exact_match("apple", "company", [existing])
        assert match is not None
        assert match.id == existing.id

    def test_returns_none_when_no_match(self):
        resolver = EntityResolver()
        existing = _make_entity("Apple", "company")
        match = resolver._find_exact_match("google", "company", [existing])
        assert match is None

    def test_returns_none_when_type_differs(self):
        resolver = EntityResolver()
        existing = _make_entity("Apple", "company")
        match = resolver._find_exact_match("apple", "fruit", [existing])
        assert match is None


class TestFuzzyMatch:
    def test_finds_similar_entity_above_threshold(self):
        resolver = EntityResolver()
        existing = _make_entity("Microsoft", "company")
        # "microsof" vs "microsoft" — very close
        match = resolver._find_fuzzy_match("microsof", "company", [existing])
        assert match is not None
        assert match.id == existing.id

    def test_returns_none_when_below_threshold(self):
        resolver = EntityResolver()
        existing = _make_entity("Apple", "company")
        # "xyz" vs "apple" — very different
        match = resolver._find_fuzzy_match("xyz", "company", [existing])
        assert match is None

    def test_returns_none_when_type_differs(self):
        resolver = EntityResolver()
        existing = _make_entity("Apple", "company")
        match = resolver._find_fuzzy_match("apple", "fruit", [existing])
        assert match is None


class TestResolve:
    def test_creates_new_entity_when_no_match(self):
        resolver = EntityResolver()
        new_entities = [{"name": "Google", "type": "company", "properties": {"sector": "tech"}}]
        resolved = resolver.resolve(new_entities, [])
        assert len(resolved) == 1
        assert resolved[0].name == "Google"
        assert resolved[0].type == "company"
        assert resolved[0].properties == {"sector": "tech"}

    def test_merges_properties_on_exact_match(self):
        resolver = EntityResolver()
        existing = _make_entity(
            "Apple",
            "company",
            properties={"sector": "tech"},
            source_count=1,
        )
        new_entities = [{"name": "Apple", "type": "company", "properties": {"revenue": 394}}]
        resolved = resolver.resolve(new_entities, [existing])
        assert len(resolved) == 1
        assert resolved[0].id == existing.id
        assert resolved[0].properties == {"sector": "tech", "revenue": 394}
        assert resolved[0].source_count == 2

    def test_resolves_multiple_entities_independently(self):
        resolver = EntityResolver()
        new_entities = [
            {"name": "Apple", "type": "company", "properties": {}},
            {"name": "Google", "type": "company", "properties": {}},
        ]
        resolved = resolver.resolve(new_entities, [])
        assert len(resolved) == 2
        assert resolved[0].name == "Apple"
        assert resolved[1].name == "Google"

    def test_subsequent_entities_match_against_newly_created(self):
        """The second 'Apple' should merge with the first, not create a duplicate."""
        resolver = EntityResolver()
        new_entities = [
            {"name": "Apple Inc", "type": "company", "properties": {"a": 1}},
            {"name": "Apple Inc.", "type": "company", "properties": {"b": 2}},
        ]
        resolved = resolver.resolve(new_entities, [])
        assert len(resolved) == 2
        # Second should merge with first (both canonicalize to "apple")
        assert resolved[1].properties == {"a": 1, "b": 2}
        assert resolved[1].source_count == 2

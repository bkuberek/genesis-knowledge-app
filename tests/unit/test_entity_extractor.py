from knowledge_workers.ingestion.entity_extractor import EntityExtractor


class TestParseExtractionResponse:
    def setup_method(self):
        """Create an extractor with a dummy LLM client for testing parse logic."""
        self._extractor = EntityExtractor(llm_client=None)  # type: ignore[arg-type]

    def test_parses_valid_json(self):
        response = '{"entities": [{"name": "Apple"}], "relationships": []}'
        result = self._extractor._parse_extraction_response(response)
        assert result["entities"] == [{"name": "Apple"}]
        assert result["relationships"] == []

    def test_parses_json_with_code_block_markers(self):
        response = '```json\n{"entities": [{"name": "Google"}], "relationships": []}\n```'
        result = self._extractor._parse_extraction_response(response)
        assert result["entities"] == [{"name": "Google"}]

    def test_returns_empty_for_invalid_json(self):
        response = "This is not JSON at all"
        result = self._extractor._parse_extraction_response(response)
        assert result == {"entities": [], "relationships": []}

    def test_returns_empty_for_partial_json(self):
        response = '{"entities": [{"name": "Incomplete"'
        result = self._extractor._parse_extraction_response(response)
        assert result == {"entities": [], "relationships": []}

    def test_handles_empty_string(self):
        result = self._extractor._parse_extraction_response("")
        assert result == {"entities": [], "relationships": []}

    def test_strips_leading_trailing_whitespace(self):
        response = '  \n  {"entities": [], "relationships": []}  \n  '
        result = self._extractor._parse_extraction_response(response)
        assert result == {"entities": [], "relationships": []}


class TestStripCodeBlockMarkers:
    def setup_method(self):
        self._extractor = EntityExtractor(llm_client=None)  # type: ignore[arg-type]

    def test_removes_json_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert self._extractor._strip_code_block_markers(text) == '{"key": "value"}'

    def test_removes_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        assert self._extractor._strip_code_block_markers(text) == '{"key": "value"}'

    def test_leaves_non_code_block_unchanged(self):
        text = '{"key": "value"}'
        assert self._extractor._strip_code_block_markers(text) == '{"key": "value"}'

import json
from typing import Any

from knowledge_core.ports.llm_port import LLMPort

EXTRACTION_PROMPT_TEMPLATE = """Analyze the following text and extract structured \
entities and relationships.

For each entity found, provide:
- name: the entity's name
- type: the category/type (e.g., "company", "person", "technology", "industry")
- properties: key-value pairs of attributes (use snake_case for keys, \
preserve numeric values as numbers)

For each relationship found, provide:
- source: name of the source entity
- target: name of the target entity
- relation_type: type of relationship (e.g., "operates_in", "founded_by", \
"competes_with")
- description: brief description
- confidence: 0.0 to 1.0

Context: {context}

Text to analyze:
{text}

Respond in JSON format:
{{
    "entities": [
        {{"name": "...", "type": "...", "properties": {{...}}}}
    ],
    "relationships": [
        {{"source": "...", "target": "...", "relation_type": "...", \
"description": "...", "confidence": 0.9}}
    ]
}}

IMPORTANT: Return ONLY valid JSON, no markdown formatting."""

EMPTY_EXTRACTION: dict[str, Any] = {"entities": [], "relationships": []}

MAX_EXTRACTION_TOKENS = 16384


class EntityExtractor:
    """Extracts entities and relationships from text using an LLM."""

    def __init__(self, llm_client: LLMPort) -> None:
        self._llm = llm_client

    async def extract(
        self,
        text: str,
        document_context: str = "",
    ) -> dict[str, Any]:
        """Extract entities and relationships from text using LLM.

        Uses the extraction model when available, with a larger token
        limit than the default to handle full document content.
        """
        prompt = self._build_extraction_prompt(text, document_context)
        model = self._get_extraction_model()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
            max_tokens=MAX_EXTRACTION_TOKENS,
        )
        return self._parse_extraction_response(response)

    def _get_extraction_model(self) -> str | None:
        """Get the extraction model if the LLM client exposes it."""
        return getattr(self._llm, "extraction_model", None)

    def _build_extraction_prompt(self, text: str, context: str) -> str:
        """Build the extraction prompt with text and context."""
        return EXTRACTION_PROMPT_TEMPLATE.format(text=text, context=context)

    def _parse_extraction_response(
        self,
        response: str,
    ) -> dict[str, Any]:
        """Parse LLM response into structured entity/relationship data."""
        cleaned = self._strip_code_block_markers(response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return EMPTY_EXTRACTION

    def _strip_code_block_markers(self, text: str) -> str:
        """Remove markdown code block markers if present."""
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.split("\n")
        return "\n".join(lines[1:-1])

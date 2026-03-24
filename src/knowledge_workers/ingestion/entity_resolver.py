import re
import uuid
from difflib import SequenceMatcher
from typing import Any

from knowledge_core.domain.entity import Entity

SIMILARITY_THRESHOLD = 0.85

CORPORATE_SUFFIXES = (
    " inc",
    " inc.",
    " llc",
    " ltd",
    " corp",
    " corp.",
)


class EntityResolver:
    """Resolves new entities against existing ones using multi-layer matching."""

    def resolve(
        self,
        new_entities: list[dict[str, Any]],
        existing_entities: list[Entity],
    ) -> list[Entity]:
        """Resolve new entities against existing ones, merging duplicates."""
        resolved: list[Entity] = []
        working_entities = list(existing_entities)

        for raw_entity in new_entities:
            canonical = self._canonicalize(raw_entity["name"])
            entity_type = raw_entity.get("type", "unknown")
            properties = raw_entity.get("properties", {})

            match = self._find_match(canonical, entity_type, working_entities)

            if match is not None:
                merged = self._merge_entity(match, properties)
                resolved.append(merged)
                working_entities = [
                    merged if entity.id == match.id else entity for entity in working_entities
                ]
            else:
                new_entity = Entity(
                    id=uuid.uuid4(),
                    name=raw_entity["name"],
                    canonical_name=canonical,
                    type=entity_type,
                    properties=properties,
                )
                resolved.append(new_entity)
                working_entities.append(new_entity)

        return resolved

    def _find_match(
        self,
        canonical: str,
        entity_type: str,
        entities: list[Entity],
    ) -> Entity | None:
        """Find a matching entity using exact then fuzzy matching."""
        exact = self._find_exact_match(canonical, entity_type, entities)
        if exact is not None:
            return exact
        return self._find_fuzzy_match(canonical, entity_type, entities)

    def _canonicalize(self, name: str) -> str:
        """Normalize entity name for matching."""
        normalized = name.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)
        for suffix in CORPORATE_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return normalized.strip()

    def _find_exact_match(
        self,
        canonical: str,
        entity_type: str,
        entities: list[Entity],
    ) -> Entity | None:
        """Find an entity with an identical canonical name and type."""
        for entity in entities:
            if entity.canonical_name == canonical and entity.type == entity_type:
                return entity
        return None

    def _find_fuzzy_match(
        self,
        canonical: str,
        entity_type: str,
        entities: list[Entity],
    ) -> Entity | None:
        """Find the best fuzzy match above the similarity threshold."""
        best_match = None
        best_score = 0.0
        for entity in entities:
            if entity.type != entity_type:
                continue
            score = SequenceMatcher(
                None,
                canonical,
                entity.canonical_name,
            ).ratio()
            if score >= SIMILARITY_THRESHOLD and score > best_score:
                best_match = entity
                best_score = score
        return best_match

    def _merge_entity(
        self,
        existing: Entity,
        new_properties: dict[str, Any],
    ) -> Entity:
        """Merge new properties into an existing entity."""
        merged_properties = {**existing.properties, **new_properties}
        return existing.model_copy(
            update={
                "properties": merged_properties,
                "source_count": existing.source_count + 1,
            }
        )

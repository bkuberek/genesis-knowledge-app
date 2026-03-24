"""PostgreSQL implementation of DatabaseRepositoryPort."""

import uuid
from typing import Any

from sqlalchemy import Float, String, and_, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_core.domain.chat_message import ChatMessage, MessageRole
from knowledge_core.domain.chat_session import ChatSession
from knowledge_core.domain.document import (
    Document,
    DocumentStatus,
    SourceType,
    Visibility,
)
from knowledge_core.domain.entity import Entity
from knowledge_core.domain.relationship import Relationship
from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_workers.adapters.models.chat_message_model import (
    ChatMessageModel,
)
from knowledge_workers.adapters.models.chat_session_model import (
    ChatSessionModel,
)
from knowledge_workers.adapters.models.document_model import DocumentModel
from knowledge_workers.adapters.models.entity_document_model import (
    EntityDocumentModel,
)
from knowledge_workers.adapters.models.entity_model import EntityModel
from knowledge_workers.adapters.models.relationship_model import (
    RelationshipModel,
)

ALLOWED_FILTER_OPERATORS = frozenset({"=", "!=", ">", "<", ">=", "<=", "contains", "like"})
ALLOWED_AGGREGATE_OPERATIONS = frozenset({"count", "avg", "sum", "min", "max"})

MAX_SAMPLE_VALUES = 10


def _is_numeric_string(value: str) -> bool:
    """Check if a string represents a numeric value."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _describe_property(value: Any) -> dict[str, Any]:
    """Build an initial property descriptor from a sample value."""
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, float):
        return {"type": "float", "min": value, "max": value}
    if isinstance(value, int):
        return {"type": "int", "min": value, "max": value}
    if isinstance(value, str):
        return {"type": "str", "samples": [value]}
    return {"type": type(value).__name__}


def _update_numeric_range(descriptor: dict[str, Any], value: int | float) -> None:
    """Widen the min/max range of a numeric property descriptor."""
    if "min" in descriptor:
        descriptor["min"] = min(descriptor["min"], value)
    if "max" in descriptor:
        descriptor["max"] = max(descriptor["max"], value)


def _collect_sample_value(descriptor: dict[str, Any], value: str) -> None:
    """Add a distinct sample value to a string property descriptor (up to MAX_SAMPLE_VALUES)."""
    samples = descriptor.get("samples")
    if samples is None:
        return
    if len(samples) >= MAX_SAMPLE_VALUES:
        return
    if value not in samples:
        samples.append(value)


class DatabaseRepository(DatabaseRepositoryPort):
    """PostgreSQL repository using SQLAlchemy async sessions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    # -- Domain ↔ Model converters --

    def _document_to_domain(self, model: DocumentModel) -> Document:
        return Document(
            id=model.id,
            filename=model.filename,
            file_path=model.file_path,
            content_type=model.content_type,
            upload_date=model.upload_date,
            status=DocumentStatus(model.status),
            stage=model.stage,
            source_type=SourceType(model.source_type),
            owner_id=model.owner_id,
            visibility=Visibility(model.visibility),
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _entity_to_domain(self, model: EntityModel) -> Entity:
        return Entity(
            id=model.id,
            name=model.name,
            canonical_name=model.canonical_name,
            type=model.type,
            properties=model.properties or {},
            source_count=model.source_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _relationship_to_domain(self, model: RelationshipModel) -> Relationship:
        return Relationship(
            id=model.id,
            source_entity_id=model.source_entity_id,
            target_entity_id=model.target_entity_id,
            relation_type=model.relation_type,
            description=model.description,
            confidence=model.confidence,
            source_document_id=model.source_document_id,
            extracted_at=model.extracted_at,
        )

    def _chat_session_to_domain(self, model: ChatSessionModel) -> ChatSession:
        return ChatSession(
            id=model.id,
            owner_id=model.owner_id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _chat_message_to_domain(self, model: ChatMessageModel) -> ChatMessage:
        return ChatMessage(
            id=model.id,
            session_id=model.session_id,
            role=MessageRole(model.role),
            content=model.content,
            tool_calls=model.tool_calls,
            tool_call_id=model.tool_call_id,
            created_at=model.created_at,
        )

    # -- Document operations --

    async def save_document(self, document: Document) -> Document:
        async with self._session_factory() as session:
            model = DocumentModel(
                id=document.id,
                filename=document.filename,
                file_path=document.file_path,
                content_type=document.content_type,
                upload_date=document.upload_date,
                status=document.status.value,
                stage=document.stage,
                source_type=document.source_type.value,
                owner_id=document.owner_id,
                visibility=document.visibility.value,
                error_message=document.error_message,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._document_to_domain(model)

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        async with self._session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.id == document_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._document_to_domain(model)

    async def list_documents(self, owner_id: uuid.UUID) -> list[Document]:
        async with self._session_factory() as session:
            stmt = (
                select(DocumentModel)
                .where(DocumentModel.owner_id == owner_id)
                .order_by(DocumentModel.created_at.desc())
            )
            result = await session.execute(stmt)
            return [self._document_to_domain(row) for row in result.scalars().all()]

    async def update_document_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        stage: int | None = None,
        error_message: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.id == document_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.status = status.value
            if stage is not None:
                model.stage = stage
            if error_message is not None:
                model.error_message = error_message
            await session.commit()

    # -- Entity operations --

    async def save_entities(
        self,
        entities: list[Entity],
        document_id: uuid.UUID,
    ) -> list[Entity]:
        if not entities:
            return []

        async with self._session_factory() as session:
            saved: list[Entity] = []
            for entity in entities:
                stmt = pg_insert(EntityModel).values(
                    id=entity.id,
                    name=entity.name,
                    canonical_name=entity.canonical_name,
                    type=entity.type,
                    properties=entity.properties,
                    source_count=entity.source_count,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["canonical_name", "type"],
                    set_={
                        "properties": stmt.excluded.properties,
                        "source_count": (EntityModel.source_count + 1),
                    },
                )
                stmt = stmt.returning(EntityModel.__table__.c.id)
                result = await session.execute(stmt)
                entity_id = result.scalar_one()

                # Create entity–document link
                link_stmt = pg_insert(EntityDocumentModel).values(
                    entity_id=entity_id,
                    document_id=document_id,
                    relationship="extracted_from",
                )
                link_stmt = link_stmt.on_conflict_do_nothing(
                    index_elements=["entity_id", "document_id"],
                )
                await session.execute(link_stmt)

                # Reload the entity to get the merged state
                entity_model = await session.get(EntityModel, entity_id)
                saved.append(self._entity_to_domain(entity_model))

            await session.commit()
            return saved

    async def get_entity(self, entity_id: uuid.UUID) -> Entity | None:
        async with self._session_factory() as session:
            stmt = select(EntityModel).where(EntityModel.id == entity_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._entity_to_domain(model)

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[Entity]:
        async with self._session_factory() as session:
            stmt = select(EntityModel)
            if query:
                ts_query = func.plainto_tsquery("english", query)
                stmt = stmt.where(EntityModel.search_vector.op("@@")(ts_query))
                stmt = stmt.order_by(func.ts_rank(EntityModel.search_vector, ts_query).desc())
            if entity_type:
                stmt = stmt.where(EntityModel.type == entity_type)
            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [self._entity_to_domain(row) for row in result.scalars().all()]

    async def get_entity_relationships(
        self,
        entity_id: uuid.UUID,
    ) -> list[Relationship]:
        async with self._session_factory() as session:
            stmt = select(RelationshipModel).where(
                (RelationshipModel.source_entity_id == entity_id)
                | (RelationshipModel.target_entity_id == entity_id)
            )
            result = await session.execute(stmt)
            return [self._relationship_to_domain(row) for row in result.scalars().all()]

    # -- Relationship operations --

    async def save_relationships(
        self,
        relationships: list[Relationship],
    ) -> list[Relationship]:
        if not relationships:
            return []

        async with self._session_factory() as session:
            models = [
                RelationshipModel(
                    id=rel.id,
                    source_entity_id=rel.source_entity_id,
                    target_entity_id=rel.target_entity_id,
                    relation_type=rel.relation_type,
                    description=rel.description,
                    confidence=rel.confidence,
                    source_document_id=rel.source_document_id,
                    extracted_at=rel.extracted_at,
                )
                for rel in relationships
            ]
            session.add_all(models)
            await session.commit()
            for model in models:
                await session.refresh(model)
            return [self._relationship_to_domain(m) for m in models]

    # -- Chat operations --

    async def create_chat_session(
        self,
        owner_id: uuid.UUID,
        title: str = "New Chat",
    ) -> ChatSession:
        async with self._session_factory() as session:
            model = ChatSessionModel(
                id=uuid.uuid4(),
                owner_id=owner_id,
                title=title,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._chat_session_to_domain(model)

    async def get_chat_sessions(
        self,
        owner_id: uuid.UUID,
    ) -> list[ChatSession]:
        async with self._session_factory() as session:
            stmt = (
                select(ChatSessionModel)
                .where(ChatSessionModel.owner_id == owner_id)
                .order_by(ChatSessionModel.updated_at.desc())
            )
            result = await session.execute(stmt)
            return [self._chat_session_to_domain(row) for row in result.scalars().all()]

    async def get_chat_session(
        self,
        session_id: uuid.UUID,
    ) -> ChatSession | None:
        async with self._session_factory() as session:
            stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._chat_session_to_domain(model)

    async def update_chat_session(
        self,
        session_id: uuid.UUID,
        title: str,
    ) -> None:
        async with self._session_factory() as session:
            stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.title = title
            await session.commit()

    async def delete_chat_session(
        self,
        session_id: uuid.UUID,
    ) -> None:
        async with self._session_factory() as session:
            stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return
            await session.delete(model)
            await session.commit()

    async def save_chat_message(
        self,
        message: ChatMessage,
    ) -> ChatMessage:
        async with self._session_factory() as session:
            model = ChatMessageModel(
                id=message.id,
                session_id=message.session_id,
                role=message.role.value,
                content=message.content,
                tool_calls=message.tool_calls,
                tool_call_id=message.tool_call_id,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._chat_message_to_domain(model)

    async def get_chat_messages(
        self,
        session_id: uuid.UUID,
    ) -> list[ChatMessage]:
        async with self._session_factory() as session:
            stmt = (
                select(ChatMessageModel)
                .where(ChatMessageModel.session_id == session_id)
                .order_by(ChatMessageModel.created_at.asc())
            )
            result = await session.execute(stmt)
            return [self._chat_message_to_domain(row) for row in result.scalars().all()]

    # -- Query operations (for chat agent tools) --

    async def describe_entity_schema(self) -> dict[str, Any]:
        async with self._session_factory() as session:
            stmt = select(
                EntityModel.type,
                func.count(EntityModel.id),
            ).group_by(EntityModel.type)
            result = await session.execute(stmt)
            types: dict[str, Any] = {
                row[0]: {"count": row[1], "properties": {}} for row in result.all()
            }

            for entity_type in types:
                prop_stmt = (
                    select(EntityModel.properties).where(EntityModel.type == entity_type).limit(50)
                )
                prop_result = await session.execute(prop_stmt)
                props: dict[str, Any] = {}
                for row in prop_result.scalars().all():
                    if row:
                        for key, value in row.items():
                            if key not in props:
                                props[key] = _describe_property(value)
                            elif isinstance(value, (int, float)):
                                _update_numeric_range(props[key], value)
                            elif isinstance(value, str) and key in props:
                                _collect_sample_value(props[key], value)
                types[entity_type]["properties"] = props

            return types

    async def query_entities(
        self,
        entity_type: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int = 20,
    ) -> list[Entity]:
        async with self._session_factory() as session:
            stmt = select(EntityModel)

            if entity_type:
                stmt = stmt.where(EntityModel.type == entity_type)

            if filters:
                conditions = self._build_filter_conditions(filters)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            if sort_by:
                json_val = EntityModel.properties[sort_by].astext
                sort_expr = cast(json_val, Float)
                if sort_order == "desc":
                    sort_expr = sort_expr.desc()
                stmt = stmt.order_by(sort_expr)

            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [self._entity_to_domain(row) for row in result.scalars().all()]

    def _build_filter_conditions(self, filters: list[dict[str, Any]]) -> list:
        """Build SQLAlchemy WHERE clauses from JSONB filter dicts."""
        conditions = []
        for f in filters:
            prop = f.get("property", "")
            operator = f.get("operator", "=")
            value = f.get("value")

            if operator not in ALLOWED_FILTER_OPERATORS:
                continue

            json_text = EntityModel.properties[prop].astext

            if operator in {"=", "!=", ">", "<", ">=", "<="}:
                is_numeric = isinstance(value, (int, float)) or (
                    isinstance(value, str) and _is_numeric_string(value)
                )
                if is_numeric:
                    column_expr = cast(json_text, Float)
                    compare_value = float(value)
                    condition = _comparison(column_expr, operator, compare_value)
                elif operator in {"=", "!="}:
                    column_expr = func.lower(cast(json_text, String))
                    compare_value = str(value).lower()
                    condition = _comparison(column_expr, operator, compare_value)
                else:
                    column_expr = cast(json_text, String)
                    compare_value = str(value)
                    condition = _comparison(column_expr, operator, compare_value)
            elif operator == "contains":
                condition = json_text.contains(str(value))
            elif operator == "like":
                condition = json_text.like(str(value))
            else:
                continue

            conditions.append(condition)
        return conditions

    async def aggregate_entities(
        self,
        entity_type: str | None = None,
        property_name: str | None = None,
        operation: str = "count",
        group_by: str | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if operation not in ALLOWED_AGGREGATE_OPERATIONS:
            return []

        async with self._session_factory() as session:
            agg_expr = _aggregate_expression(operation, property_name)
            columns = [agg_expr.label("value")]

            if group_by:
                group_col = EntityModel.properties[group_by].astext.label("group_key")
                columns.insert(0, group_col)

            stmt = select(*columns)

            if entity_type:
                stmt = stmt.where(EntityModel.type == entity_type)

            if filters:
                conditions = self._build_filter_conditions(filters)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            if group_by:
                stmt = stmt.group_by(group_col)

            result = await session.execute(stmt)
            rows = result.all()

            if group_by:
                return [{"group": row.group_key, "value": row.value} for row in rows]
            return [{"value": rows[0].value}] if rows else []


def _comparison(column, operator: str, value):
    """Return a SQLAlchemy comparison expression."""
    ops = {
        "=": column.__eq__,
        "!=": column.__ne__,
        ">": column.__gt__,
        "<": column.__lt__,
        ">=": column.__ge__,
        "<=": column.__le__,
    }
    return ops[operator](value)


def _aggregate_expression(operation: str, property_name: str | None):
    """Return the appropriate SQLAlchemy aggregate function."""
    if operation == "count":
        return func.count(EntityModel.id)

    if property_name is None:
        return func.count(EntityModel.id)

    numeric_col = cast(EntityModel.properties[property_name].astext, Float)
    agg_funcs = {
        "avg": func.avg,
        "sum": func.sum,
        "min": func.min,
        "max": func.max,
    }
    return agg_funcs[operation](numeric_col)

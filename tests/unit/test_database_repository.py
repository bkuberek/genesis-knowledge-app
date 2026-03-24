"""Unit tests for DatabaseRepository — domain conversion and construction."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import async_sessionmaker

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
from knowledge_workers.adapters.database_repository import (
    DatabaseRepository,
    _is_numeric_string,
)
from knowledge_workers.adapters.models.chat_message_model import (
    ChatMessageModel,
)
from knowledge_workers.adapters.models.chat_session_model import (
    ChatSessionModel,
)
from knowledge_workers.adapters.models.document_model import DocumentModel
from knowledge_workers.adapters.models.entity_model import EntityModel
from knowledge_workers.adapters.models.relationship_model import (
    RelationshipModel,
)


def _make_session_factory():
    """Create a mock async_sessionmaker for constructor injection."""
    return MagicMock(spec=async_sessionmaker)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TestRepositoryConstruction:
    def test_requires_session_factory(self):
        factory = _make_session_factory()
        repo = DatabaseRepository(session_factory=factory)
        assert repo._session_factory is factory

    def test_implements_port_interface(self):
        from knowledge_core.ports.database_repository_port import (
            DatabaseRepositoryPort,
        )

        factory = _make_session_factory()
        repo = DatabaseRepository(session_factory=factory)
        assert isinstance(repo, DatabaseRepositoryPort)


class TestDocumentToDomainConversion:
    def test_converts_all_fields(self):
        now = _utcnow()
        model = DocumentModel(
            id=uuid.uuid4(),
            filename="report.pdf",
            file_path="/uploads/report.pdf",
            content_type="application/pdf",
            upload_date=now,
            status="complete",
            stage=3,
            source_type="file",
            owner_id=uuid.uuid4(),
            visibility="public",
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._document_to_domain(model)

        assert isinstance(domain, Document)
        assert domain.id == model.id
        assert domain.filename == "report.pdf"
        assert domain.file_path == "/uploads/report.pdf"
        assert domain.content_type == "application/pdf"
        assert domain.status == DocumentStatus.COMPLETE
        assert domain.stage == 3
        assert domain.source_type == SourceType.FILE
        assert domain.owner_id == model.owner_id
        assert domain.visibility == Visibility.PUBLIC
        assert domain.error_message is None

    def test_converts_queued_status(self):
        now = _utcnow()
        model = DocumentModel(
            id=uuid.uuid4(),
            filename="test.txt",
            file_path=None,
            content_type=None,
            upload_date=now,
            status="queued",
            stage=0,
            source_type="url",
            owner_id=uuid.uuid4(),
            visibility="private",
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._document_to_domain(model)

        assert domain.status == DocumentStatus.QUEUED
        assert domain.source_type == SourceType.URL
        assert domain.visibility == Visibility.PRIVATE

    def test_converts_error_status_with_message(self):
        now = _utcnow()
        model = DocumentModel(
            id=uuid.uuid4(),
            filename="bad.pdf",
            file_path=None,
            content_type=None,
            upload_date=now,
            status="error",
            stage=2,
            source_type="file",
            owner_id=uuid.uuid4(),
            visibility="private",
            error_message="Parse failed",
            created_at=now,
            updated_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._document_to_domain(model)

        assert domain.status == DocumentStatus.ERROR
        assert domain.error_message == "Parse failed"


class TestEntityToDomainConversion:
    def test_converts_all_fields(self):
        now = _utcnow()
        model = EntityModel(
            id=uuid.uuid4(),
            name="Apple Inc.",
            canonical_name="apple_inc",
            type="organization",
            properties={"sector": "tech", "founded": 1976},
            source_count=5,
            created_at=now,
            updated_at=now,
            search_vector=None,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._entity_to_domain(model)

        assert isinstance(domain, Entity)
        assert domain.id == model.id
        assert domain.name == "Apple Inc."
        assert domain.canonical_name == "apple_inc"
        assert domain.type == "organization"
        assert domain.properties == {
            "sector": "tech",
            "founded": 1976,
        }
        assert domain.source_count == 5

    def test_converts_empty_properties(self):
        now = _utcnow()
        model = EntityModel(
            id=uuid.uuid4(),
            name="Test",
            canonical_name="test",
            type="concept",
            properties=None,
            source_count=1,
            created_at=now,
            updated_at=now,
            search_vector=None,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._entity_to_domain(model)

        assert domain.properties == {}


class TestRelationshipToDomainConversion:
    def test_converts_all_fields(self):
        now = _utcnow()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        model = RelationshipModel(
            id=uuid.uuid4(),
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type="works_at",
            description="Employee relationship",
            confidence=0.85,
            source_document_id=doc_id,
            extracted_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._relationship_to_domain(model)

        assert isinstance(domain, Relationship)
        assert domain.id == model.id
        assert domain.source_entity_id == source_id
        assert domain.target_entity_id == target_id
        assert domain.relation_type == "works_at"
        assert domain.description == "Employee relationship"
        assert domain.confidence == 0.85
        assert domain.source_document_id == doc_id

    def test_converts_minimal_relationship(self):
        now = _utcnow()
        model = RelationshipModel(
            id=uuid.uuid4(),
            source_entity_id=uuid.uuid4(),
            target_entity_id=uuid.uuid4(),
            relation_type="related_to",
            description=None,
            confidence=1.0,
            source_document_id=None,
            extracted_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._relationship_to_domain(model)

        assert domain.description is None
        assert domain.source_document_id is None
        assert domain.confidence == 1.0


class TestChatSessionToDomainConversion:
    def test_converts_all_fields(self):
        now = _utcnow()
        owner_id = uuid.uuid4()
        model = ChatSessionModel(
            id=uuid.uuid4(),
            owner_id=owner_id,
            title="Research Notes",
            created_at=now,
            updated_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._chat_session_to_domain(model)

        assert isinstance(domain, ChatSession)
        assert domain.id == model.id
        assert domain.owner_id == owner_id
        assert domain.title == "Research Notes"


class TestChatMessageToDomainConversion:
    def test_converts_user_message(self):
        now = _utcnow()
        model = ChatMessageModel(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role="user",
            content="Hello world",
            tool_calls=None,
            tool_call_id=None,
            created_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._chat_message_to_domain(model)

        assert isinstance(domain, ChatMessage)
        assert domain.id == model.id
        assert domain.role == MessageRole.USER
        assert domain.content == "Hello world"
        assert domain.tool_calls is None
        assert domain.tool_call_id is None

    def test_converts_assistant_message_with_tool_calls(self):
        now = _utcnow()
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "search",
                    "arguments": "{}",
                },
            }
        ]
        model = ChatMessageModel(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role="assistant",
            content="Let me search.",
            tool_calls=tool_calls,
            tool_call_id=None,
            created_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._chat_message_to_domain(model)

        assert domain.role == MessageRole.ASSISTANT
        assert domain.tool_calls == tool_calls

    def test_converts_tool_message(self):
        now = _utcnow()
        model = ChatMessageModel(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role="tool",
            content='{"result": "found 5 items"}',
            tool_calls=None,
            tool_call_id="call_1",
            created_at=now,
        )
        repo = DatabaseRepository(session_factory=_make_session_factory())
        domain = repo._chat_message_to_domain(model)

        assert domain.role == MessageRole.TOOL
        assert domain.tool_call_id == "call_1"


class TestFilterConditions:
    def test_rejects_invalid_operator(self):
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "name",
                "operator": "DROP TABLE",
                "value": "x",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert conditions == []

    def test_builds_equality_condition(self):
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "sector",
                "operator": "=",
                "value": "tech",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1

    def test_builds_numeric_comparison(self):
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "revenue",
                "operator": ">",
                "value": 500,
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1

    def test_builds_multiple_conditions(self):
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "sector",
                "operator": "=",
                "value": "tech",
            },
            {
                "property": "revenue",
                "operator": ">=",
                "value": 100.0,
            },
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 2

    def test_skips_invalid_mixed_with_valid(self):
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "name",
                "operator": "=",
                "value": "foo",
            },
            {
                "property": "x",
                "operator": "INVALID",
                "value": "y",
            },
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1

    def test_string_numeric_value_produces_float_cast(self):
        """LLM may send '2020' instead of 2020 — should still use Float cast."""
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "founding_year",
                "operator": ">",
                "value": "2020",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1
        compiled = str(conditions[0])
        assert "FLOAT" in compiled.upper()

    def test_float_string_value_produces_float_cast(self):
        """Decimal strings like '3.14' should also use Float cast."""
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "growth_rate",
                "operator": ">=",
                "value": "3.14",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1
        compiled = str(conditions[0])
        assert "FLOAT" in compiled.upper()

    def test_non_numeric_string_stays_as_string_cast(self):
        """Non-numeric strings like 'fintech' should use String cast."""
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "industry_vertical",
                "operator": "=",
                "value": "fintech",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1
        compiled = str(conditions[0])
        assert "VARCHAR" in compiled.upper() or "TEXT" in compiled.upper()
        assert "FLOAT" not in compiled.upper()

    def test_mixed_alphanumeric_stays_as_string(self):
        """Mixed alphanumeric like 'abc123' should not be treated as numeric."""
        repo = DatabaseRepository(session_factory=_make_session_factory())
        filters = [
            {
                "property": "code",
                "operator": "=",
                "value": "abc123",
            }
        ]
        conditions = repo._build_filter_conditions(filters)
        assert len(conditions) == 1
        compiled = str(conditions[0])
        assert "FLOAT" not in compiled.upper()


class TestIsNumericString:
    def test_integer_string(self):
        assert _is_numeric_string("2020") is True

    def test_float_string(self):
        assert _is_numeric_string("3.14") is True

    def test_negative_string(self):
        assert _is_numeric_string("-42") is True

    def test_non_numeric(self):
        assert _is_numeric_string("fintech") is False

    def test_mixed_alphanumeric(self):
        assert _is_numeric_string("abc123") is False

    def test_empty_string(self):
        assert _is_numeric_string("") is False

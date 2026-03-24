import uuid

import pytest
from pydantic import ValidationError

from knowledge_core.domain.chat_message import ChatMessage, MessageRole
from knowledge_core.domain.chat_session import ChatSession
from knowledge_core.domain.document import (
    Document,
    DocumentStatus,
    SourceType,
    Visibility,
)
from knowledge_core.domain.entity import Entity
from knowledge_core.domain.entity_document import EntityDocument
from knowledge_core.domain.relationship import Relationship
from knowledge_core.domain.user import User

# --- Document tests ---


class TestDocument:
    def test_create_document_with_defaults(self):
        owner = uuid.uuid4()
        doc = Document(filename="report.pdf", owner_id=owner)

        assert doc.id is not None
        assert doc.filename == "report.pdf"
        assert doc.file_path is None
        assert doc.content_type is None
        assert doc.status == DocumentStatus.QUEUED
        assert doc.stage == 0
        assert doc.source_type == SourceType.FILE
        assert doc.owner_id == owner
        assert doc.visibility == Visibility.PRIVATE
        assert doc.error_message is None
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_document_status_enum_values(self):
        assert DocumentStatus.QUEUED == "queued"
        assert DocumentStatus.PROCESSING == "processing"
        assert DocumentStatus.COMPLETE == "complete"
        assert DocumentStatus.ERROR == "error"

    def test_document_source_type_enum_values(self):
        assert SourceType.FILE == "file"
        assert SourceType.URL == "url"

    def test_document_visibility_enum_values(self):
        assert Visibility.PRIVATE == "private"
        assert Visibility.PUBLIC == "public"

    def test_document_stage_validation_rejects_negative(self):
        with pytest.raises(ValidationError):
            Document(filename="test.pdf", owner_id=uuid.uuid4(), stage=-1)

    def test_document_stage_validation_rejects_over_five(self):
        with pytest.raises(ValidationError):
            Document(filename="test.pdf", owner_id=uuid.uuid4(), stage=6)

    def test_document_accepts_valid_stage_boundaries(self):
        owner = uuid.uuid4()
        doc_zero = Document(filename="a.pdf", owner_id=owner, stage=0)
        doc_five = Document(filename="b.pdf", owner_id=owner, stage=5)
        assert doc_zero.stage == 0
        assert doc_five.stage == 5

    def test_document_with_all_fields(self):
        owner = uuid.uuid4()
        doc = Document(
            filename="data.csv",
            file_path="/uploads/data.csv",
            content_type="text/csv",
            status=DocumentStatus.COMPLETE,
            stage=5,
            source_type=SourceType.URL,
            owner_id=owner,
            visibility=Visibility.PUBLIC,
            error_message=None,
        )
        assert doc.file_path == "/uploads/data.csv"
        assert doc.content_type == "text/csv"
        assert doc.status == DocumentStatus.COMPLETE
        assert doc.source_type == SourceType.URL
        assert doc.visibility == Visibility.PUBLIC


# --- Entity tests ---


class TestEntity:
    def test_create_entity_with_properties(self):
        entity = Entity(
            name="Apple Inc.",
            canonical_name="apple_inc",
            type="organization",
            properties={"sector": "tech", "founded": 1976},
        )
        assert entity.name == "Apple Inc."
        assert entity.canonical_name == "apple_inc"
        assert entity.type == "organization"
        assert entity.properties == {"sector": "tech", "founded": 1976}
        assert entity.source_count == 1
        assert entity.id is not None

    def test_entity_defaults(self):
        entity = Entity(
            name="Test",
            canonical_name="test",
            type="concept",
        )
        assert entity.properties == {}
        assert entity.source_count == 1

    def test_entity_source_count_minimum_one(self):
        with pytest.raises(ValidationError):
            Entity(
                name="Bad",
                canonical_name="bad",
                type="concept",
                source_count=0,
            )


# --- Relationship tests ---


class TestRelationship:
    def test_create_relationship_with_defaults(self):
        source = uuid.uuid4()
        target = uuid.uuid4()
        rel = Relationship(
            source_entity_id=source,
            target_entity_id=target,
            relation_type="works_at",
        )
        assert rel.source_entity_id == source
        assert rel.target_entity_id == target
        assert rel.relation_type == "works_at"
        assert rel.confidence == 1.0
        assert rel.description is None
        assert rel.source_document_id is None
        assert rel.id is not None

    def test_relationship_confidence_range(self):
        source = uuid.uuid4()
        target = uuid.uuid4()
        rel_zero = Relationship(
            source_entity_id=source,
            target_entity_id=target,
            relation_type="test",
            confidence=0.0,
        )
        rel_one = Relationship(
            source_entity_id=source,
            target_entity_id=target,
            relation_type="test",
            confidence=1.0,
        )
        rel_mid = Relationship(
            source_entity_id=source,
            target_entity_id=target,
            relation_type="test",
            confidence=0.75,
        )
        assert rel_zero.confidence == 0.0
        assert rel_one.confidence == 1.0
        assert rel_mid.confidence == 0.75

    def test_relationship_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            Relationship(
                source_entity_id=uuid.uuid4(),
                target_entity_id=uuid.uuid4(),
                relation_type="test",
                confidence=-0.1,
            )

    def test_relationship_rejects_over_one_confidence(self):
        with pytest.raises(ValidationError):
            Relationship(
                source_entity_id=uuid.uuid4(),
                target_entity_id=uuid.uuid4(),
                relation_type="test",
                confidence=1.5,
            )


# --- EntityDocument tests ---


class TestEntityDocument:
    def test_create_entity_document_with_defaults(self):
        entity_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        ed = EntityDocument(entity_id=entity_id, document_id=doc_id)
        assert ed.entity_id == entity_id
        assert ed.document_id == doc_id
        assert ed.relationship == "extracted_from"

    def test_entity_document_custom_relationship(self):
        ed = EntityDocument(
            entity_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            relationship="mentioned_in",
        )
        assert ed.relationship == "mentioned_in"


# --- ChatSession tests ---


class TestChatSession:
    def test_create_chat_session_with_defaults(self):
        owner = uuid.uuid4()
        session = ChatSession(owner_id=owner)
        assert session.id is not None
        assert session.owner_id == owner
        assert session.title == "New Chat"
        assert session.created_at is not None

    def test_chat_session_custom_title(self):
        session = ChatSession(owner_id=uuid.uuid4(), title="Research Notes")
        assert session.title == "Research Notes"


# --- ChatMessage tests ---


class TestChatMessage:
    def test_create_chat_message_with_defaults(self):
        session_id = uuid.uuid4()
        msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content="Hello, world!",
        )
        assert msg.id is not None
        assert msg.session_id == session_id
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, world!"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_chat_message_with_tool_calls(self):
        tool_calls = [{"id": "call_1", "function": {"name": "search", "arguments": "{}"}}]
        msg = ChatMessage(
            session_id=uuid.uuid4(),
            role=MessageRole.ASSISTANT,
            content="Let me search for that.",
            tool_calls=tool_calls,
        )
        assert msg.tool_calls == tool_calls
        assert len(msg.tool_calls) == 1

    def test_message_role_enum_values(self):
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"


# --- User tests ---


class TestUser:
    def test_user_is_value_object(self):
        """User is a simple value object resolved from JWT, not persisted."""
        user = User(
            id=uuid.uuid4(),
            email="alice@example.com",
            name="Alice",
        )
        assert user.email == "alice@example.com"
        assert user.name == "Alice"

    def test_user_name_defaults_to_empty(self):
        user = User(id=uuid.uuid4(), email="bob@example.com")
        assert user.name == ""

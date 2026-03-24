"""Initial schema: tables, indexes, tsvector trigger, and RLS policies.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- documents ---
    op.create_table(
        "documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column(
            "upload_date",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "stage",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "source_type",
            sa.String(),
            nullable=False,
            server_default="file",
        ),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "visibility",
            sa.String(),
            nullable=False,
            server_default="private",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])

    # --- entities ---
    op.create_table(
        "entities",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "properties",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("ALTER TABLE entities ADD COLUMN search_vector tsvector")

    op.create_index(
        "ix_entities_properties",
        "entities",
        ["properties"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_entities_search_vector",
        "entities",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_entities_canonical_name_type",
        "entities",
        ["canonical_name", "type"],
        unique=True,
    )

    # --- relationships ---
    op.create_table(
        "relationships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "source_entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "source_document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column(
            "extracted_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- entity_documents ---
    op.create_table(
        "entity_documents",
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            primary_key=True,
        ),
        sa.Column(
            "relationship",
            sa.String(),
            nullable=False,
            server_default="extracted_from",
        ),
    )

    # --- chat_sessions ---
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "title",
            sa.String(),
            nullable=False,
            server_default="New Chat",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_sessions_owner_id",
        "chat_sessions",
        ["owner_id"],
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", JSONB(), nullable=True),
        sa.Column("tool_call_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_messages_session_id",
        "chat_messages",
        ["session_id"],
    )

    # --- tsvector trigger for entities.search_vector ---
    op.execute("""
        CREATE OR REPLACE FUNCTION entities_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                to_tsvector('english', COALESCE(NEW.name, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER entities_search_vector_trigger
            BEFORE INSERT OR UPDATE OF name ON entities
            FOR EACH ROW
            EXECUTE FUNCTION entities_search_vector_update()
    """)

    # --- Row-Level Security: documents ---
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY documents_owner_policy ON documents
            USING (
                owner_id::text
                    = current_setting('app.current_user_id', true)
                OR visibility = 'public'
            )
    """)

    # --- Row-Level Security: entities ---
    op.execute("ALTER TABLE entities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE entities FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY entities_visibility_policy ON entities
            USING (
                EXISTS (
                    SELECT 1 FROM entity_documents ed
                    JOIN documents d ON d.id = ed.document_id
                    WHERE ed.entity_id = entities.id
                    AND (
                        d.owner_id::text
                            = current_setting(
                                'app.current_user_id', true
                            )
                        OR d.visibility = 'public'
                    )
                )
            )
    """)

    # --- Row-Level Security: chat_sessions ---
    op.execute("ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_sessions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY chat_sessions_owner_policy ON chat_sessions
            USING (
                owner_id::text
                    = current_setting('app.current_user_id', true)
            )
    """)

    # --- Row-Level Security: chat_messages ---
    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_messages FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY chat_messages_session_policy ON chat_messages
            USING (
                session_id IN (
                    SELECT id FROM chat_sessions
                    WHERE owner_id::text
                        = current_setting(
                            'app.current_user_id', true
                        )
                )
            )
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS chat_messages_session_policy ON chat_messages")
    op.execute("DROP POLICY IF EXISTS chat_sessions_owner_policy ON chat_sessions")
    op.execute("DROP POLICY IF EXISTS entities_visibility_policy ON entities")
    op.execute("DROP POLICY IF EXISTS documents_owner_policy ON documents")

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS entities_search_vector_trigger ON entities")
    op.execute("DROP FUNCTION IF EXISTS entities_search_vector_update()")

    # Drop tables in reverse FK order
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("entity_documents")
    op.drop_table("relationships")
    op.drop_table("entities")
    op.drop_table("documents")

"""Create the Phase 1 persistence schema and pgvector extension."""
from alembic import op
import sqlalchemy as sa

revision = "0001_foundation_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table("sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("label", sa.String(200), nullable=False, server_default="New conversation"), sa.Column("owner_label", sa.String(120)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("transcripts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("source_key", sa.String(255), nullable=False, unique=True), sa.Column("episode_title", sa.String(500), nullable=False), sa.Column("guest_name", sa.String(300)), sa.Column("publish_date", sa.Date()), sa.Column("source_url", sa.Text(), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.execute("""
        CREATE TABLE chunks (
            id UUID PRIMARY KEY,
            transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            CONSTRAINT uq_chunks_transcript_position UNIQUE (transcript_id, position)
        )
    """)
    op.create_table("messages", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("provider", sa.String(50)), sa.Column("model_name", sa.String(150)), sa.Column("latency_ms", sa.Integer()), sa.Column("token_count", sa.Integer()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("citations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("message_id", sa.Uuid(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False), sa.Column("chunk_id", sa.Uuid(), sa.ForeignKey("chunks.id", ondelete="RESTRICT"), nullable=False), sa.Column("episode_title", sa.String(500), nullable=False), sa.Column("guest_name", sa.String(300)), sa.Column("source_url", sa.Text(), nullable=False))
    op.create_table("artifacts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("message_id", sa.Uuid(), sa.ForeignKey("messages.id", ondelete="SET NULL")), sa.Column("type", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("citations")
    op.drop_table("messages")
    op.drop_table("chunks")
    op.drop_table("transcripts")
    op.drop_table("sessions")

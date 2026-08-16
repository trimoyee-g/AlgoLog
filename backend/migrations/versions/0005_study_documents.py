"""add documents + chunks for study-material RAG

Study material (uploaded PDFs) lives in the same database as everything else — not
to rank it against problems.embedding (nothing joins the two corpora), but so the
chunks get real foreign keys, a cascading delete from documents, and an ingest that
commits the document and its vectors in one transaction.

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.config import settings

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.EMBEDDING_DIM), nullable=True),
    )
    op.create_index("ix_chunks_id", "chunks", ["id"])
    op.create_index("ix_chunks_user", "chunks", ["user_id"])
    # No ivfflat index: it needs training data to be worth anything and hurts
    # recall below ~50k rows. Add one when a real corpus makes search measurably slow.


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")

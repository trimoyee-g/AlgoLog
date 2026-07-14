"""baseline: the schema as create_all() shipped it

This revision reproduces exactly what the old `Base.metadata.create_all()` +
lifespan DDL produced, ivfflat index included. It exists so an already-running
deploy can adopt Alembic without recreating anything:

    alembic stamp 0001 && alembic upgrade head

A fresh database just runs it normally.

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Migrations are static by definition: a change to settings.EMBEDDING_DIM needs
# its own revision to rewrite the column, not a silently-different baseline.
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("leetcode", "codeforces", "codechef", "atcoder", "gfg", "other", name="platform"),
            nullable=False,
        ),
        sa.Column("official_difficulty", sa.String(), nullable=True),
        sa.Column("tags", sa.String(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "url", name="uq_problem_user_url"),
    )
    op.create_index("ix_problems_id", "problems", ["id"])
    op.create_index("ix_problems_user_id", "problems", ["user_id"])
    op.create_index("ix_problems_url", "problems", ["url"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("solved_self", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempts_id", "attempts", ["id"])
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])

    # The ANN index the old lifespan created on every boot. 0002 removes it —
    # it's reproduced here only so `stamp 0001` describes a real deploy truthfully.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_problems_embedding ON problems "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("attempts")
    op.drop_table("problems")
    op.drop_table("users")
    sa.Enum(name="platform").drop(op.get_bind(), checkfirst=True)

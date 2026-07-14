"""multi-user: drop the ivfflat index, index the hot attempt query, add digest claims

Three changes, all of which only start mattering once there is more than one user:

1. Drop ix_problems_embedding. An ivfflat index probes a fixed number of lists
   and *then* applies the WHERE clause. Every similarity query filters
   `user_id = :me`, so as the table fills with other users' rows, an ever-larger
   share of each probe's candidates get discarded by that filter — and a user
   silently gets back fewer than `limit` neighbours, or none. Exact search over
   one user's few hundred problems is sub-millisecond and exactly correct.

2. Index attempts (user_id, created_at). topic_rates() and the digest's
   _stats_window() both filter on precisely that pair; without it they scan
   every user's attempts to answer a question about one user's.

3. digest_sends: one row per user per ISO week, claimed by insert. Makes the
   weekly digest at-most-once even though every replica fires the cron.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_problems_embedding")

    op.create_index("ix_attempts_user_created", "attempts", ["user_id", "created_at"])

    op.create_table(
        "digest_sends",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("week", sa.String(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "week"),
    )


def downgrade() -> None:
    op.drop_table("digest_sends")
    op.drop_index("ix_attempts_user_created", table_name="attempts")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_problems_embedding ON problems "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

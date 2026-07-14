"""reconcile create_all-era databases with the models

Databases grown by the old `Base.metadata.create_all()` carry columns from model
versions that no longer exist — create_all only ever CREATEs, so a removed column
lingers forever. Neither is referenced anywhere in the codebase:

    attempts.time_taken_minutes   (dropped from the model; was never populated)
    problems.description_snippet  (dropped from the model)

and `problems.tags` stayed NULLable there even though the model says NOT NULL.

Written to be idempotent: a database created *by* these migrations never had any
of this, so every statement below is a no-op on a fresh DB and this revision is
safe to run anywhere. That's what makes `alembic check` usable as a drift guard.

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE attempts DROP COLUMN IF EXISTS time_taken_minutes")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS description_snippet")

    # SET NOT NULL fails outright if any row is NULL, so give those rows the
    # empty string the model would have written anyway.
    op.execute("UPDATE problems SET tags = '' WHERE tags IS NULL")
    op.alter_column("problems", "tags", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    # The dropped columns are gone for good — recreating them empty is the most
    # honest reversal available, and matches what a legacy DB would look like
    # with no data ever written back into them.
    op.alter_column("problems", "tags", existing_type=sa.String(), nullable=True)
    op.add_column("problems", sa.Column("description_snippet", sa.Text(), nullable=True))
    op.add_column("attempts", sa.Column("time_taken_minutes", sa.Integer(), nullable=True))

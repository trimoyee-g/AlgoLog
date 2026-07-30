"""drop problems.official_difficulty

The column was plumbed end to end — model, request/response schemas, TS types,
table cell — but nothing ever wrote a value into it. The only producer is the
browser extension, and it hardcoded `official_difficulty: null` on every POST;
no platform scraping was ever implemented. Every row is NULL, so there is no
data to preserve.

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS official_difficulty")


def downgrade() -> None:
    op.add_column("problems", sa.Column("official_difficulty", sa.String(), nullable=True))

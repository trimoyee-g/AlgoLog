"""add page number to chunks

Chunks are made by splitting each PDF page independently (app/services/documents.py),
so the source page is known at ingest time and worth keeping — it lets answers cite
a page instead of just a chunk ordinal.

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("page", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "page")

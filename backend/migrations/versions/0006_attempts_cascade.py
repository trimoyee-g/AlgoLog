"""cascade attempts when their problem is deleted

DELETE /problems/{id} used to load the problem, load its attempts, delete each
one, then delete the problem — four round trips to express one statement. Moving
the cascade from the ORM relationship to the FK lets the endpoint issue a single
DELETE and read the row count as the 404 check.

The constraint 0001 created was unnamed, so Postgres called it
attempts_problem_id_fkey; it is recreated here under that same name.

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE attempts DROP CONSTRAINT IF EXISTS attempts_problem_id_fkey")
    op.create_foreign_key("attempts_problem_id_fkey", "attempts", "problems",
                          ["problem_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("attempts_problem_id_fkey", "attempts", type_="foreignkey")
    op.create_foreign_key("attempts_problem_id_fkey", "attempts", "problems",
                          ["problem_id"], ["id"])

"""[4]: add created_by_id to orders

Revision ID: 01e6fb5c903e
Revises: 3afa6f8ee004
Create Date: 2026-06-20 14:58:58.938710

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "01e6fb5c903e"
down_revision: Union[str, None] = "3afa6f8ee004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())

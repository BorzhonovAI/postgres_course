"""[3]: set default 0 for order

Revision ID: 804b7e3d7219
Revises: eef814199b97
Create Date: 2026-06-12 18:34:41.408858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '804b7e3d7219'
down_revision: Union[str, None] = 'eef814199b97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
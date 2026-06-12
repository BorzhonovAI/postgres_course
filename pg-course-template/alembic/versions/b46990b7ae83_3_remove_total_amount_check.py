"""[3]: remove total_amount check

Revision ID: b46990b7ae83
Revises: 8553ed3d57f6
Create Date: 2026-06-12 20:52:20.129977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b46990b7ae83'
down_revision: Union[str, None] = '8553ed3d57f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
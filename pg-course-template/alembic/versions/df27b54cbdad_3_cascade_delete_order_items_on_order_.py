"""[3]: cascade delete order items on order delete

Revision ID: df27b54cbdad
Revises: b46990b7ae83
Create Date: 2026-06-12 22:04:03.616112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df27b54cbdad'
down_revision: Union[str, None] = 'b46990b7ae83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
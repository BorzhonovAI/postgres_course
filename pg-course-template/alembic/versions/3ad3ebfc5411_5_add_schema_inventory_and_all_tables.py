"""[5]: add schema inventory and all tables

Revision ID: 3ad3ebfc5411
Revises: e34dcb9ce90d
Create Date: 2026-06-23 22:28:00.230546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3ad3ebfc5411'
down_revision: Union[str, None] = 'e1e6ad3fb326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())

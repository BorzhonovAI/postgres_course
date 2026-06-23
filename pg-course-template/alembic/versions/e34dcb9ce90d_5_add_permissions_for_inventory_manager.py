"""[5]: add permissions for inventory_manager

Revision ID: e34dcb9ce90d
Revises: e1e6ad3fb326
Create Date: 2026-06-23 22:09:57.672959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e34dcb9ce90d'
down_revision: Union[str, None] = '3ad3ebfc5411'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())

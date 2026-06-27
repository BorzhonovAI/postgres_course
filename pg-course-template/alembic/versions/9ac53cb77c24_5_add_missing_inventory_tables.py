"""[5]: add missing inventory tables

Revision ID: 9ac53cb77c24
Revises: e34dcb9ce90d
Create Date: 2026-06-27 18:05:49.984839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ac53cb77c24'
down_revision: Union[str, None] = 'e34dcb9ce90d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
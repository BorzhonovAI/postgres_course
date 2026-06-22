"""[4]: grant permissions for new roles

Revision ID: 3afa6f8ee004
Revises: 2117aa704145
Create Date: 2026-06-16 23:11:03.867329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3afa6f8ee004'
down_revision: Union[str, None] = '2117aa704145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())
"""[5]: add catalog.cities

Revision ID: e1e6ad3fb326
Revises: 01e6fb5c903e
Create Date: 2026-06-22 22:08:44.964915

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1e6ad3fb326'
down_revision: Union[str, None] = '01e6fb5c903e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open(f"alembic/sql/{revision}/up.sql") as file:
        op.execute(file.read())


def downgrade() -> None:
    with open(f"alembic/sql/{revision}/down.sql") as file:
        op.execute(file.read())